from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "license_server" / "src"))

from license_server.signing import sign_claims  # noqa: E402


KEY_PREFIX = "COPRO-TRIAL-"
DEVICE_HASH = "portable-offline-trial"
ACTIVATION_PREFIX = "offline-trial-activation-"
LICENSE_PREFIX = "offline-trial-license-"
PERMISSIONS = ["create", "import_cad", "generate_docx"]


def _load_or_create_private_key(path: Path) -> Ed25519PrivateKey:
    if path.exists():
        raw = base64.b64decode(path.read_text(encoding="ascii").strip())
        return Ed25519PrivateKey.from_private_bytes(raw)
    private_key = Ed25519PrivateKey.generate()
    raw = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(base64.b64encode(raw).decode("ascii"), encoding="ascii")
    return private_key


def _write_public_config(private_key: Ed25519PrivateKey, path: Path) -> None:
    public_raw = private_key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "server_url": "https://licence.example.invalid",
                "public_key": base64.b64encode(public_raw).decode("ascii"),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _create_trial_code(private_key: Ed25519PrivateKey, days: int) -> tuple[str, datetime, datetime]:
    issued_at = datetime.now(timezone.utc).replace(microsecond=0)
    expires_at = issued_at + timedelta(days=days)
    identifier = str(uuid4())
    claims = {
        "license_id": LICENSE_PREFIX + identifier,
        "activation_id": ACTIVATION_PREFIX + identifier,
        "device_hash": DEVICE_HASH,
        "plan": "individual",
        "trial": True,
        "permissions": PERMISSIONS,
        "issued_at": issued_at.isoformat(),
        "lease_expires_at": expires_at.isoformat(),
        "commercial_expires_at": expires_at.isoformat(),
        "server_time": issued_at.isoformat(),
        "token_id": str(uuid4()),
    }
    return KEY_PREFIX + sign_claims(private_key, claims), issued_at, expires_at


def _write_tester_file(path: Path, code: str, issued_at: datetime, expires_at: datetime, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"""COPRO AUTO — ESSAI HORS LIGNE DE 30 JOURS

Testeur : {label}
Début : {issued_at.astimezone().strftime('%d/%m/%Y %H:%M %Z')}
Expiration : {expires_at.astimezone().strftime('%d/%m/%Y %H:%M %Z')}

CLÉ D'ESSAI (copier la ligne complète) :
{code}

ACTIVATION
1. Lancez CoproAuto.exe.
2. Cliquez sur le bouton de licence en bas à gauche.
3. Collez la clé complète ci-dessus.
4. Cliquez sur « Activer cette licence ».

Cette clé fonctionne hors ligne et donne accès à la création, à l'import CAD
et à la génération DOCX pendant 30 jours. Après expiration, les dossiers
existants restent consultables. Cette clé est réservée au testeur indiqué.
"""
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prépare une clé d'essai Copro Auto hors ligne de 30 jours.")
    parser.add_argument(
        "--private-key-file",
        type=Path,
        default=ROOT / "packaging" / "offline_trial_signing.key",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "resources" / "license" / "config.json",
    )
    parser.add_argument("--out", type=Path)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--label", default="Topographe testeur")
    args = parser.parse_args()
    if args.days < 1 or args.days > 30:
        parser.error("--days doit être compris entre 1 et 30")

    private_key = _load_or_create_private_key(args.private_key_file.resolve())
    _write_public_config(private_key, args.config.resolve())
    print(f"Configuration publique : {args.config.resolve()}")
    if args.out is not None:
        code, issued_at, expires_at = _create_trial_code(private_key, args.days)
        _write_tester_file(args.out.resolve(), code, issued_at, expires_at, args.label)
        print(f"Fichier testeur : {args.out.resolve()}")
        print(f"Expiration UTC : {expires_at.isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
