from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import select

from license_server.admin_auth import hash_password, issue_session, verify_session
from license_server.app import create_app
from license_server.config import Settings
from license_server.models import Activation, AuditEvent, License


ADMIN_PASSWORD = "correct-horse-battery-staple"


def _application(tmp_path, database_name: str = "admin.db"):
    settings = Settings(
        f"sqlite:///{tmp_path / database_name}",
        Ed25519PrivateKey.generate(),
        "admin-test-pepper-with-enough-entropy",
        30,
        hash_password(ADMIN_PASSWORD, iterations=100_000),
        "admin-session-secret-with-at-least-32-characters",
    )
    return create_app(settings, create_schema=True)


def _client(app) -> TestClient:
    return TestClient(app, base_url="https://testserver")


def _login(client: TestClient) -> str:
    response = client.post("/admin/api/login", json={"password": ADMIN_PASSWORD})
    assert response.status_code == 200
    return response.json()["csrf"]


def test_admin_login_session_csrf_and_security_headers(tmp_path) -> None:
    client = _client(_application(tmp_path))

    assert client.get("/admin/api/licenses").status_code == 401
    failed = client.post("/admin/api/login", json={"password": "wrong-password"})
    assert failed.status_code == 401

    response = client.post("/admin/api/login", json={"password": ADMIN_PASSWORD})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert client.get("/admin/api/session").json()["authenticated"] is True

    missing_csrf = client.post("/admin/api/licenses", json={
        "organization": "Cabinet Atlas", "plan": "individual", "seats": 2, "days": 30, "trial": True,
    })
    assert missing_csrf.status_code == 403

    csrf = response.json()["csrf"]
    logout = client.post("/admin/api/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 200
    assert client.get("/admin/api/licenses").status_code == 401


def test_admin_login_rate_limit_is_database_backed(tmp_path) -> None:
    app = _application(tmp_path, "shared-admin.db")
    first = _client(app)
    second = _client(create_app(app.state.settings))

    responses = [
        (first if index % 2 == 0 else second).post(
            "/admin/api/login", json={"password": "wrong-password"}, headers={"x-forwarded-for": "198.51.100.4"},
        )
        for index in range(5)
    ]
    blocked = second.post(
        "/admin/api/login", json={"password": ADMIN_PASSWORD}, headers={"x-forwarded-for": "198.51.100.4"},
    )

    assert all(response.status_code == 401 for response in responses)
    assert blocked.status_code == 429


def test_admin_can_manage_full_license_lifecycle(tmp_path) -> None:
    app = _application(tmp_path)
    client = _client(app)
    csrf = _login(client)
    headers = {"X-CSRF-Token": csrf}

    created = client.post("/admin/api/licenses", headers=headers, json={
        "organization": "Cabinet Démonstration", "plan": "individual", "seats": 1, "days": 30, "trial": True,
    })
    assert created.status_code == 200
    created_body = created.json()
    assert created_body["license_key"].startswith("COPRO-")
    license_id = created_body["license_id"]

    listed = client.get("/admin/api/licenses")
    assert listed.status_code == 200
    assert listed.json()["items"][0]["organization"] == "Cabinet Démonstration"
    assert "license_key" not in listed.text

    activated = client.post("/v1/activate", json={
        "license_key": created_body["license_key"], "device_hash": "d" * 64,
        "device_label": "Portable test", "app_version": "0.1.0",
    })
    assert activated.status_code == 200
    detail = client.get(f"/admin/api/licenses/{license_id}").json()
    assert detail["active_devices"] == 1
    activation_id = detail["activations"][0]["id"]

    before = datetime.fromisoformat(detail["commercial_expires_at"])
    renewed = client.post(f"/admin/api/licenses/{license_id}/renew", headers=headers, json={"days": 30})
    assert renewed.status_code == 200
    assert datetime.fromisoformat(renewed.json()["expires_at"]) >= before + timedelta(days=29)

    revoked = client.post(f"/admin/api/licenses/{license_id}/revoke", headers=headers)
    assert revoked.json()["status"] == "revoked"
    reactivated = client.post(f"/admin/api/licenses/{license_id}/reactivate", headers=headers)
    assert reactivated.json()["status"] == "active"
    released = client.post(f"/admin/api/activations/{activation_id}/release", headers=headers)
    assert released.json()["status"] == "deactivated"

    summary = client.get("/admin/api/summary").json()
    assert summary == {"licenses": 1, "valid_licenses": 1, "trials": 1, "active_devices": 0}
    audit = client.get("/admin/api/audit").json()["items"]
    event_types = {event["event_type"] for event in audit}
    assert {"license_created", "admin_license_renewed", "admin_license_revoked", "admin_license_reactivated", "admin_activation_released"} <= event_types

    with app.state.session_factory() as session:
        assert session.get(License, license_id).status == "active"
        assert session.get(Activation, activation_id).status == "deactivated"
        assert session.scalars(select(AuditEvent)).all()


def test_admin_page_and_assets_are_available(tmp_path) -> None:
    client = _client(_application(tmp_path))
    page = client.get("/admin")
    stylesheet = client.get("/admin/static/admin.css")
    script = client.get("/admin/static/admin.js")

    assert page.status_code == stylesheet.status_code == script.status_code == 200
    assert "Administration des licences" in page.text
    assert "Nouvelle licence" in page.text
    assert "default-src 'self'" in page.headers["Content-Security-Policy"]
    assert "DATABASE_URL" not in script.text
    assert "LICENSE_SIGNING_PRIVATE_KEY" not in script.text


def test_signed_admin_session_expires() -> None:
    issued_at = datetime(2026, 8, 11, tzinfo=timezone.utc)
    token, claims = issue_session("session-secret", now=issued_at)

    assert verify_session(token, "session-secret", now=issued_at) == claims
    assert verify_session(token + "tampered", "session-secret", now=issued_at) is None
    assert verify_session(token, "session-secret", now=issued_at + timedelta(hours=9)) is None
