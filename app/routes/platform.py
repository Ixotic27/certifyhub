"""
Platform Admin Routes
Club management endpoints for platform admins
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from uuid import UUID
from app.auth import get_platform_admin
from app.services.club_service import club_service
from app.services.admin_service import admin_service
from app.schemas.club import CreateClubRequest, ClubResponse, ClubListResponse, ClubDetailedResponse, PlatformAnalyticsResponse
from app.schemas.admin import CreateClubAdminRequest, ClubAdminCreatedResponse, ClubAdminListResponse

router = APIRouter()


@router.post("/clubs", response_model=ClubResponse, status_code=status.HTTP_201_CREATED)
async def create_club(
    request: CreateClubRequest,
    current_admin: dict = Depends(get_platform_admin)
):
    """
    Create a new club (Platform Admin only)
    
    - **name**: Club name (required)
    - **slug**: URL-friendly identifier (required, must be unique)
    - **contact_email**: Club contact email (required, must be unique)
    - **logo_url**: Optional URL to club logo
    
    Returns: Created club details
    """
    club = await club_service.create_club(request)
    return club


@router.get("/clubs", response_model=ClubListResponse)
async def list_clubs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    active_only: bool = Query(True, description="Only show active clubs"),
    current_admin: dict = Depends(get_platform_admin)
):
    """
    List all clubs (Platform Admin only)
    
    Supports pagination and filtering by active status.
    """
    result = await club_service.list_clubs(skip=skip, limit=limit, active_only=active_only)
    return {
        "total": result["total"],
        "clubs": result["clubs"]
    }


@router.get("/clubs/{club_id}", response_model=ClubDetailedResponse)
async def get_club_details(
    club_id: UUID,
    current_admin: dict = Depends(get_platform_admin)
):
    """
    Get club details with statistics (Platform Admin only)
    
    Returns club info + admin count, template count, attendee count
    """
    club = await club_service.get_club_by_id(club_id)
    stats = await club_service.get_club_stats(club_id)
    
    return {
        **club,
        "admin_count": stats["admin_count"],
        "template_count": stats["template_count"],
        "attendee_count": stats["attendee_count"]
    }


@router.get("/clubs/{club_id}/stats")
async def get_club_stats(
    club_id: UUID,
    current_admin: dict = Depends(get_platform_admin)
):
    """
    Get club statistics (Platform Admin only)
    
    Returns: Counts of admins, templates, attendees, and certificates
    """
    stats = await club_service.get_club_stats(club_id)
    return stats


@router.get("/analytics", response_model=PlatformAnalyticsResponse)
async def get_platform_analytics(
    current_admin: dict = Depends(get_platform_admin)
):
    """
    Platform-wide analytics (Platform Admin only)
    """
    return await club_service.get_platform_analytics()


@router.post("/clubs/{club_id}/administrators", response_model=ClubAdminCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_club_admin(
    club_id: UUID,
    request: CreateClubAdminRequest,
    current_admin: dict = Depends(get_platform_admin)
):
    """
    Add a club admin to a club (Platform Admin only)
    
    - **email**: Admin's email address (required, must be unique)
    - **full_name**: Admin's full name (required)
    
    Returns:
    - Admin ID and details
    - **temp_password**: Temporary password (displayed only once)
    
    Admin will receive welcome email with credentials and must change password on first login.
    """
    admin = await admin_service.create_club_admin(str(club_id), request)
    return admin


@router.get("/clubs/{club_id}/administrators", response_model=ClubAdminListResponse)
async def list_club_admins(
    club_id: UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    current_admin: dict = Depends(get_platform_admin)
):
    """
    List all admins for a club (Platform Admin only)
    
    Supports pagination.
    """
    result = await admin_service.get_club_admins(str(club_id), skip=skip, limit=limit)
    return {
        "club_id": result["club_id"],
        "total": result["total"],
        "admins": result["admins"]
    }


@router.delete("/clubs/{club_id}", response_model=ClubResponse)
async def deactivate_club(
    club_id: UUID,
    current_admin: dict = Depends(get_platform_admin)
):
    """
    Deactivate a club (Platform Admin only)
    """
    club = await club_service.deactivate_club(club_id)
    return club


@router.put("/clubs/{club_id}/reactivate")
async def reactivate_club(
    club_id: UUID,
    current_admin: dict = Depends(get_platform_admin)
):
    """Reactivate a deactivated club"""
    from app.database import database
    
    club = await database.fetch_one("SELECT id FROM clubs WHERE id = :id", {"id": str(club_id)})
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    
    await database.execute(
        "UPDATE clubs SET is_active = TRUE, updated_at = NOW() WHERE id = :id",
        {"id": str(club_id)}
    )
    updated = await database.fetch_one("SELECT * FROM clubs WHERE id = :id", {"id": str(club_id)})
    return dict(updated)


@router.delete("/clubs/{club_id}/permanent")
async def delete_club_permanently(
    club_id: UUID,
    current_admin: dict = Depends(get_platform_admin)
):
    """Permanently delete a club and all its data (Platform Admin only)"""
    from app.database import database
    
    club = await database.fetch_one("SELECT id, name FROM clubs WHERE id = :id", {"id": str(club_id)})
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    
    club_name = club["name"]
    cid = str(club_id)
    
    # Delete in order respecting all foreign keys
    # 1. certificate_generations -> attendees, certificate_templates, clubs
    await database.execute("DELETE FROM certificate_generations WHERE club_id = :cid", {"cid": cid})
    # 2. activity_logs -> clubs, club_administrators
    await database.execute("DELETE FROM activity_logs WHERE club_id = :cid", {"cid": cid})
    # 3. attendees -> certificate_templates, club_administrators, clubs
    await database.execute("DELETE FROM attendees WHERE club_id = :cid", {"cid": cid})
    # 4. attendee_imports -> clubs
    await database.execute("DELETE FROM attendee_imports WHERE club_id = :cid", {"cid": cid})
    # 5. certificate_templates -> club_administrators, clubs
    await database.execute("DELETE FROM certificate_templates WHERE club_id = :cid", {"cid": cid})
    # 6. club_administrators -> clubs
    await database.execute("DELETE FROM club_administrators WHERE club_id = :cid", {"cid": cid})
    # 7. clubs
    await database.execute("DELETE FROM clubs WHERE id = :cid", {"cid": cid})
    
    return {"status": "success", "message": f"Club '{club_name}' permanently deleted"}


@router.put("/administrators/{admin_id}/deactivate")
async def deactivate_club_admin(
    admin_id: UUID,
    current_admin: dict = Depends(get_platform_admin)
):
    """Deactivate a club admin"""
    result = await admin_service.deactivate_admin(str(admin_id))
    return result


@router.put("/administrators/{admin_id}/activate")
async def activate_club_admin(
    admin_id: UUID,
    current_admin: dict = Depends(get_platform_admin)
):
    """Reactivate a deactivated club admin"""
    from app.database import database
    
    admin = await database.fetch_one(
        "SELECT * FROM club_administrators WHERE id = :id", {"id": str(admin_id)}
    )
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    await database.execute(
        "UPDATE club_administrators SET is_active = TRUE WHERE id = :id", {"id": str(admin_id)}
    )
    updated = await database.fetch_one(
        "SELECT * FROM club_administrators WHERE id = :id", {"id": str(admin_id)}
    )
    return dict(updated)


@router.put("/administrators/{admin_id}/reset-password")
async def reset_admin_password(
    admin_id: UUID,
    current_admin: dict = Depends(get_platform_admin)
):
    """Reset a club admin's password to a new random one"""
    from app.database import database
    from app.auth import hash_password, generate_random_password
    
    admin = await database.fetch_one(
        "SELECT id, email, full_name FROM club_administrators WHERE id = :id",
        {"id": str(admin_id)}
    )
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    
    new_password = generate_random_password(12)
    password_hash = hash_password(new_password)
    
    await database.execute(
        """
        UPDATE club_administrators 
        SET password_hash = :hash, must_change_password = TRUE, password_changed_at = NOW()
        WHERE id = :id
        """,
        {"hash": password_hash, "id": str(admin_id)}
    )
    
    return {
        "status": "success",
        "admin_email": admin["email"],
        "admin_name": admin["full_name"],
        "temp_password": new_password,
        "message": "Password reset. Admin must change password on next login."
    }
