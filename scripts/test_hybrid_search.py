#!/usr/bin/env python3
"""
Hybrid Search Quality Tester

This script tests adaptive search strategies using both semantic and pure content embeddings.
"""

import asyncio
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from openai import AsyncOpenAI

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.database import PortfolioContent


class HybridSearchTester:
    """Test adaptive search strategies with dual embedding types."""

    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def test_adaptive_search(self):
        """Test different search strategies based on query analysis."""
        print("🔍 Testing Adaptive Hybrid Search Strategies")
        print("=" * 60)
        print()

        test_scenarios = [
            {
                "query": "What FastAPI architecture patterns does Steven use?",
                "expected_strategy": "semantic",
                "reason": "Technical framework query - needs contextual understanding"
            },
            {
                "query": "Tell me about all of Steven's projects",
                "expected_strategy": "hybrid",
                "reason": "Broad overview - needs diversity and coverage"
            },
            {
                "query": "What databases does Steven work with?",
                "expected_strategy": "pure_content", 
                "reason": "Specific technology search - pure content often better"
            },
            {
                "query": "Steven's React component architecture approach",
                "expected_strategy": "semantic",
                "reason": "Complex technical concept - benefits from context"
            },
            {
                "query": "Show me code examples from Steven's projects",
                "expected_strategy": "pure_content",
                "reason": "Content-specific search - looking for actual code"
            }
        ]

        async with AsyncSessionLocal() as session:
            for i, scenario in enumerate(test_scenarios, 1):
                print(f"🧪 Test {i}: Adaptive Search Strategy")
                print(f"📝 Query: '{scenario['query']}'")
                print(f"🎯 Expected Strategy: {scenario['expected_strategy']}")
                print(f"💡 Reason: {scenario['reason']}")
                print()

                # Classify query and choose strategy
                query_type = self._classify_query(scenario['query'])
                chosen_strategy = self._choose_search_strategy(query_type)
                
                print(f"🔍 Query Type: {query_type}")
                print(f"⚡ Chosen Strategy: {chosen_strategy}")
                print()

                # Execute different search strategies
                if chosen_strategy == "semantic":
                    results = await self._semantic_search(session, scenario['query'], limit=5)
                    print("🧠 Using SEMANTIC search (contextual embeddings)")
                elif chosen_strategy == "pure_content":
                    results = await self._pure_content_search(session, scenario['query'], limit=5)
                    print("📄 Using PURE CONTENT search (content-only embeddings)")
                else:  # hybrid
                    results = await self._hybrid_search(session, scenario['query'], limit=5)
                    print("🔄 Using HYBRID search (combining both methods)")

                print()
                self._display_results(results)
                print("-" * 60)
                print()

    async def _semantic_search(self, session: AsyncSession, query: str, limit: int = 5) -> List[PortfolioContent]:
        """Search using semantic embeddings only."""
        embedding = await self._get_embedding(query)
        
        stmt = (
            select(PortfolioContent)
            .where(PortfolioContent.content_metadata['embedding_type'].astext == 'semantic')
            .order_by(PortfolioContent.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        
        result = await session.execute(stmt)
        return result.scalars().all()

    async def _pure_content_search(self, session: AsyncSession, query: str, limit: int = 5) -> List[PortfolioContent]:
        """Search using pure content embeddings only."""
        embedding = await self._get_embedding(query)
        
        stmt = (
            select(PortfolioContent)
            .where(PortfolioContent.content_metadata['embedding_type'].astext == 'pure_content')
            .order_by(PortfolioContent.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        
        result = await session.execute(stmt)
        return result.scalars().all()

    async def _hybrid_search(self, session: AsyncSession, query: str, limit: int = 5) -> List[PortfolioContent]:
        """Hybrid search combining both embedding types with intelligent merging."""
        embedding = await self._get_embedding(query)
        
        # Get top results from both methods
        semantic_stmt = (
            select(PortfolioContent)
            .where(PortfolioContent.content_metadata['embedding_type'].astext == 'semantic')
            .order_by(PortfolioContent.embedding.cosine_distance(embedding))
            .limit(limit * 2)
        )
        
        pure_stmt = (
            select(PortfolioContent)
            .where(PortfolioContent.content_metadata['embedding_type'].astext == 'pure_content')
            .order_by(PortfolioContent.embedding.cosine_distance(embedding))
            .limit(limit * 2)
        )
        
        semantic_results = (await session.execute(semantic_stmt)).scalars().all()
        pure_results = (await session.execute(pure_stmt)).scalars().all()
        
        # Merge and deduplicate by content similarity
        merged_results = self._merge_and_deduplicate(semantic_results, pure_results, limit)
        
        return merged_results

    def _merge_and_deduplicate(self, semantic_results: List[PortfolioContent], 
                              pure_results: List[PortfolioContent], limit: int) -> List[PortfolioContent]:
        """Intelligently merge results from both methods."""
        merged = []
        seen_content = set()
        
        # Interleave results to get diversity
        max_len = max(len(semantic_results), len(pure_results))
        
        for i in range(max_len):
            # Add semantic result if available and not duplicate
            if i < len(semantic_results):
                semantic_result = semantic_results[i]
                content_hash = hash(semantic_result.content_chunk[:100])  # Hash first 100 chars
                if content_hash not in seen_content:
                    merged.append(semantic_result)
                    seen_content.add(content_hash)
            
            # Add pure content result if available and not duplicate
            if i < len(pure_results) and len(merged) < limit:
                pure_result = pure_results[i]
                content_hash = hash(pure_result.content_chunk[:100])
                if content_hash not in seen_content:
                    merged.append(pure_result)
                    seen_content.add(content_hash)
            
            if len(merged) >= limit:
                break
        
        return merged[:limit]

    def _classify_query(self, query: str) -> str:
        """Use the real service classification with weighted scoring."""
        # Import here to avoid circular imports
        from app.services.portfolio_agent_service import PortfolioAgentService
        
        # Create a temporary service instance just for classification
        service = PortfolioAgentService.__new__(PortfolioAgentService)
        return service._classify_query(query)

    def _choose_search_strategy(self, query_type: str) -> str:
        """Use the real service search strategy."""
        # Import here to avoid circular imports
        from app.services.portfolio_agent_service import PortfolioAgentService
        
        # Create a temporary service instance just for strategy selection
        service = PortfolioAgentService.__new__(PortfolioAgentService)
        return service._choose_search_strategy(query_type)

    def _display_results(self, results: List[PortfolioContent]):
        """Display search results with metadata analysis."""
        print(f"📊 Found {len(results)} results:")
        print()
        
        embedding_types = {}
        section_types = {}
        
        for i, result in enumerate(results, 1):
            metadata = result.content_metadata or {}
            embedding_type = metadata.get('embedding_type', 'unknown')
            section_type = metadata.get('section_type', 'general')
            section_title = metadata.get('section_title', 'Unknown')
            word_count = metadata.get('word_count', 0)
            
            # Track distribution
            embedding_types[embedding_type] = embedding_types.get(embedding_type, 0) + 1
            section_types[section_type] = section_types.get(section_type, 0) + 1
            
            print(f"   {i}. 📄 {result.title}")
            print(f"      🧠 Embedding: {embedding_type}")
            print(f"      🏷️  Section: {section_title}")
            print(f"      🔖 Type: {section_type} | Words: {word_count}")
            print(f"      📝 Preview: {result.content_chunk[:100]}...")
            print()
        
        # Show distribution analysis
        print("📈 Result Distribution:")
        print(f"   🧠 Embedding Types: {dict(embedding_types)}")
        print(f"   🏷️  Section Types: {dict(section_types)}")
        print()

    async def analyze_dual_embeddings(self):
        """Analyze the distribution and coverage of dual embeddings."""
        print("📈 Dual Embedding Analysis")
        print("=" * 40)
        print()

        async with AsyncSessionLocal() as session:
            # Get all chunks
            stmt = select(PortfolioContent)
            result = await session.execute(stmt)
            chunks = result.scalars().all()

            # Analyze by embedding type
            semantic_chunks = [c for c in chunks if c.content_metadata and c.content_metadata.get('embedding_type') == 'semantic']
            pure_chunks = [c for c in chunks if c.content_metadata and c.content_metadata.get('embedding_type') == 'pure_content']

            print(f"📊 Total chunks: {len(chunks)}")
            print(f"🧠 Semantic embeddings: {len(semantic_chunks)}")
            print(f"📄 Pure content embeddings: {len(pure_chunks)}")
            print(f"🔄 Hybrid coverage: {len(semantic_chunks) == len(pure_chunks)}")
            print()

            if len(semantic_chunks) == len(pure_chunks):
                print("✅ Perfect hybrid coverage - each chunk has both embedding types")
            else:
                print("⚠️  Uneven coverage - some chunks may be missing embedding types")
            
            print()

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate OpenAI embedding for text."""
        response = await self.openai_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=text.strip(),
            dimensions=1536,
        )
        return response.data[0].embedding


async def main():
    """Main entry point."""
    print("🤖 Portfolio AI Assistant - Hybrid Search Testing")
    print("🧠 Adaptive Search Strategy with Dual Embeddings")
    print()

    if not settings.openai_api_key or not settings.database_url:
        print("❌ Required environment variables missing")
        return

    tester = HybridSearchTester()
    
    # Analyze dual embedding coverage
    await tester.analyze_dual_embeddings()
    
    # Test adaptive search strategies
    await tester.test_adaptive_search()


if __name__ == "__main__":
    asyncio.run(main())