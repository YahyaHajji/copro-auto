from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from copro_auto.licensing.token_store import TokenVerifier
from license_server.app import create_app
from license_server.config import Settings


def _application(tmp_path):
    private = Ed25519PrivateKey.generate()
    settings = Settings(f"sqlite:///{tmp_path / 'licenses.db'}", private, "test-pepper-with-enough-entropy", 30)
    app = create_app(settings, create_schema=True)
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    verifier = TokenVerifier(base64.b64encode(public).decode("ascii"))
    return app, verifier


def _create_license(app, *, seats: int = 2) -> str:
    with app.state.session_factory() as session:
        _record, key = app.state.license_service.create_license(
            session, "Cabinet Atlas", "office", "office", seats,
            datetime.now(timezone.utc) + timedelta(days=180), False,
        )
        return key


def test_activate_refresh_status_and_deactivate(tmp_path) -> None:
    app, verifier = _application(tmp_path)
    key = _create_license(app)
    client = TestClient(app)
    device = "a" * 64

    activation = client.post("/v1/activate", json={
        "license_key": key, "device_hash": device, "device_label": "PC Bureau", "app_version": "0.1.0",
    })
    assert activation.status_code == 200
    body = activation.json()
    claims = verifier.verify(body["token"])
    assert claims.device_hash == device
    assert claims.plan == "office"
    assert "generate_docx" in claims.permissions

    refreshed = client.post("/v1/refresh", json={
        "activation_id": claims.activation_id, "activation_secret": body["activation_secret"],
        "device_hash": device, "app_version": "0.1.1",
    })
    assert refreshed.status_code == 200
    assert verifier.verify(refreshed.json()["token"]).token_id != claims.token_id

    status = client.post("/v1/status", json={
        "activation_id": claims.activation_id, "activation_secret": body["activation_secret"],
    })
    assert status.json()["license_status"] == "active"

    deactivated = client.post("/v1/deactivate", json={
        "activation_id": claims.activation_id, "activation_secret": body["activation_secret"],
    })
    assert deactivated.status_code == 200


def test_seat_limit_is_enforced(tmp_path) -> None:
    app, _verifier = _application(tmp_path)
    key = _create_license(app, seats=1)
    client = TestClient(app)
    first = client.post("/v1/activate", json={
        "license_key": key, "device_hash": "a" * 64, "device_label": "PC 1", "app_version": "0.1.0",
    })
    second = client.post("/v1/activate", json={
        "license_key": key, "device_hash": "b" * 64, "device_label": "PC 2", "app_version": "0.1.0",
    })
    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "device_limit_reached"
