"""
Activity Log Schemas
Request and response models for activity logging
"""

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional, Any, List


class ActivityLogEntry(BaseModel):
    """Single activity log entry"""
    id: UUID
    club_id: Optional[UUID]
    admin_id: Optional[UUID]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[UUID]
    details: Optional[dict] = None
    ip_address: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


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
