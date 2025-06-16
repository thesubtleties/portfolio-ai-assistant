"""Repository for PortfolioContent database operations."""

from typing import List, Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.database import PortfolioContent


class PortfolioRepository:
    """Repository for managing portfolio content database operations."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the portfolio repository.

        Args:
            db: Database session for executing queries
        """
        self.db = db

    async def search_by_embedding_type_and_content_types(
        self,
        embedding_type: str,
        query_embedding: List[float],
        content_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Sequence[PortfolioContent]:
        """
        Search portfolio content by embedding type with optional content type filtering.

        Args:
            embedding_type: Type of embedding ("semantic" or "pure_content")
            query_embedding: Vector embedding to search against
            content_types: Optional list of content types to filter by
            limit: Maximum number of results to return

        Returns:
            List of matching PortfolioContent objects ordered by similarity
        """
        query = select(PortfolioContent).where(
            PortfolioContent.content_metadata["embedding_type"].astext
            == embedding_type
        )

        if content_types:
            query = query.where(
                PortfolioContent.content_type.in_(content_types)
            )

        query = query.order_by(
            PortfolioContent.embedding.cosine_distance(query_embedding)
        ).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_nearby_chunks(
        self,
        knowledge_source_id: str,
        center_chunk_index: int,
        range_before: int = 2,
        range_after: int = 2,
        limit: int = 5,
    ) -> Sequence[PortfolioContent]:
        """
        Get chunks near a specific chunk index from the same knowledge source.

        Args:
            knowledge_source_id: ID of the knowledge source
            center_chunk_index: The center chunk index to search around
            range_before: Number of chunks to include before the center
            range_after: Number of chunks to include after the center
            limit: Maximum number of chunks to return

        Returns:
            List of nearby PortfolioContent chunks ordered by chunk_index
        """
        min_index = max(0, center_chunk_index - range_before)
        max_index = center_chunk_index + range_after

        query = (
            select(PortfolioContent)
            .where(
                PortfolioContent.knowledge_source_id == knowledge_source_id,
                PortfolioContent.chunk_index.between(min_index, max_index),
            )
            .order_by(PortfolioContent.chunk_index)
            .limit(limit)
        )

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_project_metadata(self) -> List[dict]:
        """
        Get metadata for all project content.

        Returns:
            List of content metadata dictionaries for project content
        """
        query = (
            select(PortfolioContent.content_metadata)
            .where(PortfolioContent.content_type == "project")
            .distinct()
        )

        result = await self.db.execute(query)
        metadata_list = result.scalars().all()

        # Filter out None values and return as list
        return [metadata for metadata in metadata_list if metadata is not None]

    async def semantic_search(
        self,
        query_embedding: List[float],
        content_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Sequence[PortfolioContent]:
        """
        Perform semantic embedding search.

        Args:
            query_embedding: Vector embedding to search against
            content_types: Optional list of content types to filter by
            limit: Maximum number of results to return

        Returns:
            List of matching PortfolioContent objects ordered by semantic similarity
        """
        return await self.search_by_embedding_type_and_content_types(
            embedding_type="semantic",
            query_embedding=query_embedding,
            content_types=content_types,
            limit=limit,
        )

    async def pure_content_search(
        self,
        query_embedding: List[float],
        content_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Sequence[PortfolioContent]:
        """
        Perform pure content embedding search.

        Args:
            query_embedding: Vector embedding to search against
            content_types: Optional list of content types to filter by
            limit: Maximum number of results to return

        Returns:
            List of matching PortfolioContent objects ordered by content similarity
        """
        return await self.search_by_embedding_type_and_content_types(
            embedding_type="pure_content",
            query_embedding=query_embedding,
            content_types=content_types,
            limit=limit,
        )

    async def hybrid_search(
        self,
        query_embedding: List[float],
        content_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> tuple[Sequence[PortfolioContent], Sequence[PortfolioContent]]:
        """
        Perform both semantic and pure content searches for hybrid results.

        Args:
            query_embedding: Vector embedding to search against
            content_types: Optional list of content types to filter by
            limit: Maximum number of results to return from each search

        Returns:
            Tuple of (semantic_results, pure_content_results)
        """
        # Execute both searches concurrently would be ideal, but for simplicity:
        semantic_results = await self.semantic_search(
            query_embedding=query_embedding,
            content_types=content_types,
            limit=limit * 2,  # Get more for merging
        )

        pure_results = await self.pure_content_search(
            query_embedding=query_embedding,
            content_types=content_types,
            limit=limit * 2,  # Get more for merging
        )

        return semantic_results, pure_results

    async def get_content_by_ids(
        self, content_ids: List[int]
    ) -> Sequence[PortfolioContent]:
        """
        Get portfolio content by a list of IDs.

        Args:
            content_ids: List of content IDs to retrieve

        Returns:
            List of PortfolioContent objects
        """
        if not content_ids:
            return []

        query = select(PortfolioContent).where(
            PortfolioContent.id.in_(content_ids)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_content_by_source(
        self, knowledge_source_id: str
    ) -> Sequence[PortfolioContent]:
        """
        Get all content from a specific knowledge source.

        Args:
            knowledge_source_id: ID of the knowledge source

        Returns:
            List of PortfolioContent objects from the source
        """
        query = (
            select(PortfolioContent)
            .where(PortfolioContent.knowledge_source_id == knowledge_source_id)
            .order_by(PortfolioContent.chunk_index)
        )

        result = await self.db.execute(query)
        return result.scalars().all()
