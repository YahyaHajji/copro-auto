from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_vercel_has_a_fastapi_entrypoint_without_embedded_secrets() -> None:
    entrypoint = (ROOT / "license_server" / "app.py").read_text(encoding="utf-8")
    project = (ROOT / "license_server" / "pyproject.toml").read_text(encoding="utf-8")

    assert "from license_server.app import create_app" in entrypoint
    assert 'Path(__file__).parent / "src"' in entrypoint
    assert "app = create_app()" in entrypoint
    assert '[tool.vercel]' in project
    assert 'entrypoint = "app:app"' in project
    for secret in ("DATABASE_URL", "LICENSE_SIGNING_PRIVATE_KEY", "LICENSE_KEY_PEPPER"):
        assert secret not in entrypoint
        assert secret not in project


def test_render_blueprint_is_not_part_of_the_vercel_deployment() -> None:
    assert not (ROOT / "render.yaml").exists()
