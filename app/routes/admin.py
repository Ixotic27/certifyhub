"""
Club Admin Routes
Endpoints for club admins to manage templates, attendees, and certificates
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from pathlib import Path
import csv
import json
import uuid
from uuid import UUID
from app.auth import get_club_admin
from app.database import database
from app.services.template_service import template_service
from app.services.attendee_service import attendee_service
from app.services.csv_parser import CSVParser
from app.services.storage_service import StorageService
from app.services.admin_service import admin_service
from app.services.activity_log_service import ActivityLogService
from app.schemas.template import CreateTemplateRequest, UpdateTemplateCoordinatesRequest, TemplateResponse, TemplateListResponse, TemplateDetailResponse
from app.schemas.attendee import CSVUploadRequest, CSVUploadResponse, AttendeeResponse, AttendeeListResponse
from app.schemas.admin import AdminDashboardResponse
from app.schemas.activity_log import ActivityLogResponse, ActivityStatsResponse

router = APIRouter()


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def get_admin_dashboard(
    current_admin: dict = Depends(get_club_admin)
):
    """
    Club admin dashboard stats
    """

    club_id = current_admin.get("club_id")
    if not club_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Club admin must be associated with a club"
        )

    return await admin_service.get_dashboard_stats(str(club_id))


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def upload_certificate_template(
    request: CreateTemplateRequest,
    current_admin: dict = Depends(get_club_admin)
):
    """
    Upload a new certificate template (Club Admin only)
    
    - **template_name**: Name of this template (required)
    - **template_image_url**: Public URL to template image (PNG/JPG, required)
    - **text_fields**: List of text field coordinates and formatting
    
    Returns: Created template details with version 1
    
    Note: Image URL must be publicly accessible. Coordinates are in pixels.
    """
    
    # Get club_id from current admin
    club_id = current_admin.get("club_id")
    
    if not club_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Club admin must be associated with a club"
        )
    
    template = await template_service.create_template(str(club_id), request)
    return template


@router.post("/templates/upload", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def upload_certificate_template_file(
    template_name: str = Form(...),
    audience: str = Form("student"),
    text_fields: str = Form("[]"),
    image: UploadFile = File(...),
    current_admin: dict = Depends(get_club_admin)
):
    """Upload a new certificate template with image file (Club Admin only)"""
    club_id = current_admin.get("club_id")
    if not club_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Club admin must be associated with a club"
        )

    if audience not in {"student", "management"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audience must be student or management"
        )

    # Enforce per-club storage quota (100 MB) across template images + CSV imports
    max_bytes = 100 * 1024 * 1024
    size_row = await database.fetch_one(
        """
        SELECT
            COALESCE(SUM(image_size_bytes), 0) AS template_bytes
        FROM certificate_templates
        WHERE club_id = :club_id
        """,
        {"club_id": str(club_id)}
    )
    import_size_row = await database.fetch_one(
        """
        SELECT
            COALESCE(SUM(file_size_bytes), 0) AS import_bytes
        FROM attendee_imports
        WHERE club_id = :club_id
        """,
        {"club_id": str(club_id)}
    )
    used_bytes = int((size_row["template_bytes"] if size_row else 0) or 0) + int((import_size_row["import_bytes"] if import_size_row else 0) or 0)

    content = await image.read()
    if used_bytes + len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage limit exceeded (100 MB per club)."
        )

    # Upload image to Supabase Storage
    file_ext = Path(image.filename).suffix or ".png"
    file_name = f"template_{uuid.uuid4().hex}{file_ext}"
    storage_path = f"clubs/{club_id}/templates/{file_name}"
    image_url = await StorageService.upload_bytes(storage_path, content, image.content_type or "image/png")

    try:
        parsed_fields = json.loads(text_fields) if text_fields else []
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid text_fields JSON")

    request = CreateTemplateRequest(
        template_name=template_name,
        template_image_url=image_url,
        audience=audience,
        text_fields=parsed_fields
    )

    template = await template_service.create_template(str(club_id), request)
    await database.execute(
        """
        UPDATE certificate_templates
        SET image_size_bytes = :size
        WHERE id = :template_id
        """,
        {"size": len(content), "template_id": template["id"]}
    )
    return template


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Number of records to return"),
    active_only: bool = Query(True, description="Only show active templates"),
    current_admin: dict = Depends(get_club_admin)
):
    """
    List all templates for the club (Club Admin only)
    
    Supports pagination and filtering by active status.
    """
    
    club_id = current_admin.get("club_id")
    if not club_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Club admin must be associated with a club"
        )
    
    result = await template_service.list_templates(str(club_id), skip=skip, limit=limit, active_only=active_only)
    return {
        "club_id": result["club_id"],
        "total": result["total"],
        "templates": result["templates"]
    }


@router.get("/templates/{template_id}", response_model=TemplateDetailResponse)
async def get_template_details(
    template_id: UUID,
    current_admin: dict = Depends(get_club_admin)
):
    """
    Get template details with statistics (Club Admin only)
    
    Returns template info + certificate generation count and last used date
    """
    
    template = await template_service.get_template(str(template_id))
    
    # Verify club ownership
    if str(template["club_id"]) != str(current_admin.get("club_id")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this template"
        )
    
    stats = await template_service.get_template_stats(str(template_id))
    
    return {
        **template,
        "certificate_count": stats["certificate_count"],
        "last_used": stats["last_used"]
    }


@router.put("/templates/{template_id}/coordinates", response_model=TemplateResponse)
async def update_template_coordinates(
    template_id: UUID,
    request: UpdateTemplateCoordinatesRequest,
    current_admin: dict = Depends(get_club_admin)
):
    """
    Update text field coordinates for a template (Club Admin only)
    
    This creates a new version of the template. Old versions are kept for audit.
    
    - **text_fields**: New list of text field coordinates
    
    Returns: Updated template with new version number
    """
    
    template = await template_service.get_template(str(template_id))
    
    # Verify club ownership
    if str(template["club_id"]) != str(current_admin.get("club_id")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this template"
        )
    
    updated_template = await template_service.update_template_coordinates(str(template_id), request)
    return updated_template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_template(
    template_id: UUID,
    current_admin: dict = Depends(get_club_admin)
):
    """
    Deactivate a template (Club Admin only)
    
    Deactivating prevents it from being used for new certificates.
    Existing certificates remain valid.
    """
    
    template = await template_service.get_template(str(template_id))
    
    # Verify club ownership
    if str(template["club_id"]) != str(current_admin.get("club_id")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this template"
        )
    
    await template_service.deactivate_template(str(template_id))
    return None


@router.get("/templates/{template_id}/stats")
async def get_template_statistics(
    template_id: UUID,
    current_admin: dict = Depends(get_club_admin)
):
    """
    Get statistics for a template (Club Admin only)
    
    Returns: Certificate generation count and last used date
    """
    
    template = await template_service.get_template(str(template_id))
    
    # Verify club ownership
    if str(template["club_id"]) != str(current_admin.get("club_id")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this template"
        )
    
    stats = await template_service.get_template_stats(str(template_id))
    return stats


@router.post("/attendees/upload", response_model=CSVUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_attendees_csv(
    request: CSVUploadRequest,
    current_admin: dict = Depends(get_club_admin)
):
    """
    Upload attendees via CSV file (Club Admin only)
    
    CSV must have headers: name, student_id, [email] (email optional)
    
    Each row will be validated:
    - name must not be empty
    - student_id must be unique (within club and CSV)
    - Email must be valid format if provided
    
    Returns: Summary of import with count of successful/failed rows
    """
    
    club_id = current_admin.get("club_id")
    if not club_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Club admin must be associated with a club"
        )
    
    # Parse and validate CSV
    validated_attendees, errors = await attendee_service.parse_and_validate_csv(
        request.csv_content,
        str(club_id),
        skip_errors=request.skip_errors,
        default_role=request.role
    )
    
    # Import validated attendees
    if validated_attendees:
        successful_count = await attendee_service.upload_attendees(str(club_id), validated_attendees)
    else:
        successful_count = 0
    
    return {
        "club_id": club_id,
        "total_rows_processed": successful_count + len(errors),
        "successful_imports": successful_count,
        "failed_imports": len(errors),
        "errors": [{"row": e.row, "error": e.error} for e in errors]
    }


@router.post("/attendees/upload-file", response_model=CSVUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_attendees_csv_file(
    file: UploadFile = File(...),
    role: str = Form("student"),
    skip_errors: bool = Form(False),
    current_admin: dict = Depends(get_club_admin)
):
    """Upload attendees via CSV file (multipart)"""
    club_id = current_admin.get("club_id")
    if not club_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Club admin must be associated with a club"
        )

    if role not in {"student", "management"}:
        raise HTTPException(status_code=400, detail="Role must be student or management")

    content = await file.read()
    csv_content = content.decode("utf-8", errors="ignore")

    # Enforce per-club storage quota (100 MB) across template images + CSV imports
    max_bytes = 100 * 1024 * 1024
    size_row = await database.fetch_one(
        """
        SELECT
            COALESCE(SUM(image_size_bytes), 0) AS template_bytes
        FROM certificate_templates
        WHERE club_id = :club_id
        """,
        {"club_id": str(club_id)}
    )
    import_size_row = await database.fetch_one(
        """
        SELECT
            COALESCE(SUM(file_size_bytes), 0) AS import_bytes
        FROM attendee_imports
        WHERE club_id = :club_id
        """,
        {"club_id": str(club_id)}
    )
    used_bytes = int((size_row["template_bytes"] if size_row else 0) or 0) + int((import_size_row["import_bytes"] if import_size_row else 0) or 0)

    if used_bytes + len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage limit exceeded (100 MB per club)."
        )

    # Upload CSV to Supabase Storage
    file_ext = Path(file.filename).suffix or ".csv"
    file_name = f"attendees_{uuid.uuid4().hex}{file_ext}"
    storage_path = f"clubs/{club_id}/imports/{file_name}"
    file_url = await StorageService.upload_bytes(storage_path, content, file.content_type or "text/csv")

    validated_attendees, errors = await attendee_service.parse_and_validate_csv(
        csv_content,
        str(club_id),
        skip_errors=skip_errors,
        default_role=role
    )

    if validated_attendees:
        successful_count = await attendee_service.upload_attendees(str(club_id), validated_attendees)
    else:
        successful_count = 0

    try:
        await database.execute(
            """
            INSERT INTO attendee_imports (id, club_id, filename, file_path, role, rows_count)
            VALUES (:id, :club_id, :filename, :file_path, :role, :rows_count)
            """,
            {
                "id": uuid.uuid4(),
                "club_id": club_id,
                "filename": file.filename,
                "file_path": file_url,
                "role": role,
                "rows_count": successful_count + len(errors),
                "file_size_bytes": len(content)
            }
        )
    except Exception:
        pass

    return {
        "club_id": club_id,
        "total_rows_processed": successful_count + len(errors),
        "successful_imports": successful_count,
        "failed_imports": len(errors),
        "errors": [{"row": e.row, "error": e.error} for e in errors]
    }


@router.post("/attendees/preview")
async def preview_attendees_csv(
    file: UploadFile = File(...),
    template_id: str = Form(...),
    role: str = Form("student"),
    current_admin: dict = Depends(get_club_admin)
):
    club_id = current_admin.get("club_id")
    if not club_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Club admin must be associated with a club")

    template = await database.fetch_one(
        "SELECT id FROM certificate_templates WHERE id = :template_id AND club_id = :club_id",
        {"template_id": template_id, "club_id": str(club_id)}
    )
    if not template:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Template not found or access denied")

    content = await file.read()
    parsed_rows = CSVParser.parse_attendee_csv(content)

    # Apply role default if CSV doesn't include role
    for row in parsed_rows:
        if not row.get("role"):
            row["role"] = role

    new_records, duplicates = await CSVParser.check_duplicates(parsed_rows, str(club_id), template_id)

    preview_rows = new_records[:50]

    return {
        "total_rows": len(parsed_rows),
        "new_records": len(new_records),
        "duplicate_records": len(duplicates),
        "preview": preview_rows,
        "payload": new_records
    }


@router.post("/attendees/import")
async def import_attendees_csv(
    template_id: str = Form(...),
    attendees_json: str = Form(...),
    current_admin: dict = Depends(get_club_admin)
):
    club_id = current_admin.get("club_id")
    if not club_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Club admin must be associated with a club")

    template = await database.fetch_one(
        "SELECT id FROM certificate_templates WHERE id = :template_id AND club_id = :club_id",
        {"template_id": template_id, "club_id": str(club_id)}
    )
    if not template:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Template not found or access denied")

    try:
        attendees = json.loads(attendees_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid attendees payload")

    if not isinstance(attendees, list):
        raise HTTPException(status_code=400, detail="Invalid attendees payload")

    # Re-check duplicates before insert
    new_records, duplicates = await CSVParser.check_duplicates(attendees, str(club_id), template_id)

    if not new_records:
        return {
            "imported": 0,
            "duplicates": len(duplicates)
        }

    # Insert attendees with club_id isolation
    records = []
    for attendee in new_records:
        records.append({
            "id": str(uuid.uuid4()),
            "club_id": str(club_id),
            "template_id": template_id,
            "name": attendee.get("name"),
            "student_id": attendee.get("student_id"),
            "email": attendee.get("email"),
            "course": attendee.get("course"),
            "role": attendee.get("role") or "student",
            "uploaded_by": current_admin.get("user_id")
        })

    values_placeholder = ",".join([
        f"(:id_{i}, :club_id_{i}, :template_id_{i}, :name_{i}, :student_id_{i}, :email_{i}, :course_{i}, :role_{i}, :uploaded_by_{i})"
        for i in range(len(records))
    ])

    query = f"""
        INSERT INTO attendees
        (id, club_id, template_id, name, student_id, email, course, role, uploaded_by)
        VALUES {values_placeholder}
    """

    params = {}
    for i, record in enumerate(records):
        params[f"id_{i}"] = record["id"]
        params[f"club_id_{i}"] = record["club_id"]
        params[f"template_id_{i}"] = record["template_id"]
        params[f"name_{i}"] = record["name"]
        params[f"student_id_{i}"] = record["student_id"]
        params[f"email_{i}"] = record["email"]
        params[f"course_{i}"] = record["course"]
        params[f"role_{i}"] = record["role"]
        params[f"uploaded_by_{i}"] = record["uploaded_by"]

    await database.execute(query, params)

    return {
        "imported": len(new_records),
        "duplicates": len(duplicates)
    }


@router.post("/attendees/import-file")
async def import_attendees_csv_file(
    file: UploadFile = File(...),
    template_id: str = Form(...),
    role: str = Form("student"),
    current_admin: dict = Depends(get_club_admin)
):
    club_id = current_admin.get("club_id")
    if not club_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Club admin must be associated with a club")

    if role not in {"student", "management"}:
        raise HTTPException(status_code=400, detail="Role must be student or management")

    template = await database.fetch_one(
        "SELECT id FROM certificate_templates WHERE id = :template_id AND club_id = :club_id",
        {"template_id": template_id, "club_id": str(club_id)}
    )
    if not template:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Template not found or access denied")

    content = await file.read()

    # Enforce per-club storage quota (100 MB) across template images + CSV imports
    max_bytes = 100 * 1024 * 1024
    size_row = await database.fetch_one(
        """
        SELECT
            COALESCE(SUM(image_size_bytes), 0) AS template_bytes
        FROM certificate_templates
        WHERE club_id = :club_id
        """,
        {"club_id": str(club_id)}
    )
    import_size_row = await database.fetch_one(
        """
        SELECT
            COALESCE(SUM(file_size_bytes), 0) AS import_bytes
        FROM attendee_imports
        WHERE club_id = :club_id
        """,
        {"club_id": str(club_id)}
    )
    used_bytes = int((size_row["template_bytes"] if size_row else 0) or 0) + int((import_size_row["import_bytes"] if import_size_row else 0) or 0)

    if used_bytes + len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Storage limit exceeded (100 MB per club)."
        )

    # Upload CSV to Supabase Storage
    file_ext = Path(file.filename).suffix or ".csv"
    file_name = f"attendees_{uuid.uuid4().hex}{file_ext}"
    storage_path = f"clubs/{club_id}/imports/{file_name}"
    file_url = await StorageService.upload_bytes(storage_path, content, file.content_type or "text/csv")

    parsed_rows = CSVParser.parse_attendee_csv(content)

    # Apply role default if CSV doesn't include role
    for row in parsed_rows:
        if not row.get("role"):
            row["role"] = role

    new_records, duplicates = await CSVParser.check_duplicates(parsed_rows, str(club_id), template_id)

    if not new_records:
        return {
            "imported": 0,
            "duplicates": len(duplicates)
        }

    records = []
    for attendee in new_records:
        records.append({
            "id": str(uuid.uuid4()),
            "club_id": str(club_id),
            "template_id": template_id,
            "name": attendee.get("name"),
            "student_id": attendee.get("student_id"),
            "email": attendee.get("email"),
            "course": attendee.get("course"),
            "role": attendee.get("role") or "student",
            "uploaded_by": current_admin.get("user_id")
        })

    values_placeholder = ",".join([
        f"(:id_{i}, :club_id_{i}, :template_id_{i}, :name_{i}, :student_id_{i}, :email_{i}, :course_{i}, :role_{i}, :uploaded_by_{i})"
        for i in range(len(records))
    ])

    query = f"""
        INSERT INTO attendees
        (id, club_id, template_id, name, student_id, email, course, role, uploaded_by)
        VALUES {values_placeholder}
    """

    params = {}
    for i, record in enumerate(records):
        params[f"id_{i}"] = record["id"]
        params[f"club_id_{i}"] = record["club_id"]
        params[f"template_id_{i}"] = record["template_id"]
        params[f"name_{i}"] = record["name"]
        params[f"student_id_{i}"] = record["student_id"]
        params[f"email_{i}"] = record["email"]
        params[f"course_{i}"] = record["course"]
        params[f"role_{i}"] = record["role"]
        params[f"uploaded_by_{i}"] = record["uploaded_by"]

    await database.execute(query, params)

    try:
        await database.execute(
            """
            INSERT INTO attendee_imports (id, club_id, filename, file_path, role, rows_count, file_size_bytes)
            VALUES (:id, :club_id, :filename, :file_path, :role, :rows_count, :file_size_bytes)
            """,
            {
                "id": uuid.uuid4(),
                "club_id": club_id,
                "filename": file.filename,
                "file_path": file_url,
                "role": role,
                "rows_count": len(new_records) + len(duplicates),
                "file_size_bytes": len(content)
            }
        )
    except Exception:
        pass

    return {
        "imported": len(new_records),
        "duplicates": len(duplicates)
    }


@router.post("/attendees/import-simple")
async def import_attendees_simple(
    file: UploadFile = File(...),
    batch_name: str = Form(""),
    role: str = Form("student"),
    current_admin: dict = Depends(get_club_admin)
):
    """Simple attendee import without template requirement"""
    club_id = current_admin.get("club_id")
    if not club_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Club admin must be associated with a club")

    if role not in {"student", "management"}:
        raise HTTPException(status_code=400, detail="Role must be student or management")

    content = await file.read()

    # Enforce per-club storage quota (100 MB)
    max_bytes = 100 * 1024 * 1024
    size_row = await database.fetch_one(
        "SELECT COALESCE(SUM(image_size_bytes), 0) AS template_bytes FROM certificate_templates WHERE club_id = :club_id",
        {"club_id": str(club_id)}
    )
    import_size_row = await database.fetch_one(
        "SELECT COALESCE(SUM(file_size_bytes), 0) AS import_bytes FROM attendee_imports WHERE club_id = :club_id",
        {"club_id": str(club_id)}
    )
    used_bytes = int((size_row["template_bytes"] if size_row else 0) or 0) + int((import_size_row["import_bytes"] if import_size_row else 0) or 0)

    if used_bytes + len(content) > max_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Storage limit exceeded (100 MB per club).")

    # Upload CSV to Supabase Storage
    file_ext = Path(file.filename).suffix or ".csv"
    file_name = f"attendees_{uuid.uuid4().hex}{file_ext}"
    storage_path = f"clubs/{club_id}/imports/{file_name}"
    file_url = await StorageService.upload_bytes(storage_path, content, file.content_type or "text/csv")

    parsed_rows = CSVParser.parse_attendee_csv(content)

    # Apply role default
    for row in parsed_rows:
        if not row.get("role"):
            row["role"] = role

    # Check duplicates without template filter
    new_records, duplicates = await CSVParser.check_duplicates_simple(parsed_rows, str(club_id))

    if not new_records:
        return {"imported": 0, "duplicates": len(duplicates)}

    records = []
    for attendee in new_records:
        records.append({
            "id": str(uuid.uuid4()),
            "club_id": str(club_id),
            "name": attendee.get("name"),
            "student_id": attendee.get("student_id"),
            "email": attendee.get("email"),
            "course": attendee.get("course"),
            "role": attendee.get("role") or "student",
            "uploaded_by": current_admin.get("user_id")
        })

    values_placeholder = ",".join([
        f"(:id_{i}, :club_id_{i}, :name_{i}, :student_id_{i}, :email_{i}, :course_{i}, :role_{i}, :uploaded_by_{i})"
        for i in range(len(records))
    ])

    query = f"""
        INSERT INTO attendees
        (id, club_id, name, student_id, email, course, role, uploaded_by)
        VALUES {values_placeholder}
    """

    params = {}
    for i, record in enumerate(records):
        params[f"id_{i}"] = record["id"]
        params[f"club_id_{i}"] = record["club_id"]
        params[f"name_{i}"] = record["name"]
        params[f"student_id_{i}"] = record["student_id"]
        params[f"email_{i}"] = record["email"]
        params[f"course_{i}"] = record["course"]
        params[f"role_{i}"] = record["role"]
        params[f"uploaded_by_{i}"] = record["uploaded_by"]

    await database.execute(query, params)

    # Log the import
    final_batch_name = batch_name or file.filename
    try:
        await database.execute(
            """
            INSERT INTO attendee_imports (id, club_id, filename, file_path, role, rows_count, file_size_bytes)
            VALUES (:id, :club_id, :filename, :file_path, :role, :rows_count, :file_size_bytes)
            """,
            {
                "id": uuid.uuid4(),
                "club_id": club_id,
                "filename": final_batch_name,
                "file_path": file_url,
                "role": role,
                "rows_count": len(new_records) + len(duplicates),
                "file_size_bytes": len(content)
            }
        )
    except Exception:
        pass

    return {"imported": len(new_records), "duplicates": len(duplicates)}


@router.get("/attendees/imports")
async def list_attendee_imports(
    current_admin: dict = Depends(get_club_admin)
):
    club_id = current_admin.get("club_id")
    if not club_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Club admin must be associated with a club"
        )

    rows = await database.fetch_all(
        """
        SELECT id, filename, role, rows_count, uploaded_at
        FROM attendee_imports
        WHERE club_id = :club_id
        ORDER BY uploaded_at DESC
        """,
        {"club_id": str(club_id)}
    )

    return {
        "total": len(rows),
        "imports": [dict(r) for r in rows]
    }


@router.get("/attendees/imports/{import_id}/rows")
async def get_attendee_import_rows(
    import_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    current_admin: dict = Depends(get_club_admin)
):
    club_id = current_admin.get("club_id")
    if not club_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Club admin must be associated with a club"
        )

    row = await database.fetch_one(
        """
        SELECT file_path, role
        FROM attendee_imports
        WHERE id = :import_id AND club_id = :club_id
        """,
        {"import_id": str(import_id), "club_id": str(club_id)}
    )

    if not row:
        raise HTTPException(status_code=404, detail="Import not found")

    file_path = row["file_path"]
    if not file_path:
        raise HTTPException(status_code=404, detail="CSV file not found")

    csv_text = ""
    if str(file_path).startswith("http"):
        csv_text = await StorageService.fetch_text(str(file_path))
    else:
        local_path = Path(str(file_path))
        if not local_path.exists():
            raise HTTPException(status_code=404, detail="CSV file not found")
        csv_text = local_path.read_text(encoding="utf-8", errors="ignore")

    rows = []
    lines = csv_text.splitlines()
    if not lines:
        return {"rows": []}
    
    # Normalize headers (lowercase, strip BOM, remove spaces)
    header_line = lines[0].replace('\ufeff', '')
    headers = [h.strip().lower() for h in header_line.split(',')]
    
    # Create normalized header mapping (remove spaces/underscores for matching)
    def normalize_key(key):
        return key.replace(' ', '').replace('_', '').replace('-', '')
    
    header_map = {normalize_key(h): h for h in headers}
    
    reader = csv.DictReader(lines, fieldnames=headers)
    next(reader)  # Skip header row
    
    for i, r in enumerate(reader):
        if i >= limit:
            break
        
        # Try multiple possible column names for student_id
        student_id = ""
        for key in ["student_id", "studentid", "student id", "id", "student_no", "studentno", "roll", "rollno", "roll_no"]:
            normalized = normalize_key(key)
            if normalized in header_map:
                student_id = (r.get(header_map[normalized]) or "").strip()
                if student_id:
                    break
        
        rows.append({
            "name": (r.get("name") or "").strip(),
            "student_id": student_id,
            "email": (r.get("email") or r.get("e-mail") or r.get("emailid") or r.get("email_id") or "").strip(),
            "course": (r.get("course") or r.get("program") or r.get("programme") or r.get("branch") or "").strip(),
            "role": (r.get("role") or row["role"]).strip() or "student"
        })

    return {"rows": rows}


@router.get("/attendees", response_model=AttendeeListResponse)
async def list_attendees(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Number of records to return"),
    current_admin: dict = Depends(get_club_admin)
):
    """
    List all attendees for the club (Club Admin only)
    
    Supports pagination.
    """
    
    club_id = current_admin.get("club_id")
    if not club_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Club admin must be associated with a club"
        )
    
    result = await attendee_service.get_attendees(str(club_id), skip=skip, limit=limit)
    return {
        "club_id": result["club_id"],
        "total": result["total"],
        "attendees": result["attendees"]
    }


@router.get("/activity-logs", response_model=ActivityLogResponse)
async def get_activity_logs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=500, description="Number of records to return"),
    action: str = Query(None, description="Filter by action type"),
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    current_admin: dict = Depends(get_club_admin)
):
    """
    Get activity logs for the club (Club Admin only)
    
    Shows all actions performed in the club: template uploads, attendee imports, certificate generations.
    """
    
    club_id = current_admin.get("club_id")
    if not club_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Club admin must be associated with a club"
        )
    
    logs, total = await ActivityLogService.get_club_activity_logs(
        club_id=UUID(club_id),
        limit=limit,
        offset=skip,
        action_filter=action,
        days=days
    )
    
    return ActivityLogResponse(
        logs=logs,
        total=total,
        limit=limit,
        offset=skip,
        has_more=(skip + limit) < total
    )


@router.get("/activity-stats", response_model=ActivityStatsResponse)
async def get_activity_stats(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    current_admin: dict = Depends(get_club_admin)
):
    """
    Get activity statistics for the club (Club Admin only)
    
    Returns aggregated stats about actions: counts, unique admins, last activity times.
    """
    
    club_id = current_admin.get("club_id")
    if not club_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Club admin must be associated with a club"
        )
    
    stats = await ActivityLogService.get_activity_stats(
        club_id=UUID(club_id),
        days=days
    )
    
    return ActivityStatsResponse(**stats)

