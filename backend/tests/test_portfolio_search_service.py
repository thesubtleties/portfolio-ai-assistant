"""Tests for PortfolioSearchService."""

import pytest
from unittest.mock import AsyncMock, Mock
from app.services.search.portfolio_search_service import PortfolioSearchService


class TestPortfolioSearchService:
    """Test cases for PortfolioSearchService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Mock database session
        self.db_mock = AsyncMock()
        self.search_service = PortfolioSearchService(self.db_mock)
    
    def test_classify_search_strategy_project_specific(self):
        """Test that project names get classified and use pure_content strategy."""
        queries = [
            "tell me about atria",
            "show me the spookyspot project", 
            "what is taskflow"
        ]
        
        for query in queries:
            query_type = self.search_service.classify_search_strategy(query)
            strategy = self.search_service.choose_search_strategy(query_type)
            assert strategy == "pure_content", f"Expected pure_content for '{query}', got {strategy}"
    
    def test_classify_search_strategy_technical(self):
        """Test that technical queries get semantic search."""
        queries = [
            "what's your react architecture",
            "explain your fastapi approach",
            "database design patterns"
        ]
        
        for query in queries:
            query_type = self.search_service.classify_search_strategy(query)
            strategy = self.search_service.choose_search_strategy(query_type)
            assert strategy == "semantic", f"Expected semantic for '{query}', got {strategy}"
    
    def test_detect_content_types_projects(self):
        """Test content type detection for projects."""
        query = "show me your projects"
        content_types = self.search_service.detect_content_types(query)
        assert content_types == ["project"]
    
    def test_detect_content_types_experience(self):
        """Test content type detection for experience."""
        query = "tell me about your background and experience"
        content_types = self.search_service.detect_content_types(query)
        assert "experience" in content_types
    
    def test_needs_portfolio_search(self):
        """Test portfolio search detection."""
        # This will need settings.portfolio_search_keywords
        search_query = "tell me about your projects"
        no_search_query = "hello how are you"
        
        # Mock the settings import
        import app.core.config
        app.core.config.settings = Mock()
        app.core.config.settings.portfolio_search_keywords = ["project", "experience", "work", "built"]
        
        assert self.search_service.needs_portfolio_search(search_query) is True
        assert self.search_service.needs_portfolio_search(no_search_query) is False
    
    def test_get_search_limit(self):
        """Test search limit calculation."""
        comprehensive_query = "list all of Steven's projects"
        focused_query = "what is atria"
        
        assert self.search_service.get_search_limit(comprehensive_query) == 14
        assert self.search_service.get_search_limit(focused_query) == 5