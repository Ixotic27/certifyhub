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


@router.delete("/administrators/{admin_id}/permanent")
async def delete_admin_permanently(
    admin_id: UUID,
    current_admin: dict = Depends(get_platform_admin)
):
    """Permanently delete a club admin (Platform Admin only)"""
    from app.database import database

    admin = await database.fetch_one(
        "SELECT id, email, full_name FROM club_administrators WHERE id = :id",
        {"id": str(admin_id)}
    )
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")

    aid = str(admin_id)
    # Remove references then the admin
    await database.execute("UPDATE certificate_templates SET created_by = NULL WHERE created_by = :aid", {"aid": aid})
    await database.execute("UPDATE attendees SET uploaded_by = NULL WHERE uploaded_by = :aid", {"aid": aid})
    await database.execute("DELETE FROM activity_logs WHERE admin_id = :aid", {"aid": aid})
    await database.execute("DELETE FROM club_administrators WHERE id = :aid", {"aid": aid})

    return {"status": "success", "message": f"Admin '{admin['full_name']}' permanently deleted"}


# ──────────────── Resource Management ────────────────

@router.get("/resources/templates")
async def list_all_templates(
    club_id: str = Query(None, description="Filter by club ID"),
    current_admin: dict = Depends(get_platform_admin)
):
    """List all templates across clubs (Platform Admin only)"""
    from app.database import database

    if club_id:
        rows = await database.fetch_all(
            """
            SELECT t.*, c.name AS club_name
            FROM certificate_templates t
            JOIN clubs c ON c.id = t.club_id
            WHERE t.club_id = :club_id AND t.is_active = TRUE
            ORDER BY t.created_at DESC
            """,
            {"club_id": club_id}
        )
    else:
        rows = await database.fetch_all(
            """
            SELECT t.*, c.name AS club_name
            FROM certificate_templates t
            JOIN clubs c ON c.id = t.club_id
            WHERE t.is_active = TRUE
            ORDER BY t.created_at DESC
            """
        )
    return {"templates": [dict(r) for r in rows], "total": len(rows)}


@router.delete("/resources/templates/{template_id}")
async def delete_template_resource(
    template_id: UUID,
    current_admin: dict = Depends(get_platform_admin)
):
    """Permanently delete a template and its storage (Platform Admin only)"""
    from app.database import database
    from app.services.storage_service import StorageService

    template = await database.fetch_one(
        "SELECT * FROM certificate_templates WHERE id = :id", {"id": str(template_id)}
    )
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    tid = str(template_id)
    # Clean up storage
    try:
        if template["template_image_url"]:
            await StorageService.delete_by_url(template["template_image_url"])
    except Exception:
        pass

    # Remove dependent rows then template
    await database.execute("DELETE FROM certificate_generations WHERE template_id = :tid", {"tid": tid})
    await database.execute("DELETE FROM attendees WHERE template_id = :tid", {"tid": tid})
    await database.execute("DELETE FROM certificate_templates WHERE id = :tid", {"tid": tid})

    return {"status": "success", "message": f"Template '{template['name']}' deleted"}


@router.get("/resources/attendees")
async def list_attendees_resource(
    club_id: str = Query(None, description="Filter by club ID"),
    import_id: str = Query(None, description="Filter by import ID"),
    limit: int = Query(100, ge=1, le=500),
    current_admin: dict = Depends(get_platform_admin)
):
    """List attendees across clubs with counts (Platform Admin only)"""
    from app.database import database

    filters = []
    params = {"limit": limit}
    if club_id:
        filters.append("a.club_id = :club_id")
        params["club_id"] = club_id
    if import_id:
        filters.append("a.import_id = :import_id")
        params["import_id"] = import_id

    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    rows = await database.fetch_all(
        f"""
        SELECT a.id, a.name, a.student_id, a.email, a.club_id, a.role,
               a.uploaded_at, a.import_id, c.name AS club_name
        FROM attendees a
        JOIN clubs c ON c.id = a.club_id
        {where}
        ORDER BY a.uploaded_at DESC
        LIMIT :limit
        """,
        params
    )
    return {"attendees": [dict(r) for r in rows], "total": len(rows)}


@router.delete("/resources/attendees/{attendee_id}")
async def delete_attendee_resource(
    attendee_id: UUID,
    current_admin: dict = Depends(get_platform_admin)
):
    """Permanently delete a single attendee (Platform Admin only)"""
    from app.database import database

    att = await database.fetch_one("SELECT id, name FROM attendees WHERE id = :id", {"id": str(attendee_id)})
    if not att:
        raise HTTPException(status_code=404, detail="Attendee not found")

    aid = str(attendee_id)
    await database.execute("DELETE FROM certificate_generations WHERE attendee_id = :aid", {"aid": aid})
    await database.execute("DELETE FROM attendees WHERE id = :aid", {"aid": aid})
    return {"status": "success", "message": f"Attendee '{att['name']}' deleted"}


@router.delete("/resources/attendees/club/{club_id}")
async def delete_all_attendees_for_club(
    club_id: UUID,
    current_admin: dict = Depends(get_platform_admin)
):
    """Delete ALL attendees for a club (Platform Admin only)"""
    from app.database import database

    club = await database.fetch_one("SELECT id, name FROM clubs WHERE id = :id", {"id": str(club_id)})
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")

    cid = str(club_id)
    await database.execute("DELETE FROM certificate_generations WHERE club_id = :cid", {"cid": cid})
    await database.execute("DELETE FROM attendees WHERE club_id = :cid", {"cid": cid})
    await database.execute("DELETE FROM attendee_imports WHERE club_id = :cid", {"cid": cid})
    return {"status": "success", "message": f"All attendees for '{club['name']}' deleted"}


@router.get("/resources/imports")
async def list_imports_resource(
    club_id: str = Query(None, description="Filter by club ID"),
    current_admin: dict = Depends(get_platform_admin)
):
    """List attendee imports across clubs (Platform Admin only)"""
    from app.database import database

    if club_id:
        rows = await database.fetch_all(
            """
            SELECT i.id, i.filename, i.club_id, i.role, i.rows_count,
                   i.file_size_bytes, i.uploaded_at, c.name AS club_name,
                   (SELECT COUNT(*) FROM attendees a WHERE a.import_id = i.id) AS attendee_count
            FROM attendee_imports i
            JOIN clubs c ON c.id = i.club_id
            WHERE i.club_id = :club_id
            ORDER BY i.uploaded_at DESC
            """,
            {"club_id": club_id}
        )
    else:
        rows = await database.fetch_all(
            """
            SELECT i.id, i.filename, i.club_id, i.role, i.rows_count,
                   i.file_size_bytes, i.uploaded_at, c.name AS club_name,
                   (SELECT COUNT(*) FROM attendees a WHERE a.import_id = i.id) AS attendee_count
            FROM attendee_imports i
            JOIN clubs c ON c.id = i.club_id
            ORDER BY i.uploaded_at DESC
            """
        )
    return {"imports": [dict(r) for r in rows], "total": len(rows)}


@router.delete("/resources/imports/{import_id}")
async def delete_import_resource(
    import_id: UUID,
    current_admin: dict = Depends(get_platform_admin)
):
    """Delete an attendee import and its uploaded file (Platform Admin only)"""
    from app.database import database
    from app.services.storage_service import StorageService

    imp = await database.fetch_one("SELECT * FROM attendee_imports WHERE id = :id", {"id": str(import_id)})
    if not imp:
        raise HTTPException(status_code=404, detail="Import not found")

    iid = str(import_id)
    # Clean up storage
    try:
        if imp["file_path"]:
            await StorageService.delete_by_url(imp["file_path"])
    except Exception:
        pass

    # Remove attendees linked to this import, then the import
    await database.execute(
        "DELETE FROM certificate_generations WHERE attendee_id IN (SELECT id FROM attendees WHERE import_id = :iid)",
        {"iid": iid}
    )
    await database.execute("DELETE FROM attendees WHERE import_id = :iid", {"iid": iid})
    await database.execute("DELETE FROM attendee_imports WHERE id = :iid", {"iid": iid})
    return {"status": "success", "message": f"Import '{imp['filename']}' and linked attendees deleted"}


@router.get("/storage/unused-templates")
async def get_unused_templates(
    days: int = Query(30, ge=1, le=365, description="Days of inactivity"),
    current_admin: dict = Depends(get_platform_admin)
):
    """
    List templates unused for N days (Platform Admin only).
    These are candidates for cleanup.
    """
    templates = await admin_service.get_unused_templates(days)
    return {
        "days": days,
        "count": len(templates),
        "templates": templates
    }


@router.post("/storage/cleanup")
async def cleanup_unused_templates(
    days: int = Query(30, ge=1, le=365, description="Days of inactivity"),
    current_admin: dict = Depends(get_platform_admin)
):
    """
    Cleanup templates unused for N days (Platform Admin only).
    Deactivates templates and deletes their images from storage.
    """
    result = await admin_service.cleanup_unused_templates(days)
    return {
        "status": "success",
        "days": days,
        "cleaned_count": result["cleaned_count"],
        "bytes_freed": result["bytes_freed"],
        "bytes_freed_mb": round(result["bytes_freed"] / (1024 * 1024), 2)
    }


@router.get("/storage/stats")
async def get_storage_stats(
    current_admin: dict = Depends(get_platform_admin)
):
    """
    Get global storage statistics (Platform Admin only).
    """
    from app.database import database
    
    stats = await database.fetch_one(
        """
        SELECT
            (SELECT COALESCE(SUM(image_size_bytes), 0) FROM certificate_templates WHERE is_active = TRUE) AS template_bytes,
            (SELECT COALESCE(SUM(file_size_bytes), 0) FROM attendee_imports) AS import_bytes,
            (SELECT COUNT(*) FROM certificate_templates WHERE is_active = TRUE) AS active_templates,
            (SELECT COUNT(*) FROM clubs WHERE is_active = TRUE) AS active_clubs
        """
    )
    
    template_bytes = int(stats["template_bytes"] or 0)
    import_bytes = int(stats["import_bytes"] or 0)
    total_used = template_bytes + import_bytes
    limit = 500 * 1024 * 1024
    
    return {
        "template_storage_bytes": template_bytes,
        "import_storage_bytes": import_bytes,
        "total_used_bytes": total_used,
        "total_limit_bytes": limit,
        "used_percentage": round((total_used / limit) * 100, 1),
        "active_templates": stats["active_templates"],
        "active_clubs": stats["active_clubs"]
    }

