"""
Storage Service
Supabase Storage integration for templates and CSV imports
"""

from typing import Optional
import httpx
from fastapi import HTTPException, status
from app.config import settings


class StorageService:
    """Supabase Storage helper"""

    @staticmethod
    def _ensure_config():
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Supabase Storage is not configured"
            )

    @staticmethod
    async def upload_bytes(path: str, content: bytes, content_type: str) -> str:
        StorageService._ensure_config()

        base = settings.SUPABASE_URL.rstrip("/")
        bucket = settings.STORAGE_BUCKET
        url = f"{base}/storage/v1/object/{bucket}/{path}"

        headers = {
            "Authorization": f"Bearer {settings.SUPABASE_KEY}",
            "apikey": settings.SUPABASE_KEY,
            "Content-Type": content_type or "application/octet-stream",
            "x-upsert": "true"
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, content=content)

        if resp.status_code not in (200, 201):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Storage upload failed: {resp.text}"
            )

        return f"{base}/storage/v1/object/public/{bucket}/{path}"

    @staticmethod
    async def fetch_text(url: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Stored file not found")
        return resp.text
