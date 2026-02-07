"""
Seed a demo Club Admin account for testing
"""

import sys
import asyncio
import uuid
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import database, connect_db, disconnect_db
from app.auth import hash_password

DEFAULTS = {
    "club_name": "Demo Club",
    "club_slug": "demo-club",
    "contact_email": "demo@certifyhub.com",
    "admin_email": "clubadmin@certifyhub.com",
    "admin_name": "Club Administrator",
    "admin_password": "SecurePass123"
}


async def seed_club_admin():
    await connect_db()

    try:
        # Ensure club exists
        club = await database.fetch_one(
            "SELECT id FROM clubs WHERE slug = :slug",
            {"slug": DEFAULTS["club_slug"]}
        )

        if not club:
            club_id = str(uuid.uuid4())
            await database.execute(
                """
                INSERT INTO clubs (id, name, slug, contact_email, logo_url, is_active)
                VALUES (:id, :name, :slug, :contact_email, NULL, TRUE)
                """,
                {
                    "id": club_id,
                    "name": DEFAULTS["club_name"],
                    "slug": DEFAULTS["club_slug"],
                    "contact_email": DEFAULTS["contact_email"]
                }
            )
        else:
            club_id = str(club["id"])

        # Check if admin already exists
        existing = await database.fetch_one(
            "SELECT id FROM club_administrators WHERE email = :email",
            {"email": DEFAULTS["admin_email"]}
        )

        if existing:
            print("✅ Club admin already exists:")
            print(f"   Email: {DEFAULTS['admin_email']}")
            return

        # Create club admin
        admin_id = str(uuid.uuid4())
        password_hash = hash_password(DEFAULTS["admin_password"])

        await database.execute(
            """
            INSERT INTO club_administrators
            (id, club_id, email, password_hash, full_name, must_change_password)
            VALUES (:id, :club_id, :email, :password_hash, :full_name, FALSE)
            """,
            {
                "id": admin_id,
                "club_id": club_id,
                "email": DEFAULTS["admin_email"],
                "password_hash": password_hash,
                "full_name": DEFAULTS["admin_name"]
            }
        )

        print("✅ Demo Club Admin created successfully!")
        print(f"   Email: {DEFAULTS['admin_email']}")
        print(f"   Password: {DEFAULTS['admin_password']}")

    finally:
        await disconnect_db()


if __name__ == "__main__":
    asyncio.run(seed_club_admin())
