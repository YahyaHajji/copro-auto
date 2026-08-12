from __future__ import annotations

import base64
import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    private_key: Ed25519PrivateKey
    key_pepper: str
    lease_days: int = 1
    admin_password_hash: str = ""
    admin_session_secret: str = ""

    @classmethod
    def from_environment(cls) -> "Settings":
        database_url = os.environ.get("DATABASE_URL", "")
        private_key_b64 = os.environ.get("LICENSE_SIGNING_PRIVATE_KEY", "")
        pepper = os.environ.get("LICENSE_KEY_PEPPER", "")
        if not database_url or not private_key_b64 or not pepper:
            raise RuntimeError("DATABASE_URL, LICENSE_SIGNING_PRIVATE_KEY et LICENSE_KEY_PEPPER sont obligatoires.")
        try:
            private_key = Ed25519PrivateKey.from_private_bytes(base64.b64decode(private_key_b64))
        except (ValueError, TypeError) as exc:
            raise RuntimeError("LICENSE_SIGNING_PRIVATE_KEY est invalide.") from exc
        return cls(
            database_url,
            private_key,
            pepper,
            int(os.environ.get("LEASE_DAYS", "1")),
            os.environ.get("ADMIN_PASSWORD_HASH", ""),
            os.environ.get("ADMIN_SESSION_SECRET", ""),
        )
