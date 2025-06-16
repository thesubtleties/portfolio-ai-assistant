"""Portfolio content search service with RAG and embedding strategies."""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.database import PortfolioContent
from app.repositories.portfolio_repository import PortfolioRepository
import os
import yaml
from pathlib import Path


class PortfolioSearchService:
    """Service for searching portfolio content using various strategies."""

    def __init__(self, db: AsyncSession):
        """
        Initialize the portfolio search service.

        Args:
            db: Database session for content queries
        """
        self.db = db
        self.portfolio_repo = PortfolioRepository(db)

    async def search_portfolio_content(
        self,
        query_embedding: List[float],
        content_types: Optional[List[str]] = None,
        limit: int = 3,
        query_text: str = "",
    ) -> List[PortfolioContent]:
        """Search portfolio content using adaptive hybrid strategy."""
        # Classify query to choose optimal search strategy
        query_type = self.classify_search_strategy(query_text)
        strategy = self.choose_search_strategy(query_type)

        print(f"🔍 [SEARCH] Query type: {query_type}, Strategy: {strategy}")

        if strategy == "semantic":
            return await self._semantic_search(
                query_embedding, content_types, limit
            )
        elif strategy == "pure_content":
            return await self._pure_content_search(
                query_embedding, content_types, limit
            )
        else:  # hybrid
            return await self._hybrid_search(
                query_embedding, content_types, limit
            )

    async def _semantic_search(
        self,
        query_embedding: List[float],
        content_types: Optional[List[str]],
        limit: int,
    ) -> List[PortfolioContent]:
        """Search using semantic embeddings only."""
        initial_results = await self.portfolio_repo.semantic_search(
            query_embedding=query_embedding,
            content_types=content_types,
            limit=limit,
        )

        # Add nearby chunks for better context
        return await self._expand_with_nearby_chunks(initial_results, limit)

    async def _pure_content_search(
        self,
        query_embedding: List[float],
        content_types: Optional[List[str]],
        limit: int,
    ) -> List[PortfolioContent]:
        """Search using pure content embeddings only."""
        initial_results = await self.portfolio_repo.pure_content_search(
            query_embedding=query_embedding,
            content_types=content_types,
            limit=limit,
        )

        # Add nearby chunks for better context
        return await self._expand_with_nearby_chunks(initial_results, limit)

    async def _hybrid_search(
        self,
        query_embedding: List[float],
        content_types: Optional[List[str]],
        limit: int,
    ) -> List[PortfolioContent]:
        """Hybrid search combining both embedding types with intelligent merging."""
        # Get results from both methods using repository
        semantic_results, pure_results = (
            await self.portfolio_repo.hybrid_search(
                query_embedding=query_embedding,
                content_types=content_types,
                limit=limit,
            )
        )

        # Merge and deduplicate
        return self._merge_and_deduplicate(
            semantic_results, pure_results, limit
        )

    def _merge_and_deduplicate(
        self,
        semantic_results: List[PortfolioContent],
        pure_results: List[PortfolioContent],
        limit: int,
    ) -> List[PortfolioContent]:
        """Intelligently merge results from both methods."""
        merged = []
        seen_content = set()

        # Interleave results to get diversity
        max_len = max(len(semantic_results), len(pure_results))

        for i in range(max_len):
            # Add semantic result if available and not duplicate
            if i < len(semantic_results):
                semantic_result = semantic_results[i]
                content_hash = hash(
                    semantic_result.content_chunk[:100]
                )  # Hash first 100 chars
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

    def classify_search_strategy(self, query: str) -> str:
        """Classify query type to determine optimal search strategy."""
        query_lower = query.lower()

        # Initialize scores for each category
        scores = {
            "technical_conceptual": 0,
            "broad_overview": 0,
            "specific_content": 0,
            "personal_background": 0,
        }

        # Project names get high specific_content score (highest priority)
        project_names = [
            "atria",
            "spookyspot",
            "taskflow",
            "hills house",
            "hillshouse",
            "styleatc",
            "linkedin",
            "portfolio",
        ]
        project_matches = sum(
            1 for name in project_names if name in query_lower
        )
        if project_matches > 0:
            scores["specific_content"] += (
                project_matches * 5
            )  # Very high weight

        # URL/link requests are always specific content
        url_terms = ["url", "link", "demo", "github", "repository", "source"]
        url_matches = sum(1 for term in url_terms if term in query_lower)
        if url_matches > 0:
            scores["specific_content"] += url_matches * 3

        # Technical framework/architecture terms
        tech_conceptual_terms = [
            "fastapi",
            "react",
            "typescript",
            "python",
            "architecture",
            "design",
            "patterns",
            "approach",
            "philosophy",
            "methodology",
            "framework",
            "library",
            "technology",
            "database",
            "api",
            "backend",
            "frontend",
            "fullstack",
            "development",
            "engineering",
        ]
        tech_matches = sum(
            1 for term in tech_conceptual_terms if term in query_lower
        )
        scores["technical_conceptual"] += tech_matches * 2

        # Broad overview terms
        overview_terms = [
            "overview",
            "summary",
            "about",
            "tell me about",
            "what is",
            "describe",
            "explain",
            "general",
            "broad",
            "high level",
            "introduction",
        ]
        overview_matches = sum(
            1 for term in overview_terms if term in query_lower
        )
        scores["broad_overview"] += overview_matches * 2

        # Personal/background terms
        personal_terms = [
            "background",
            "experience",
            "career",
            "personal",
            "journey",
            "story",
            "interests",
            "hobbies",
            "passion",
            "motivation",
            "transition",
            "leadership",
            "team",
            "management",
        ]
        personal_matches = sum(
            1 for term in personal_terms if term in query_lower
        )
        scores["personal_background"] += personal_matches * 2

        # Determine winning category
        max_score = max(scores.values())
        if max_score == 0:
            return "broad_overview"  # Default fallback

        # Find category with highest score
        for category, score in scores.items():
            if score == max_score:
                print(
                    f"🔍 [CLASSIFY] Query classified as '{category}' (score: {score})"
                )
                print(f"🔍 [CLASSIFY] All scores: {scores}")
                return category

        return "broad_overview"  # Should never reach here

    def choose_search_strategy(self, query_type: str) -> str:
        """Choose optimal search strategy based on query classification."""
        strategy_map = {
            "technical_conceptual": "semantic",  # Good for concepts, patterns
            "broad_overview": "hybrid",  # Mix both for comprehensive coverage
            "specific_content": "pure_content",  # Direct content matching
            "personal_background": "semantic",  # Conceptual understanding
        }

        strategy = strategy_map.get(query_type, "hybrid")
        print(
            f"🔍 [STRATEGY] Using '{strategy}' strategy for '{query_type}' query"
        )
        return strategy

    def detect_content_types(self, message: str) -> Optional[List[str]]:
        """Determine content types to filter by based on keywords."""
        message_lower = message.lower()
        content_types = []

        # Project-specific keywords
        if any(
            word in message_lower
            for word in [
                "project",
                "projects",
                "built",
                "app",
                "application",
                "system",
                # Project names
                "atria",
                "spookyspot",
                "taskflow",
                "hillshouse",
                "hills house",
                "styleatc",
                "linkedin analyzer",
                "portfolio assistant",
                "stack",
                "technologies",
                "fun",
            ]
        ):
            content_types.append("project")

        # Experience/career keywords
        if any(
            word in message_lower
            for word in [
                "experience",
                "experienced",
                "background",
                "career",
                "job",
                "work history",
                "leadership",
            ]
        ):
            content_types.append("experience")

        # Personal/about keywords
        if any(
            word in message_lower
            for word in [
                "personal",
                "background",
                "interests",
                "hobbies",
                "leadership",
                "experience",
                "experiences",
                "fun",
                "facts",
                "likes",
                "dislikes",
            ]
        ):
            content_types.append("about")

        # Return None if no specific types detected (search all)
        return content_types if content_types else None

    def needs_portfolio_search(self, message: str) -> bool:
        """Decide if we need to search portfolio content."""
        from app.core.config import settings

        message_lower = message.lower()
        return any(
            keyword in message_lower
            for keyword in settings.portfolio_search_keywords
        )

    def get_search_limit(self, message: str) -> int:
        """Determine search limit based on query type."""
        message_lower = message.lower()

        # Keywords that indicate comprehensive queries
        comprehensive_keywords = [
            "all",
            "list",
            "every",
            "each",
            "show me all",
            "everything",
            "complete",
            "entire",
            "full",
            "comprehensive",
            "overview",
            "summary",
        ]

        # Check if this is a comprehensive query (gets doubled by nearby chunks expansion)
        if any(keyword in message_lower for keyword in comprehensive_keywords):
            return 14  # 14 * 2 = 28 total (4 per project for 7 projects)
        else:
            return 5  # 5 * 2 = 10 total for focused queries

    async def _expand_with_nearby_chunks(
        self, initial_results: List[PortfolioContent], limit: int
    ) -> List[PortfolioContent]:
        """Expand results with nearby chunks from same documents for better context."""
        if not initial_results:
            return []

        expanded_results = []
        seen_chunks = set()

        for result in initial_results:
            # Add the original result
            chunk_id = f"{result.knowledge_source_id}_{result.chunk_index}"
            if chunk_id not in seen_chunks:
                expanded_results.append(result)
                seen_chunks.add(chunk_id)

            # Get nearby chunks from same document (±2 chunks)
            source_id = result.knowledge_source_id
            current_index = result.chunk_index

            # Get chunks before and after current chunk using repository
            nearby_chunks = await self.portfolio_repo.get_nearby_chunks(
                knowledge_source_id=source_id,
                center_chunk_index=current_index,
                range_before=2,
                range_after=2,
                limit=5,
            )

            # Add nearby chunks that haven't been seen
            for chunk in nearby_chunks:
                chunk_id = f"{chunk.knowledge_source_id}_{chunk.chunk_index}"
                if (
                    chunk_id not in seen_chunks
                    and len(expanded_results) < limit * 2
                ):  # Allow some expansion
                    expanded_results.append(chunk)
                    seen_chunks.add(chunk_id)

        # Sort by original relevance order while preserving document flow
        return expanded_results[:limit]

    async def expand_query_for_better_search(self, query: str) -> str:
        """Expand query with contextual terms for improved search results."""
        query_lower = query.lower()
        expanded_parts = [query]  # Start with original query
        expansion_triggered = False
        expansion_source = "none"

        # Project-specific expansion using database metadata
        project_terms = await self._get_project_metadata_from_db(query_lower)
        if project_terms:
            expanded_parts.extend(project_terms)
            print(
                f"🔍 [EXPAND] Enhanced project query with database metadata: {project_terms[:5]}..."
            )
            expansion_triggered = True
            expansion_source = "project_metadata_db"

        # Fallback to static project metadata if database didn't provide results
        if not expansion_triggered:
            project_metadata = self._get_project_metadata_terms()
            for project, terms in project_metadata.items():
                if project in query_lower:
                    expanded_parts.extend(terms)
                    print(
                        f"🔍 [EXPAND] Enhanced '{project}' query with metadata: {terms}"
                    )
                    expansion_triggered = True
                    expansion_source = f"project_metadata_{project}"
                    break

        # Technology-specific expansion
        tech_expansions = {
            "react": [
                "React 18",
                "TypeScript",
                "component architecture",
                "hooks",
                "state management",
            ],
            "fastapi": [
                "FastAPI",
                "Python",
                "async",
                "REST API",
                "Pydantic",
            ],
            "database": [
                "PostgreSQL",
                "MongoDB",
                "data modeling",
                "schema design",
            ],
            "api": [
                "REST API",
                "endpoints",
                "backend",
                "server",
                "integration",
            ],
            "frontend": [
                "user interface",
                "React",
                "TypeScript",
                "responsive design",
            ],
            "backend": ["server", "API", "database", "Flask", "FastAPI"],
        }

        # Add tech context if query contains technical terms
        if (
            not expansion_triggered
        ):  # Only if project expansion didn't already trigger
            for tech, keywords in tech_expansions.items():
                if tech in query_lower:
                    expanded_parts.extend(keywords[:3])
                    print(
                        f"🔍 [EXPAND] Enhanced '{tech}' query with tech keywords: {keywords[:3]}"
                    )
                    expansion_triggered = True
                    expansion_source = f"tech_expansion_{tech}"
                    break

        # Experience/career context
        career_terms = ["experience", "career", "background", "work history"]
        career_keywords = [
            "leadership",
            "team management",
            "technical transition",
            "App Academy",
            "audio visual production",
            "career change",
        ]

        if (
            any(term in query_lower for term in career_terms)
            and not expansion_triggered
        ):
            expanded_parts.extend(career_keywords)
            print(
                f"🔍 [EXPAND] Enhanced career query with experience keywords: {career_keywords}"
            )
            expansion_triggered = True
            expansion_source = "career_expansion"

        expanded_query = " ".join(expanded_parts)

        # Log expansion results
        if expansion_triggered:
            print(
                f"🔍 [EXPAND-SUCCESS] Expansion triggered by: {expansion_source}"
            )
            print(f"🔍 [EXPAND-BEFORE] Original: '{query}'")
            print(f"🔍 [EXPAND-AFTER] Expanded: '{expanded_query}'")
            print(
                f"🔍 [EXPAND-STATS] Added {len(expanded_parts) - 1} expansion terms"
            )
        else:
            print(
                f"🔍 [EXPAND-SKIP] No expansion triggered for query: '{query}'"
            )

        return expanded_query

    async def _get_project_metadata_from_db(self, query_lower: str) -> list:
        """Get project metadata from PostgreSQL for query expansion."""

        # Define project name mappings
        project_mappings = {
            "atria": ["atria", "atria event"],
            "spookyspot": ["spookyspot", "spooky spot"],
            "taskflow": ["taskflow", "task flow"],
            "hills house": ["hills house", "hillshouse"],
            "styleatc": ["styleatc", "style atc"],
            "linkedin": ["linkedin", "linkedin analyzer"],
            "portfolio": ["portfolio", "portfolio assistant"],
        }

        # Check if any project name is in the query
        detected_project = None
        for project_key, variations in project_mappings.items():
            if any(variation in query_lower for variation in variations):
                detected_project = project_key
                print(f"🔍 [DB-METADATA] Detected project: {project_key}")
                break

        if not detected_project:
            print(f"🔍 [DB-METADATA] No project detected in query")
            return []

        try:
            # Get project metadata using repository
            all_metadata = await self.portfolio_repo.get_project_metadata()

            print(
                f"🔍 [DB-METADATA] Found {len(all_metadata)} project metadata records"
            )

            # Find matching project metadata
            matching_metadata = None
            for metadata in all_metadata:
                if not metadata:
                    continue

                title = metadata.get("title", "").lower()
                # Check if this metadata matches our detected project
                if any(
                    variation in title
                    for variation in project_mappings[detected_project]
                ):
                    matching_metadata = metadata
                    print(
                        f"🔍 [DB-METADATA] Found matching metadata for {detected_project}: {metadata.get('title')}"
                    )
                    break

            if not matching_metadata:
                print(
                    f"🔍 [DB-METADATA] No matching metadata found for {detected_project}"
                )
                return []

            # Extract key terms for expansion - tech stack + URLs
            expansion_terms = []

            # Add tech stack terms (frontend + backend only)
            tech_stack = matching_metadata.get("tech_stack", {})
            if isinstance(tech_stack, dict):
                # Only get frontend and backend categories
                for category in ["frontend", "backend"]:
                    technologies = tech_stack.get(category, [])
                    if isinstance(technologies, list):
                        expansion_terms.extend(technologies)
                    elif isinstance(technologies, str):
                        expansion_terms.append(technologies)

            # Add specific URLs
            url_fields = ["live_url", "github_repo"]
            for field in url_fields:
                url_value = matching_metadata.get(field)
                if (
                    url_value
                    and isinstance(url_value, str)
                    and url_value.strip()
                ):
                    expansion_terms.append(url_value.strip())

            # Clean terms
            cleaned_terms = []
            for term in expansion_terms:
                if isinstance(term, str) and len(term.strip()) > 1:
                    cleaned_terms.append(term.strip())

            tech_terms = [t for t in cleaned_terms if not t.startswith("http")]
            url_terms = [t for t in cleaned_terms if t.startswith("http")]

            print(f"🔍 [DB-METADATA] Extracted expansion terms:")
            print(f"  - Tech stack: {tech_terms}")
            print(f"  - URLs: {url_terms}")

            return cleaned_terms  # Return tech stack + URLs (~14 terms)

        except Exception as e:
            print(f"⚠️  [DB-METADATA] Error querying project metadata: {e}")
            return []

    def _get_project_metadata_terms(self) -> dict:
        """Extract metadata terms from actual project files for dynamic expansion."""
        project_metadata = {}
        content_dir = (
            Path(__file__).parent.parent.parent.parent / "content" / "projects"
        )

        print(
            f"🔍 [METADATA] Attempting to load project metadata from: {content_dir}"
        )

        if not content_dir.exists():
            print(
                f"🔍 [METADATA] Content directory does not exist: {content_dir}"
            )
            return self._get_fallback_project_metadata()

        try:
            for yaml_file in content_dir.glob("*.yaml"):
                print(f"🔍 [METADATA] Processing file: {yaml_file}")
                try:
                    with open(yaml_file, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)

                    if not data or "projects" not in data:
                        print(
                            f"🔍 [METADATA] No projects found in {yaml_file}"
                        )
                        continue

                    for project_data in data["projects"]:
                        project_name = project_data.get("title", "").lower()
                        if not project_name:
                            continue

                        # Extract terms from this project
                        terms = self._extract_terms_from_metadata(
                            project_data, project_name
                        )

                        # Add variations of project name as keys
                        name_variations = [project_name]
                        if "hills house" in project_name:
                            name_variations.extend(
                                ["hills house", "hillshouse"]
                            )
                        elif "spooky" in project_name:
                            name_variations.extend(
                                ["spookyspot", "spooky spot"]
                            )
                        elif "task" in project_name:
                            name_variations.extend(["taskflow", "task flow"])
                        elif "style" in project_name:
                            name_variations.extend(["styleatc", "style atc"])

                        for variation in name_variations:
                            project_metadata[variation] = terms

                except Exception as e:
                    print(f"⚠️  [METADATA] Error processing {yaml_file}: {e}")
                    continue

        except Exception as e:
            print(f"⚠️  [METADATA] Error accessing content directory: {e}")

        if project_metadata:
            print(
                f"🔍 [METADATA-SUCCESS] Loaded metadata for {len(project_metadata)} project variations: {list(project_metadata.keys())}"
            )
            return project_metadata
        else:
            print(
                f"🔍 [METADATA] No metadata extracted, falling back to hardcoded metadata"
            )
            return self._get_fallback_project_metadata()

    def _extract_terms_from_metadata(
        self, metadata: dict, project_name: str
    ) -> list:
        """Extract searchable terms from project metadata."""
        terms = []
        extraction_log = {}

        # Add project title exactly as it appears
        if "title" in metadata:
            terms.append(metadata["title"])
            extraction_log["title"] = metadata["title"]

        # Extract from tech_stack
        if "tech_stack" in metadata:
            tech_stack = metadata["tech_stack"]
            tech_terms = []
            if isinstance(tech_stack, dict):
                for category, technologies in tech_stack.items():
                    if isinstance(technologies, list):
                        tech_terms.extend(technologies)
                        terms.extend(technologies)
                    elif isinstance(technologies, str):
                        tech_terms.append(technologies)
                        terms.append(technologies)
            extraction_log["tech_stack"] = tech_terms

        # Extract keywords
        if "keywords" in metadata and isinstance(metadata["keywords"], list):
            terms.extend(metadata["keywords"])
            extraction_log["keywords"] = metadata["keywords"]

        # Extract technical challenges
        if "technical_challenges" in metadata and isinstance(
            metadata["technical_challenges"], list
        ):
            terms.extend(metadata["technical_challenges"])
            extraction_log["technical_challenges"] = metadata[
                "technical_challenges"
            ]

        # Extract architecture patterns
        if "architecture_patterns" in metadata and isinstance(
            metadata["architecture_patterns"], list
        ):
            terms.extend(metadata["architecture_patterns"])
            extraction_log["architecture_patterns"] = metadata[
                "architecture_patterns"
            ]

        # Extract highlight_for terms
        if "highlight_for" in metadata and isinstance(
            metadata["highlight_for"], list
        ):
            terms.extend(metadata["highlight_for"])
            extraction_log["highlight_for"] = metadata["highlight_for"]

        # Add domain and complexity info
        other_fields = []
        for field in [
            "domain",
            "complexity_level",
            "project_scale",
            "business_impact",
        ]:
            if field in metadata and isinstance(metadata[field], str):
                terms.append(metadata[field])
                other_fields.append(f"{field}: {metadata[field]}")
        if other_fields:
            extraction_log["other_fields"] = other_fields

        # Clean and return terms
        cleaned_terms = []
        for term in terms:
            if isinstance(term, str) and len(term.strip()) > 1:
                cleaned_terms.append(term.strip())

        # Log extraction details
        print(f"🔍 [METADATA-EXTRACT] For {project_name}:")
        for source, extracted in extraction_log.items():
            print(
                f"  - {source}: {extracted if isinstance(extracted, list) and len(extracted) <= 3 else (extracted[:3] + ['...'] if isinstance(extracted, list) else extracted)}"
            )
        print(
            f"  - Total raw terms: {len(terms)}, Cleaned terms: {len(cleaned_terms)}"
        )

        final_terms = cleaned_terms[:15]  # Limit to top 15 terms
        print(f"  - Final terms (max 15): {final_terms}")

        return final_terms

    def _get_fallback_project_metadata(self) -> dict:
        """Fallback project metadata if file reading fails."""
        return {
            "atria": [
                "Atria Event Management Platform",
                "Flask API",
                "React 18",
                "TypeScript",
                "Redux Toolkit",
                "event management",
                "capstone project",
            ],
            "spookyspot": [
                "SpookySpot",
                "Halloween vacation rental",
                "React 18",
                "Node.js",
                "PostgreSQL",
                "social platform",
                "Redux",
            ],
            "taskflow": [
                "TaskFlow",
                "agile project management",
                "React",
                "Flask API",
                "Redux" "team collaboration",
            ],
            "hills house": [
                "Hills House",
                "headless CMS",
                "Next.js",
                "Payload CMS",
                "musician website",
                "Canvas animations",
            ],
            "hillshouse": [
                "Hills House",
                "headless CMS",
                "Next.js",
                "Payload CMS",
                "musician website",
                "Canvas animations",
            ],
            "styleatc": [
                "StyleATC",
                "MCP integration",
                "design system",
                "AI-controlled",
                "component library",
            ],
            "style atc": [
                "StyleATC",
                "MCP integration",
                "design system",
                "AI-controlled",
                "component library",
            ],
            "linkedin": [
                "LinkedIn Job Analyzer",
                "data scraping",
                "Python automation",
                "job market analysis",
            ],
            "portfolio": [
                "Portfolio AI Assistant",
                "FastAPI",
                "vector search",
                "RAG system",
                "OpenAI embeddings",
            ],
        }
