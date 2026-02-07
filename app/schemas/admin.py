"""
Club Admin Request/Response Models
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class CreateClubAdminRequest(BaseModel):
    """Request to add a club admin"""
    email: EmailStr = Field(..., description="Admin email (must be unique)")
    full_name: str = Field(..., min_length=1, max_length=100, description="Full name")
    
    class Config:
        example = {
            "email": "admin@club.com",
            "full_name": "John Doe"
        }


class ClubAdminResponse(BaseModel):
    """Club admin details"""
    id: UUID
    club_id: UUID
    email: str
    full_name: Optional[str]
    is_active: bool
    last_login: Optional[datetime]
    password_changed_at: Optional[datetime]
    must_change_password: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ClubAdminCreatedResponse(ClubAdminResponse):
    """Response after creating admin (includes generated password)"""
    temp_password: str = Field(..., description="Generated temporary password (send via email)")


class ClubAdminListResponse(BaseModel):
    """List of club admins"""
    club_id: UUID
    total: int
    admins: list[ClubAdminResponse]


class DashboardTrendItem(BaseModel):
    """Daily generation count"""
    date: datetime
    count: int


class DashboardTopDownloaded(BaseModel):
    """Top downloaded attendee"""
    name: str
    student_id: str
    certificate_generated_count: int


class AdminDashboardResponse(BaseModel):
    """Club admin dashboard stats"""
    club_id: UUID
    total_templates: int
    active_templates: int
    total_attendees: int
    certificates_generated: int
    never_generated: int
    trend_7_days: list[DashboardTrendItem]
    top_downloaded: list[DashboardTopDownloaded]
