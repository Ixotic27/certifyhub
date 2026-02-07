#!/usr/bin/env python
"""Create the PostgreSQL database from `DATABASE_URL` in .env.

Usage:
  python scripts/create_database.py
"""
import os
import sys

# Ensure project root is on sys.path so `app` package can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings
from sqlalchemy.engine import make_url
import argparse
import os
import psycopg2
from psycopg2 import sql
from psycopg2 import OperationalError
from getpass import getpass
import sys


def main():
    url = make_url(settings.DATABASE_URL)
    target_db = url.database
    if not target_db:
        print("No database name found in DATABASE_URL")
        sys.exit(1)

    admin_db = "postgres"

    def try_connect(pw):
        return psycopg2.connect(
            dbname=admin_db,
            user=url.username,
            password=pw,
            host=url.host or "localhost",
            port=url.port or 5432,
        )
    # Accept password from CLI or environment for non-interactive use
    parser = argparse.ArgumentParser()
    parser.add_argument("--password", "-p", help="Postgres admin password")
    args = parser.parse_args()

    pw_source = args.password or os.getenv("POSTGRES_PASSWORD") or url.password

    try:
        # Try with provided password (CLI/env/.env)
        conn = try_connect(pw_source)
        conn.autocommit = True
        cur = conn.cursor()

        cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (target_db,))
        exists = cur.fetchone()
        if exists:
            print(f"Database '{target_db}' already exists.")
        else:
            cur.execute(sql.SQL("CREATE DATABASE {};").format(sql.Identifier(target_db)))
            print(f"Database '{target_db}' created.")

        cur.close()
        conn.close()

    except OperationalError as e:
        # If interactive terminal, prompt for password fallback
        if sys.stdin.isatty():
            print("Password authentication failed. Please enter the Postgres password for user:", url.username)
            pw = getpass()
            try:
                conn = try_connect(pw)
            except Exception as e2:
                print("Error creating database:", e2)
                sys.exit(1)
        else:
            print("Password authentication failed. Provide the password via --password or POSTGRES_PASSWORD env var.")
            sys.exit(1)
    except Exception as e:
        print("Error creating database:", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
