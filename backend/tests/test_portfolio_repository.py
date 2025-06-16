"""Tests for PortfolioRepository."""

import pytest
from unittest.mock import AsyncMock, Mock
from app.repositories.portfolio_repository import PortfolioRepository


class TestPortfolioRepository:
    """Test cases for PortfolioRepository."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock database session
        self.db_mock = AsyncMock()
        self.portfolio_repo = PortfolioRepository(self.db_mock)
    
    @pytest.mark.asyncio
    async def test_semantic_search(self):
        """Test semantic search functionality."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = ["mock_content1", "mock_content2"]
        self.db_mock.execute.return_value = mock_result
        
        # Test the search
        query_embedding = [0.1, 0.2, 0.3]
        results = await self.portfolio_repo.semantic_search(
            query_embedding=query_embedding,
            content_types=["project"],
            limit=5
        )
        
        # Verify the results
        assert results == ["mock_content1", "mock_content2"]
        
        # Verify the database was called
        self.db_mock.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_pure_content_search(self):
        """Test pure content search functionality."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = ["mock_content1"]
        self.db_mock.execute.return_value = mock_result
        
        # Test the search
        query_embedding = [0.1, 0.2, 0.3]
        results = await self.portfolio_repo.pure_content_search(
            query_embedding=query_embedding,
            limit=3
        )
        
        # Verify the results
        assert results == ["mock_content1"]
        
        # Verify the database was called
        self.db_mock.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_hybrid_search(self):
        """Test hybrid search functionality."""
        # Mock database responses for both calls
        mock_result1 = Mock()
        mock_result1.scalars.return_value.all.return_value = ["semantic1", "semantic2"]
        
        mock_result2 = Mock()
        mock_result2.scalars.return_value.all.return_value = ["pure1", "pure2"]
        
        # Set up side effect for multiple calls
        self.db_mock.execute.side_effect = [mock_result1, mock_result2]
        
        # Test the search
        query_embedding = [0.1, 0.2, 0.3]
        semantic_results, pure_results = await self.portfolio_repo.hybrid_search(
            query_embedding=query_embedding,
            limit=5
        )
        
        # Verify the results
        assert semantic_results == ["semantic1", "semantic2"]
        assert pure_results == ["pure1", "pure2"]
        
        # Verify the database was called twice (once for each search type)
        assert self.db_mock.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_get_nearby_chunks(self):
        """Test getting nearby chunks functionality."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = ["chunk1", "chunk2", "chunk3"]
        self.db_mock.execute.return_value = mock_result
        
        # Test getting nearby chunks
        results = await self.portfolio_repo.get_nearby_chunks(
            knowledge_source_id="source123",
            center_chunk_index=5,
            range_before=2,
            range_after=2,
            limit=5
        )
        
        # Verify the results
        assert results == ["chunk1", "chunk2", "chunk3"]
        
        # Verify the database was called
        self.db_mock.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_project_metadata(self):
        """Test getting project metadata."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [
            {"title": "Project 1", "tech_stack": {"frontend": ["React"]}},
            None,  # Test filtering out None values
            {"title": "Project 2", "tech_stack": {"backend": ["FastAPI"]}}
        ]
        self.db_mock.execute.return_value = mock_result
        
        # Test getting metadata
        results = await self.portfolio_repo.get_project_metadata()
        
        # Verify the results (None should be filtered out)
        assert len(results) == 2
        assert results[0]["title"] == "Project 1"
        assert results[1]["title"] == "Project 2"
        
        # Verify the database was called
        self.db_mock.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_content_by_ids_empty_list(self):
        """Test getting content by IDs with empty list."""
        # Test with empty list
        results = await self.portfolio_repo.get_content_by_ids([])
        
        # Should return empty list without calling database
        assert results == []
        self.db_mock.execute.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_content_by_ids(self):
        """Test getting content by IDs."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = ["content1", "content2"]
        self.db_mock.execute.return_value = mock_result
        
        # Test getting content by IDs
        results = await self.portfolio_repo.get_content_by_ids([1, 2, 3])
        
        # Verify the results
        assert results == ["content1", "content2"]
        
        # Verify the database was called
        self.db_mock.execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_content_by_source(self):
        """Test getting content by knowledge source."""
        # Mock database response
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = ["content1", "content2"]
        self.db_mock.execute.return_value = mock_result
        
        # Test getting content by source
        results = await self.portfolio_repo.get_content_by_source("source123")
        
        # Verify the results
        assert results == ["content1", "content2"]
        
        # Verify the database was called
        self.db_mock.execute.assert_called_once()