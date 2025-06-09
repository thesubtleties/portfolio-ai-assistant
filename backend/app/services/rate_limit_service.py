"""Rate limiting service for portfolio AI assistant."""

import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import Optional
import hashlib


class RateLimitService:
    """Service for managing rate limits by IP address with point system."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.daily_limit = 100  # Total points allowed per day
        self.on_topic_cost = 1  # Points for on-topic messages
        self.off_topic_cost = 10  # Points for off-topic messages

    def _get_ip_key(self, ip_address: str) -> str:
        """Generate Redis key for IP address (hashed for privacy)."""
        # Hash IP for privacy while maintaining uniqueness
        ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:16]
        today = datetime.now().strftime("%Y-%m-%d")
        return f"rate_limit:{ip_hash}:{today}"

    async def check_rate_limit(self, ip_address: str) -> tuple[bool, int, int]:
        """
        Check if IP is within rate limits.
        
        Returns:
            tuple: (is_allowed, current_points, remaining_points)
        """
        key = self._get_ip_key(ip_address)
        current_points = await self.redis.get(key)
        current_points = int(current_points) if current_points else 0
        
        remaining_points = max(0, self.daily_limit - current_points)
        is_allowed = current_points < self.daily_limit
        
        return is_allowed, current_points, remaining_points

    async def add_points(
        self, ip_address: str, is_off_topic: bool = False
    ) -> tuple[int, int]:
        """
        Add points for a message and return current/remaining points.
        
        Args:
            ip_address: Client IP address
            is_off_topic: Whether the message was off-topic
            
        Returns:
            tuple: (current_points, remaining_points)
        """
        key = self._get_ip_key(ip_address)
        points_to_add = self.off_topic_cost if is_off_topic else self.on_topic_cost
        
        # Add points with 24-hour expiry
        current_points = await self.redis.incrby(key, points_to_add)
        await self.redis.expire(key, 86400)  # 24 hours
        
        remaining_points = max(0, self.daily_limit - current_points)
        
        return current_points, remaining_points

    async def is_rate_limited(self, ip_address: str) -> tuple[bool, Optional[str]]:
        """
        Check if IP is rate limited and return appropriate message.
        
        Returns:
            tuple: (is_limited, message_if_limited)
        """
        # Temporarily disable rate limiting for localhost/development
        if ip_address in ['127.0.0.1', 'localhost', '::1']:
            return False, None
            
        is_allowed, current_points, remaining_points = await self.check_rate_limit(
            ip_address
        )
        
        if not is_allowed:
            message = (
                "I think we've covered a lot about Steven today! "
                "Feel free to come back tomorrow if you have more questions about his work."
            )
            return True, message
        
        return False, None

    async def get_usage_stats(self, ip_address: str) -> dict:
        """Get current usage statistics for an IP."""
        is_allowed, current_points, remaining_points = await self.check_rate_limit(
            ip_address
        )
        
        return {
            "current_points": current_points,
            "remaining_points": remaining_points,
            "daily_limit": self.daily_limit,
            "is_rate_limited": not is_allowed,
            "on_topic_cost": self.on_topic_cost,
            "off_topic_cost": self.off_topic_cost,
        }