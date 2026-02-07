"""
CSV Parser Service
Parsing, validation, and duplicate detection for attendee CSV uploads
"""

import csv
import io
from typing import List, Dict, Tuple
from fastapi import HTTPException, status
from app.database import database


class CSVParser:
    """Utility for parsing attendee CSV files"""

    HEADER_ALIASES = {
        "name": {"name", "full name", "fullname"},
        "student_id": {"student id", "student_id", "studentid", "id", "student"},
        "email": {"email", "email address", "mail"},
        "course": {"course", "program", "class", "department"},
        "role": {"role", "type"},
    }

    @staticmethod
    def _normalize_header(header: str) -> str:
        if not header:
            return ""
        return header.strip().lstrip("\ufeff").lower()

    @classmethod
    def _map_headers(cls, headers: List[str]) -> Dict[str, str]:
        mapped = {}
        for h in headers:
            normalized = cls._normalize_header(h)
            for key, aliases in cls.HEADER_ALIASES.items():
                if normalized in aliases:
                    mapped[key] = h
        return mapped

    @classmethod
    def parse_attendee_csv(cls, file_content: bytes) -> List[dict]:
        try:
            csv_text = file_content.decode("utf-8-sig", errors="ignore")
        except Exception:
            csv_text = file_content.decode("utf-8", errors="ignore")

        reader = csv.DictReader(io.StringIO(csv_text))
        if not reader.fieldnames:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CSV file is empty or has no headers"
            )

        header_map = cls._map_headers(reader.fieldnames)
        required = {"name", "student_id"}
        if not required.issubset(header_map.keys()):
            missing = required - set(header_map.keys())
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required columns: {', '.join(sorted(missing))}"
            )

        rows = []
        for row in reader:
            if not row:
                continue
            name = (row.get(header_map["name"]) or "").strip()
            student_id = (row.get(header_map["student_id"]) or "").strip()
            email = (row.get(header_map.get("email", "")) or "").strip() if header_map.get("email") else ""
            course = (row.get(header_map.get("course", "")) or "").strip() if header_map.get("course") else ""
            role = (row.get(header_map.get("role", "")) or "").strip().lower() if header_map.get("role") else None

            if not name or not student_id:
                continue

            rows.append({
                "name": name,
                "student_id": student_id,
                "email": email,
                "course": course,
                "role": role
            })

        if not rows:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid rows found in CSV"
            )

        return rows

    @staticmethod
    async def check_duplicates(attendees: List[dict], club_id: str, template_id: str) -> Tuple[List[dict], List[dict]]:
        student_ids = list({a["student_id"] for a in attendees if a.get("student_id")})
        if not student_ids:
            return [], attendees

        existing = await database.fetch_all(
            """
            SELECT student_id FROM attendees
            WHERE club_id = :club_id
              AND (:template_id IS NULL OR template_id = :template_id)
              AND student_id = ANY(:student_ids)
            """,
            {"club_id": club_id, "template_id": template_id, "student_ids": student_ids}
        )
        existing_ids = {row["student_id"] for row in existing}

        new_records = []
        duplicates = []
        seen = set()
        for attendee in attendees:
            sid = attendee.get("student_id")
            if not sid:
                continue
            if sid in seen or sid in existing_ids:
                duplicates.append(attendee)
                continue
            seen.add(sid)
            new_records.append(attendee)

        return new_records, duplicates

    @staticmethod
    async def check_duplicates_simple(attendees: List[dict], club_id: str) -> Tuple[List[dict], List[dict]]:
        """Check duplicates within club only (no template filter)"""
        student_ids = list({a["student_id"] for a in attendees if a.get("student_id")})
        if not student_ids:
            return [], attendees

        # Build IN clause with parameters
        placeholders = ", ".join([f":sid_{i}" for i in range(len(student_ids))])
        params = {"club_id": club_id}
        for i, sid in enumerate(student_ids):
            params[f"sid_{i}"] = sid

        existing = await database.fetch_all(
            f"""
            SELECT student_id FROM attendees
            WHERE club_id = :club_id
              AND student_id IN ({placeholders})
            """,
            params
        )
        existing_ids = {row["student_id"] for row in existing}

        new_records = []
        duplicates = []
        seen = set()
        for attendee in attendees:
            sid = attendee.get("student_id")
            if not sid:
                continue
            if sid in seen or sid in existing_ids:
                duplicates.append(attendee)
                continue
            seen.add(sid)
            new_records.append(attendee)

        return new_records, duplicates
