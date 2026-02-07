"""
Club Request/Response Models
For platform admin club management
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class CreateClubRequest(BaseModel):
    """Request to create a new club"""
    name: str = Field(..., min_length=1, max_length=100, description="Club name")
    slug: str = Field(..., min_length=1, max_length=50, description="URL-friendly slug (lowercase, no spaces)")
    contact_email: EmailStr = Field(..., description="Club contact email")
    logo_url: Optional[str] = Field(None, description="URL to club logo")
    
    class Config:
        example = {
            "name": "Computer Science Club",
            "slug": "cs-club",
            "contact_email": "cs@university.edu",
            "logo_url": "https://cdn.example.com/logos/cs.png"
        }


class UpdateClubRequest(BaseModel):
    """Request to update club details"""
    name: Optional[str] = Field(None, max_length=100)
    contact_email: Optional[EmailStr] = None
    logo_url: Optional[str] = None
    is_active: Optional[bool] = None


class ClubResponse(BaseModel):
    """Club details response"""
    id: UUID
    name: str
    slug: str
    contact_email: str
    logo_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ClubListResponse(BaseModel):
    """List of clubs response"""
    total: int
    clubs: list[ClubResponse]


class ClubDetailedResponse(ClubResponse):
    """Club with admin count"""
    admin_count: int
    template_count: int
    attendee_count: int


class PlatformAnalyticsResponse(BaseModel):
    """Platform-wide analytics response"""
    total_clubs: int
    active_clubs: int
    inactive_clubs: int
    platform_admins: int
    club_admins: int
    templates: int
    attendees: int
    certificates: int
