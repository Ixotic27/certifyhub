"""
Certificate Service
Business logic for certificate verification and PDF generation
"""

import json
import uuid
from io import BytesIO
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

import httpx
import img2pdf
from PIL import Image, ImageDraw, ImageFont
from fastapi import HTTPException, status

from app.database import database
from app.config import settings
from app.services.activity_log_service import ActivityLogService


class CertificateService:
    """Service for public certificate operations"""

    @staticmethod
    async def get_club_by_slug(slug: str) -> dict:
        club = await database.fetch_one(
            "SELECT * FROM clubs WHERE slug = :slug AND is_active = TRUE",
            {"slug": slug}
        )
        if not club:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Club not found"
            )
        return dict(club)

    @staticmethod
    async def get_attendee_for_verification(
        club_id: str,
        name: str,
        student_id: str,
        role: Optional[str] = None
    ) -> dict:
        if role:
            attendee = await database.fetch_one(
                """
                SELECT * FROM attendees
                WHERE club_id = :club_id
                  AND student_id = :student_id
                  AND LOWER(name) = LOWER(:name)
                  AND role = :role
                """,
                {"club_id": club_id, "student_id": student_id, "name": name, "role": role}
            )
        else:
            attendee = await database.fetch_one(
                """
                SELECT * FROM attendees
                WHERE club_id = :club_id
                  AND student_id = :student_id
                  AND LOWER(name) = LOWER(:name)
                """,
                {"club_id": club_id, "student_id": student_id, "name": name}
            )
        if not attendee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching attendee found"
            )
        return dict(attendee)

    @staticmethod
    async def get_attendee_for_verification_any_club(
        name: str,
        student_id: str,
        role: Optional[str] = None
    ) -> dict:
        if role:
            attendee = await database.fetch_one(
                """
                SELECT a.*, c.slug AS club_slug
                FROM attendees a
                JOIN clubs c ON c.id = a.club_id
                WHERE a.student_id = :student_id
                  AND LOWER(a.name) = LOWER(:name)
                  AND a.role = :role
                  AND c.is_active = TRUE
                ORDER BY a.updated_at DESC
                LIMIT 1
                """,
                {"student_id": student_id, "name": name, "role": role}
            )
        else:
            attendee = await database.fetch_one(
                """
                SELECT a.*, c.slug AS club_slug
                FROM attendees a
                JOIN clubs c ON c.id = a.club_id
                WHERE a.student_id = :student_id
                  AND LOWER(a.name) = LOWER(:name)
                  AND c.is_active = TRUE
                ORDER BY a.updated_at DESC
                LIMIT 1
                """,
                {"student_id": student_id, "name": name}
            )
        if not attendee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No matching attendee found"
            )
        return dict(attendee)

    @staticmethod
    async def resolve_template(
        club_id: str,
        template_id: Optional[str],
        attendee_template_id: Optional[str],
        audience: Optional[str] = None
    ) -> dict:
        if template_id:
            template = await database.fetch_one(
                """
                SELECT * FROM certificate_templates
                WHERE id = :template_id AND club_id = :club_id AND is_active = TRUE
                """,
                {"template_id": template_id, "club_id": club_id}
            )
        elif attendee_template_id:
            template = await database.fetch_one(
                """
                SELECT * FROM certificate_templates
                WHERE id = :template_id AND club_id = :club_id AND is_active = TRUE
                """,
                {"template_id": attendee_template_id, "club_id": club_id}
            )
        else:
            template = await database.fetch_one(
                """
                SELECT * FROM certificate_templates
                WHERE club_id = :club_id AND is_active = TRUE
                  AND (:audience IS NULL OR audience = :audience)
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                {"club_id": club_id, "audience": audience}
            )

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active template found for this club"
            )

        return dict(template)

    @staticmethod
    def _parse_text_fields(text_fields) -> list:
        if isinstance(text_fields, str):
            try:
                return json.loads(text_fields)
            except json.JSONDecodeError:
                return []
        if isinstance(text_fields, list):
            return text_fields
        return []

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        if not hex_color:
            return (0, 0, 0)
        color = hex_color.strip().lstrip("#")
        if len(color) != 6:
            return (0, 0, 0)
        try:
            return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            return (0, 0, 0)

    @staticmethod
    def _load_font(font_family: str, font_size: int) -> ImageFont.ImageFont:
        candidates = []
        if font_family:
            candidates.append(font_family)
            if not font_family.lower().endswith(".ttf"):
                candidates.append(f"{font_family}.ttf")

        windows_fonts = Path("C:/Windows/Fonts")
        for candidate in candidates:
            font_path = windows_fonts / candidate
            if font_path.exists():
                return ImageFont.truetype(str(font_path), font_size)
            try:
                return ImageFont.truetype(candidate, font_size)
            except Exception:
                continue

        return ImageFont.load_default()

    @staticmethod
    def _resolve_field_value(field_type: str, attendee: dict, template: dict, field: dict) -> str:
        if field_type == "name":
            return attendee.get("name", "")
        if field_type == "student_id":
            return attendee.get("student_id", "")
        if field_type == "date":
            event_date = attendee.get("event_date")
            if event_date:
                return event_date.strftime("%B %d, %Y")
            return datetime.utcnow().strftime("%B %d, %Y")
        if field_type == "achievement":
            return attendee.get("course") or attendee.get("event_name") or template.get("event_name") or ""
        if field_type == "custom":
            return field.get("field_name") or field.get("label", "")
        return ""

    @staticmethod
    def _apply_alignment(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, x: int, align: str) -> int:
        if not text:
            return x
        align_value = (align or "left").lower()
        if align_value not in {"center", "right"}:
            return x
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        if align_value == "center":
            return x - (text_width // 2)
        return x - text_width

    @staticmethod
    async def generate_certificate_pdf(
        club_slug: str,
        name: str,
        student_id: str,
        template_id: Optional[str],
        client_ip: Optional[str],
        role: Optional[str] = None,
        event_id: Optional[str] = None
    ) -> Tuple[bytes, str]:
        club = await CertificateService.get_club_by_slug(club_slug)

        if event_id:
            event = await database.fetch_one(
                """
                SELECT * FROM certificate_events
                WHERE id = :event_id AND is_active = TRUE
                """,
                {"event_id": event_id}
            )
            if not event:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

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
                    "club_id": str(club["id"]),
                    "import_id": str(event["import_id"]),
                    "student_id": student_id,
                    "name": name,
                    "role": event["role"]
                }
            )
            if not attendee:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching attendee found")

            attendee = dict(attendee)
            attendee["event_date"] = event["event_date"]
            attendee["event_name"] = event["name"]
            template_id = str(event["template_id"])
            role = event["role"]
        else:
            attendee = await CertificateService.get_attendee_for_verification(
                str(club["id"]),
                name,
                student_id,
                role=role
            )

        template = await CertificateService.resolve_template(
            str(club["id"]),
            template_id,
            attendee.get("template_id"),
            audience=attendee.get("role")
        )

        text_fields = CertificateService._parse_text_fields(template.get("text_fields"))

        image = None
        try:
            template_url = template["template_image_url"]
            if template_url.startswith("/static/") or "://" not in template_url:
                local_path = Path(".") / template_url.lstrip("/")
                image_bytes = local_path.read_bytes()
            else:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(template_url)
                    if response.status_code != 200:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Template image could not be fetched"
                        )
                    image_bytes = response.content

            image = Image.open(BytesIO(image_bytes))
        except Exception as e:
            if settings.APP_ENV == "development":
                image = Image.new("RGB", (1200, 800), "white")
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid template image: {str(e)}"
                )

        if image.mode != "RGB":
            image = image.convert("RGB")

        draw = ImageDraw.Draw(image)
        for field in text_fields:
            field_type = str(field.get("field_type") or field.get("field") or "").lower()
            value = CertificateService._resolve_field_value(field_type, attendee, template, field)
            if value is None:
                value = ""
            font_size = int(field.get("font_size", 40))
            font_family = field.get("font_family", "Arial")
            font_color = CertificateService._hex_to_rgb(field.get("font_color") or field.get("color", "#000000"))
            font = CertificateService._load_font(font_family, font_size)
            x = int(field.get("x", 0))
            y = int(field.get("y", 0))
            align = field.get("align", "left")
            x = CertificateService._apply_alignment(draw, str(value), font, x, align)
            draw.text((x, y), str(value), fill=font_color, font=font)

        img_buffer = BytesIO()
        image.save(img_buffer, format="PNG")
        pdf_bytes = img2pdf.convert(img_buffer.getvalue())

        certificate_id = f"CERT-{club_slug.upper()}-{student_id}"
        await database.execute(
            """
            INSERT INTO certificate_generations
            (id, club_id, attendee_id, template_id, certificate_id, generated_by_user, ip_address, event_id)
            VALUES (:id, :club_id, :attendee_id, :template_id, :certificate_id, 'public', :ip_address, :event_id)
            """,
            {
                "id": str(uuid.uuid4()),
                "club_id": str(club["id"]),
                "attendee_id": str(attendee["id"]),
                "template_id": str(template["id"]),
                "certificate_id": certificate_id,
                "ip_address": client_ip,
                "event_id": event_id
            }
        )

        await database.execute(
            """
            UPDATE attendees
            SET certificate_generated_count = COALESCE(certificate_generated_count, 0) + 1,
                first_generated_at = COALESCE(first_generated_at, NOW()),
                last_generated_at = NOW(),
                template_id = :template_id
            WHERE id = :attendee_id
            """,
            {"template_id": str(template["id"]), "attendee_id": str(attendee["id"])}
        )

        # Log the activity
        try:
            await ActivityLogService.log_activity(
                club_id=uuid.UUID(str(club["id"])),
                admin_id=None,
                action="generate_certificate",
                resource_type="certificate",
                resource_id=uuid.UUID(str(attendee["id"])),
                details={
                    "certificate_id": certificate_id,
                    "student_id": student_id,
                    "template_id": str(template["id"])
                },
                ip_address=client_ip
            )
        except Exception:
            pass  # Don't fail if logging fails

        return pdf_bytes, certificate_id
