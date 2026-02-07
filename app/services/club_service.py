"""
Club Service
Business logic for club management
"""

from app.database import database
from app.schemas.club import CreateClubRequest, ClubResponse
from fastapi import HTTPException, status
from uuid import UUID, uuid4


class ClubService:
    """Service for club management operations"""
    
    @staticmethod
    async def create_club(data: CreateClubRequest) -> dict:
        """Create a new club"""
        
        # Check if slug already exists
        existing = await database.fetch_one(
            "SELECT id FROM clubs WHERE slug = :slug",
            {"slug": data.slug.lower()}
        )
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Club with slug '{data.slug}' already exists"
            )
        
        # Check if contact email is already used
        email_exists = await database.fetch_one(
            "SELECT id FROM clubs WHERE contact_email = :email",
            {"email": data.contact_email}
        )
        
        if email_exists:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Club with email '{data.contact_email}' already exists"
            )
        
        # Create club
        club_id = str(uuid4())
        
        await database.execute(
            """
            INSERT INTO clubs (id, name, slug, contact_email, logo_url, is_active)
            VALUES (:id, :name, :slug, :contact_email, :logo_url, TRUE)
            """,
            {
                "id": club_id,
                "name": data.name,
                "slug": data.slug.lower(),
                "contact_email": data.contact_email,
                "logo_url": data.logo_url
            }
        )
        
        # Fetch and return created club
        club = await database.fetch_one(
            "SELECT * FROM clubs WHERE id = :id",
            {"id": club_id}
        )
        
        return dict(club) if club else None
    
    @staticmethod
    async def get_club_by_id(club_id: UUID) -> dict:
        """Get club by ID"""
        
        club = await database.fetch_one(
            "SELECT * FROM clubs WHERE id = :id",
            {"id": club_id}
        )
        
        if not club:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found"
            )
        
        return dict(club)
    
    @staticmethod
    async def get_club_by_slug(slug: str) -> dict:
        """Get club by slug"""
        
        club = await database.fetch_one(
            "SELECT * FROM clubs WHERE slug = :slug AND is_active = TRUE",
            {"slug": slug.lower()}
        )
        
        if not club:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found"
            )
        
        return dict(club)
    
    @staticmethod
    async def list_clubs(skip: int = 0, limit: int = 50, active_only: bool = True) -> dict:
        """List clubs with pagination"""
        
        # Get total count
        total_query = "SELECT COUNT(*) as count FROM clubs"
        if active_only:
            total_query += " WHERE is_active = TRUE"
        
        total_result = await database.fetch_one(total_query)
        total = total_result["count"] if total_result else 0
        
        # Get paginated clubs
        query = "SELECT * FROM clubs"
        if active_only:
            query += " WHERE is_active = TRUE"
        query += " ORDER BY created_at DESC LIMIT :limit OFFSET :skip"
        
        clubs = await database.fetch_all(
            query,
            {"skip": skip, "limit": limit}
        )
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "clubs": [dict(club) for club in clubs]
        }
    
    @staticmethod
    async def get_club_stats(club_id: UUID) -> dict:
        """Get club statistics"""
        
        # Check club exists
        club = await database.fetch_one(
            "SELECT id FROM clubs WHERE id = :id",
            {"id": club_id}
        )
        
        if not club:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found"
            )
        
        # Get counts
        admin_count = await database.fetch_val(
            "SELECT COUNT(*) FROM club_administrators WHERE club_id = :club_id",
            {"club_id": club_id}
        )
        
        template_count = await database.fetch_val(
            "SELECT COUNT(*) FROM certificate_templates WHERE club_id = :club_id",
            {"club_id": club_id}
        )
        
        attendee_count = await database.fetch_val(
            "SELECT COUNT(*) FROM attendees WHERE club_id = :club_id",
            {"club_id": club_id}
        )
        
        certificate_count = await database.fetch_val(
            "SELECT COUNT(*) FROM certificate_generations WHERE club_id = :club_id",
            {"club_id": club_id}
        )
        
        return {
            "club_id": str(club_id),
            "admin_count": admin_count or 0,
            "template_count": template_count or 0,
            "attendee_count": attendee_count or 0,
            "certificate_count": certificate_count or 0
        }

    @staticmethod
    async def deactivate_club(club_id: UUID) -> dict:
        """Soft delete (deactivate) a club"""

        club = await database.fetch_one(
            "SELECT id FROM clubs WHERE id = :id",
            {"id": club_id}
        )

        if not club:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found"
            )

        await database.execute(
            """
            UPDATE clubs
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = :id
            """,
            {"id": club_id}
        )

        updated = await database.fetch_one(
            "SELECT * FROM clubs WHERE id = :id",
            {"id": club_id}
        )

        return dict(updated) if updated else None

    @staticmethod
    async def get_platform_analytics() -> dict:
        """Get platform-wide analytics"""

        total_clubs = await database.fetch_val("SELECT COUNT(*) FROM clubs")
        active_clubs = await database.fetch_val("SELECT COUNT(*) FROM clubs WHERE is_active = TRUE")
        inactive_clubs = (total_clubs or 0) - (active_clubs or 0)

        platform_admins = await database.fetch_val("SELECT COUNT(*) FROM platform_admins")
        club_admins = await database.fetch_val("SELECT COUNT(*) FROM club_administrators")
        templates = await database.fetch_val("SELECT COUNT(*) FROM certificate_templates")
        attendees = await database.fetch_val("SELECT COUNT(*) FROM attendees")
        certificates = await database.fetch_val("SELECT COUNT(*) FROM certificate_generations")

        return {
            "total_clubs": total_clubs or 0,
            "active_clubs": active_clubs or 0,
            "inactive_clubs": inactive_clubs or 0,
            "platform_admins": platform_admins or 0,
            "club_admins": club_admins or 0,
            "templates": templates or 0,
            "attendees": attendees or 0,
            "certificates": certificates or 0,
        }


# Create singleton instance
club_service = ClubService()
