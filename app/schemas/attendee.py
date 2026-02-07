"""
Attendee Request/Response Models
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class AttendeeRequest(BaseModel):
    """Single attendee record"""
    name: str = Field(..., min_length=1, max_length=200, description="Full name")
    student_id: str = Field(..., min_length=1, max_length=50, description="Unique student/roll number")
    email: Optional[EmailStr] = Field(default=None, description="Email address (optional)")
    role: str = Field(default="student", description="Attendee role: student or management")
    
    class Config:
        example = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "student_id": "CS-2024-001"
        }


class CSVUploadRequest(BaseModel):
    """CSV file upload request"""
    csv_content: str = Field(..., description="CSV content as string (first line should be headers)")
    skip_errors: bool = Field(default=False, description="Skip invalid rows instead of failing")
    role: str = Field(default="student", description="Default role for attendees if CSV has no role column")
    
    class Config:
        example = {
            "csv_content": "name,email,student_id\nJohn Doe,john@example.com,CS-2024-001\nJane Smith,jane@example.com,CS-2024-002",
            "skip_errors": False
        }


class AttendeeResponse(BaseModel):
    """Attendee details"""
    id: UUID
    club_id: UUID
    name: str
    student_id: str
    email: Optional[str]
    role: str
    certificate_generated_count: int
    first_generated_at: Optional[datetime]
    last_generated_at: Optional[datetime]
    uploaded_at: datetime
    
    class Config:
        from_attributes = True


class AttendeeListResponse(BaseModel):
    """List of attendees"""
    club_id: UUID
    total: int
    attendees: List[AttendeeResponse]


class CSVUploadResponse(BaseModel):
    """Response from CSV upload"""
    club_id: UUID
    total_rows_processed: int
    successful_imports: int
    failed_imports: int
    errors: List[dict] = Field(default_factory=list, description="List of errors with row number and message")
    
    class Config:
        example = {
            "club_id": "uuid-here",
            "total_rows_processed": 100,
            "successful_imports": 98,
            "failed_imports": 2,
            "errors": [
                {"row": 5, "error": "Missing student_id"},
                {"row": 23, "error": "Duplicate student_id: CS-2024-005"}
            ]
        }


class CSVValidationError(BaseModel):
    """Error in CSV row"""
    row: int = Field(..., description="Row number (1-indexed)")
    error: str = Field(..., description="Error message")
    data: Optional[dict] = Field(default=None, description="Row data that failed")
