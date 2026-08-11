from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_render_blueprint_uses_free_service_and_external_secrets() -> None:
    blueprint = (ROOT / "render.yaml").read_text(encoding="utf-8")

    for expected in (
        "type: web",
        "runtime: docker",
        "plan: free",
        "region: frankfurt",
        "rootDir: license_server",
        "dockerfilePath: ./license_server/Dockerfile",
        "healthCheckPath: /health",
    ):
        assert expected in blueprint
    for secret in ("DATABASE_URL", "LICENSE_SIGNING_PRIVATE_KEY", "LICENSE_KEY_PEPPER"):
        assert f"key: {secret}\n        sync: false" in blueprint
    assert "POSTGRES_PASSWORD=" not in blueprint
    assert "postgresql://" not in blueprint


def test_license_container_uses_render_port_with_local_fallback() -> None:
    dockerfile = (ROOT / "license_server" / "Dockerfile").read_text(encoding="utf-8")

    assert "${PORT:-8000}" in dockerfile
