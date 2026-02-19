#!/usr/bin/env python3
import argparse
import sys
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import text

from app import app, db
from app.models import Source, Country


def mask_db_uri(uri: str) -> str:
    if not uri:
        return "<empty>"
    try:
        parsed = urlsplit(uri)
        if parsed.password is None:
            return uri

        netloc = parsed.netloc
        creds = f"{parsed.username}:{parsed.password}@"
        if creds in netloc:
            netloc = netloc.replace(creds, f"{parsed.username}:****@")
            return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
    except Exception:
        pass
    return uri


def main() -> int:
    parser = argparse.ArgumentParser(description="Check stats-admin database connectivity and basic reads")
    parser.add_argument(
        "--show-uri",
        action="store_true",
        help="show full SQLALCHEMY_DATABASE_URI (default masks password)",
    )
    args = parser.parse_args()

    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    shown_uri = db_uri if args.show_uri else mask_db_uri(db_uri)

    print(f"SQLALCHEMY_DATABASE_URI={shown_uri}")

    try:
        with app.app_context():
            with db.engine.connect() as conn:
                one = conn.execute(text("SELECT 1")).scalar()
                print(f"SELECT 1 -> {one}")

                try:
                    database_name = conn.execute(text("SELECT DATABASE()")).scalar()
                    print(f"DATABASE() -> {database_name}")
                except Exception:
                    print("DATABASE() -> <not available for this dialect>")

            source_count = db.session.query(Source).count()
            country_count = db.session.query(Country).count()
            print(f"Source count -> {source_count}")
            print(f"Country count -> {country_count}")
    except Exception as exc:
        print(f"DB check FAILED: {exc}")
        return 1

    print("DB check OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
