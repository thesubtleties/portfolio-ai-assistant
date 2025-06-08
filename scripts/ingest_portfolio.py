#!/usr/bin/env python3
"""
Portfolio Content Ingestion Script

This script processes markdown files from the content/ directory and stores them
in the PostgreSQL database with pgvector embeddings for semantic search.

Usage:
    python scripts/ingest_portfolio.py

Environment Variables Required:
    - POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, POSTGRES_HOST
    - OPENAI_API_KEY
"""

import asyncio
import hashlib
import sys
from pathlib import Path
from typing import Dict, List
import frontmatter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.sql import func
from openai import AsyncOpenAI

# Add the backend directory to Python path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.database import KnowledgeSource, PortfolioContent


class PortfolioIngester:
    """Handles ingestion of portfolio content into pgvector database."""

    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.content_dir = Path(__file__).parent.parent / "content"

    async def ingest_all_content(self):
        """Main entry point - process all content files."""
        print(
            f"=� Starting portfolio content ingestion from {self.content_dir}"
        )

        if not self.content_dir.exists():
            print(f"L Content directory not found: {self.content_dir}")
            print(
                "Please create the content/ directory with your portfolio files"
            )
            return

        # Find all markdown files
        md_files = list(self.content_dir.rglob("*.md"))
        if not md_files:
            print(f"�  No markdown files found in {self.content_dir}")
            return

        print(f"=� Found {len(md_files)} markdown files")

        async with AsyncSessionLocal() as session:
            processed_count = 0
            skipped_count = 0

            for md_file in md_files:
                try:
                    was_processed = await self.process_file(session, md_file)
                    if was_processed:
                        processed_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    print(f"L Error processing {md_file}: {e}")
                    continue

            await session.commit()

        print(f"\n Ingestion complete!")
        print(f"   =� Processed: {processed_count} files")
        print(f"   �  Skipped: {skipped_count} files (unchanged)")

    async def process_file(
        self, session: AsyncSession, file_path: Path
    ) -> bool:
        """
        Process a single markdown file.

        Returns:
            bool: True if file was processed, False if skipped (unchanged)
        """
        relative_path = file_path.relative_to(Path(__file__).parent.parent)

        # 1. Check if file changed (via checksum)
        content_hash = self._get_file_hash(file_path)
        source = await self._get_or_create_knowledge_source(
            session, str(relative_path), content_hash
        )

        if source.checksum == content_hash:
            print(f"�  Skipping unchanged: {relative_path}")
            return False

        print(f"=� Processing: {relative_path}")

        try:
            # 2. Parse frontmatter + content
            metadata, content = self._parse_markdown(file_path)

            # 3. Delete existing content for this source
            await self._delete_existing_content(session, source.id)

            # 4. Chunk content and create embeddings
            chunks = self._chunk_content(content)
            print(f"   =� Creating {len(chunks)} chunks")

            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = await self._get_embedding(chunk)

                # Store in database
                portfolio_content = PortfolioContent(
                    knowledge_source_id=source.id,
                    content_type=metadata.get("content_type", "general"),
                    title=metadata.get(
                        "title", file_path.stem.replace("-", " ").title()
                    ),
                    content=content,  # Full content
                    content_chunk=chunk,  # This specific chunk
                    chunk_index=i,
                    embedding=embedding,
                    content_metadata=metadata,
                )
                session.add(portfolio_content)

                print(f"    Chunk {i + 1}/{len(chunks)} embedded")

            # 5. Update source metadata
            source.checksum = content_hash
            source.last_indexed_at = func.now()

            print(f"   <� Completed: {relative_path}")
            return True

        except Exception as e:
            print(f"   L Failed to process {relative_path}: {e}")
            raise

    async def _get_or_create_knowledge_source(
        self, session: AsyncSession, source_path: str, checksum: str
    ) -> KnowledgeSource:
        """Get existing knowledge source or create new one."""
        stmt = select(KnowledgeSource).where(
            KnowledgeSource.source_name == source_path
        )
        result = await session.execute(stmt)
        source = result.scalar_one_or_none()

        if source is None:
            source = KnowledgeSource(
                source_name=source_path,
                description=f"Portfolio content from {source_path}",
                checksum=checksum,
                last_indexed_at=func.now(),
            )
            session.add(source)
            await session.flush()  # Get the ID

        return source

    async def _delete_existing_content(self, session: AsyncSession, source_id):
        """Delete all existing content for a knowledge source."""
        stmt = delete(PortfolioContent).where(
            PortfolioContent.knowledge_source_id == source_id
        )
        await session.execute(stmt)

    def _parse_markdown(self, file_path: Path) -> tuple[Dict, str]:
        """Parse markdown file with frontmatter."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
                return dict(post.metadata), post.content
        except Exception as e:
            print(f"   �  Error parsing frontmatter in {file_path}: {e}")
            # Fallback to plain content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                return {}, content

    def _chunk_content(self, content: str, max_words: int = 800) -> List[str]:
        """
        Split content into semantic chunks with overlap.

        Args:
            content: Full text content
            max_words: Maximum words per chunk

        Returns:
            List of content chunks
        """
        # Clean and split content
        words = content.replace("\n", " ").split()

        if len(words) <= max_words:
            return [content] if content.strip() else []

        chunks = []
        overlap_words = 100  # Words to overlap between chunks

        for i in range(0, len(words), max_words - overlap_words):
            chunk_words = words[i : i + max_words]
            chunk_text = " ".join(chunk_words)

            # Only add non-empty chunks
            if chunk_text.strip():
                chunks.append(chunk_text)

        return chunks

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate OpenAI embedding for text."""
        try:
            response = await self.openai_client.embeddings.create(
                model=settings.openai_embedding_model,
                input=text.strip(),
                dimensions=1536,
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"   L Error generating embedding: {e}")
            raise

    def _get_file_hash(self, file_path: Path) -> str:
        """Generate SHA-256 hash of file content."""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception as e:
            print(f"   �  Error hashing file {file_path}: {e}")
            return ""


async def main():
    """Main entry point."""
    print("> Portfolio AI Assistant - Content Ingestion")
    print("=" * 50)

    # Verify environment
    try:
        if not settings.openai_api_key:
            print("L OPENAI_API_KEY environment variable is required")
            return

        if not settings.database_url:
            print("L Database environment variables are required")
            return

        print(
            f"= Database: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        print(f"> OpenAI API: Configured")
        print()

    except Exception as e:
        print(f"L Configuration error: {e}")
        return

    # Run ingestion
    ingester = PortfolioIngester()
    await ingester.ingest_all_content()


if __name__ == "__main__":
    asyncio.run(main())
