from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import Settings
from .models import Activation, AuditEvent, License, Organization, utc_now
from .signing import sign_claims


LOGGER = logging.getLogger("license_server.service")


def aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class ServiceError(RuntimeError):
    code: str
    message: str
    status_code: int = 400

    def __str__(self) -> str:
        return self.message


def generate_license_key() -> str:
    value = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
    return "COPRO-" + "-".join(value[index:index + 4] for index in range(0, len(value), 4))


def digest_secret(secret: str, pepper: str) -> str:
    return hmac.new(pepper.encode("utf-8"), secret.encode("utf-8"), hashlib.sha256).hexdigest()


class LicenseService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _audit(self, session: Session, event: str, license_id: str | None, activation_id: str | None, **details) -> None:
        session.add(AuditEvent(event_type=event, license_id=license_id, activation_id=activation_id, details=json.dumps(details)))

    def _license_by_key(self, session: Session, key: str) -> License:
        digest = digest_secret(key.strip().upper(), self.settings.key_pepper)
        license_record = session.scalar(select(License).where(License.key_digest == digest))
        if license_record is None:
            raise ServiceError("invalid_key", "Clé de licence inconnue.", 404)
        return license_record

    @staticmethod
    def _validate_license(license_record: License, now: datetime) -> None:
        if license_record.status == "revoked":
            raise ServiceError("revoked", "Cette licence a été révoquée.", 403)
        if license_record.status != "active":
            raise ServiceError("inactive", "Cette licence n'est pas active.", 403)
        if aware(license_record.commercial_expires_at) < now:
            raise ServiceError("expired", "Cette licence est arrivée à expiration.", 403)

    def _verify_activation_secret(self, activation: Activation, secret: str) -> None:
        expected = digest_secret(secret, self.settings.key_pepper)
        if not hmac.compare_digest(expected, activation.secret_digest):
            raise ServiceError("invalid_activation", "Activation non reconnue.", 403)

    def _issue(self, license_record: License, activation: Activation, now: datetime) -> str:
        lease_expiry = min(now + timedelta(days=self.settings.lease_days), aware(license_record.commercial_expires_at))
        claims = {
            "license_id": license_record.id,
            "activation_id": activation.id,
            "device_hash": activation.device_hash,
            "plan": license_record.plan,
            "trial": license_record.trial,
            "permissions": ["create", "import_cad", "generate_docx"],
            "issued_at": now.isoformat(),
            "lease_expires_at": lease_expiry.isoformat(),
            "commercial_expires_at": aware(license_record.commercial_expires_at).isoformat(),
            "server_time": now.isoformat(),
            "token_id": str(uuid4()),
        }
        return sign_claims(self.settings.private_key, claims)

    def activate(self, session: Session, key: str, device_hash: str, device_label: str, app_version: str) -> tuple[str, str]:
        now = utc_now()
        license_record = self._license_by_key(session, key)
        self._validate_license(license_record, now)
        activation = session.scalar(select(Activation).where(
            Activation.license_id == license_record.id, Activation.device_hash == device_hash,
        ))
        activation_secret = secrets.token_urlsafe(32)
        if activation is None:
            active_count = session.scalar(select(func.count()).select_from(Activation).where(
                Activation.license_id == license_record.id, Activation.status == "active",
            )) or 0
            if active_count >= license_record.seat_limit:
                raise ServiceError("device_limit_reached", "Nombre maximal d'appareils atteint.", 409)
            activation = Activation(
                license_id=license_record.id, device_hash=device_hash, device_label=device_label[:160],
                secret_digest=digest_secret(activation_secret, self.settings.key_pepper), app_version=app_version,
            )
            session.add(activation)
            session.flush()
        else:
            if activation.status == "deactivated":
                active_count = session.scalar(select(func.count()).select_from(Activation).where(
                    Activation.license_id == license_record.id, Activation.status == "active",
                )) or 0
                if active_count >= license_record.seat_limit:
                    raise ServiceError("device_limit_reached", "Nombre maximal d'appareils atteint.", 409)
            activation.status = "active"
            activation.deactivated_at = None
            activation.secret_digest = digest_secret(activation_secret, self.settings.key_pepper)
            activation.device_label = device_label[:160]
            activation.app_version = app_version
            activation.last_seen_at = now
        token = self._issue(license_record, activation, now)
        self._audit(session, "activate", license_record.id, activation.id, app_version=app_version)
        session.commit()
        LOGGER.info("license_activated license_id=%s activation_id=%s app_version=%s", license_record.id, activation.id, app_version)
        return token, activation_secret

    def refresh(self, session: Session, activation_id: str, secret: str, device_hash: str, app_version: str) -> str:
        now = utc_now()
        activation = session.get(Activation, activation_id)
        if activation is None or activation.status != "active":
            raise ServiceError("invalid_activation", "Activation inactive ou inconnue.", 403)
        self._verify_activation_secret(activation, secret)
        if not hmac.compare_digest(activation.device_hash, device_hash):
            raise ServiceError("device_mismatch", "L'empreinte de l'appareil ne correspond pas.", 403)
        self._validate_license(activation.license, now)
        activation.last_seen_at = now
        activation.app_version = app_version
        token = self._issue(activation.license, activation, now)
        self._audit(session, "refresh", activation.license_id, activation.id, app_version=app_version)
        session.commit()
        LOGGER.info("license_refreshed license_id=%s activation_id=%s", activation.license_id, activation.id)
        return token

    def deactivate(self, session: Session, activation_id: str, secret: str) -> None:
        activation = session.get(Activation, activation_id)
        if activation is None:
            return
        self._verify_activation_secret(activation, secret)
        activation.status = "deactivated"
        activation.deactivated_at = utc_now()
        self._audit(session, "deactivate", activation.license_id, activation.id)
        session.commit()
        LOGGER.info("license_deactivated license_id=%s activation_id=%s", activation.license_id, activation.id)

    def status(self, session: Session, activation_id: str, secret: str) -> dict:
        activation = session.get(Activation, activation_id)
        if activation is None:
            raise ServiceError("invalid_activation", "Activation inconnue.", 404)
        self._verify_activation_secret(activation, secret)
        return {
            "activation_status": activation.status,
            "license_status": activation.license.status,
            "commercial_expires_at": aware(activation.license.commercial_expires_at).isoformat(),
            "server_time": utc_now().isoformat(),
        }

    def create_license(
        self, session: Session, organization_name: str, kind: str, plan: str,
        seat_limit: int, expires_at: datetime, trial: bool,
    ) -> tuple[License, str]:
        organization = Organization(name=organization_name, kind=kind)
        key = generate_license_key()
        license_record = License(
            organization=organization, key_digest=digest_secret(key, self.settings.key_pepper),
            key_hint=key[-9:], plan=plan, seat_limit=seat_limit,
            commercial_expires_at=expires_at, trial=trial,
        )
        session.add_all((organization, license_record))
        session.flush()
        self._audit(session, "license_created", license_record.id, None, plan=plan, trial=trial)
        session.commit()
        LOGGER.info("license_created license_id=%s plan=%s trial=%s", license_record.id, plan, trial)
        return license_record, key
