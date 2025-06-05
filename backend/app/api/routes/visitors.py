"""Visitor identification and management endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.redis import get_redis
from app.services.visitor_service import VisitorService
import hashlib
import redis.asyncio as redis

router = APIRouter(prefix="/api/visitors", tags=["visitors"])


class VisitorIdentifyRequest(BaseModel):
    """Request model for visitor identification."""

    fingerprint_id: str = Field(
        ...,
        description="Unique browser fingerprint identifier",
        examples=["fp_abc123def456ghi789"]
    )
    user_agent: Optional[str] = Field(
        None,
        description="Browser user agent string",
        examples=["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"]
    )
    ip_address: Optional[str] = Field(
        None,
        description="Client IP address (will be hashed for privacy)",
        examples=["192.168.1.100"]
    )
    profile_data: Optional[dict] = Field(
        None,
        description="Additional visitor profile information",
        examples=[{"timezone": "America/New_York", "screen_resolution": "1920x1080"}]
    )


class VisitorIdentifyResponse(BaseModel):
    """Response model for visitor identification."""

    visitor_id: str = Field(
        ...,
        description="Unique visitor identifier",
        examples=["550e8400-e29b-41d4-a716-446655440000"]
    )
    is_new_visitor: bool = Field(
        ...,
        description="Whether this is a new visitor or returning",
        examples=[False]
    )
    first_seen_at: str = Field(
        ...,
        description="When the visitor was first seen (ISO datetime)",
        examples=["2024-01-15T10:00:00Z"]
    )
    last_seen_at: str = Field(
        ...,
        description="When the visitor was last seen (ISO datetime)",
        examples=["2024-01-15T10:30:00Z"]
    )


@router.post("/identify", response_model=VisitorIdentifyResponse)
async def identify_visitor(
    request: VisitorIdentifyRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
) -> VisitorIdentifyResponse:
    """
    Identify or create a visitor based on fingerprint.

    This endpoint:
    1. Checks if visitor exists by fingerprint_id
    2. Creates new visitor if not found
    3. Updates last_seen_at timestamp
    4. Returns visitor information for session management
    """
    # Create service instance with dependencies
    visitor_service = VisitorService(db, redis_client)

    # Hash IP address if provided for privacy
    ip_hash = None
    if request.ip_address:
        ip_hash = hashlib.sha256(request.ip_address.encode()).hexdigest()

    try:
        # Use get_or_create which handles everything
        visitor, is_new = await visitor_service.get_or_create(
            fingerprint_id=request.fingerprint_id,
            user_agent_raw=request.user_agent,
            ip_address_hash=ip_hash,
        )

        # Update profile data if provided and visitor exists
        if request.profile_data and not is_new:
            await visitor_service.update_visitor_data(
                visitor=visitor, profile_data=request.profile_data
            )

        return VisitorIdentifyResponse(
            visitor_id=str(visitor.id),
            is_new_visitor=is_new,
            first_seen_at=visitor.first_seen_at.isoformat(),
            last_seen_at=visitor.last_seen_at.isoformat(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to identify visitor: {str(e)}"
        )
