from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


def main() -> int:
    parser = argparse.ArgumentParser(description="Injecte uniquement la configuration publique de licence avant le build.")
    parser.add_argument("--server-url", required=True)
    parser.add_argument("--public-key", required=True, help="Clé publique Ed25519 encodée en base64")
    args = parser.parse_args()
    parsed = urlparse(args.server_url)
    if parsed.scheme != "https" or not parsed.netloc:
        parser.error("--server-url doit être une URL HTTPS complète")
    destination = Path(__file__).resolve().parents[1] / "resources" / "license" / "config.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps({
        "server_url": args.server_url.rstrip("/"),
        "public_key": args.public_key.strip(),
    }, indent=2), encoding="utf-8")
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
