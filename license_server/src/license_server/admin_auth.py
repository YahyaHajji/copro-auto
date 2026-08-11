from __future__ import annotations

import base64
import getpass
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from .models import AdminLoginAttempt


PASSWORD_ITERATIONS = 600_000
SESSION_SECONDS = 8 * 60 * 60
LOGIN_WINDOW = timedelta(minutes=10)
LOGIN_LIMIT = 5
COOKIE_NAME = "copro_admin_session"


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str, *, iterations: int = PASSWORD_ITERATIONS) -> str:
    if len(password) < 12:
        raise ValueError("Le mot de passe administrateur doit contenir au moins 12 caractères.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64encode(salt)}${_b64encode(digest)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, expected_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        if iterations < 100_000 or iterations > 2_000_000:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _b64decode(salt_text), iterations,
        )
        return hmac.compare_digest(actual, _b64decode(expected_text))
    except (ValueError, TypeError):
        return False


def address_digest(address: str, pepper: str) -> str:
    return hmac.new(pepper.encode("utf-8"), f"admin:{address}".encode("utf-8"), hashlib.sha256).hexdigest()


def check_login(
    session: Session, address_hash: str, password: str, expected_hash: str,
    *, now: datetime | None = None,
) -> str:
    moment = now or datetime.now(timezone.utc)
    cutoff = moment - LOGIN_WINDOW
    session.execute(delete(AdminLoginAttempt).where(AdminLoginAttempt.attempted_at < cutoff))
    failures = session.scalar(
        select(func.count()).select_from(AdminLoginAttempt).where(
            AdminLoginAttempt.address_hash == address_hash,
            AdminLoginAttempt.attempted_at >= cutoff,
        ),
    ) or 0
    if failures >= LOGIN_LIMIT:
        session.commit()
        return "limited"
    if not verify_password(password, expected_hash):
        session.add(AdminLoginAttempt(address_hash=address_hash, attempted_at=moment))
        session.commit()
        return "invalid"
    session.execute(delete(AdminLoginAttempt).where(AdminLoginAttempt.address_hash == address_hash))
    session.commit()
    return "ok"


@dataclass(frozen=True, slots=True)
class AdminSession:
    csrf: str
    expires_at: int


def issue_session(secret: str, *, now: datetime | None = None) -> tuple[str, AdminSession]:
    moment = now or datetime.now(timezone.utc)
    claims = AdminSession(csrf=secrets.token_urlsafe(24), expires_at=int(moment.timestamp()) + SESSION_SECONDS)
    payload = json.dumps({"csrf": claims.csrf, "exp": claims.expires_at}, separators=(",", ":")).encode("utf-8")
    encoded = _b64encode(payload)
    signature = _b64encode(hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest())
    return f"{encoded}.{signature}", claims


def verify_session(token: str, secret: str, *, now: datetime | None = None) -> AdminSession | None:
    if not token or not secret:
        return None
    try:
        encoded, provided_signature = token.split(".", 1)
        expected_signature = _b64encode(
            hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest(),
        )
        if not hmac.compare_digest(provided_signature, expected_signature):
            return None
        data = json.loads(_b64decode(encoded).decode("utf-8"))
        claims = AdminSession(csrf=str(data["csrf"]), expires_at=int(data["exp"]))
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    moment = now or datetime.now(timezone.utc)
    return claims if claims.expires_at > int(moment.timestamp()) else None


def main() -> int:
    password = getpass.getpass("Nouveau mot de passe administrateur : ")
    confirmation = getpass.getpass("Confirmez le mot de passe : ")
    if password != confirmation:
        raise SystemExit("Les mots de passe ne correspondent pas.")
    print(hash_password(password))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
