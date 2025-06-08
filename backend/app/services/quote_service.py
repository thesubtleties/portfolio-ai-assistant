"""Quote service for conversation starters."""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
import redis.asyncio as redis

from app.models.database import ConversationQuote


class QuoteService:
    """Service for managing conversation starter quotes."""

    def __init__(self, db: AsyncSession, redis_client: redis.Redis):
        """Initialize quote service with database and Redis."""
        self.db = db
        self.redis = redis_client

    async def get_random_quote(self, category: str = "noir") -> Optional[ConversationQuote]:
        """
        Get a random active quote from database.
        
        Args:
            category: Quote category to filter by
            
        Returns:
            ConversationQuote or None if no quotes available
        """
        try:
            # Query for active quotes in category, ordered randomly
            stmt = (
                select(ConversationQuote)
                .where(ConversationQuote.is_active == True)
                .where(ConversationQuote.category == category)
                .order_by(func.random())
                .limit(1)
            )
            
            result = await self.db.execute(stmt)
            quote = result.scalar_one_or_none()
            
            if quote:
                # Increment usage count
                await self._increment_usage(quote.id)
                
            return quote
            
        except Exception as e:
            print(f"Error getting random quote: {e}")
            return None

    async def get_all_quotes(self, category: Optional[str] = None, active_only: bool = True) -> List[ConversationQuote]:
        """
        Get all quotes, optionally filtered by category and active status.
        
        Args:
            category: Optional category filter
            active_only: Whether to only return active quotes
            
        Returns:
            List of ConversationQuote objects
        """
        stmt = select(ConversationQuote)
        
        if active_only:
            stmt = stmt.where(ConversationQuote.is_active == True)
            
        if category:
            stmt = stmt.where(ConversationQuote.category == category)
            
        stmt = stmt.order_by(ConversationQuote.created_at.desc())
        
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_quote_by_id(self, quote_id: str) -> Optional[ConversationQuote]:
        """Get a specific quote by ID."""
        stmt = select(ConversationQuote).where(ConversationQuote.id == quote_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def add_quote(self, quote_text: str, category: str = "noir") -> ConversationQuote:
        """
        Add a new quote to the database.
        
        Args:
            quote_text: The quote text
            category: Quote category
            
        Returns:
            Created ConversationQuote object
        """
        quote = ConversationQuote(
            quote_text=quote_text,
            category=category
        )
        
        self.db.add(quote)
        await self.db.flush()  # Get the ID
        
        return quote

    async def _increment_usage(self, quote_id: str) -> None:
        """Increment the usage count for a quote."""
        try:
            stmt = (
                update(ConversationQuote)
                .where(ConversationQuote.id == quote_id)
                .values(usage_count=ConversationQuote.usage_count + 1)
            )
            await self.db.execute(stmt)
            
        except Exception as e:
            print(f"Error incrementing quote usage: {e}")

    async def get_quote_stats(self, category: Optional[str] = None) -> dict:
        """Get usage statistics for quotes."""
        stmt = select(
            ConversationQuote.category,
            func.count(ConversationQuote.id).label('total_quotes'),
            func.sum(ConversationQuote.usage_count).label('total_usage'),
            func.avg(ConversationQuote.usage_count).label('avg_usage')
        ).group_by(ConversationQuote.category)
        
        if category:
            stmt = stmt.where(ConversationQuote.category == category)
            
        result = await self.db.execute(stmt)
        return result.fetchall()