from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from copro_auto.licensing.client import LicenseApiError
from copro_auto.licensing.service import (
    OFFLINE_TRIAL_ACTIVATION_PREFIX,
    OFFLINE_TRIAL_DEVICE_HASH,
    OFFLINE_TRIAL_KEY_PREFIX,
    LicenseService,
    LicenseState,
)
from copro_auto.licensing.token_store import TokenStore, TokenVerifier, device_fingerprint
from license_server.signing import sign_claims


def _licensing(tmp_path, now: datetime) -> tuple[LicenseService, TokenStore, Ed25519PrivateKey]:
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    verifier = TokenVerifier(base64.b64encode(public).decode("ascii"))
    store = TokenStore(tmp_path / "license.json")
    service = LicenseService(store, verifier, None)
    claims = {
        "license_id": "license-1", "activation_id": "activation-1", "device_hash": device_fingerprint(),
        "plan": "individual", "trial": True, "permissions": ["create", "import_cad", "generate_docx"],
        "issued_at": now.isoformat(), "lease_expires_at": (now + timedelta(days=1)).isoformat(),
        "commercial_expires_at": (now + timedelta(days=180)).isoformat(), "server_time": now.isoformat(),
        "token_id": "token-1",
    }
    store.save(sign_claims(private, claims), "activation-secret", now=now)
    return service, store, private


def test_signed_lease_active_grace_and_read_only_expiry(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("COPRO_AUTO_DEV_LICENSE", raising=False)
    now = datetime(2026, 7, 14, tzinfo=timezone.utc)
    service, _store, _private = _licensing(tmp_path, now)

    active = service.evaluate(now=now + timedelta(hours=12), update_seen=False)
    grace = service.evaluate(now=now + timedelta(hours=36), update_seen=False)
    expired = service.evaluate(now=now + timedelta(days=4), update_seen=False)

    assert active.state is LicenseState.TRIAL_ACTIVE
    assert active.permits("generate_docx")
    assert grace.state is LicenseState.OFFLINE_GRACE
    assert not grace.permits("create")
    assert grace.permits("open") and grace.permits("export_json")
    assert expired.state is LicenseState.EXPIRED
    assert not expired.permits("generate_docx")
    assert expired.permits("open") and expired.permits("export_json")


class _RejectingClient:
    def __init__(self, code: str) -> None:
        self.code = code

    def refresh(self, *_args, **_kwargs) -> str:
        messages = {
            "revoked": "Cette licence a été révoquée.",
            "expired": "Cette licence est arrivée à expiration.",
            "invalid_activation": "Activation inactive ou inconnue.",
            "network_error": "Serveur de licence inaccessible.",
        }
        raise LicenseApiError(messages[self.code], self.code)


def test_online_sync_invalidates_authoritative_revocation_or_release(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("COPRO_AUTO_DEV_LICENSE", raising=False)
    now = datetime(2026, 7, 14, tzinfo=timezone.utc)

    for code, expected in (
        ("revoked", LicenseState.REVOKED),
        ("expired", LicenseState.EXPIRED),
        ("invalid_activation", LicenseState.UNLICENSED),
    ):
        service, store, _private = _licensing(tmp_path / code, now)
        service.client = _RejectingClient(code)

        decision = service.sync_status(now=now + timedelta(hours=1))

        assert decision.state is expected
        assert store.load() is None


def test_online_sync_keeps_valid_cached_lease_during_network_outage(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("COPRO_AUTO_DEV_LICENSE", raising=False)
    now = datetime(2026, 7, 14, tzinfo=timezone.utc)
    service, store, _private = _licensing(tmp_path, now)
    service.client = _RejectingClient("network_error")

    decision = service.sync_status(now=now + timedelta(hours=1))

    assert decision.state is LicenseState.TRIAL_ACTIVE
    assert decision.permits("generate_docx")
    assert store.load() is not None


def test_clock_rollback_and_token_tampering_are_detected(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("COPRO_AUTO_DEV_LICENSE", raising=False)
    now = datetime(2026, 7, 14, tzinfo=timezone.utc)
    service, store, _private = _licensing(tmp_path, now)
    rollback = service.evaluate(now=now - timedelta(days=1), update_seen=False)
    assert rollback.state is LicenseState.ONLINE_CHECK_REQUIRED

    cached = store.load()
    assert cached is not None
    cached.token = ("A" if cached.token[0] != "A" else "B") + cached.token[1:]
    store._write(cached)
    assert service.evaluate(now=now, update_seen=False).state is LicenseState.INVALID


def test_portable_offline_trial_activates_for_30_days_without_server(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("COPRO_AUTO_DEV_LICENSE", raising=False)
    now = datetime(2026, 7, 20, tzinfo=timezone.utc)
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    store = TokenStore(tmp_path / "license.json")
    service = LicenseService(store, TokenVerifier(base64.b64encode(public).decode("ascii")), None)
    claims = {
        "license_id": "offline-trial-license-1",
        "activation_id": f"{OFFLINE_TRIAL_ACTIVATION_PREFIX}1",
        "device_hash": OFFLINE_TRIAL_DEVICE_HASH,
        "plan": "individual",
        "trial": True,
        "permissions": ["create", "import_cad", "generate_docx"],
        "issued_at": now.isoformat(),
        "lease_expires_at": (now + timedelta(days=30)).isoformat(),
        "commercial_expires_at": (now + timedelta(days=30)).isoformat(),
        "server_time": now.isoformat(),
        "token_id": "offline-trial-token-1",
    }
    key = OFFLINE_TRIAL_KEY_PREFIX + sign_claims(private, claims)

    activated = service.activate(key, now=now)
    assert activated.state is LicenseState.TRIAL_ACTIVE
    assert activated.permits("create") and activated.permits("generate_docx")
    assert service.refresh(now=now + timedelta(days=1)).state is LicenseState.TRIAL_ACTIVE

    service.deactivate()
    assert store.load() is None


def test_portable_offline_trial_rejects_more_than_30_days(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("COPRO_AUTO_DEV_LICENSE", raising=False)
    now = datetime(2026, 7, 20, tzinfo=timezone.utc)
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    service = LicenseService(
        TokenStore(tmp_path / "license.json"),
        TokenVerifier(base64.b64encode(public).decode("ascii")),
        None,
    )
    claims = {
        "license_id": "offline-trial-license-2",
        "activation_id": f"{OFFLINE_TRIAL_ACTIVATION_PREFIX}2",
        "device_hash": OFFLINE_TRIAL_DEVICE_HASH,
        "plan": "individual",
        "trial": True,
        "permissions": ["create", "import_cad", "generate_docx"],
        "issued_at": now.isoformat(),
        "lease_expires_at": (now + timedelta(days=31)).isoformat(),
        "commercial_expires_at": (now + timedelta(days=31)).isoformat(),
        "server_time": now.isoformat(),
        "token_id": "offline-trial-token-2",
    }

    try:
        service.activate(OFFLINE_TRIAL_KEY_PREFIX + sign_claims(private, claims), now=now)
    except ValueError as exc:
        assert "30 jours" in str(exc)
    else:
        raise AssertionError("Une clé d'essai hors ligne de plus de 30 jours a été acceptée")
