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


def _application(tmp_path, database_name: str = "admin.db", current_version: str = "0.1.0"):
    settings = Settings(
        f"sqlite:///{tmp_path / database_name}",
        Ed25519PrivateKey.generate(),
        "admin-test-pepper-with-enough-entropy",
        30,
        hash_password(ADMIN_PASSWORD, iterations=100_000),
        "admin-session-secret-with-at-least-32-characters",
        current_version,
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
    assert {
        "licenses": summary["licenses"],
        "valid_licenses": summary["valid_licenses"],
        "trials": summary["trials"],
        "active_devices": summary["active_devices"],
        "seat_capacity": summary["seat_capacity"],
    } == {"licenses": 1, "valid_licenses": 1, "trials": 1, "active_devices": 0, "seat_capacity": 1}
    assert summary["current_app_version"] == "0.1.0"
    assert datetime.fromisoformat(summary["updated_at"]).tzinfo is not None
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


def test_dashboard_exposes_safe_device_metadata_and_connection_state(tmp_path, monkeypatch) -> None:
    app = _application(tmp_path, current_version="0.2.0")
    client = _client(app)
    csrf = _login(client)
    created = client.post("/admin/api/licenses", headers={"X-CSRF-Token": csrf}, json={
        "organization": "Cabinet Atlas", "plan": "office", "seats": 2, "days": 20, "trial": False,
    }).json()

    activated = client.post("/v1/activate", json={
        "license_key": created["license_key"], "device_hash": "a" * 64,
        "device_label": "PC Accueil", "app_version": "0.1.4",
        "os_name": "Windows", "os_edition": "Professional", "os_version": "11",
        "os_build": "26100.4946", "architecture": "AMD64",
    })
    assert activated.status_code == 200

    detail = client.get(f"/admin/api/licenses/{created['license_id']}").json()
    device = detail["activations"][0]
    assert device["os_name"] == "Windows"
    assert device["os_edition"] == "Professional"
    assert device["os_version"] == "11"
    assert device["os_build"] == "26100.4946"
    assert device["architecture"] == "AMD64"
    assert device["connection_status"] == "online"
    assert device["outdated"] is True
    assert device["device_hint"] == "AAAAAAAA"
    assert "device_hash" not in device and "secret_digest" not in device

    summary = client.get("/admin/api/summary").json()
    assert summary["online_devices"] == 1
    assert summary["outdated_devices"] == 1
    assert summary["expiring_soon"] == 1
    listed = client.get("/admin/api/licenses").json()["items"][0]
    assert listed["device_labels"] == ["PC Accueil"]

    activation_id = device["id"]
    secret = activated.json()["activation_secret"]
    legacy_refresh = client.post("/v1/refresh", json={
        "activation_id": activation_id, "activation_secret": secret,
        "device_hash": "a" * 64, "app_version": "0.1.5",
    })
    assert legacy_refresh.status_code == 200
    preserved = client.get(f"/admin/api/licenses/{created['license_id']}").json()["activations"][0]
    assert preserved["os_build"] == "26100.4946"

    fixed_now = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("license_server.admin_service.utc_now", lambda: fixed_now)
    with app.state.session_factory() as session:
        activation = session.get(Activation, activation_id)
        activation.last_seen_at = fixed_now - timedelta(minutes=19)
        session.commit()
    online_at_19 = client.get(f"/admin/api/licenses/{created['license_id']}").json()["activations"][0]
    assert online_at_19["connection_status"] == "online"

    with app.state.session_factory() as session:
        activation = session.get(Activation, activation_id)
        activation.last_seen_at = fixed_now - timedelta(minutes=20)
        session.commit()
    offline_at_20 = client.get(f"/admin/api/licenses/{created['license_id']}").json()["activations"][0]
    assert offline_at_20["connection_status"] == "offline"


def test_activity_cursor_pagination_is_complete_and_stable(tmp_path) -> None:
    app = _application(tmp_path)
    client = _client(app)
    _login(client)
    anchor = datetime(2026, 8, 29, 12, 0, tzinfo=timezone.utc)
    with app.state.session_factory() as session:
        session.add_all([
            AuditEvent(id=f"event-{index:03d}", event_type="activate", created_at=anchor - timedelta(seconds=index))
            for index in range(61)
        ])
        session.commit()

    first = client.get("/admin/api/audit?period=all&include_refresh=true&limit=25").json()
    assert len(first["items"]) == 25 and first["total"] == 61
    first_ids = [item["id"] for item in first["items"]]

    with app.state.session_factory() as session:
        session.add(AuditEvent(id="newer-event", event_type="activate", created_at=anchor + timedelta(seconds=1)))
        session.commit()

    second = client.get(
        "/admin/api/audit", params={"period": "all", "include_refresh": True, "limit": 25,
                                    "cursor": first["next_cursor"], "direction": "next"},
    ).json()
    third = client.get(
        "/admin/api/audit", params={"period": "all", "include_refresh": True, "limit": 25,
                                    "cursor": second["next_cursor"], "direction": "next"},
    ).json()
    collected = first_ids + [item["id"] for item in second["items"] + third["items"]]
    assert len(second["items"]) == 25
    assert len(third["items"]) == 11
    assert len(collected) == len(set(collected)) == 61
    assert "newer-event" not in collected
    assert second["previous_cursor"]

    previous = client.get(
        "/admin/api/audit", params={"period": "all", "include_refresh": True, "limit": 25,
                                    "cursor": second["previous_cursor"], "direction": "previous"},
    ).json()
    assert [item["id"] for item in previous["items"]][-24:] == first_ids[1:]


def test_activity_filters_validation_and_csv_export(tmp_path) -> None:
    app = _application(tmp_path)
    client = _client(app)
    csrf = _login(client)
    headers = {"X-CSRF-Token": csrf}
    created = client.post("/admin/api/licenses", headers=headers, json={
        "organization": "Cabinet Recherche", "plan": "individual", "seats": 1, "days": 90, "trial": False,
    }).json()
    activated_response = client.post("/v1/activate", json={
        "license_key": created["license_key"], "device_hash": "b" * 64,
        "device_label": "Portable Terrain", "app_version": "0.1.0",
    })
    activated = activated_response.json()
    activation_id = client.get(f"/admin/api/licenses/{created['license_id']}").json()["activations"][0]["id"]
    client.post("/v1/refresh", json={
        "activation_id": activation_id, "activation_secret": activated["activation_secret"],
        "device_hash": "b" * 64, "app_version": "0.1.0",
    })

    default_events = client.get("/admin/api/audit?period=all").json()["items"]
    assert "refresh" not in {item["event_type"] for item in default_events}
    application = client.get(
        "/admin/api/audit?period=all&origin=application&category=devices&include_refresh=true",
    ).json()
    assert {item["event_type"] for item in application["items"]} == {"activate", "refresh"}
    searched = client.get("/admin/api/audit?period=all&search=Portable%20Terrain").json()["items"]
    assert searched and all(item["device_label"] == "Portable Terrain" for item in searched)

    assert client.get("/admin/api/audit?limit=10").status_code == 400
    assert client.get("/admin/api/audit?period=wrong").status_code == 400
    assert client.get("/admin/api/audit?category=wrong").status_code == 400
    assert client.get("/admin/api/audit?cursor=not-a-cursor&period=all").status_code == 400
    assert client.post("/admin/api/audit/export?period=all").status_code == 403

    exported = client.post("/admin/api/audit/export?period=all&include_refresh=true", headers=headers)
    assert exported.status_code == 200
    assert exported.content.startswith(b"\xef\xbb\xbf")
    text = exported.content.decode("utf-8-sig")
    assert ";" in text and "Cabinet Recherche" in text and "Portable Terrain" in text
    assert created["license_key"] not in text
    assert "bbbbbbbb" not in text.lower()
    assert "attachment; filename=" in exported.headers["content-disposition"]


def test_signed_admin_session_expires() -> None:
    issued_at = datetime(2026, 8, 11, tzinfo=timezone.utc)
    token, claims = issue_session("session-secret", now=issued_at)

    assert verify_session(token, "session-secret", now=issued_at) == claims
    assert verify_session(token + "tampered", "session-secret", now=issued_at) is None
    assert verify_session(token, "session-secret", now=issued_at + timedelta(hours=9)) is None
