from __future__ import annotations

import os
import platform
import json
import logging
import sys
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from copro_auto import __version__

from .client import LicenseApiClient
from .token_store import CachedLicense, TokenClaims, TokenStore, TokenVerifier, device_fingerprint, parse_timestamp


LOGGER = logging.getLogger(__name__)
OFFLINE_TRIAL_KEY_PREFIX = "COPRO-TRIAL-"
OFFLINE_TRIAL_DEVICE_HASH = "portable-offline-trial"
OFFLINE_TRIAL_ACTIVATION_PREFIX = "offline-trial-activation-"
OFFLINE_TRIAL_LICENSE_PREFIX = "offline-trial-license-"
OFFLINE_TRIAL_PERMISSIONS = frozenset({"create", "import_cad", "generate_docx"})
OFFLINE_TRIAL_MAX_DURATION = timedelta(days=30)

PRODUCTIVE_STATES = {
    "trial_active", "paid_active", "expiring_soon", "offline_grace", "development",
}


class LicenseState(StrEnum):
    UNLICENSED = "unlicensed"
    TRIAL_ACTIVE = "trial_active"
    PAID_ACTIVE = "paid_active"
    EXPIRING_SOON = "expiring_soon"
    OFFLINE_GRACE = "offline_grace"
    EXPIRED = "expired"
    REVOKED = "revoked"
    DEVICE_LIMIT_REACHED = "device_limit_reached"
    ONLINE_CHECK_REQUIRED = "online_check_required"
    INVALID = "invalid"
    DEVELOPMENT = "development"


@dataclass(frozen=True, slots=True)
class LicenseDecision:
    state: LicenseState
    message: str
    claims: TokenClaims | None = None

    def permits(self, permission: str) -> bool:
        if permission in {"open", "read", "export_json"}:
            return True
        if self.state.value not in PRODUCTIVE_STATES:
            return False
        return self.state is LicenseState.DEVELOPMENT or (self.claims is not None and permission in self.claims.permissions)


class LicenseService:
    def __init__(
        self,
        store: TokenStore,
        verifier: TokenVerifier | None,
        client: LicenseApiClient | None,
        *,
        grace_days: int = 7,
    ) -> None:
        self.store = store
        self.verifier = verifier
        self.client = client
        self.grace = timedelta(days=grace_days)

    @classmethod
    def from_environment(cls) -> "LicenseService":
        store = TokenStore()
        if getattr(sys, "frozen", False):
            config_path = Path(sys._MEIPASS) / "resources" / "license" / "config.json"  # type: ignore[attr-defined]
        else:
            config_path = Path(__file__).resolve().parents[3] / "resources" / "license" / "config.json"
        packaged: dict[str, str] = {}
        if config_path.exists():
            try:
                packaged = json.loads(config_path.read_text(encoding="utf-8"))
            except (OSError, ValueError, json.JSONDecodeError):
                packaged = {}
        public_key = os.environ.get("COPRO_AUTO_LICENSE_PUBLIC_KEY", packaged.get("public_key", ""))
        server = os.environ.get("COPRO_AUTO_LICENSE_SERVER", packaged.get("server_url", "https://licence.example.invalid"))
        return cls(store, TokenVerifier(public_key) if public_key else None, LicenseApiClient(server))

    def evaluate(self, *, now: datetime | None = None, update_seen: bool = True) -> LicenseDecision:
        if os.environ.get("COPRO_AUTO_DEV_LICENSE") == "1":
            return LicenseDecision(LicenseState.DEVELOPMENT, "Licence de développement")
        record = self.store.load()
        if record is None:
            return LicenseDecision(LicenseState.UNLICENSED, "Aucune licence activée")
        if self.verifier is None:
            return LicenseDecision(LicenseState.INVALID, "Clé publique de licence non configurée")
        moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        try:
            claims = self.verifier.verify(record.token)
            portable_trial = self._is_portable_offline_trial(claims)
            if claims.device_hash != device_fingerprint() and not portable_trial:
                return LicenseDecision(LicenseState.INVALID, "Ce jeton appartient à un autre appareil")
            last_seen = parse_timestamp(record.last_seen_at)
            signed_time = parse_timestamp(claims.server_time)
            if moment < max(last_seen, signed_time) - timedelta(minutes=5):
                return LicenseDecision(LicenseState.ONLINE_CHECK_REQUIRED, "Horloge modifiée : vérification en ligne requise", claims)
            commercial_expiry = parse_timestamp(claims.commercial_expires_at)
            lease_expiry = parse_timestamp(claims.lease_expires_at)
        except ValueError as exc:
            return LicenseDecision(LicenseState.INVALID, str(exc))
        if update_seen and moment >= last_seen:
            self.store.record_seen(record, moment)
        if portable_trial and moment > min(lease_expiry, commercial_expiry):
            return LicenseDecision(LicenseState.EXPIRED, "Essai de 30 jours arrivé à expiration — consultation autorisée", claims)
        if moment > commercial_expiry:
            return LicenseDecision(LicenseState.EXPIRED, "Licence arrivée à expiration — consultation autorisée", claims)
        if moment > lease_expiry + self.grace:
            return LicenseDecision(LicenseState.EXPIRED, "Connexion requise pour renouveler la licence", claims)
        if moment > lease_expiry:
            return LicenseDecision(LicenseState.OFFLINE_GRACE, "Mode hors ligne temporaire — reconnectez-vous", claims)
        if lease_expiry - moment <= timedelta(days=3):
            return LicenseDecision(LicenseState.EXPIRING_SOON, "Licence à actualiser bientôt", claims)
        state = LicenseState.TRIAL_ACTIVE if claims.trial else LicenseState.PAID_ACTIVE
        return LicenseDecision(state, "Essai actif" if claims.trial else "Licence active", claims)

    def activate(self, license_key: str, *, now: datetime | None = None) -> LicenseDecision:
        normalized = license_key.strip()
        if normalized.startswith(OFFLINE_TRIAL_KEY_PREFIX):
            return self._activate_offline_trial(normalized, now=now)
        if self.client is None or self.verifier is None:
            return LicenseDecision(LicenseState.INVALID, "Service de licence non configuré")
        response = self.client.activate(normalized, device_fingerprint(), platform.node(), __version__)
        claims = self.verifier.verify(response.token)
        if claims.device_hash != device_fingerprint():
            raise ValueError("Le serveur a retourné un jeton pour un autre appareil.")
        self.store.save(response.token, response.activation_secret)
        return self.evaluate()

    def refresh(self, *, now: datetime | None = None) -> LicenseDecision:
        record = self.store.load()
        if record is None or self.verifier is None or self.client is None:
            return self.evaluate(now=now)
        claims = self.verifier.verify(record.token)
        if self._is_portable_offline_trial(claims):
            return self.evaluate(now=now)
        token = self.client.refresh(claims.activation_id, record.activation_secret, device_fingerprint(), __version__)
        self.store.save(token, record.activation_secret)
        return self.evaluate()

    def deactivate(self) -> None:
        record = self.store.load()
        if record and self.verifier and self.client:
            claims = self.verifier.verify(record.token)
            if not self._is_portable_offline_trial(claims):
                self.client.deactivate(claims.activation_id, record.activation_secret)
        self.store.clear()

    @staticmethod
    def _is_portable_offline_trial(claims: TokenClaims) -> bool:
        return (
            claims.trial
            and claims.plan == "individual"
            and claims.device_hash == OFFLINE_TRIAL_DEVICE_HASH
            and claims.activation_id.startswith(OFFLINE_TRIAL_ACTIVATION_PREFIX)
            and claims.license_id.startswith(OFFLINE_TRIAL_LICENSE_PREFIX)
            and set(claims.permissions).issubset(OFFLINE_TRIAL_PERMISSIONS)
        )

    def _activate_offline_trial(self, license_key: str, *, now: datetime | None = None) -> LicenseDecision:
        if self.verifier is None:
            raise ValueError("Clé publique de licence non configurée.")
        token = license_key.removeprefix(OFFLINE_TRIAL_KEY_PREFIX)
        claims = self.verifier.verify(token)
        if not self._is_portable_offline_trial(claims):
            raise ValueError("Clé d'essai hors ligne invalide.")
        issued_at = parse_timestamp(claims.issued_at)
        server_time = parse_timestamp(claims.server_time)
        lease_expires_at = parse_timestamp(claims.lease_expires_at)
        commercial_expires_at = parse_timestamp(claims.commercial_expires_at)
        expiry = min(lease_expires_at, commercial_expires_at)
        if expiry <= issued_at or expiry - issued_at > OFFLINE_TRIAL_MAX_DURATION:
            raise ValueError("Une clé d'essai hors ligne ne peut pas dépasser 30 jours.")
        moment = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        if moment < max(issued_at, server_time) - timedelta(minutes=5):
            raise ValueError("Cette clé d'essai n'est pas encore valide.")
        if moment > expiry:
            raise ValueError("Cette clé d'essai de 30 jours est arrivée à expiration.")
        self.store.save(token, "offline-trial", now=moment)
        LOGGER.info("offline_trial_activated license_id=%s expires_at=%s", claims.license_id, expiry.isoformat())
        return self.evaluate(now=moment)
