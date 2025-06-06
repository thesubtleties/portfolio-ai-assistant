from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import Visitor
import redis.asyncio as redis
import json
import logging
import uuid


logger = logging.getLogger(__name__)


class VisitorService:
    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        self.db = db
        self.redis = redis_client

    async def get_or_create(
        self,
        fingerprint_id: str,
        user_agent_raw: Optional[str] = None,
        ip_address_hash: Optional[str] = None,
    ) -> Tuple[Visitor, bool]:
        """Get or create a visitor record.

        Args:
            db (AsyncSession): Database session for executing queries
            fingerprint_id (str): Unique browser fingerprint ID
            user_agent_raw (Optional[str], optional): Raw user agent string. Defaults to None.
            ip_address_hash (Optional[str], optional): Hashed IP address. Defaults to None.

        Returns:
            Tuple[Visitor, bool]: The visitor record and a boolean indicating if it was created (True) or fetched (False).
        """

        # Try to get visitor from Redis cache first
        cache_key = f"visitor:{fingerprint_id}"
        try:
            cached_visitor = await self.redis.hgetall(cache_key)
            if cached_visitor and cached_visitor.get("visitor_id"):
                # Update last seen in cache
                await self.redis.hset(
                    cache_key,
                    "last_seen_at",
                    datetime.now(timezone.utc).isoformat(),
                )
                await self.redis.expire(
                    cache_key, 7 * 24 * 3600
                )  # Reset 7-day TTL

                # Get visitor from DB to ensure we have latest data
                stmt = select(Visitor).where(
                    Visitor.id == uuid.UUID(cached_visitor["visitor_id"])
                )
                result = await self.db.execute(stmt)
                visitor = result.scalar_one_or_none()

                if visitor:
                    visitor.last_seen_at = datetime.now(timezone.utc)
                    await self.db.commit()
                    logger.info(f"Cache HIT for fingerprint {fingerprint_id}")
                    return visitor, False
        except Exception as e:
            logger.error(f"Cache FAIL for fingerprint {fingerprint_id}: {e}")

        # Cache miss or error, fall back to DB
        logger.info(f"Falling back to DB for fingerprint {fingerprint_id}")

        stmt = select(Visitor).where(Visitor.fingerprint_id == fingerprint_id)
        result = await self.db.execute(stmt)
        visitor = result.scalar_one_or_none()

        if visitor:
            # Update last seen
            visitor.last_seen_at = datetime.now(timezone.utc)
            await self.db.commit()

            # Cache the visitor
            await self._cache_visitor(visitor)
            return visitor, False

        now = datetime.now(timezone.utc)
        visitor = Visitor(
            fingerprint_id=fingerprint_id,
            first_seen_at=now,
            last_seen_at=now,
            user_agent_raw=user_agent_raw,
            ip_address_hash=ip_address_hash,
        )
        try:
            self.db.add(visitor)
            await self.db.commit()
            await self.db.refresh(visitor)

            # Cache the new visitor
            await self._cache_visitor(visitor)
            return visitor, True
        except IntegrityError:
            await self.db.rollback()
            stmt = select(Visitor).where(
                Visitor.fingerprint_id == fingerprint_id
            )
            result = await db.execute(stmt)
            visitor = result.scalar_one_or_none()
            if visitor:
                # Cache the existing visitor found after race condition
                await self._cache_visitor(visitor)
                return visitor, False
            else:
                raise RuntimeError(
                    "Failed to create visitor and could not find existing one."
                )

    async def _cache_visitor(self, visitor: Visitor) -> None:
        """Cache visitor data in Redis with 7-day TTL"""
        cache_key = f"visitor:{visitor.fingerprint_id}"

        visitor_data = {
            "visitor_id": str(visitor.id),
            "fingerprint_id": visitor.fingerprint_id,
            "first_seen_at": visitor.first_seen_at.isoformat(),
            "last_seen_at": visitor.last_seen_at.isoformat(),
            "user_agent_raw": visitor.user_agent_raw or "",
            "ip_address_hash": visitor.ip_address_hash or "",
            "profile_data": (
                json.dumps(visitor.profile_data)
                if visitor.profile_data
                else "{}"
            ),
            "notes_by_agent": visitor.notes_by_agent or "",
        }

        await self.redis.hset(cache_key, mapping=visitor_data)
        await self.redis.expire(cache_key, 7 * 24 * 3600)  # 7 days in seconds

    async def update_visitor_data(
        self,
        visitor: Visitor,
        profile_data: dict,
    ) -> None:
        """Update visitor profile data extracted from chat messages.
        Args:
            visitor (Visitor): The visitor record to update
            profile_data (dict): Profile data to update
            db (AsyncSession): Database session for executing queries
            redis_client (redis.Redis): Redis client for updating cache
        """
        if visitor.profile_data:
            visitor.profile_data.update(profile_data)
        else:
            visitor.profile_data = profile_data
        await db.commit()

        # Update cache
        await VisitorService._cache_visitor(redis_client, visitor)

    async def update_agent_notes(
        self,
        visitor: Visitor,
        notes: str,
    ) -> None:
        """Update notes by agent for a visitor.

        Args:
            visitor (Visitor): The visitor record to update
            notes (str): Notes to update
            db (AsyncSession): Database session for executing queries
            redis_client (redis.Redis): Redis client for updating cache
        """
        if visitor.notes_by_agent:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            visitor.notes_by_agent += f"\n\n[{timestamp}] {notes}"
        else:
            visitor.notes_by_agent = notes
        await db.commit()

        # Update cache
        await VisitorService._cache_visitor(redis_client, visitor)
