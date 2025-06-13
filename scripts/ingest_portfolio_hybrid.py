#!/usr/bin/env python3
"""
Hybrid Portfolio Content Ingestion Script

This script creates BOTH semantic_v2 and pure_content embeddings for each chunk,
allowing for adaptive search strategies based on query type.
"""

import argparse
import asyncio
import hashlib
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
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


class HybridPortfolioIngester:
    """Creates both contextual and pure content embeddings for hybrid search."""

    def __init__(self, force_reingest: bool = False):
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.content_dir = Path(__file__).parent.parent / "content"
        self.force_reingest = force_reingest

    async def ingest_all_content(self):
        """Main entry point - process all content files with dual embeddings."""
        print(f"🚀 Starting HYBRID portfolio content ingestion from {self.content_dir}")
        print("🧠 Creating BOTH semantic and pure content embeddings for adaptive search")
        print()

        if self.force_reingest:
            print("⚠️  Force reingest enabled - will delete all existing content")
            print()

        # Process all markdown files
        markdown_files = list(self.content_dir.rglob("*.md"))
        print(f"📁 Found {len(markdown_files)} markdown files")

        processed_count = 0
        skipped_count = 0

        async with AsyncSessionLocal() as session:
            if self.force_reingest:
                await self._wipe_all_content(session)
                await session.commit()

            for file_path in markdown_files:
                try:
                    was_processed = await self.process_file(session, file_path)
                    if was_processed:
                        processed_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    print(f"❌ Error processing {file_path}: {e}")
                    continue

            await session.commit()

        print(f"\n✅ Hybrid ingestion complete!")
        print(f"   📊 Processed: {processed_count} files")
        print(f"   ⏭️  Skipped: {skipped_count} files (unchanged)")
        print(f"   🔄 Each chunk now has BOTH semantic and pure embeddings")

    async def process_file(self, session: AsyncSession, file_path: Path) -> bool:
        """Process file creating TWO chunks per section - one semantic, one pure."""
        relative_path = file_path.relative_to(Path(__file__).parent.parent)

        # 1. Check if file changed
        content_hash = self._get_file_hash(file_path)
        source = await self._get_or_create_knowledge_source(
            session, str(relative_path), content_hash
        )

        if source.checksum == content_hash:
            print(f"⏭️  Skipping unchanged: {relative_path}")
            return False

        print(f"📝 Processing: {relative_path}")

        try:
            # 2. Parse frontmatter + content
            metadata, content = self._parse_markdown(file_path)

            # 3. Delete existing content for this source
            await self._delete_existing_content(session, source.id)

            # 4. Enhanced semantic chunking with DUAL embeddings
            chunks = self._chunk_content_semantic(content)
            print(f"   📊 Creating {len(chunks)} chunks x 2 embedding types = {len(chunks) * 2} total embeddings")

            for i, chunk_data in enumerate(chunks):
                # Create SEMANTIC embedding (with light context)
                semantic_embedding = await self._create_semantic_embedding(
                    chunk_data, metadata, metadata.get("title", file_path.stem.replace("-", " ").title())
                )

                # Create PURE CONTENT embedding (no context)
                pure_embedding = await self._get_embedding(chunk_data['content'])

                # Base metadata for both variants
                base_metadata = {
                    **metadata,
                    'section_title': chunk_data.get('section_title'),
                    'section_type': chunk_data.get('section_type'),
                    'hierarchy_level': chunk_data.get('hierarchy_level'),
                    'word_count': chunk_data.get('word_count'),
                    'has_code': self._has_code_blocks(chunk_data['content']),
                    'is_technical': chunk_data.get('section_type') in ['technical', 'code']
                }

                # Store SEMANTIC version
                semantic_metadata = {
                    **base_metadata,
                    'embedding_type': 'semantic',
                    'chunk_method': 'hybrid_semantic'
                }

                portfolio_content_semantic = PortfolioContent(
                    knowledge_source_id=source.id,
                    content_type=metadata.get("content_type", "general"),
                    title=metadata.get("title", file_path.stem.replace("-", " ").title()),
                    content=content,
                    content_chunk=chunk_data['content'],
                    chunk_index=chunk_data['chunk_index'] * 2,  # Even numbers for semantic
                    embedding=semantic_embedding,
                    content_metadata=semantic_metadata,
                )
                session.add(portfolio_content_semantic)

                # Store PURE CONTENT version
                pure_metadata = {
                    **base_metadata,
                    'embedding_type': 'pure_content',
                    'chunk_method': 'hybrid_pure'
                }

                portfolio_content_pure = PortfolioContent(
                    knowledge_source_id=source.id,
                    content_type=metadata.get("content_type", "general"),
                    title=metadata.get("title", file_path.stem.replace("-", " ").title()),
                    content=content,
                    content_chunk=chunk_data['content'],
                    chunk_index=chunk_data['chunk_index'] * 2 + 1,  # Odd numbers for pure
                    embedding=pure_embedding,
                    content_metadata=pure_metadata,
                )
                session.add(portfolio_content_pure)

                # Enhanced logging
                section_info = f" ({chunk_data.get('section_title', 'Main')})" if chunk_data.get('section_title') else ""
                print(f"    📝 Chunk {i + 1}/{len(chunks)}{section_info} - {chunk_data.get('word_count', 0)} words - {chunk_data.get('section_type', 'general')} [SEMANTIC + PURE]")

            # 5. Update source metadata
            source.checksum = content_hash
            source.last_indexed_at = func.now()

            print(f"   ✅ Completed: {relative_path}")
            return True

        except Exception as e:
            print(f"   ❌ Failed to process {relative_path}: {e}")
            raise

    async def _create_semantic_embedding(self, chunk: Dict, metadata: Dict, title: str) -> List[float]:
        """Create light semantic embedding - minimal context to avoid dominance."""
        content = chunk['content']
        context_parts = []
        
        # Only add section title for structure awareness
        if chunk.get('section_title') and chunk['section_title'] != 'Main Content':
            context_parts.append(chunk['section_title'])
        
        # Add key technologies ONLY if they appear in the content
        if chunk.get('section_type') in ['technical', 'code'] and metadata.get('tech_stack'):
            tech_list = self._flatten_tech_stack(metadata['tech_stack'])
            if tech_list:
                # Only include technologies that are actually mentioned in this chunk
                relevant_techs = [tech for tech in tech_list[:4] if any(
                    tech_word.lower() in content.lower() for tech_word in tech.split()
                )]
                if relevant_techs:
                    context_parts.append(f"Tech: {', '.join(relevant_techs)}")
        
        # Lightweight context prefix
        if context_parts:
            context_prefix = f"[{' | '.join(context_parts)}]\n\n"
            full_context = f"{context_prefix}{content}"
        else:
            full_context = content
        
        return await self._get_embedding(full_context)

    # ... (include all chunking methods from previous versions)
    def _chunk_content_semantic(self, content: str, target_words: int = 600) -> List[Dict]:
        """Split content into semantic chunks preserving structure."""
        sections = self._split_by_headers(content)
        
        chunks = []
        for section in sections:
            section_content = section['content'].strip()
            if not section_content:
                continue
                
            word_count = len(section_content.split())
            
            if word_count <= target_words:
                chunks.append({
                    'content': section_content,
                    'section_title': section['title'],
                    'section_type': self._classify_section_type(section['title'], section_content),
                    'hierarchy_level': section['level'],
                    'chunk_index': len(chunks),
                    'word_count': word_count
                })
            else:
                sub_chunks = self._sub_chunk_by_structure(section_content, target_words)
                for j, sub_chunk in enumerate(sub_chunks):
                    chunks.append({
                        'content': sub_chunk,
                        'section_title': section['title'],
                        'section_type': self._classify_section_type(section['title'], sub_chunk),
                        'hierarchy_level': section['level'],
                        'chunk_index': len(chunks),
                        'sub_chunk_index': j,
                        'word_count': len(sub_chunk.split())
                    })
        
        return chunks

    def _split_by_headers(self, content: str) -> List[Dict]:
        """Split content by markdown headers."""
        sections = []
        header_pattern = r'^(#{1,3})\s+(.+)$'
        lines = content.split('\n')
        
        current_section = {'title': '', 'level': 0, 'content': '', 'lines': []}
        
        for line in lines:
            header_match = re.match(header_pattern, line.strip())
            
            if header_match:
                if current_section['content'].strip():
                    sections.append(current_section)
                
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                
                current_section = {'title': title, 'level': level, 'content': '', 'lines': []}
            else:
                current_section['lines'].append(line)
                current_section['content'] = '\n'.join(current_section['lines'])
        
        if current_section['content'].strip():
            sections.append(current_section)
        
        if not sections:
            sections.append({'title': 'Main Content', 'level': 1, 'content': content, 'lines': content.split('\n')})
        
        return sections

    def _sub_chunk_by_structure(self, content: str, target_words: int) -> List[str]:
        """Sub-chunk by paragraphs and sentences."""
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        if not paragraphs:
            return self._split_by_sentences(content, target_words)
        
        chunks = []
        current_chunk = []
        current_words = 0
        
        for paragraph in paragraphs:
            para_words = len(paragraph.split())
            
            if current_words + para_words > target_words and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [paragraph]
                current_words = para_words
            else:
                current_chunk.append(paragraph)
                current_words += para_words
        
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))
        
        return chunks

    def _split_by_sentences(self, content: str, target_words: int) -> List[str]:
        """Split by sentences."""
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        chunks = []
        current_chunk = []
        current_words = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_words = len(sentence.split())
            
            if current_words + sentence_words > target_words and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_words = sentence_words
            else:
                current_chunk.append(sentence)
                current_words += sentence_words
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks

    def _classify_section_type(self, section_title: str, content: str) -> str:
        """Classify sections by semantic purpose."""
        title_lower = section_title.lower()
        content_sample = content[:500].lower()
        
        if any(word in title_lower for word in [
            'architecture', 'implementation', 'technical', 'stack', 'technology',
            'database', 'api', 'system', 'performance', 'optimization'
        ]):
            return 'technical'
        elif any(word in title_lower for word in [
            'overview', 'about', 'impact', 'business', 'project', 'introduction'
        ]):
            return 'overview'
        elif any(word in title_lower for word in [
            'feature', 'component', 'module', 'functionality', 'capabilities'
        ]):
            return 'feature'
        elif any(word in content_sample for word in [
            'travel', 'hobby', 'personal', 'interest', 'passion', 'experience',
            'grew up', 'family', 'childhood'
        ]):
            return 'personal'
        elif any(indicator in content_sample for indicator in [
            'def ', 'class ', 'import ', '```', 'function', 'const ', 'let '
        ]):
            return 'code'
        
        return 'general'

    def _has_code_blocks(self, content: str) -> bool:
        """Check if content contains code blocks."""
        return '```' in content or any(indicator in content for indicator in [
            'def ', 'class ', 'import ', 'function', 'const ', 'let ', '<script'
        ])

    def _flatten_tech_stack(self, tech_stack: Dict) -> List[str]:
        """Flatten tech stack dictionary."""
        if not isinstance(tech_stack, dict):
            return []
        
        technologies = []
        for category, techs in tech_stack.items():
            if isinstance(techs, list):
                technologies.extend(techs)
            elif isinstance(techs, str):
                technologies.append(techs)
        
        return [tech for tech in technologies if tech]

    async def _get_embedding(self, text: str) -> List[float]:
        """Generate OpenAI embedding."""
        try:
            response = await self.openai_client.embeddings.create(
                model=settings.openai_embedding_model,
                input=text.strip(),
                dimensions=1536,
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"   ❌ Error generating embedding: {e}")
            raise

    def _parse_markdown(self, file_path: Path) -> tuple[Dict, str]:
        """Parse markdown file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
                return dict(post.metadata), post.content
        except Exception as e:
            print(f"   ⚠️  Error parsing frontmatter in {file_path}: {e}")
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                return {}, content

    def _get_file_hash(self, file_path: Path) -> str:
        """Generate file hash."""
        try:
            with open(file_path, "rb") as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception as e:
            print(f"   ⚠️  Error hashing file {file_path}: {e}")
            return ""

    async def _get_or_create_knowledge_source(self, session: AsyncSession, source_path: str, checksum: str) -> KnowledgeSource:
        """Get or create knowledge source."""
        stmt = select(KnowledgeSource).where(KnowledgeSource.source_name == source_path)
        result = await session.execute(stmt)
        source = result.scalar_one_or_none()

        if source is None:
            source = KnowledgeSource(
                source_name=source_path,
                description=f"Portfolio content from {source_path}",
                checksum="",
                last_indexed_at=func.now(),
            )
            session.add(source)
            await session.flush()

        return source

    async def _delete_existing_content(self, session: AsyncSession, source_id):
        """Delete existing content."""
        stmt = delete(PortfolioContent).where(PortfolioContent.knowledge_source_id == source_id)
        await session.execute(stmt)

    async def _wipe_all_content(self, session: AsyncSession):
        """Delete all content."""
        await session.execute(delete(PortfolioContent))
        print("   🗑️  Deleted all PortfolioContent")
        
        await session.execute(delete(KnowledgeSource))
        print("   🗑️  Deleted all KnowledgeSource records")


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Hybrid ingestion with dual embeddings")
    parser.add_argument("--force", action="store_true", help="Delete all existing content and re-ingest")
    args = parser.parse_args()

    print("🤖 Portfolio AI Assistant - Hybrid Dual-Embedding Ingestion")
    print("🧠 Creating BOTH Semantic and Pure Content Embeddings")
    print("=" * 70)

    if not settings.openai_api_key or not settings.database_url:
        print("❌ Required environment variables missing")
        return

    print(f"🗄️  Database: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")
    print(f"🤖 OpenAI API: Configured")
    print()

    ingester = HybridPortfolioIngester(force_reingest=args.force)
    await ingester.ingest_all_content()


if __name__ == "__main__":
    asyncio.run(main())