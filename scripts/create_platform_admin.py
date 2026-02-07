"""
Script to create a Platform Admin
Run this to create the first admin user
"""

import sys
import asyncio
import uuid
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import database, connect_db, disconnect_db
from app.auth import hash_password, generate_random_password


async def create_platform_admin(email: str, full_name: str, password: str = None):
    """
    Create a platform admin user
    
    Args:
        email: Admin email
        full_name: Admin full name
        password: Password (if None, will generate random)
    """
    
    await connect_db()
    
    try:
        # Check if admin already exists
        existing = await database.fetch_one(
            "SELECT id FROM platform_admins WHERE email = :email",
            {"email": email}
        )
        
        if existing:
            print(f"❌ Platform admin with email {email} already exists!")
            return
        
        # Generate password if not provided
        if password is None:
            password = generate_random_password(12)
            generated = True
        else:
            generated = False
        
        # Hash password
        password_hash = hash_password(password)
        
        # Generate UUID for new admin
        admin_id = str(uuid.uuid4())
        
        # Insert admin
        await database.execute(
            """
            INSERT INTO platform_admins (id, email, password_hash, full_name, must_change_password)
            VALUES (:id, :email, :password_hash, :full_name, :must_change_password)
            """,
            {
                "id": admin_id,
                "email": email,
                "password_hash": password_hash,
                "full_name": full_name,
                "must_change_password": generated
            }
        )
        
        print("✅ Platform Admin created successfully!")
        print(f"   Email: {email}")
        print(f"   Name: {full_name}")
        
        if generated:
            print(f"   Password: {password}")
            print("   ⚠️  IMPORTANT: Save this password! User must change it on first login.")
        else:
            print("   Password: (custom password set)")
        
    except Exception as e:
        print(f"❌ Error creating platform admin: {e}")
    
    finally:
        await disconnect_db()


async def main():
    """Main function"""
    print("\n" + "="*60)
    print("CREATE PLATFORM ADMIN")
    print("="*60 + "\n")
    
    # Get input
    email = input("Enter email: ").strip()
    full_name = input("Enter full name: ").strip()
    
    use_custom = input("Set custom password? (y/n): ").strip().lower()
    
    if use_custom == 'y':
        password = input("Enter password: ").strip()
        confirm = input("Confirm password: ").strip()
        
        if password != confirm:
            print("❌ Passwords do not match!")
            return
        
        if len(password) < 8:
            print("❌ Password must be at least 8 characters!")
            return
    else:
        password = None
    
    print("\n")
    await create_platform_admin(email, full_name, password)
    print("\n")


if __name__ == "__main__":
    asyncio.run(main())