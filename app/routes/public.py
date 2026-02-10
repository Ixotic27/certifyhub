"""
Public Endpoints
Certificate download and verification
"""

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from typing import Optional
from io import BytesIO

from app.database import database
from app.schemas.public import (
    PublicClubListResponse,
    PublicClubResponse,
    PublicClubDetailResponse,
    PublicTemplateResponse,
    PublicEventListResponse,
    PublicEventResponse,
    CertificateVerifyRequest,
    CertificateVerifyResponse,
)
from app.services.certificate_service import CertificateService

router = APIRouter()


@router.get("/clubs", response_model=PublicClubListResponse)
async def list_public_clubs():
    """List all active clubs (public)"""
    clubs = await database.fetch_all(
        "SELECT id, name, slug, logo_url FROM clubs WHERE is_active = TRUE ORDER BY created_at DESC"
    )
    return {
        "total": len(clubs),
        "clubs": [PublicClubResponse(**dict(club)) for club in clubs]
    }


@router.get("/club/{slug}", response_model=PublicClubDetailResponse)
async def get_public_club(slug: str):
    """Get club details and active templates (public)"""
    club = await database.fetch_one(
        "SELECT id, name, slug, logo_url FROM clubs WHERE slug = :slug AND is_active = TRUE",
        {"slug": slug}
    )
    if not club:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Club not found"
        )

    templates = await database.fetch_all(
        """
        SELECT id, name, template_image_url, event_name, description
        FROM certificate_templates
        WHERE club_id = :club_id AND is_active = TRUE
        ORDER BY created_at DESC
        """,
        {"club_id": str(club["id"])}
    )

    return {
        **dict(club),
        "templates": [PublicTemplateResponse(**dict(t)) for t in templates]
    }


@router.get("/events", response_model=PublicEventListResponse)
async def list_public_events(
    club_slug: str = Query(..., min_length=1),
    role: Optional[str] = Query(default=None)
):
    club = await database.fetch_one(
        "SELECT id FROM clubs WHERE slug = :slug AND is_active = TRUE",
        {"slug": club_slug}
    )
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found")

    params = {"club_id": str(club["id"])}
    role_filter = ""
    if role:
        role_filter = "AND role = :role"
        params["role"] = role

    rows = await database.fetch_all(
        f"""
        SELECT id, name, description, event_date, template_id, role
        FROM certificate_events
        WHERE club_id = :club_id AND is_active = TRUE
        {role_filter}
        ORDER BY event_date DESC, created_at DESC
        """,
        params
    )

    return {
        "total": len(rows),
        "events": [PublicEventResponse(**dict(r)) for r in rows]
    }


@router.post("/certificate/verify", response_model=CertificateVerifyResponse)
async def verify_certificate(request: CertificateVerifyRequest):
    """Verify certificate by club slug, name, and student ID"""
    if request.event_id:
        event = await database.fetch_one(
            """
            SELECT e.*, c.slug AS club_slug
            FROM certificate_events e
            JOIN clubs c ON c.id = e.club_id
            WHERE e.id = :event_id AND e.is_active = TRUE
            """,
            {"event_id": str(request.event_id)}
        )
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        attendee = await database.fetch_one(
            """
            SELECT * FROM attendees
            WHERE club_id = :club_id
              AND import_id = :import_id
              AND student_id = :student_id
              AND LOWER(name) = LOWER(:name)
              AND role = :role
            """,
            {
                "club_id": str(event["club_id"]),
                "import_id": str(event["import_id"]),
                "student_id": request.student_id,
                "name": request.name,
                "role": event["role"]
            }
        )
        if not attendee:
            raise HTTPException(status_code=404, detail="No matching attendee found")

        attendee = dict(attendee)
        attendee["event_date"] = event["event_date"]
        attendee["event_name"] = event["name"]
        attendee["template_id"] = event["template_id"]
        club = {"id": event["club_id"], "slug": event["club_slug"]}
    else:
        if request.club_slug:
            club = await CertificateService.get_club_by_slug(request.club_slug)
            attendee = await CertificateService.get_attendee_for_verification(
                str(club["id"]),
                request.name,
                request.student_id,
                role=request.role
            )
        else:
            attendee = await CertificateService.get_attendee_for_verification_any_club(
                request.name,
                request.student_id,
                role=request.role
            )
            club = await CertificateService.get_club_by_slug(attendee["club_slug"])

    template = await CertificateService.resolve_template(
        str(club["id"]),
        attendee.get("template_id"),
        attendee.get("template_id"),
        audience=attendee.get("role")
    )
    text_fields = CertificateService._parse_text_fields(template.get("text_fields"))

    return {
        "verified": True,
        "attendee_id": attendee["id"],
        "club_id": club["id"],
        "template_id": attendee.get("template_id"),
        "template_image_url": template.get("template_image_url"),
        "text_fields": text_fields,
        "name": attendee.get("name"),
        "student_id": attendee.get("student_id"),
        "event_date": attendee.get("event_date")
    }


@router.post("/verify", response_model=CertificateVerifyResponse)
async def verify_certificate_alias(request: CertificateVerifyRequest):
    """Alias for certificate verification"""
    return await verify_certificate(request)


@router.get("/certificate/download")
async def download_certificate(
    request: Request,
    club_slug: Optional[str] = Query(default=None, description="Club slug"),
    name: str = Query(..., description="Attendee name"),
    student_id: str = Query(..., description="Attendee student ID"),
    template_id: Optional[str] = Query(default=None, description="Optional template ID"),
    role: Optional[str] = Query(default=None, description="Optional attendee role"),
    event_id: Optional[str] = Query(default=None, description="Optional event ID")
):
    """Generate and download certificate PDF"""
    client_ip = request.client.host if request and request.client else None
    
    # If event_id is provided, derive template_id and club_slug from event
    if event_id:
        event = await database.fetch_one(
            """
            SELECT e.*, c.slug AS club_slug
            FROM certificate_events e
            JOIN clubs c ON c.id = e.club_id
            WHERE e.id = :event_id AND e.is_active = TRUE
            """,
            {"event_id": event_id}
        )
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        template_id = str(event["template_id"])
        club_slug = event["club_slug"]

    # If template_id is provided, get club_slug from template (allows "Try Certificate" without attendee in DB)
    if not club_slug and template_id:
        template = await database.fetch_one(
            """
            SELECT t.*, c.slug AS club_slug
            FROM certificate_templates t
            JOIN clubs c ON c.id = t.club_id
            WHERE t.id = :template_id AND t.is_active = TRUE
            """,
            {"template_id": template_id}
        )
        if template:
            club_slug = template["club_slug"]
    
    # Fallback: get club_slug from attendee lookup
    if not club_slug:
        attendee = await CertificateService.get_attendee_for_verification_any_club(name, student_id, role=role)
        club_slug = attendee["club_slug"]

    # If event_id is set, validate attendee against the event import list
    if event_id:
        event = await database.fetch_one(
            """
            SELECT * FROM certificate_events
            WHERE id = :event_id AND is_active = TRUE
            """,
            {"event_id": event_id}
        )
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        attendee = await database.fetch_one(
            """
            SELECT * FROM attendees
            WHERE club_id = :club_id
              AND import_id = :import_id
              AND student_id = :student_id
              AND LOWER(name) = LOWER(:name)
              AND role = :role
            """,
            {
                "club_id": str(event["club_id"]),
                "import_id": str(event["import_id"]),
                "student_id": student_id,
                "name": name,
                "role": event["role"]
            }
        )
        if not attendee:
            raise HTTPException(status_code=404, detail="No matching attendee found")
        attendee = dict(attendee)
        attendee["event_date"] = event["event_date"]
        attendee["event_name"] = event["name"]
        
    pdf_bytes, certificate_id = await CertificateService.generate_certificate_pdf(
        club_slug=club_slug,
        name=name,
        student_id=student_id,
        template_id=template_id,
        client_ip=client_ip,
        role=role,
        event_id=event_id
    )

    filename = f"certificate_{student_id}_{certificate_id}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/certificate")
async def download_certificate_alias(
    request: Request,
    club_slug: str = Query(..., description="Club slug"),
    name: str = Query(..., description="Attendee name"),
    student_id: str = Query(..., description="Attendee student ID"),
    template_id: Optional[str] = Query(default=None, description="Optional template ID")
):
    """Alias for certificate download"""
    return await download_certificate(
        request=request,
        club_slug=club_slug,
        name=name,
        student_id=student_id,
        template_id=template_id
    )
