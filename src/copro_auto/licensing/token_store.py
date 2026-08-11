from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from platformdirs import user_data_path


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


@dataclass(frozen=True, slots=True)
class TokenClaims:
    license_id: str
    activation_id: str
    device_hash: str
    plan: str
    trial: bool
    permissions: tuple[str, ...]
    issued_at: str
    lease_expires_at: str
    commercial_expires_at: str
    server_time: str
    token_id: str

    @classmethod
    def from_dict(cls, data: dict) -> "TokenClaims":
        required = {
            "license_id", "activation_id", "device_hash", "plan", "trial", "permissions",
            "issued_at", "lease_expires_at", "commercial_expires_at", "server_time", "token_id",
        }
        missing = required - set(data)
        if missing:
            raise ValueError(f"Jeton incomplet : {', '.join(sorted(missing))}")
        return cls(
            license_id=str(data["license_id"]), activation_id=str(data["activation_id"]),
            device_hash=str(data["device_hash"]), plan=str(data["plan"]), trial=bool(data["trial"]),
            permissions=tuple(str(item) for item in data["permissions"]),
            issued_at=str(data["issued_at"]), lease_expires_at=str(data["lease_expires_at"]),
            commercial_expires_at=str(data["commercial_expires_at"]), server_time=str(data["server_time"]),
            token_id=str(data["token_id"]),
        )


class TokenVerifier:
    def __init__(self, public_key_b64: str) -> None:
        try:
            self.public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
        except (ValueError, TypeError) as exc:
            raise ValueError("Clé publique de licence invalide.") from exc

    def verify(self, token: str) -> TokenClaims:
        try:
            payload_encoded, signature_encoded = token.split(".", 1)
            payload = _b64decode(payload_encoded)
            signature = _b64decode(signature_encoded)
            self.public_key.verify(signature, payload)
            data = json.loads(payload.decode("utf-8"))
        except (ValueError, InvalidSignature, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("Signature du jeton de licence invalide.") from exc
        if not isinstance(data, dict):
            raise ValueError("Contenu du jeton de licence invalide.")
        return TokenClaims.from_dict(data)


@dataclass(slots=True)
class CachedLicense:
    token: str
    activation_secret: str
    saved_at: str
    last_seen_at: str


class TokenStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else Path(user_data_path("CoproAuto", ensure_exists=True)) / "license.json"

    def load(self) -> CachedLicense | None:
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return CachedLicense(**data)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None

    def save(self, token: str, activation_secret: str, *, now: datetime | None = None) -> CachedLicense:
        moment = (now or utc_now()).isoformat()
        record = CachedLicense(token=token, activation_secret=activation_secret, saved_at=moment, last_seen_at=moment)
        self._write(record)
        return record

    def record_seen(self, record: CachedLicense, now: datetime) -> None:
        record.last_seen_at = now.isoformat()
        self._write(record)

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)

    def _write(self, record: CachedLicense) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(record), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)


def device_fingerprint() -> str:
    machine_id = ""
    if platform.system() == "Windows":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                machine_id = str(winreg.QueryValueEx(key, "MachineGuid")[0])
        except OSError:
            machine_id = ""
    if not machine_id:
        machine_id = f"{uuid.getnode()}:{platform.node()}"
    return hashlib.sha256(f"copro-auto-device-v1:{machine_id}".encode("utf-8")).hexdigest()
