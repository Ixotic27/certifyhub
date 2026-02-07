"""
Activity Logging Service
Handles activity log operations and queries
"""

from app.database import database
from uuid import UUID
from datetime import datetime, timedelta
from typing import List, Optional


class ActivityLogService:
    """Service for activity logging operations"""
    
    @staticmethod
    async def log_activity(
        club_id: Optional[UUID],
        admin_id: Optional[UUID],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[UUID] = None,
        details: Optional[dict] = None,
        ip_address: Optional[str] = None
    ) -> dict:
        """
        Log an activity
        
        Args:
            club_id: Club ID (for club-level activities)
            admin_id: Admin ID who performed the action
            action: Action type (e.g., 'upload_template', 'import_attendees')
            resource_type: Type of resource affected (e.g., 'template', 'attendee')
            resource_id: ID of the resource
            details: Additional JSON details
            ip_address: IP address of the request
            
        Returns:
            Created activity log entry
        """
        import uuid
        import json
        log_id = uuid.uuid4()
        
        query = """
        INSERT INTO activity_logs (id, club_id, admin_id, action, resource_type, resource_id, details, ip_address)
        VALUES (:id, :club_id, :admin_id, :action, :resource_type, :resource_id, :details, :ip_address)
        RETURNING id, club_id, admin_id, action, resource_type, resource_id, details, ip_address, created_at
        """
        
        result = await database.fetch_one(
            query,
            {
                "id": log_id,
                "club_id": club_id,
                "admin_id": admin_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "details": json.dumps(details) if details else None,
                "ip_address": ip_address
            }
        )
        
        return dict(result) if result else None
    
    @staticmethod
    async def get_club_activity_logs(
        club_id: UUID,
        limit: int = 50,
        offset: int = 0,
        action_filter: Optional[str] = None,
        days: int = 30
    ) -> tuple[List[dict], int]:
        """
        Get activity logs for a club
        
        Args:
            club_id: Club ID
            limit: Number of records to return
            offset: Offset for pagination
            action_filter: Filter by action type
            days: Only return logs from last N days
            
        Returns:
            Tuple of (activity logs list, total count)
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        # Build query
        where_clause = "club_id = :club_id AND created_at >= :since"
        params = {"club_id": club_id, "since": since}
        
        if action_filter:
            where_clause += " AND action = :action"
            params["action"] = action_filter
        
        # Get total count
        count_query = f"SELECT COUNT(*) as count FROM activity_logs WHERE {where_clause}"
        count_result = await database.fetch_one(count_query, params)
        total = count_result["count"] if count_result else 0
        
        # Get logs
        query = f"""
        SELECT 
            id, club_id, admin_id, action, resource_type, resource_id, 
            details, ip_address, created_at
        FROM activity_logs
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """
        
        params["limit"] = limit
        params["offset"] = offset
        
        logs = await database.fetch_all(query, params)
        
        return [dict(log) for log in logs], total
    
    @staticmethod
    async def get_activity_stats(
        club_id: UUID,
        days: int = 7
    ) -> dict:
        """
        Get activity statistics for a club
        
        Args:
            club_id: Club ID
            days: Number of days to analyze
            
        Returns:
            Activity statistics
        """
        since = datetime.utcnow() - timedelta(days=days)
        
        query = """
        SELECT 
            action,
            COUNT(*) as count,
            COUNT(DISTINCT admin_id) as unique_admins,
            MAX(created_at) as last_activity
        FROM activity_logs
        WHERE club_id = :club_id AND created_at >= :since
        GROUP BY action
        ORDER BY count DESC
        """
        
        results = await database.fetch_all(
            query,
            {"club_id": club_id, "since": since}
        )
        
        return {
            "period_days": days,
            "total_actions": sum(r["count"] for r in results),
            "actions_breakdown": [
                {
                    "action": r["action"],
                    "count": r["count"],
                    "unique_admins": r["unique_admins"],
                    "last_activity": r["last_activity"]
                }
                for r in results
            ]
        }
    
    @staticmethod
    async def get_admin_activity_logs(
        admin_id: UUID,
        limit: int = 50,
        offset: int = 0
    ) -> tuple[List[dict], int]:
        """
        Get activity logs for a specific admin
        
        Args:
            admin_id: Admin ID
            limit: Number of records to return
            offset: Offset for pagination
            
        Returns:
            Tuple of (activity logs list, total count)
        """
        # Get total count
        count_query = "SELECT COUNT(*) as count FROM activity_logs WHERE admin_id = :admin_id"
        count_result = await database.fetch_one(count_query, {"admin_id": admin_id})
        total = count_result["count"] if count_result else 0
        
        # Get logs
        query = """
        SELECT 
            id, club_id, admin_id, action, resource_type, resource_id, 
            details, ip_address, created_at
        FROM activity_logs
        WHERE admin_id = :admin_id
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
        """
        
        logs = await database.fetch_all(
            query,
            {"admin_id": admin_id, "limit": limit, "offset": offset}
        )
        
        return [dict(log) for log in logs], total
