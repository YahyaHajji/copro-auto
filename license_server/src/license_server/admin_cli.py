from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from .config import Settings
from .models import Activation, License
from .service import LicenseService


def main() -> int:
    parser = argparse.ArgumentParser(description="Administration des licences Copro Auto")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("organization")
    create.add_argument("--kind", choices=("individual", "office"), default="individual")
    create.add_argument("--plan", choices=("individual", "office"), default="individual")
    create.add_argument("--seats", type=int, default=2)
    create.add_argument("--days", type=int, default=30)
    create.add_argument("--trial", action="store_true")
    renew = commands.add_parser("renew")
    renew.add_argument("license_id")
    renew.add_argument("--days", type=int, required=True)
    revoke = commands.add_parser("revoke")
    revoke.add_argument("license_id")
    release = commands.add_parser("release")
    release.add_argument("activation_id")
    args = parser.parse_args()
    settings = Settings.from_environment()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    service = LicenseService(settings)
    with Session(engine) as session:
        if args.command == "create":
            expires = datetime.now(timezone.utc) + timedelta(days=args.days)
            record, key = service.create_license(session, args.organization, args.kind, args.plan, args.seats, expires, args.trial)
            print(f"license_id={record.id}")
            print(f"license_key={key}")
        elif args.command == "renew":
            record = session.get(License, args.license_id)
            if record is None:
                raise SystemExit("Licence introuvable")
            base = max(datetime.now(timezone.utc), record.commercial_expires_at)
            record.commercial_expires_at = base + timedelta(days=args.days)
            record.status = "active"
            session.commit()
            print("renewed")
        elif args.command == "revoke":
            record = session.get(License, args.license_id)
            if record is None:
                raise SystemExit("Licence introuvable")
            record.status = "revoked"
            session.commit()
            print("revoked")
        else:
            activation = session.get(Activation, args.activation_id)
            if activation is None:
                raise SystemExit("Activation introuvable")
            activation.status = "deactivated"
            activation.deactivated_at = datetime.now(timezone.utc)
            session.commit()
            print("released")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
