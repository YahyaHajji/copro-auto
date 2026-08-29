from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from psycopg import sql
from sqlalchemy.engine import make_url

from license_server.app import create_app
from license_server.config import Settings


pytestmark = pytest.mark.postgres


@pytest.fixture
def postgres_url() -> str:
    value = os.environ.get("TEST_POSTGRES_URL", "")
    if not value:
        pytest.skip("TEST_POSTGRES_URL is not configured")
    database = make_url(value).database or ""
    if not database.startswith("copro_auto_test_"):
        pytest.fail("TEST_POSTGRES_URL must target a disposable copro_auto_test_* database")
    return value


def _connection_parameters(postgres_url: str, *, database: str | None = None) -> dict:
    parsed = make_url(postgres_url)
    return {
        "host": parsed.host or "127.0.0.1",
        "port": parsed.port or 5432,
        "user": parsed.username,
        "password": parsed.password,
        "dbname": database or parsed.database,
    }


def _migration_sql() -> str:
    migrations = Path(__file__).parents[1] / "migrations"
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(migrations.glob("*.sql")))


def _reset_and_migrate(postgres_url: str) -> None:
    with psycopg.connect(**_connection_parameters(postgres_url), autocommit=True) as connection:
        connection.execute("DROP SCHEMA public CASCADE")
        connection.execute("CREATE SCHEMA public")
        connection.execute(_migration_sql())


def test_initial_migration_is_idempotent_on_real_postgresql(postgres_url) -> None:
    _reset_and_migrate(postgres_url)
    with psycopg.connect(**_connection_parameters(postgres_url), autocommit=True) as connection:
        connection.execute(_migration_sql())
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'",
            ).fetchall()
        }
        activation_columns = {
            row[0]
            for row in connection.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'activations'",
            ).fetchall()
        }
        indexes = {
            row[0]
            for row in connection.execute(
                "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'",
            ).fetchall()
        }

    assert tables == {
        "organizations", "licenses", "activations", "audit_events", "activation_attempts",
        "admin_login_attempts",
    }
    assert {"os_name", "os_edition", "os_version", "os_build", "architecture"} <= activation_columns
    assert "ix_audit_events_created_id" in indexes

    settings = Settings(postgres_url, Ed25519PrivateKey.generate(), "postgres-test-pepper", 30)
    app = create_app(settings)
    with app.state.session_factory() as session:
        _record, key = app.state.license_service.create_license(
            session,
            "PostgreSQL Integration",
            "individual",
            "individual",
            1,
            datetime.now(timezone.utc) + timedelta(days=30),
            True,
        )
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.post("/v1/activate", json={
        "license_key": key,
        "device_hash": "a" * 64,
        "device_label": "PostgreSQL test",
        "app_version": "0.1.0",
    }).status_code == 200


def test_backup_script_dump_can_be_restored(postgres_url, tmp_path) -> None:
    pg_bin_value = os.environ.get("TEST_POSTGRES_BIN", "")
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if not pg_bin_value or not powershell:
        pytest.skip("TEST_POSTGRES_BIN and PowerShell are required")
    pg_bin = Path(pg_bin_value)
    pg_dump = pg_bin / ("pg_dump.exe" if os.name == "nt" else "pg_dump")
    psql = pg_bin / ("psql.exe" if os.name == "nt" else "psql")
    if not pg_dump.is_file() or not psql.is_file():
        pytest.skip("PostgreSQL backup tools were not found")

    _reset_and_migrate(postgres_url)
    marker = str(uuid4())
    source = _connection_parameters(postgres_url)
    with psycopg.connect(**source, autocommit=True) as connection:
        connection.execute(
            "INSERT INTO organizations (id, name, kind, created_at) VALUES (%s, %s, %s, %s)",
            (marker, "Backup Restore Marker", "individual", datetime.now(timezone.utc)),
        )

    environment_file = tmp_path / ".env"
    environment_file.write_text(
        "\n".join([
            f"POSTGRES_DB={source['dbname']}",
            f"POSTGRES_USER={source['user']}",
            "POSTGRES_PASSWORD=unused-test-password",
            f"PGHOST={source['host']}",
            f"PGPORT={source['port']}",
        ]) + "\n",
        encoding="utf-8",
    )
    output_directory = tmp_path / "backups"
    backup_script = Path(__file__).parents[2] / "deploy" / "license_server" / "backup.ps1"
    completed = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(backup_script),
            "-OutputDirectory",
            str(output_directory),
            "-EnvironmentFile",
            str(environment_file),
            "-PgDumpExecutable",
            str(pg_dump),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    backup_path = Path(completed.stdout.strip().splitlines()[-1])
    assert backup_path.is_file()
    assert backup_path.stat().st_size > 0

    restore_database = f"copro_auto_test_restore_{uuid4().hex[:8]}"
    admin = _connection_parameters(postgres_url, database="postgres")
    with psycopg.connect(**admin, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(restore_database)))
    try:
        restore_environment = os.environ.copy()
        if source["password"]:
            restore_environment["PGPASSWORD"] = source["password"]
        subprocess.run(
            [
                str(psql),
                "-h",
                str(source["host"]),
                "-p",
                str(source["port"]),
                "-U",
                str(source["user"]),
                "-d",
                restore_database,
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                str(backup_path),
            ],
            check=True,
            capture_output=True,
            env=restore_environment,
        )
        with psycopg.connect(**_connection_parameters(postgres_url, database=restore_database)) as restored:
            count = restored.execute("SELECT count(*) FROM organizations WHERE id = %s", (marker,)).fetchone()[0]
        assert count == 1
    finally:
        with psycopg.connect(**admin, autocommit=True) as connection:
            connection.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(restore_database)))
