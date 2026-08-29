from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from .models import Activation, AuditEvent, License, Organization, utc_now
from .service import LicenseService, aware


ONLINE_WINDOW = timedelta(minutes=20)
EXPIRING_WINDOW = timedelta(days=30)
ACTIVITY_CATEGORIES = {
    "licenses": {
        "license_created", "admin_license_renewed", "admin_license_revoked", "admin_license_reactivated",
    },
    "devices": {"activate", "refresh", "deactivate", "admin_activation_released"},
    "administration": {"admin_audit_exported"},
}
APPLICATION_EVENTS = {"activate", "refresh", "deactivate"}


@dataclass(frozen=True, slots=True)
class AdminError(RuntimeError):
    code: str
    message: str
    status_code: int = 400


def _timestamp(value: datetime | None) -> str | None:
    return aware(value).isoformat() if value is not None else None


def _version_key(value: str) -> tuple[int, ...] | None:
    match = re.fullmatch(r"\s*[vV]?(\d+(?:\.\d+){0,3})(?:[-+].*)?\s*", value or "")
    return tuple(int(part) for part in match.group(1).split(".")) if match else None


def _is_outdated(installed: str, current: str) -> bool:
    installed_key = _version_key(installed)
    current_key = _version_key(current)
    if installed_key is None or current_key is None:
        return False
    width = max(len(installed_key), len(current_key))
    return installed_key + (0,) * (width - len(installed_key)) < current_key + (0,) * (width - len(current_key))


def _event_origin(event_type: str) -> str:
    return "application" if event_type in APPLICATION_EVENTS else "administrator"


def _event_category(event_type: str) -> str:
    for category, event_types in ACTIVITY_CATEGORIES.items():
        if event_type in event_types:
            return category
    return "administration"


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
        active_licenses = session.scalars(select(License).where(
            License.status == "active", License.commercial_expires_at >= now,
        )).all()
        active_devices = session.scalars(select(Activation).where(Activation.status == "active")).all()
        return {
            "licenses": session.scalar(select(func.count()).select_from(License)) or 0,
            "valid_licenses": len(active_licenses),
            "trials": session.scalar(select(func.count()).select_from(License).where(License.trial.is_(True))) or 0,
            "active_devices": len(active_devices),
            "seat_capacity": sum(item.seat_limit for item in active_licenses),
            "expiring_soon": sum(aware(item.commercial_expires_at) <= now + EXPIRING_WINDOW for item in active_licenses),
            "online_devices": sum(aware(item.last_seen_at) > now - ONLINE_WINDOW for item in active_devices),
            "outdated_devices": sum(
                _is_outdated(item.app_version, self.licenses.settings.desktop_current_version)
                for item in active_devices
            ),
            "current_app_version": self.licenses.settings.desktop_current_version,
            "updated_at": _timestamp(now),
        }

    def list_licenses(self, session: Session) -> list[dict]:
        active_by_license: dict[str, list[Activation]] = {}
        for activation in session.scalars(select(Activation).where(Activation.status == "active")).all():
            active_by_license.setdefault(activation.license_id, []).append(activation)
        rows = session.execute(
            select(License, Organization)
            .join(Organization, License.organization_id == Organization.id)
            .order_by(License.created_at.desc()),
        ).all()
        return [self._license_dict(record, organization, active_by_license.get(record.id, [])) for record, organization in rows]

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
        result = self._license_dict(record, organization, [item for item in activations if item.status == "active"])
        result["activations"] = [self._activation_dict(item) for item in activations]
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

    def activity_page(
        self, session: Session, *, limit: int = 25, cursor: str | None = None, direction: str = "next",
        search: str = "", category: str = "all", origin: str = "all", start: datetime | None = None,
        end: datetime | None = None, include_refresh: bool = False,
    ) -> dict:
        if limit not in {25, 50, 100}:
            raise AdminError("invalid_limit", "La taille de page doit être 25, 50 ou 100.")
        if direction not in {"next", "previous"}:
            raise AdminError("invalid_direction", "Direction de pagination invalide.")
        base = self._activity_statement(
            search=search, category=category, origin=origin, start=start, end=end,
            include_refresh=include_refresh,
        )
        total = session.scalar(select(func.count()).select_from(base.with_only_columns(AuditEvent.id).subquery())) or 0
        cursor_value = self._decode_cursor(cursor) if cursor else None
        statement = base
        if cursor_value is not None:
            moment, event_id = cursor_value
            if direction == "next":
                statement = statement.where(or_(
                    AuditEvent.created_at < moment,
                    and_(AuditEvent.created_at == moment, AuditEvent.id < event_id),
                ))
            else:
                statement = statement.where(or_(
                    AuditEvent.created_at > moment,
                    and_(AuditEvent.created_at == moment, AuditEvent.id > event_id),
                ))
        ascending = direction == "previous"
        order = (AuditEvent.created_at.asc(), AuditEvent.id.asc()) if ascending else (
            AuditEvent.created_at.desc(), AuditEvent.id.desc(),
        )
        rows = session.execute(statement.order_by(*order).limit(limit + 1)).all()
        if len(rows) > limit:
            rows = rows[:limit]
        if ascending:
            rows.reverse()
        items = [self._event_dict(event, organization, device) for event, organization, device in rows]
        newer = self._has_activity(session, base, rows[0][0], newer=True) if rows else False
        older = self._has_activity(session, base, rows[-1][0], newer=False) if rows else False
        return {
            "items": items,
            "total": int(total),
            "limit": limit,
            "next_cursor": self._encode_cursor(rows[-1][0]) if rows and older else None,
            "previous_cursor": self._encode_cursor(rows[0][0]) if rows and newer else None,
            "summary": self._activity_summary(session, base),
        }

    def export_activity(
        self, session: Session, *, search: str = "", category: str = "all", origin: str = "all",
        start: datetime | None = None, end: datetime | None = None, include_refresh: bool = False,
    ) -> list[dict]:
        statement = self._activity_statement(
            search=search, category=category, origin=origin, start=start, end=end,
            include_refresh=include_refresh,
        ).order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(10_000)
        rows = session.execute(statement).all()
        items = [self._event_dict(event, organization, device) for event, organization, device in rows]
        self._audit(session, "admin_audit_exported", count=len(items), category=category, origin=origin)
        session.commit()
        return items

    def _activity_statement(
        self, *, search: str, category: str, origin: str, start: datetime | None,
        end: datetime | None, include_refresh: bool,
    ):
        statement = (
            select(AuditEvent, Organization.name, Activation.device_label)
            .select_from(AuditEvent)
            .outerjoin(License, AuditEvent.license_id == License.id)
            .outerjoin(Organization, License.organization_id == Organization.id)
            .outerjoin(Activation, AuditEvent.activation_id == Activation.id)
        )
        if search.strip():
            pattern = f"%{search.strip()}%"
            statement = statement.where(or_(Organization.name.ilike(pattern), Activation.device_label.ilike(pattern)))
        if category != "all":
            event_types = ACTIVITY_CATEGORIES.get(category)
            if event_types is None:
                raise AdminError("invalid_category", "Catégorie d'activité invalide.")
            statement = statement.where(AuditEvent.event_type.in_(event_types))
        if origin == "application":
            statement = statement.where(AuditEvent.event_type.in_(APPLICATION_EVENTS))
        elif origin == "administrator":
            statement = statement.where(AuditEvent.event_type.not_in(APPLICATION_EVENTS))
        elif origin != "all":
            raise AdminError("invalid_origin", "Origine d'activité invalide.")
        if not include_refresh:
            statement = statement.where(AuditEvent.event_type != "refresh")
        if start is not None:
            statement = statement.where(AuditEvent.created_at >= start)
        if end is not None:
            statement = statement.where(AuditEvent.created_at < end)
        return statement

    @staticmethod
    def _activity_summary(session: Session, base) -> dict:
        matching_ids = base.with_only_columns(AuditEvent.id).subquery()
        counts = dict(session.execute(
            select(AuditEvent.event_type, func.count())
            .where(AuditEvent.id.in_(select(matching_ids.c.id)))
            .group_by(AuditEvent.event_type),
        ).all())
        return {
            "events": sum(int(value) for value in counts.values()),
            "activations": int(counts.get("activate", 0)),
            "admin_actions": sum(int(value) for key, value in counts.items() if _event_origin(key) == "administrator"),
            "released_devices": int(counts.get("deactivate", 0)) + int(counts.get("admin_activation_released", 0)),
        }

    @staticmethod
    def _has_activity(session: Session, base, event: AuditEvent, *, newer: bool) -> bool:
        comparison = or_(
            AuditEvent.created_at > event.created_at,
            and_(AuditEvent.created_at == event.created_at, AuditEvent.id > event.id),
        ) if newer else or_(
            AuditEvent.created_at < event.created_at,
            and_(AuditEvent.created_at == event.created_at, AuditEvent.id < event.id),
        )
        return bool(session.scalar(
            select(func.count()).select_from(base.where(comparison).with_only_columns(AuditEvent.id).subquery()),
        ))

    @staticmethod
    def _encode_cursor(event: AuditEvent) -> str:
        payload = json.dumps([_timestamp(event.created_at), event.id], separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")

    @staticmethod
    def _decode_cursor(value: str) -> tuple[datetime, str]:
        try:
            padding = "=" * (-len(value) % 4)
            timestamp, event_id = json.loads(base64.urlsafe_b64decode(value + padding).decode("utf-8"))
            moment = datetime.fromisoformat(timestamp)
            if not isinstance(event_id, str) or not event_id:
                raise ValueError
            return aware(moment), event_id
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise AdminError("invalid_cursor", "Curseur de pagination invalide.") from exc

    @staticmethod
    def _event_dict(event: AuditEvent, organization: str | None, device: str | None) -> dict:
        try:
            details = json.loads(event.details or "{}")
        except json.JSONDecodeError:
            details = {}
        if not isinstance(details, dict):
            details = {}
        return {
            "id": event.id,
            "event_type": event.event_type,
            "category": _event_category(event.event_type),
            "origin": _event_origin(event.event_type),
            "license_id": event.license_id,
            "organization": organization or None,
            "device_label": device or None,
            "details": details,
            "created_at": _timestamp(event.created_at),
        }

    def _activation_dict(self, item: Activation) -> dict:
        now = utc_now()
        return {
            "id": item.id,
            "device_label": item.device_label or "Appareil sans nom",
            "device_hint": item.device_hash[:8].upper(),
            "status": item.status,
            "connection_status": "online" if item.status == "active" and aware(item.last_seen_at) > now - ONLINE_WINDOW else "offline",
            "app_version": item.app_version,
            "current_app_version": self.licenses.settings.desktop_current_version,
            "outdated": _is_outdated(item.app_version, self.licenses.settings.desktop_current_version),
            "os_name": item.os_name,
            "os_edition": item.os_edition,
            "os_version": item.os_version,
            "os_build": item.os_build,
            "architecture": item.architecture,
            "created_at": _timestamp(item.created_at),
            "last_seen_at": _timestamp(item.last_seen_at),
            "deactivated_at": _timestamp(item.deactivated_at),
        }

    @staticmethod
    def _record(session: Session, license_id: str) -> License:
        record = session.get(License, license_id)
        if record is None:
            raise AdminError("not_found", "Licence introuvable.", 404)
        return record

    def _license_dict(self, record: License, organization: Organization, active_devices: list[Activation]) -> dict:
        now = utc_now()
        expires_at = aware(record.commercial_expires_at)
        expired = expires_at < now
        last_seen = max((item.last_seen_at for item in active_devices), default=None)
        return {
            "id": record.id,
            "organization": organization.name,
            "kind": organization.kind,
            "key_hint": record.key_hint,
            "plan": record.plan,
            "status": "expired" if expired and record.status == "active" else record.status,
            "seat_limit": record.seat_limit,
            "active_devices": len(active_devices),
            "device_labels": [item.device_label for item in active_devices if item.device_label],
            "online_devices": sum(aware(item.last_seen_at) > now - ONLINE_WINDOW for item in active_devices),
            "outdated_devices": sum(
                _is_outdated(item.app_version, self.licenses.settings.desktop_current_version)
                for item in active_devices
            ),
            "last_seen_at": _timestamp(last_seen),
            "expiring_soon": record.status == "active" and not expired and expires_at <= now + EXPIRING_WINDOW,
            "trial": record.trial,
            "commercial_expires_at": _timestamp(record.commercial_expires_at),
            "created_at": _timestamp(record.created_at),
            "updated_at": _timestamp(record.updated_at),
        }
