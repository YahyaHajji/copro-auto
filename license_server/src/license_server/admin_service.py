from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Activation, AuditEvent, License, Organization, utc_now
from .service import LicenseService, aware


@dataclass(frozen=True, slots=True)
class AdminError(RuntimeError):
    code: str
    message: str
    status_code: int = 400


def _timestamp(value: datetime | None) -> str | None:
    return aware(value).isoformat() if value is not None else None


class AdminService:
    def __init__(self, licenses: LicenseService) -> None:
        self.licenses = licenses

    @staticmethod
    def _audit(
        session: Session, event: str, license_id: str | None = None,
        activation_id: str | None = None, **details,
    ) -> None:
        session.add(AuditEvent(
            event_type=event,
            license_id=license_id,
            activation_id=activation_id,
            details=json.dumps(details, ensure_ascii=False),
        ))

    def summary(self, session: Session) -> dict:
        now = utc_now()
        return {
            "licenses": session.scalar(select(func.count()).select_from(License)) or 0,
            "valid_licenses": session.scalar(
                select(func.count()).select_from(License).where(
                    License.status == "active", License.commercial_expires_at >= now,
                ),
            ) or 0,
            "trials": session.scalar(select(func.count()).select_from(License).where(License.trial.is_(True))) or 0,
            "active_devices": session.scalar(
                select(func.count()).select_from(Activation).where(Activation.status == "active"),
            ) or 0,
        }

    def list_licenses(self, session: Session) -> list[dict]:
        active_counts = (
            select(Activation.license_id, func.count(Activation.id).label("active_devices"))
            .where(Activation.status == "active")
            .group_by(Activation.license_id)
            .subquery()
        )
        rows = session.execute(
            select(License, Organization, active_counts.c.active_devices)
            .join(Organization, License.organization_id == Organization.id)
            .outerjoin(active_counts, active_counts.c.license_id == License.id)
            .order_by(License.created_at.desc()),
        ).all()
        return [self._license_dict(record, organization, int(active_devices or 0)) for record, organization, active_devices in rows]

    def get_license(self, session: Session, license_id: str) -> dict:
        row = session.execute(
            select(License, Organization)
            .join(Organization, License.organization_id == Organization.id)
            .where(License.id == license_id),
        ).one_or_none()
        if row is None:
            raise AdminError("not_found", "Licence introuvable.", 404)
        record, organization = row
        activations = session.scalars(
            select(Activation).where(Activation.license_id == license_id).order_by(Activation.created_at.desc()),
        ).all()
        result = self._license_dict(
            record, organization, sum(item.status == "active" for item in activations),
        )
        result["activations"] = [{
            "id": item.id,
            "device_label": item.device_label or "Appareil sans nom",
            "device_hint": item.device_hash[:8],
            "status": item.status,
            "app_version": item.app_version,
            "created_at": _timestamp(item.created_at),
            "last_seen_at": _timestamp(item.last_seen_at),
            "deactivated_at": _timestamp(item.deactivated_at),
        } for item in activations]
        return result

    def create_license(
        self, session: Session, organization: str, plan: str, seats: int, days: int, trial: bool,
    ) -> dict:
        name = organization.strip()
        if len(name) < 2 or len(name) > 200:
            raise AdminError("invalid_organization", "Le nom du client doit contenir entre 2 et 200 caractères.")
        if plan not in {"individual", "office"}:
            raise AdminError("invalid_plan", "Plan de licence invalide.")
        if seats < 1 or seats > 100:
            raise AdminError("invalid_seats", "Le nombre de postes doit être compris entre 1 et 100.")
        if days < 1 or days > 3650:
            raise AdminError("invalid_days", "La durée doit être comprise entre 1 et 3650 jours.")
        record, key = self.licenses.create_license(
            session, name, plan, plan, seats, utc_now() + timedelta(days=days), trial,
        )
        return {"license_id": record.id, "license_key": key, "expires_at": _timestamp(record.commercial_expires_at)}

    def renew(self, session: Session, license_id: str, days: int) -> dict:
        if days < 1 or days > 3650:
            raise AdminError("invalid_days", "La durée doit être comprise entre 1 et 3650 jours.")
        record = self._record(session, license_id)
        record.commercial_expires_at = max(utc_now(), aware(record.commercial_expires_at)) + timedelta(days=days)
        self._audit(session, "admin_license_renewed", license_id, days=days)
        session.commit()
        return {"expires_at": _timestamp(record.commercial_expires_at), "status": record.status}

    def set_status(self, session: Session, license_id: str, status: str) -> dict:
        if status not in {"active", "revoked"}:
            raise AdminError("invalid_status", "Statut de licence invalide.")
        record = self._record(session, license_id)
        if status == "active" and aware(record.commercial_expires_at) < utc_now():
            raise AdminError("expired", "Renouvelez cette licence avant de la réactiver.", 409)
        record.status = status
        self._audit(session, f"admin_license_{'reactivated' if status == 'active' else 'revoked'}", license_id)
        session.commit()
        return {"status": status}

    def release(self, session: Session, activation_id: str) -> dict:
        activation = session.get(Activation, activation_id)
        if activation is None:
            raise AdminError("not_found", "Activation introuvable.", 404)
        if activation.status != "deactivated":
            activation.status = "deactivated"
            activation.deactivated_at = utc_now()
            self._audit(session, "admin_activation_released", activation.license_id, activation.id)
            session.commit()
        return {"status": "deactivated"}

    def audit_events(self, session: Session, limit: int = 50) -> list[dict]:
        events = session.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)).all()
        return [{
            "id": event.id,
            "event_type": event.event_type,
            "license_id": event.license_id,
            "activation_id": event.activation_id,
            "created_at": _timestamp(event.created_at),
        } for event in events]

    @staticmethod
    def _record(session: Session, license_id: str) -> License:
        record = session.get(License, license_id)
        if record is None:
            raise AdminError("not_found", "Licence introuvable.", 404)
        return record

    @staticmethod
    def _license_dict(record: License, organization: Organization, active_devices: int) -> dict:
        now = datetime.now(timezone.utc)
        expired = aware(record.commercial_expires_at) < now
        return {
            "id": record.id,
            "organization": organization.name,
            "kind": organization.kind,
            "key_hint": record.key_hint,
            "plan": record.plan,
            "status": "expired" if expired and record.status == "active" else record.status,
            "seat_limit": record.seat_limit,
            "active_devices": active_devices,
            "trial": record.trial,
            "commercial_expires_at": _timestamp(record.commercial_expires_at),
            "created_at": _timestamp(record.created_at),
        }
