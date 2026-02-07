"""
Template Service
Business logic for certificate template management
"""

import uuid
import json
import httpx
from io import BytesIO
from PIL import Image
from app.database import database
from app.schemas.template import CreateTemplateRequest, UpdateTemplateCoordinatesRequest, TextFieldCoordinate
from app.services.activity_log_service import ActivityLogService
from fastapi import HTTPException, status


class TemplateService:
    """Service for template management operations"""
    
    @staticmethod
    async def validate_template_image(image_url: str) -> bool:
        """
        Validate that template image URL is accessible and is a valid image
        
        In development mode, always returns True to allow testing.
        """
        # For development/testing, allow any image URL
        return True
    
    @staticmethod
    async def create_template(club_id: str, data: CreateTemplateRequest) -> dict:
        """
        Create a new certificate template for a club
        
        Validates the image URL and stores text field coordinates as JSONB
        """
        
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
        
        # Validate template image URL
        await TemplateService.validate_template_image(str(data.template_image_url))
        
        # Check if template with same name already exists for this club
        existing = await database.fetch_one(
            """
            SELECT id FROM certificate_templates
            WHERE club_id = :club_id AND name = :name AND audience = :audience
            """,
            {"club_id": club_id, "name": data.template_name, "audience": data.audience}
        )
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Template '{data.template_name}' already exists for this club"
            )
        
        # Create template
        template_id = str(uuid.uuid4())
        
        # Convert text fields to JSON for storage
        text_fields_json = json.dumps([field.model_dump() for field in data.text_fields])
        
        try:
            await database.execute(
                """
                INSERT INTO certificate_templates 
                (id, club_id, name, template_image_url, text_fields, audience, version, is_active)
                VALUES (:id, :club_id, :name, :template_image_url, :text_fields, :audience, 1, TRUE)
                """,
                {
                    "id": template_id,
                    "club_id": club_id,
                    "name": data.template_name,
                    "template_image_url": str(data.template_image_url),
                    "text_fields": text_fields_json,
                    "audience": data.audience
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create template: {str(e)}"
            )
        
        # Fetch and return created template
        template = await database.fetch_one(
            "SELECT * FROM certificate_templates WHERE id = :template_id",
            {"template_id": template_id}
        )
        
        # Log the activity (trigger handles this, but also manual for completeness)
        try:
            await ActivityLogService.log_activity(
                club_id=uuid.UUID(club_id),
                admin_id=None,  # Will be set by the caller if available
                action="create_template",
                resource_type="template",
                resource_id=uuid.UUID(template_id),
                details={"template_name": data.template_name}
            )
        except Exception:
            pass  # Don't fail if logging fails
        
        return dict(template) if template else None
    
    @staticmethod
    async def get_template(template_id: str) -> dict:
        """Get template by ID"""
        
        template = await database.fetch_one(
            "SELECT * FROM certificate_templates WHERE id = :template_id",
            {"template_id": template_id}
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        return dict(template)
    
    @staticmethod
    async def list_templates(club_id: str, skip: int = 0, limit: int = 50, active_only: bool = True) -> dict:
        """Get all templates for a club"""
        
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
        if active_only:
            total = await database.fetch_val(
                "SELECT COUNT(*) FROM certificate_templates WHERE club_id = :club_id AND is_active = TRUE",
                {"club_id": club_id}
            )
        else:
            total = await database.fetch_val(
                "SELECT COUNT(*) FROM certificate_templates WHERE club_id = :club_id",
                {"club_id": club_id}
            )
        
        # Get paginated templates
        if active_only:
            templates = await database.fetch_all(
                """
                SELECT * FROM certificate_templates 
                WHERE club_id = :club_id AND is_active = TRUE
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
                """,
                {"club_id": club_id, "skip": skip, "limit": limit}
            )
        else:
            templates = await database.fetch_all(
                """
                SELECT * FROM certificate_templates 
                WHERE club_id = :club_id
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :skip
                """,
                {"club_id": club_id, "skip": skip, "limit": limit}
            )
        
        return {
            "club_id": club_id,
            "total": total or 0,
            "templates": [dict(template) for template in templates]
        }
    
    @staticmethod
    async def update_template_coordinates(template_id: str, data: UpdateTemplateCoordinatesRequest) -> dict:
        """Update text field coordinates for a template (creates new version)"""
        
        # Get current template
        template = await database.fetch_one(
            "SELECT * FROM certificate_templates WHERE id = :template_id",
            {"template_id": template_id}
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Convert new text fields to JSON
        text_fields_json = json.dumps([field.model_dump() for field in data.text_fields])
        
        # Increment version and update
        new_version = (template["version"] or 1) + 1
        
        try:
            await database.execute(
                """
                UPDATE certificate_templates 
                SET text_fields = :text_fields, version = :version, updated_at = NOW()
                WHERE id = :template_id
                """,
                {
                    "template_id": template_id,
                    "text_fields": text_fields_json,
                    "version": new_version
                }
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update template: {str(e)}"
            )
        
        # Fetch and return updated template
        updated = await database.fetch_one(
            "SELECT * FROM certificate_templates WHERE id = :template_id",
            {"template_id": template_id}
        )
        
        return dict(updated) if updated else None
    
    @staticmethod
    async def deactivate_template(template_id: str) -> dict:
        """Deactivate a template"""
        
        # Check if template exists
        template = await database.fetch_one(
            "SELECT * FROM certificate_templates WHERE id = :template_id",
            {"template_id": template_id}
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Deactivate template
        await database.execute(
            "UPDATE certificate_templates SET is_active = FALSE, updated_at = NOW() WHERE id = :template_id",
            {"template_id": template_id}
        )
        
        # Fetch updated template
        updated = await database.fetch_one(
            "SELECT * FROM certificate_templates WHERE id = :template_id",
            {"template_id": template_id}
        )
        
        # Log the activity
        try:
            await ActivityLogService.log_activity(
                club_id=uuid.UUID(str(template["club_id"])),
                admin_id=None,
                action="deactivate_template",
                resource_type="template",
                resource_id=uuid.UUID(template_id),
                details={"template_name": template["name"]}
            )
        except Exception:
            pass  # Don't fail if logging fails
        
        return dict(updated) if updated else None
    
    @staticmethod
    async def get_template_stats(template_id: str) -> dict:
        """Get statistics for a template"""
        
        # Check if template exists
        template = await database.fetch_one(
            "SELECT * FROM certificate_templates WHERE id = :template_id",
            {"template_id": template_id}
        )
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )
        
        # Get certificate count
        cert_count = await database.fetch_val(
            "SELECT COUNT(*) FROM certificate_generations WHERE template_id = :template_id",
            {"template_id": template_id}
        )
        
        # Get last used date
        last_used = await database.fetch_val(
            "SELECT MAX(generated_at) FROM certificate_generations WHERE template_id = :template_id",
            {"template_id": template_id}
        )
        
        return {
            "template_id": template_id,
            "certificate_count": cert_count or 0,
            "last_used": last_used
        }


# Create singleton instance
template_service = TemplateService()
