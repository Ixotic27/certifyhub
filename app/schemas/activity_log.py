"""
Activity Log Schemas
Request and response models for activity logging
"""

from pydantic import BaseModel, field_validator
from uuid import UUID
from datetime import datetime
from typing import Optional, Any, List
import json


class ActivityLogEntry(BaseModel):
    """Single activity log entry"""
    model_config = {"from_attributes": True}

    id: UUID
    club_id: Optional[UUID] = None
    admin_id: Optional[UUID] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    created_at: datetime

    @field_validator("details", mode="before")
    @classmethod
    def parse_details(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return {"raw": v}
        return v


class ActivityLogResponse(BaseModel):
    """Response with paginated activity logs"""
    logs: List[ActivityLogEntry]
    total: int
    limit: int
    offset: int
    has_more: bool


class ActionStatistic(BaseModel):
    """Single action statistic"""
    action: str
    count: int
    unique_admins: int
    last_activity: datetime


class ActivityStatsResponse(BaseModel):
    """Activity statistics response"""
    period_days: int
    total_actions: int
    actions_breakdown: List[ActionStatistic]
