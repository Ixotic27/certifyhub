"""
Certificate Template Request/Response Models
"""

from pydantic import BaseModel, Field, AliasChoices
from typing import Optional, List, Union
from datetime import datetime
from uuid import UUID
from enum import Enum
import json


class TextFieldType(str, Enum):
    """Type of text field on certificate"""
    NAME = "name"
    STUDENT_ID = "student_id"
    ACHIEVEMENT = "achievement"
    DATE = "date"
    CUSTOM = "custom"


class TextFieldCoordinate(BaseModel):
    """Coordinate for a text field on the certificate"""
    field_type: TextFieldType = Field(
        ..., 
        validation_alias=AliasChoices("field_type", "field"),
        description="Type of field (name, student_id, etc)"
    )
    field_name: str = Field(
        ..., 
        min_length=1, 
        max_length=50, 
        validation_alias=AliasChoices("field_name", "label"),
        description="Display name of field"
    )
    x: int = Field(..., ge=0, description="X coordinate in pixels")
    y: int = Field(..., ge=0, description="Y coordinate in pixels")
    font_size: int = Field(default=40, ge=8, le=200, description="Font size in pixels")
    font_color: str = Field(
        default="#000000",
        validation_alias=AliasChoices("font_color", "color"),
        description="Hex color code (e.g., #000000)"
    )
    font_family: str = Field(default="Arial", description="Font family name")
    align: str = Field(default="left", description="Text alignment (left, center, right)")
    
    class Config:
        example = {
            "field_type": "name",
            "field_name": "Recipient Name",
            "x": 100,
            "y": 200,
            "font_size": 48,
            "font_color": "#000000",
            "font_family": "Arial"
        }


class CreateTemplateRequest(BaseModel):
    """Request to upload a certificate template"""
    template_name: str = Field(..., min_length=1, max_length=100, description="Template name")
    template_image_url: str = Field(..., description="URL or path to template image")
    audience: str = Field(default="student", description="Template audience: student or management")
    text_fields: List[TextFieldCoordinate] = Field(default_factory=list, description="Text field coordinates")
    
    class Config:
        example = {
            "template_name": "Standard Certificate 2026",
            "template_image_url": "https://example.com/images/certificate-template.png",
            "text_fields": [
                {
                    "field_type": "name",
                    "field_name": "Recipient Name",
                    "x": 400,
                    "y": 350,
                    "font_size": 48,
                    "font_color": "#000000",
                    "font_family": "Arial"
                },
                {
                    "field_type": "date",
                    "field_name": "Issue Date",
                    "x": 350,
                    "y": 500,
                    "font_size": 28,
                    "font_color": "#666666",
                    "font_family": "Arial"
                }
            ]
        }


class UpdateTemplateCoordinatesRequest(BaseModel):
    """Request to update text field coordinates"""
    text_fields: List[TextFieldCoordinate] = Field(..., description="Updated text field coordinates")


class TemplateResponse(BaseModel):
    """Certificate template details"""
    id: UUID
    club_id: UUID
    name: str
    template_image_url: str
    audience: str
    text_fields: Union[dict, str]  # Can be dict or JSON string from DB
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def model_validate(cls, obj):
        """Parse text_fields if it's a JSON string"""
        if isinstance(obj, dict):
            if isinstance(obj.get("text_fields"), str):
                obj = dict(obj)  # Make a copy
                try:
                    obj["text_fields"] = json.loads(obj["text_fields"])
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep as is if not valid JSON
        return super().model_validate(obj)
    
    class Config:
        from_attributes = True


class TemplateListResponse(BaseModel):
    """List of templates for a club"""
    club_id: UUID
    total: int
    templates: List[TemplateResponse]


class TemplateDetailResponse(TemplateResponse):
    """Template with additional stats"""
    certificate_count: int = Field(default=0, description="Number of certificates generated")
    last_used: Optional[datetime] = Field(default=None, description="Last time template was used")
