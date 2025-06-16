"""Portfolio search tool following Atomic Agents BaseTool pattern."""

from typing import List, Optional
from pydantic import Field
from atomic_agents.lib.base.base_tool import BaseTool, BaseToolConfig
from atomic_agents.lib.base.base_io_schema import BaseIOSchema
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import PortfolioContent
from app.services.search.portfolio_search_service import PortfolioSearchService


class PortfolioSearchToolConfig(BaseToolConfig):
    """Configuration for the portfolio search tool."""
    
    max_results: int = Field(
        default=10,
        description="Maximum number of search results to return"
    )
    
    default_strategy: str = Field(
        default="hybrid",
        description="Default search strategy if classification fails"
    )


class PortfolioSearchInputSchema(BaseIOSchema):
    """
    Input schema for portfolio content search.
    """
    
    query: str = Field(
        ...,
        description="The search query to find relevant portfolio content"
    )
    
    content_types: Optional[List[str]] = Field(
        default=None,
        description="Optional filter for content types (e.g., ['project', 'experience', 'about'])"
    )
    
    limit: int = Field(
        default=5,
        description="Maximum number of results to return"
    )
    
    expand_query: bool = Field(
        default=True,
        description="Whether to expand the query with contextual terms for better results"
    )


class PortfolioSearchOutputSchema(BaseIOSchema):
    """
    Output schema for portfolio search results.
    """
    
    results: List[dict] = Field(
        ...,
        description="List of search results with content and metadata"
    )
    
    search_strategy: str = Field(
        ...,
        description="The search strategy that was used (semantic, pure_content, hybrid)"
    )
    
    query_expanded: bool = Field(
        default=False,
        description="Whether the original query was expanded"
    )
    
    expanded_query: Optional[str] = Field(
        default=None,
        description="The expanded query if query expansion was used"
    )
    
    total_results: int = Field(
        ...,
        description="Total number of results returned"
    )


class PortfolioSearchTool(BaseTool):
    """
    Tool for searching Steven's portfolio content using various strategies.
    
    This tool integrates the PortfolioSearchService functionality into
    the Atomic Agents framework, providing structured search capabilities
    with automatic strategy selection and query expansion.
    """
    
    input_schema = PortfolioSearchInputSchema
    output_schema = PortfolioSearchOutputSchema
    
    def __init__(self, db: AsyncSession, config: PortfolioSearchToolConfig = PortfolioSearchToolConfig()):
        """Initialize the portfolio search tool."""
        super().__init__(config)
        self.db = db
        self.search_service = PortfolioSearchService(db)
        self.config = config
    
    async def run(self, params: PortfolioSearchInputSchema) -> PortfolioSearchOutputSchema:
        """
        Execute portfolio content search.
        
        Args:
            params: Search parameters including query, filters, and options
            
        Returns:
            Search results with metadata about the search process
        """
        query = params.query
        expanded_query = query
        query_expanded = False
        
        # Expand query if requested
        if params.expand_query:
            expanded_query = await self.search_service.expand_query_for_better_search(query)
            query_expanded = (expanded_query != query)
        
        # Get embedding for the (possibly expanded) query
        from app.services.portfolio_agent_service import PortfolioAgentService
        # Note: This is a temporary coupling - ideally we'd inject an embedding service
        async_openai_client = None  # Would need to inject this properly
        
        # For now, use the search service's existing embedding method via the agent service
        # TODO: Extract embedding service as a separate component
        try:
            # Import here to avoid circular imports
            from openai import AsyncOpenAI
            from app.core.config import settings
            
            async_openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await async_openai_client.embeddings.create(
                model=settings.openai_embedding_model,
                input=expanded_query,
                dimensions=1536
            )
            query_embedding = response.data[0].embedding
        except Exception as e:
            print(f"⚠️ [SEARCH-TOOL] Error getting embedding: {e}")
            # Return empty results if embedding fails
            return PortfolioSearchOutputSchema(
                results=[],
                search_strategy="error",
                query_expanded=query_expanded,
                expanded_query=expanded_query if query_expanded else None,
                total_results=0
            )
        
        # Determine search limit
        search_limit = min(params.limit, self.config.max_results)
        
        # Auto-detect content types if not provided
        content_types = params.content_types
        if content_types is None:
            content_types = self.search_service.detect_content_types(query)
        
        # Perform the search
        search_results = await self.search_service.search_portfolio_content(
            query_embedding=query_embedding,
            content_types=content_types,
            limit=search_limit,
            query_text=query
        )
        
        # Determine which strategy was used
        query_type = self.search_service.classify_search_strategy(query)
        search_strategy = self.search_service.choose_search_strategy(query_type)
        
        # Convert results to dict format
        results = []
        for result in search_results:
            result_dict = {
                "title": result.title,
                "content": result.content_chunk or result.content,
                "content_type": result.content_type,
                "source_id": result.knowledge_source_id,
                "chunk_index": result.chunk_index,
                "metadata": result.content_metadata or {}
            }
            results.append(result_dict)
        
        return PortfolioSearchOutputSchema(
            results=results,
            search_strategy=search_strategy,
            query_expanded=query_expanded,
            expanded_query=expanded_query if query_expanded else None,
            total_results=len(results)
        )
    
    def get_tool_description(self) -> str:
        """Get a description of what this tool does."""
        return (
            "Search Steven's portfolio content including projects, experience, and personal information. "
            "Uses intelligent strategy selection (semantic, content-based, or hybrid) and automatic "
            "query expansion for optimal results."
        )