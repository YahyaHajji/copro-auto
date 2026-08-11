from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from copro_auto.licensing.token_store import TokenVerifier
from license_server.admin_cli import release_activation
from license_server.app import create_app
from license_server.config import Settings
from license_server.models import License


def _application(tmp_path):
    private = Ed25519PrivateKey.generate()
    settings = Settings(f"sqlite:///{tmp_path / 'licenses.db'}", private, "test-pepper-with-enough-entropy", 30)
    app = create_app(settings, create_schema=True)
    public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    verifier = TokenVerifier(base64.b64encode(public).decode("ascii"))
    return app, verifier


def _create_license(
    app, *, seats: int = 2, status: str = "active", expires_at: datetime | None = None,
) -> str:
    with app.state.session_factory() as session:
        record, key = app.state.license_service.create_license(
            session, "Cabinet Atlas", "office", "office", seats,
            expires_at or datetime.now(timezone.utc) + timedelta(days=180), False,
        )
        record.status = status
        session.commit()
        return key


def _activate(client: TestClient, key: str, device: str = "a" * 64):
    return client.post("/v1/activate", json={
        "license_key": key, "device_hash": device, "device_label": "PC Bureau", "app_version": "0.1.0",
    })


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


@pytest.mark.parametrize(
    ("status", "expires_at", "expected_code"),
    [
        ("revoked", None, "revoked"),
        ("active", datetime.now(timezone.utc) - timedelta(minutes=1), "expired"),
    ],
)
def test_revoked_and_expired_licenses_cannot_activate(tmp_path, status, expires_at, expected_code) -> None:
    app, _verifier = _application(tmp_path)
    key = _create_license(app, status=status, expires_at=expires_at)

    response = _activate(TestClient(app), key)

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == expected_code


@pytest.mark.parametrize(
    ("status", "expires_at", "expected_code"),
    [
        ("revoked", None, "revoked"),
        ("active", datetime.now(timezone.utc) - timedelta(minutes=1), "expired"),
    ],
)
def test_refresh_rejects_revoked_or_expired_license(tmp_path, status, expires_at, expected_code) -> None:
    app, verifier = _application(tmp_path)
    key = _create_license(app)
    client = TestClient(app)
    activation = _activate(client, key)
    body = activation.json()
    claims = verifier.verify(body["token"])
    with app.state.session_factory() as session:
        license_record = session.scalar(select(License))
        license_record.status = status
        if expires_at is not None:
            license_record.commercial_expires_at = expires_at
        session.commit()

    response = client.post("/v1/refresh", json={
        "activation_id": claims.activation_id,
        "activation_secret": body["activation_secret"],
        "device_hash": "a" * 64,
        "app_version": "0.1.1",
    })

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == expected_code


def test_refresh_rejects_device_mismatch(tmp_path) -> None:
    app, verifier = _application(tmp_path)
    key = _create_license(app)
    client = TestClient(app)
    activation = _activate(client, key)
    body = activation.json()
    claims = verifier.verify(body["token"])

    response = client.post("/v1/refresh", json={
        "activation_id": claims.activation_id,
        "activation_secret": body["activation_secret"],
        "device_hash": "b" * 64,
        "app_version": "0.1.1",
    })

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "device_mismatch"


def test_deactivation_releases_a_seat_for_another_device(tmp_path) -> None:
    app, verifier = _application(tmp_path)
    key = _create_license(app, seats=1)
    client = TestClient(app)
    activation = _activate(client, key)
    body = activation.json()
    claims = verifier.verify(body["token"])

    released = client.post("/v1/deactivate", json={
        "activation_id": claims.activation_id,
        "activation_secret": body["activation_secret"],
    })
    replacement = _activate(client, key, "b" * 64)

    assert released.status_code == 200
    assert replacement.status_code == 200


def test_administrator_release_frees_a_seat(tmp_path) -> None:
    app, verifier = _application(tmp_path)
    key = _create_license(app, seats=1)
    client = TestClient(app)
    activation = _activate(client, key)
    claims = verifier.verify(activation.json()["token"])

    with app.state.session_factory() as session:
        release_activation(session, claims.activation_id)

    replacement = _activate(client, key, "b" * 64)
    assert replacement.status_code == 200


def test_activation_rate_limit_blocks_the_twenty_first_attempt(tmp_path) -> None:
    app, _verifier = _application(tmp_path)
    client = TestClient(app)
    payload = {
        "license_key": "COPRO-INVALID-KEY",
        "device_hash": "a" * 64,
        "device_label": "PC Bureau",
        "app_version": "0.1.0",
    }

    responses = [client.post("/v1/activate", json=payload) for _ in range(21)]

    assert all(response.status_code == 404 for response in responses[:20])
    assert responses[20].status_code == 429
    assert responses[20].json()["detail"]["code"] == "rate_limited"
    assert responses[20].headers["X-Content-Type-Options"] == "nosniff"
    assert responses[20].headers["Cache-Control"] == "no-store"


def test_activation_rate_limit_is_shared_between_serverless_instances(tmp_path) -> None:
    private = Ed25519PrivateKey.generate()
    settings = Settings(
        f"sqlite:///{tmp_path / 'shared-licenses.db'}",
        private,
        "shared-test-pepper-with-enough-entropy",
        30,
    )
    first = TestClient(create_app(settings, create_schema=True))
    second = TestClient(create_app(settings))
    payload = {
        "license_key": "COPRO-INVALID-KEY",
        "device_hash": "a" * 64,
        "device_label": "PC Bureau",
        "app_version": "0.1.0",
    }

    responses = [
        (first if index % 2 == 0 else second).post("/v1/activate", json=payload)
        for index in range(20)
    ]
    blocked = second.post("/v1/activate", json=payload)

    assert all(response.status_code == 404 for response in responses)
    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "rate_limited"


def test_health_checks_database_connectivity(tmp_path) -> None:
    app, _verifier = _application(tmp_path)
    client = TestClient(app)
    assert client.get("/health").status_code == 200

    class UnavailableDatabase:
        def connect(self):
            raise OperationalError("SELECT 1", {}, RuntimeError("database unavailable"))

    app.state.database_engine = UnavailableDatabase()
    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
