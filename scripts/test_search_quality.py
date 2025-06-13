#!/usr/bin/env python3
"""
Test script to demonstrate improved search quality with semantic chunking.

This script directly queries the database to show how the enhanced chunking
provides better search results for different types of queries.
"""

import asyncio
import sys
from pathlib import Path
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from openai import AsyncOpenAI

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.database import PortfolioContent


class SearchQualityTester:
    """Test semantic search quality with enhanced chunking."""

    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def test_search_scenarios(self):
        """Test various search scenarios to demonstrate improvements."""
        print("🔍 Testing Enhanced Semantic Search Quality")
        print("=" * 60)
        print()

        test_queries = [
            {
                "query": "What FastAPI projects has Steven built?",
                "description": "Technical framework search",
                "expected": "Should find FastAPI-specific technical sections"
            },
            {
                "query": "Tell me about all of Steven's projects",
                "description": "Comprehensive project overview",
                "expected": "Should find project overview sections without hallucination"
            },
            {
                "query": "What databases and data storage does Steven use?",
                "description": "Technical infrastructure search",
                "expected": "Should find database and technical architecture sections"
            },
            {
                "query": "What is Steven's background and personal interests?",
                "description": "Personal information search",
                "expected": "Should find personal and background sections"
            },
            {
                "query": "Show me Steven's React and frontend experience",
                "description": "Specific technology search",
                "expected": "Should find frontend-specific technical sections"
            }
        ]

        async with AsyncSessionLocal() as session:
            for i, test in enumerate(test_queries, 1):
                print(f"🧪 Test {i}: {test['description']}")
                print(f"📝 Query: '{test['query']}'")
                print(f"🎯 Expected: {test['expected']}")
                print()

                # Get search results
                results = await self._search_content(session, test['query'], limit=5)
                
                print(f"📊 Found {len(results)} relevant chunks:")
                print()

                for j, result in enumerate(results, 1):
                    metadata = result.content_metadata or {}
                    section_title = metadata.get('section_title', 'Unknown')
                    section_type = metadata.get('section_type', 'general')
                    word_count = metadata.get('word_count', 0)
                    chunk_method = metadata.get('chunk_method', 'unknown')
                    
                    print(f"   {j}. 📄 {result.title}")
                    print(f"      🏷️  Section: {section_title}")
                    print(f"      🔖 Type: {section_type} | Words: {word_count} | Method: {chunk_method}")
                    print(f"      📝 Preview: {result.content_chunk[:100]}...")
                    print()

                print("-" * 60)
                print()

    async def _search_content(self, session: AsyncSession, query: str, limit: int = 5) -> List[PortfolioContent]:
        """Search content using vector similarity."""
        # Generate embedding for query
        embedding = await self._get_embedding(query)
        
        # Search using cosine distance
        stmt = (
            select(PortfolioContent)
            .order_by(PortfolioContent.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        
        result = await session.execute(stmt)
        return result.scalars().all()

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate OpenAI embedding for text."""
        response = await self.openai_client.embeddings.create(
            model=settings.openai_embedding_model,
            input=text.strip(),
            dimensions=1536,
        )
        return response.data[0].embedding

    async def analyze_chunk_distribution(self):
        """Analyze the distribution of chunks by type and section."""
        print("📈 Chunk Distribution Analysis")
        print("=" * 40)
        print()

        async with AsyncSessionLocal() as session:
            # Get all chunks
            stmt = select(PortfolioContent)
            result = await session.execute(stmt)
            chunks = result.scalars().all()

            # Analyze by section type
            type_counts = {}
            word_counts = []
            total_chunks = len(chunks)

            for chunk in chunks:
                metadata = chunk.content_metadata or {}
                section_type = metadata.get('section_type', 'general')
                word_count = metadata.get('word_count', 0)
                
                type_counts[section_type] = type_counts.get(section_type, 0) + 1
                word_counts.append(word_count)

            print(f"📊 Total chunks: {total_chunks}")
            print(f"📏 Average words per chunk: {sum(word_counts) / len(word_counts):.1f}")
            print(f"📐 Word count range: {min(word_counts)} - {max(word_counts)}")
            print()

            print("🏷️  Section type distribution:")
            for section_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_chunks) * 100
                print(f"   {section_type:12} {count:3d} chunks ({percentage:5.1f}%)")
            print()

            # Show semantic_v2 adoption
            semantic_v2_count = sum(1 for chunk in chunks 
                                  if chunk.content_metadata and 
                                  chunk.content_metadata.get('chunk_method') == 'semantic_v2')
            
            print(f"🧠 Semantic v2 chunks: {semantic_v2_count}/{total_chunks} ({(semantic_v2_count/total_chunks)*100:.1f}%)")
            print()


async def main():
    """Main entry point."""
    print("🤖 Portfolio AI Assistant - Search Quality Testing")
    print("🧠 Testing Enhanced Semantic Chunking Results")
    print()

    # Verify environment
    if not settings.openai_api_key:
        print("❌ OPENAI_API_KEY environment variable is required")
        return

    if not settings.database_url:
        print("❌ Database environment variables are required")
        return

    tester = SearchQualityTester()
    
    # Run chunk distribution analysis
    await tester.analyze_chunk_distribution()
    
    # Run search quality tests
    await tester.test_search_scenarios()


if __name__ == "__main__":
    asyncio.run(main())