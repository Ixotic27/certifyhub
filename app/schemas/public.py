"""
Public Request/Response Models
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Any
from uuid import UUID
from datetime import date


class PublicClubResponse(BaseModel):
    """Public club info"""
    id: UUID
    name: str
    slug: str
    logo_url: Optional[str] = None


class PublicClubListResponse(BaseModel):
    """List of active clubs for public display"""
    total: int
    clubs: List[PublicClubResponse]


class PublicTemplateResponse(BaseModel):
    """Public template info for a club"""
    id: UUID
    name: str
    template_image_url: str
    event_name: Optional[str] = None
    description: Optional[str] = None


class PublicClubDetailResponse(PublicClubResponse):
    """Club details with active templates"""
    templates: List[PublicTemplateResponse]


class CertificateVerifyRequest(BaseModel):
    """Verify a certificate by name + student_id"""
    club_slug: Optional[str] = Field(default=None, min_length=1, max_length=50)
    role: Optional[str] = Field(default=None, min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=200)
    student_id: str = Field(..., min_length=1, max_length=50)
    event_id: Optional[UUID] = Field(default=None)


class CertificateVerifyResponse(BaseModel):
    """Verification result"""
    verified: bool
    attendee_id: UUID
    club_id: UUID
    template_id: Optional[UUID] = None
    template_image_url: Optional[str] = None
    text_fields: Optional[List[Any]] = None
    name: str
    student_id: str
    event_date: Optional[date] = None


class PublicEventResponse(BaseModel):
    """Public event info"""
    id: UUID
    name: str
    description: Optional[str] = None
    event_date: date
    template_id: UUID
    role: str


class PublicEventListResponse(BaseModel):
    """List of events for a club"""
    total: int
    events: List[PublicEventResponse]
