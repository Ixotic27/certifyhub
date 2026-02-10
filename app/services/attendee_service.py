"""
Attendee Service
Business logic for attendee management and CSV import
"""

import csv
import uuid
import io
from typing import Optional, List, Tuple
from app.database import database
from app.schemas.attendee import CSVValidationError
from app.services.activity_log_service import ActivityLogService
from fastapi import HTTPException, status


class AttendeeService:
    """Service for attendee management operations"""
    
    @staticmethod
    async def parse_and_validate_csv(
        csv_content: str,
        club_id: str,
        skip_errors: bool = False,
        default_role: str = "student"
    ) -> Tuple[List[dict], List[CSVValidationError]]:
        """
        Parse CSV content and validate entries
        
        Required columns: name, student_id
        Optional columns: email
        
        Returns: (validated_attendees, errors)
        """
        
        errors = []
        validated_attendees = []
        seen_student_ids = set()  # For duplicate detection
        
        # Existing student IDs in database for this club
        existing_students = await database.fetch_all(
            "SELECT student_id FROM attendees WHERE club_id = :club_id",
            {"club_id": club_id}
        )
        existing_ids = {row["student_id"] for row in existing_students}
        
        try:
            # Parse CSV
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            
            if not csv_reader.fieldnames:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="CSV file is empty or has no headers"
                )

            # Normalize headers (trim, lowercase, remove BOM)
            normalized_headers = [
                (h or "").strip().lstrip("\ufeff").lower()
                for h in csv_reader.fieldnames
            ]
            csv_reader.fieldnames = normalized_headers
            
            # Required fields are validated per-row; do not hard-fail on missing headers
            
            for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (after headers)
                try:
                    # Normalize row keys
                    row = {(
                        (k or "").strip().lower()
                    ): (v if v is not None else "") for k, v in row.items()}

                    # Validate required fields
                    name = row.get("name", "").strip()
                    student_id = row.get("student_id", "").strip()
                    email = row.get("email", "").strip() if row.get("email") else None
                    role = row.get("role", "").strip().lower() if row.get("role") else default_role
                    
                    # Validation
                    if not name:
                        raise ValueError("name cannot be empty")
                    if not student_id:
                        raise ValueError("student_id cannot be empty")
                    
                    if len(name) > 200:
                        raise ValueError("name too long (max 200 characters)")
                    if len(student_id) > 50:
                        raise ValueError("student_id too long (max 50 characters)")
                    
                    # Check for duplicates within CSV
                    if student_id in seen_student_ids:
                        raise ValueError(f"Duplicate student_id in CSV: {student_id}")
                    
                    # Check for duplicates in database
                    if student_id in existing_ids:
                        raise ValueError(f"student_id already exists in database: {student_id}")
                    
                    seen_student_ids.add(student_id)
                    
                    # Validate email if provided
                    if email:
                        # Basic email validation
                        if "@" not in email or len(email) < 5:
                            raise ValueError(f"Invalid email format: {email}")
                    
                    if role not in {"student", "management"}:
                        raise ValueError("role must be student or management")

                    validated_attendees.append({
                        "name": name,
                        "student_id": student_id,
                        "email": email,
                        "role": role
                    })
                
                except ValueError as e:
                    error = CSVValidationError(
                        row=row_num,
                        error=str(e),
                        data=dict(row)
                    )
                    errors.append(error)
                    
                    if not skip_errors:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Row {row_num}: {str(e)}"
                        )
        
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"CSV parsing error: {str(e)}"
            )
        
        return validated_attendees, errors
    
    @staticmethod
    async def upload_attendees(club_id: str, attendees: List[dict], import_id: Optional[str] = None) -> int:
        """
        Insert validated attendees into database
        
        Returns: Number of attendees inserted
        """
        
        if not attendees:
            return 0
        
        # Prepare records for bulk insert
        records = []
        for attendee in attendees:
            records.append({
                "id": str(uuid.uuid4()),
                "club_id": club_id,
                "name": attendee["name"],
                "email": attendee.get("email"),
                "student_id": attendee["student_id"],
                "role": attendee.get("role", "student"),
                "certificate_generated_count": 0,
                "import_id": import_id
            })
        
        # Bulk insert
        try:
            values_placeholder = ",".join([
                f"(:id_{i}, :club_id_{i}, :name_{i}, :email_{i}, :student_id_{i}, :role_{i}, :cert_count_{i}, :import_id_{i})"
                for i in range(len(records))
            ])
            
            query = f"""
                INSERT INTO attendees 
                (id, club_id, name, email, student_id, role, certificate_generated_count, import_id)
                VALUES {values_placeholder}
            """
            
            params = {}
            for i, record in enumerate(records):
                params[f"id_{i}"] = record["id"]
                params[f"club_id_{i}"] = record["club_id"]
                params[f"name_{i}"] = record["name"]
                params[f"email_{i}"] = record["email"]
                params[f"student_id_{i}"] = record["student_id"]
                params[f"role_{i}"] = record["role"]
                params[f"cert_count_{i}"] = record["certificate_generated_count"]
                params[f"import_id_{i}"] = record["import_id"]
            
            await database.execute(query, params)
            
            # Log the activity
            try:
                await ActivityLogService.log_activity(
                    club_id=uuid.UUID(club_id),
                    admin_id=None,
                    action="import_attendees",
                    resource_type="attendee",
                    details={"count": len(records)}
                )
            except Exception:
                pass  # Don't fail if logging fails
            
            return len(records)
        
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to insert attendees: {str(e)}"
            )
    
    @staticmethod
    async def get_attendees(club_id: str, skip: int = 0, limit: int = 100) -> dict:
        """Get all attendees for a club"""
        
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
        total = await database.fetch_val(
            "SELECT COUNT(*) FROM attendees WHERE club_id = :club_id",
            {"club_id": club_id}
        )
        
        # Get paginated attendees
        attendees = await database.fetch_all(
            """
            SELECT * FROM attendees 
            WHERE club_id = :club_id
            ORDER BY uploaded_at DESC
            LIMIT :limit OFFSET :skip
            """,
            {"club_id": club_id, "skip": skip, "limit": limit}
        )
        
        return {
            "club_id": club_id,
            "total": total or 0,
            "attendees": [dict(attendee) for attendee in attendees]
        }
    
    @staticmethod
    async def get_attendee(attendee_id: str) -> dict:
        """Get attendee by ID"""
        
        attendee = await database.fetch_one(
            "SELECT * FROM attendees WHERE id = :attendee_id",
            {"attendee_id": attendee_id}
        )
        
        if not attendee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attendee not found"
            )
        
        return dict(attendee)
    
    @staticmethod
    async def get_attendee_by_student_id(club_id: str, student_id: str) -> dict:
        """Get attendee by student ID (for certificate lookup)"""
        
        attendee = await database.fetch_one(
            "SELECT * FROM attendees WHERE club_id = :club_id AND student_id = :student_id",
            {"club_id": club_id, "student_id": student_id}
        )
        
        if not attendee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Attendee not found"
            )
        
        return dict(attendee)


# Create singleton instance
attendee_service = AttendeeService()
