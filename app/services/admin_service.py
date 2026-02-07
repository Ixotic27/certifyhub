"""
Admin Service
Business logic for admin management
"""

import uuid
from app.database import database
from app.auth import hash_password, generate_random_password
from app.services.email_service import email_service
from app.schemas.admin import CreateClubAdminRequest
from fastapi import HTTPException, status


class AdminService:
    """Service for admin management operations"""
    
    @staticmethod
    async def create_club_admin(
        club_id: str,
        data: CreateClubAdminRequest
    ) -> dict:
        """
        Create a new club admin
        
        Generates random password and sends welcome email
        """
        
        # Check if club exists
        club = await database.fetch_one(
            "SELECT id, name FROM clubs WHERE id = :club_id",
            {"club_id": club_id}
        )
        
        if not club:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found"
            )
        
        # Check if email already exists
        existing = await database.fetch_one(
            "SELECT id FROM club_administrators WHERE email = :email",
            {"email": data.email}
        )
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{data.email}' is already registered"
            )
        
        # Generate password and hash it
        temp_password = generate_random_password(12)
        password_hash = hash_password(temp_password)
        
        # Create admin
        admin_id = str(uuid.uuid4())
        
        try:
            await database.execute(
                """
                INSERT INTO club_administrators 
                (id, club_id, email, password_hash, full_name, must_change_password)
                VALUES (:id, :club_id, :email, :password_hash, :full_name, TRUE)
                """,
                {
                    "id": admin_id,
                    "club_id": club_id,
                    "email": data.email,
                    "password_hash": password_hash,
                    "full_name": data.full_name
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create admin: {str(e)}"
            )
        
        # Send welcome email asynchronously (fire and forget)
        import asyncio
        asyncio.create_task(
            email_service.send_welcome_email(
                admin_email=data.email,
                admin_name=data.full_name,
                club_name=club["name"],
                temp_password=temp_password
            )
        )
        
        # Fetch created admin to get the auto-generated created_at timestamp
        admin = await database.fetch_one(
            "SELECT * FROM club_administrators WHERE id = :admin_id",
            {"admin_id": admin_id}
        )
        
        # Return admin details with temp password
        admin_dict = dict(admin) if admin else {}
        admin_dict["temp_password"] = temp_password
        return admin_dict
    
    @staticmethod
    async def get_club_admins(club_id: str, skip: int = 0, limit: int = 50) -> dict:
        """Get all admins for a club"""
        
        # Check if club exists
        club = await database.fetch_one(
            "SELECT id FROM clubs WHERE id = :club_id",
            {"club_id": club_id}
        )
        
        if not club:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found"
            )
        
        # Get total count
        total = await database.fetch_val(
            "SELECT COUNT(*) FROM club_administrators WHERE club_id = :club_id",
            {"club_id": club_id}
        )
        
        # Get paginated admins
        admins = await database.fetch_all(
            """
            SELECT * FROM club_administrators 
            WHERE club_id = :club_id
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :skip
            """,
            {"club_id": club_id, "skip": skip, "limit": limit}
        )
        
        return {
            "club_id": str(club_id),
            "total": total or 0,
            "admins": [dict(admin) for admin in admins]
        }
    
    @staticmethod
    async def deactivate_admin(admin_id: str) -> dict:
        """Deactivate a club admin"""
        
        # Check if admin exists
        admin = await database.fetch_one(
            "SELECT * FROM club_administrators WHERE id = :admin_id",
            {"admin_id": admin_id}
        )
        
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin not found"
            )
        
        # Deactivate admin
        await database.execute(
            "UPDATE club_administrators SET is_active = FALSE WHERE id = :admin_id",
            {"admin_id": admin_id}
        )
        
        # Fetch updated admin
        updated_admin = await database.fetch_one(
            "SELECT * FROM club_administrators WHERE id = :admin_id",
            {"admin_id": admin_id}
        )
        
        return dict(updated_admin)

    @staticmethod
    async def get_dashboard_stats(club_id: str) -> dict:
        """Get club admin dashboard statistics"""

        # Check club exists
        club = await database.fetch_one(
            "SELECT id FROM clubs WHERE id = :club_id",
            {"club_id": club_id}
        )

        if not club:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found"
            )

        total_templates = await database.fetch_val(
            "SELECT COUNT(*) FROM certificate_templates WHERE club_id = :club_id",
            {"club_id": club_id}
        )

        active_templates = await database.fetch_val(
            "SELECT COUNT(*) FROM certificate_templates WHERE club_id = :club_id AND is_active = TRUE",
            {"club_id": club_id}
        )

        total_attendees = await database.fetch_val(
            "SELECT COUNT(*) FROM attendees WHERE club_id = :club_id",
            {"club_id": club_id}
        )

        certificates_generated = await database.fetch_val(
            "SELECT COUNT(*) FROM certificate_generations WHERE club_id = :club_id",
            {"club_id": club_id}
        )

        never_generated = await database.fetch_val(
            """
            SELECT COUNT(*) FROM attendees
            WHERE club_id = :club_id
              AND COALESCE(certificate_generated_count, 0) = 0
            """,
            {"club_id": club_id}
        )

        trend = await database.fetch_all(
            """
            SELECT DATE(generated_at) AS date, COUNT(DISTINCT attendee_id) AS count
            FROM certificate_generations
            WHERE club_id = :club_id
              AND generated_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(generated_at)
            ORDER BY date
            """,
            {"club_id": club_id}
        )

        top_downloaded = await database.fetch_all(
            """
            SELECT name, student_id, certificate_generated_count
            FROM attendees
            WHERE club_id = :club_id
              AND COALESCE(certificate_generated_count, 0) > 0
            ORDER BY certificate_generated_count DESC
            LIMIT 10
            """,
            {"club_id": club_id}
        )

        # Storage usage
        template_bytes = await database.fetch_val(
            "SELECT COALESCE(SUM(image_size_bytes), 0) FROM certificate_templates WHERE club_id = :club_id",
            {"club_id": club_id}
        )
        import_bytes = await database.fetch_val(
            "SELECT COALESCE(SUM(file_size_bytes), 0) FROM attendee_imports WHERE club_id = :club_id",
            {"club_id": club_id}
        )
        storage_used_bytes = int(template_bytes or 0) + int(import_bytes or 0)
        storage_limit_bytes = 100 * 1024 * 1024  # 100 MB

        return {
            "club_id": club_id,
            "total_templates": total_templates or 0,
            "active_templates": active_templates or 0,
            "total_attendees": total_attendees or 0,
            "certificates_generated": certificates_generated or 0,
            "never_generated": never_generated or 0,
            "trend_7_days": [dict(row) for row in trend],
            "top_downloaded": [dict(row) for row in top_downloaded],
            "storage_used_bytes": storage_used_bytes,
            "storage_limit_bytes": storage_limit_bytes
        }


# Create singleton instance
admin_service = AdminService()
