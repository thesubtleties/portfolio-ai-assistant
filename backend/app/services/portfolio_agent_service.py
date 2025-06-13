"""Portfolio AI Agent service using atomic-agents framework."""

from typing import List, Optional
import instructor
import openai
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from atomic_agents.lib.components.agent_memory import AgentMemory
from atomic_agents.agents.base_agent import (
    BaseAgent,
    BaseAgentConfig,
    BaseAgentInputSchema,
)
from atomic_agents.lib.base.base_io_schema import BaseIOSchema
from pydantic import Field

from app.models.database import Visitor, PortfolioContent


class PortfolioAgentResponse(BaseIOSchema):
    """Response model for portfolio agent."""

    response: str = Field(description="The agent's response to the user")
    visitor_notes_update: Optional[str] = Field(
        default=None,
        description="New notes to append to visitor's profile, or None if no update needed",
    )
    is_off_topic: bool = Field(
        default=False,
        description="True if this conversation is off-topic (general coding help, unrelated questions). Off-topic: asking for coding help, generic LLM usage, unrelated topics. On-topic: Steven's portfolio, experience, personal interests, technical approaches, quotes.",
    )
    rag_summary: Optional[str] = Field(
        default=None,
        description="A brief summary (100-250 tokens) of the RAG context used for this response, to maintain conversation continuity while reducing memory bloat. Only include if RAG context was used.",
    )


class PortfolioAgentService:
    """Service for handling AI agent conversations about the portfolio."""

    def __init__(self, db: AsyncSession, redis_client):
        """Initialize the portfolio agent service."""
        self.db = db
        self.redis = redis_client

        # Set up AI client based on provider
        from app.core.config import settings

        self.settings = settings

        # Debug logging
        print(
            f"🔧 [DEBUG] Initializing with provider: '{settings.ai_provider}' (len={len(settings.ai_provider)})"
        )
        print(
            f"🔧 [DEBUG] Provider comparison: '{settings.ai_provider}' == 'gemini' -> {settings.ai_provider == 'gemini'}"
        )
        print(
            f"🔧 [DEBUG] Available models - OpenAI: {settings.openai_model}, Gemini: {getattr(settings, 'gemini_model', 'not set')}"
        )

        # Always keep OpenAI client for embeddings (for now)
        self.async_openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Initialize the instructor client based on provider
        if settings.ai_provider.strip() == "gemini":
            print(f"🔧 [DEBUG] Creating Gemini client...")
            self.client = self._create_gemini_client()
        else:  # Default to OpenAI
            print(
                f"🔧 [DEBUG] Creating OpenAI client... (provider was '{settings.ai_provider}')"
            )
            self.client = instructor.from_openai(
                openai.OpenAI(api_key=settings.openai_api_key)
            )

        # Store conversation agents: {conversation_id: BaseAgent}
        self.conversation_agents = {}

    def _create_gemini_client(self):
        """Create Gemini client using instructor."""
        if not self.settings.gemini_api_key:
            raise ValueError("Gemini API key not provided")

        # Use OpenAI-compatible endpoint for Gemini
        gemini_client = openai.OpenAI(
            api_key=self.settings.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

        return instructor.from_openai(gemini_client, mode=instructor.Mode.JSON)

    def _get_current_model(self) -> str:
        """Get the current model based on provider."""
        if self.settings.ai_provider == "gemini":
            model = self.settings.gemini_model
            print(f"🔧 [DEBUG] Using Gemini model: {model}")
            return model
        else:
            model = self.settings.openai_model
            print(f"🔧 [DEBUG] Using OpenAI model: {model}")
            return model

    def _get_system_prompt_generator(self):
        """Get the system prompt generator for the portfolio agent."""
        from atomic_agents.lib.components.system_prompt_generator import (
            SystemPromptGenerator,
        )
        from app.core.config import settings

        return SystemPromptGenerator(
            background=settings.agent_background,
            steps=settings.agent_steps,
            output_instructions=settings.agent_output_instructions,
        )

    def _create_agent_for_conversation(
        self, visitor, conversation_id: str
    ) -> BaseAgent:
        """Create a new agent instance for a conversation."""
        memory = AgentMemory()

        # Add initial greeting message to establish conversation context
        from app.core.config import settings
        from atomic_agents.agents.base_agent import BaseAgentOutputSchema

        initial_message = BaseAgentOutputSchema(
            chat_message=settings.agent_greeting
        )
        memory.add_message("assistant", initial_message)

        # Create agent with conversation-specific memory
        # Use structured output schema for RAG summarization
        agent = BaseAgent(
            config=BaseAgentConfig(
                client=self.client,
                model=self._get_current_model(),
                memory=memory,
                system_prompt_generator=self._get_system_prompt_generator(),
                output_schema=PortfolioAgentResponse,  # Enable for RAG summarization
            )
        )

        return agent

    async def search_portfolio_content(
        self,
        query_embedding: List[float],
        content_types: Optional[List[str]] = None,
        limit: int = 3,
        query_text: str = "",
    ) -> List[PortfolioContent]:
        """Search portfolio content using adaptive hybrid strategy."""
        # Classify query to choose optimal search strategy
        query_type = self._classify_query(query_text)
        strategy = self._choose_search_strategy(query_type)

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
        query = select(PortfolioContent).where(
            PortfolioContent.content_metadata["embedding_type"].astext
            == "semantic"
        )

        if content_types:
            query = query.where(
                PortfolioContent.content_type.in_(content_types)
            )

        query = query.order_by(
            PortfolioContent.embedding.cosine_distance(query_embedding)
        ).limit(limit)

        result = await self.db.execute(query)
        initial_results = result.scalars().all()

        # Add nearby chunks for better context
        return await self._expand_with_nearby_chunks(initial_results, limit)

    async def _pure_content_search(
        self,
        query_embedding: List[float],
        content_types: Optional[List[str]],
        limit: int,
    ) -> List[PortfolioContent]:
        """Search using pure content embeddings only."""
        query = select(PortfolioContent).where(
            PortfolioContent.content_metadata["embedding_type"].astext
            == "pure_content"
        )

        if content_types:
            query = query.where(
                PortfolioContent.content_type.in_(content_types)
            )

        query = query.order_by(
            PortfolioContent.embedding.cosine_distance(query_embedding)
        ).limit(limit)

        result = await self.db.execute(query)
        initial_results = result.scalars().all()

        # Add nearby chunks for better context
        return await self._expand_with_nearby_chunks(initial_results, limit)

    async def _hybrid_search(
        self,
        query_embedding: List[float],
        content_types: Optional[List[str]],
        limit: int,
    ) -> List[PortfolioContent]:
        """Hybrid search combining both embedding types with intelligent merging."""
        # Get results from both methods
        semantic_query = select(PortfolioContent).where(
            PortfolioContent.content_metadata["embedding_type"].astext
            == "semantic"
        )
        pure_query = select(PortfolioContent).where(
            PortfolioContent.content_metadata["embedding_type"].astext
            == "pure_content"
        )

        if content_types:
            semantic_query = semantic_query.where(
                PortfolioContent.content_type.in_(content_types)
            )
            pure_query = pure_query.where(
                PortfolioContent.content_type.in_(content_types)
            )

        semantic_query = semantic_query.order_by(
            PortfolioContent.embedding.cosine_distance(query_embedding)
        ).limit(limit * 2)

        pure_query = pure_query.order_by(
            PortfolioContent.embedding.cosine_distance(query_embedding)
        ).limit(limit * 2)

        semantic_results = (
            (await self.db.execute(semantic_query)).scalars().all()
        )
        pure_results = (await self.db.execute(pure_query)).scalars().all()

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

    def _classify_query(self, query: str) -> str:
        """Classify query type using weighted scoring for better accuracy."""
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
            "architecture",
            "pattern",
            "implementation",
            "framework",
            "design",
            "approach",
            "methodology",
            "component",
        ]
        tech_conceptual_matches = sum(
            1 for term in tech_conceptual_terms if term in query_lower
        )
        scores["technical_conceptual"] += tech_conceptual_matches * 2

        # Broad overview indicators
        broad_terms = [
            "all projects",
            "tell me about",
            "overview",
            "everything",
            "what has steven",
            "show me all",
            "complete list",
        ]
        broad_matches = sum(1 for term in broad_terms if term in query_lower)
        scores["broad_overview"] += broad_matches * 3

        # Specific content/technology terms (lower weight than project names)
        specific_terms = [
            "code example",
            "database",
            "what databases",
            "which database",
            "technologies",
            "tools",
            "languages",
            "stack",
            "frameworks",
            "libraries",
            "APIs",
            "services",
            "specific",
        ]
        specific_matches = sum(
            1 for term in specific_terms if term in query_lower
        )
        scores["specific_content"] += specific_matches * 2
        scores["technical_conceptual"] += (
            specific_matches * 1
        )  # Also technical

        # Personal/background terms
        personal_terms = [
            "background",
            "personal",
            "interests",
            "experience",
            "career",
            "about steven",
            "hobbies",
            "quotes",
            "inspiration",
        ]
        personal_matches = sum(
            1 for term in personal_terms if term in query_lower
        )
        scores["personal_background"] += personal_matches * 2

        # Find category with highest score
        max_score = max(scores.values())
        if max_score == 0:
            return "general"

        # Return the category with the highest score
        for category, score in scores.items():
            if score == max_score:
                return category

        return "general"

    def _choose_search_strategy(self, query_type: str) -> str:
        """Choose optimal search strategy based on query type."""
        strategy_map = {
            "technical_conceptual": "semantic",  # Benefits from contextual understanding
            "broad_overview": "hybrid",  # Needs diversity and coverage
            "specific_content": "hybrid",  # URLs/links benefit from both approaches
            "personal_background": "pure_content",  # Often in descriptive sections
            "general": "hybrid",  # Safe fallback
        }

        return strategy_map.get(query_type, "hybrid")

    async def _expand_query_for_better_search(self, query: str) -> str:
        """Expand user queries with contextual keywords for better RAG retrieval."""
        query_lower = query.lower()
        expanded_parts = [query]  # Start with original query
        expansion_triggered = False
        expansion_source = None

        print(f"🔍 [EXPAND] Starting query expansion for: '{query}'")

        # Dynamic project metadata expansion via PostgreSQL
        print(f"🔍 [EXPAND] Checking for project mentions...")
        project_metadata_terms = await self._get_project_metadata_from_db(
            query_lower
        )

        if project_metadata_terms:
            print(
                f"🔍 [EXPAND] Project metadata found, adding expansion terms"
            )
            # Add content_type for stronger project matching
            expanded_parts.append("content_type project")
            expanded_parts.extend(project_metadata_terms)

            tech_terms = [
                t for t in project_metadata_terms if not t.startswith("http")
            ]
            url_terms = [
                t for t in project_metadata_terms if t.startswith("http")
            ]
            print(
                f"🔍 [EXPAND] Enhanced query with {len(project_metadata_terms)} metadata terms:"
            )
            print(f"  - Tech terms: {tech_terms}")
            print(f"  - URL terms: {url_terms}")

            expansion_triggered = True
            expansion_source = "project_metadata_db"

        # Technology-specific expansions
        tech_expansions = {
            "react": [
                "component architecture",
                "hooks",
                "state management",
                "frontend",
            ],
            "python": [
                "backend development",
                "API",
                "automation",
                "data processing",
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
            # Query PostgreSQL for project metadata
            db_query = (
                select(PortfolioContent.content_metadata)
                .where(PortfolioContent.content_type == "project")
                .distinct()
            )

            result = await self.db.execute(db_query)
            all_metadata = result.scalars().all()

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
        import os
        import yaml
        from pathlib import Path

        project_metadata = {}
        content_dir = (
            Path(__file__).parent.parent.parent.parent / "content" / "projects"
        )

        print(
            f"🔍 [METADATA] Attempting to load project metadata from: {content_dir}"
        )

        if not content_dir.exists():
            print(f"⚠️  [METADATA] Content directory not found: {content_dir}")
            print(f"🔍 [METADATA] Falling back to hardcoded metadata")
            return self._get_fallback_project_metadata()

        try:
            project_files = list(content_dir.glob("*.md"))
            print(
                f"🔍 [METADATA] Found {len(project_files)} project files: {[f.name for f in project_files]}"
            )

            for project_file in project_files:
                project_name = project_file.stem.replace("-", " ")
                print(
                    f"🔍 [METADATA] Processing file: {project_file.name} (project: {project_name})"
                )

                # Extract frontmatter
                with open(project_file, "r", encoding="utf-8") as f:
                    content = f.read()

                if content.startswith("---"):
                    # Split frontmatter and content
                    parts = content.split("---", 2)
                    if len(parts) >= 2:
                        frontmatter = parts[1]
                        try:
                            metadata = yaml.safe_load(frontmatter)
                            print(
                                f"🔍 [METADATA] Parsed frontmatter for {project_name}: {list(metadata.keys()) if metadata else 'None'}"
                            )

                            terms = self._extract_terms_from_metadata(
                                metadata, project_name
                            )
                            print(
                                f"🔍 [METADATA] Extracted {len(terms)} terms for {project_name}: {terms[:5]}..."
                            )

                            # Map common project name variations
                            project_variations = [
                                project_name.lower(),
                                project_name.lower().replace(" ", ""),
                                project_name.lower().replace("-", " "),
                            ]

                            # Add specific mappings
                            if "atria" in project_name.lower():
                                project_variations.extend(
                                    ["atria", "atria event"]
                                )
                            elif "spooky" in project_name.lower():
                                project_variations.extend(
                                    ["spookyspot", "spooky spot"]
                                )
                            elif "task" in project_name.lower():
                                project_variations.extend(
                                    ["taskflow", "task flow"]
                                )
                            elif "hills" in project_name.lower():
                                project_variations.extend(
                                    ["hills house", "hillshouse"]
                                )
                            elif "style" in project_name.lower():
                                project_variations.extend(
                                    ["styleatc", "style atc"]
                                )
                            elif "linkedin" in project_name.lower():
                                project_variations.extend(
                                    ["linkedin", "linkedin analyzer"]
                                )
                            elif "portfolio" in project_name.lower():
                                project_variations.extend(
                                    ["portfolio", "portfolio assistant"]
                                )

                            print(
                                f"🔍 [METADATA] Created {len(project_variations)} variations for {project_name}: {project_variations}"
                            )

                            for variation in project_variations:
                                project_metadata[variation] = terms

                        except yaml.YAMLError as e:
                            print(
                                f"⚠️  [METADATA] YAML error in {project_file}: {e}"
                            )
                            continue
                else:
                    print(
                        f"⚠️  [METADATA] No frontmatter found in {project_file.name}"
                    )

        except Exception as e:
            print(f"⚠️  [METADATA] Error reading project metadata: {e}")
            print(f"🔍 [METADATA] Falling back to hardcoded metadata")
            return self._get_fallback_project_metadata()

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

            # Get chunks before and after current chunk
            nearby_query = (
                select(PortfolioContent)
                .where(
                    PortfolioContent.knowledge_source_id == source_id,
                    PortfolioContent.chunk_index.between(
                        current_index - 4, current_index + 4
                    ),
                    PortfolioContent.chunk_index != current_index,
                )
                .order_by(PortfolioContent.chunk_index)
            )

            nearby_result = await self.db.execute(nearby_query)
            nearby_chunks = nearby_result.scalars().all()

            # Add nearby chunks that aren't already included
            for nearby_chunk in nearby_chunks:
                nearby_id = f"{nearby_chunk.knowledge_source_id}_{nearby_chunk.chunk_index}"
                if (
                    nearby_id not in seen_chunks
                    and len(expanded_results) < limit * 2
                ):
                    expanded_results.append(nearby_chunk)
                    seen_chunks.add(nearby_id)

        # Return up to the limit, prioritizing original results
        return expanded_results[: limit * 2]

    async def get_embedding(self, text: str) -> List[float]:
        """Get OpenAI embedding for text."""
        from app.core.config import settings

        response = await self.async_openai_client.embeddings.create(
            model=settings.openai_embedding_model, input=text, dimensions=1536
        )
        return response.data[0].embedding

    def _needs_portfolio_search(self, message: str) -> bool:
        """Decide if we need to search portfolio content."""
        from app.core.config import settings

        message_lower = message.lower()
        return any(
            keyword in message_lower
            for keyword in settings.portfolio_search_keywords
        )

    def _get_search_limit(self, message: str) -> int:
        """Determine search limit based on query type."""
        message_lower = message.lower()

        # Keywords that indicate comprehensive queries
        comprehensive_keywords = [
            "all",
            "list",
            "every",
            "each",
            "show me all",
            "tell me all",
            "what are all",
            "give me all",
            "everything",
            "complete list",
            "all of",
            "every one",
            "each of",
            "full list",
            "some of",
            "and",
            "relocate",
            "relocation",
            "states",
            "work",
        ]

        # Check if this is a comprehensive query (gets doubled by nearby chunks expansion)
        if any(keyword in message_lower for keyword in comprehensive_keywords):
            return 14  # 14 * 2 = 28 total (4 per project for 7 projects)
        else:
            return 5  # 5 * 2 = 10 total for focused queries

    def _get_content_types_filter(self, message: str) -> Optional[List[str]]:
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

    async def chat_with_visitor(
        self, visitor: Visitor, conversation_id: str, message: str
    ) -> PortfolioAgentResponse:
        """Handle a chat message from a visitor with conversation memory."""

        # Get or create agent for this conversation
        if conversation_id not in self.conversation_agents:
            agent = self._create_agent_for_conversation(
                visitor, conversation_id
            )
            self.conversation_agents[conversation_id] = agent

        agent = self.conversation_agents[conversation_id]

        # Build message with context
        message_with_context = message

        # Add quote context if available
        try:
            stored_quote = await self.redis.get(
                f"conversation_quote:{conversation_id}"
            )
            if stored_quote:
                quote_context = f'\n\nNote: The visitor saw this conversation starter quote when they arrived: "{stored_quote}"\nThey might be responding to it, or they might be starting a completely different conversation. Either approach is fine! Do not reference the quote in your response unless it is relevant to the visitor\'s message.\n\n'
                message_with_context += quote_context
        except Exception as e:
            print(f"Error getting quote context: {e}")

        # Smart RAG: only search if needed
        if self._needs_portfolio_search(message):
            # Expand query for better search results
            expanded_query = await self._expand_query_for_better_search(
                message
            )
            message_embedding = await self.get_embedding(expanded_query)

            # Dynamic search limit based on query type
            search_limit = self._get_search_limit(message)

            # Content type filtering based on keywords
            content_types = self._get_content_types_filter(message)

            relevant_content = await self.search_portfolio_content(
                message_embedding,
                content_types=content_types,
                limit=search_limit,
                query_text=message,
            )

            if relevant_content:
                portfolio_context = "\nRelevant portfolio content:\n"
                for content in relevant_content:
                    portfolio_context += f"- {content.title}: {content.content_chunk or content.content}\n"

                message_with_context = (
                    f"{portfolio_context}\n\nUser message: {message}"
                )

        # Agent processes with conversation memory
        response = agent.run(
            BaseAgentInputSchema(chat_message=message_with_context)
        )

        return response

    async def chat_with_visitor_streaming(
        self,
        visitor: Visitor,
        conversation_id: str,
        message: str,
        chunk_callback=None,
        is_mobile: bool = False,
    ) -> PortfolioAgentResponse:
        """Handle a chat message with streaming response using atomic-agents."""
        import time

        start_time = time.time()
        print(f"🚀 [TIMING] Chat request started: {message[:50]}...")

        # Get or create agent for this conversation
        if conversation_id not in self.conversation_agents:
            agent = self._create_agent_for_conversation(
                visitor, conversation_id
            )
            self.conversation_agents[conversation_id] = agent

        agent = self.conversation_agents[conversation_id]
        setup_time = time.time()
        print(
            f"⚙️  [TIMING] Agent setup: {(setup_time - start_time)*1000:.0f}ms"
        )

        # Build message with context (same as regular chat)
        message_with_context = message

        # Add mobile context if needed
        if is_mobile:
            print(
                f"📱 [MOBILE] Mobile device detected - requesting concise response"
            )
            message_with_context += "\n\n[MOBILE CONTEXT: User is on mobile device - keep response extra concise (2-3 lines max for general questions)]"
        else:
            print(f"🖥️  [DESKTOP] Desktop device - normal response length")

        # Add quote context if available
        try:
            stored_quote = await self.redis.get(
                f"conversation_quote:{conversation_id}"
            )
            if stored_quote:
                quote_context = f'\n\nNote: The visitor saw this conversation starter quote when they arrived: "{stored_quote}"\nThey might be responding to it, or they might be starting a completely different conversation. Either approach is fine! Do not reference the quote in your response unless it is relevant to the visitor\'s message.\n\n'
                message_with_context += quote_context
        except Exception as e:
            print(f"Error getting quote context: {e}")

        context_time = time.time()
        print(
            f"📝 [TIMING] Context setup: {(context_time - setup_time)*1000:.0f}ms"
        )

        # Smart RAG: only search if needed
        rag_triggered = self._needs_portfolio_search(message)
        print(f"🔍 [TIMING] RAG triggered: {rag_triggered}")

        if rag_triggered:
            # Expand query for better search results
            expanded_query = await self._expand_query_for_better_search(
                message
            )

            embedding_start = time.time()
            message_embedding = await self.get_embedding(expanded_query)
            embedding_time = time.time()
            print(
                f"🧮 [TIMING] OpenAI embedding: {(embedding_time - embedding_start)*1000:.0f}ms"
            )

            # Dynamic search limit based on query type
            search_limit = self._get_search_limit(message)

            # Content type filtering based on keywords
            content_types = self._get_content_types_filter(message)

            search_start = time.time()
            relevant_content = await self.search_portfolio_content(
                message_embedding,
                content_types=content_types,
                limit=search_limit,
                query_text=message,
            )
            search_time = time.time()
            print(
                f"🔎 [TIMING] Vector search: {(search_time - search_start)*1000:.0f}ms"
            )

            if relevant_content:
                portfolio_context = "\nRelevant portfolio content:\n"
                for i, content in enumerate(relevant_content, 1):
                    chunk_preview = (content.content_chunk or content.content)[
                        :100
                    ]
                    print(f"📄 [RAG-{i}] {content.title}: {chunk_preview}...")
                    portfolio_context += f"- {content.title}: {content.content_chunk or content.content}\n"

                message_with_context = (
                    f"{portfolio_context}\n\nUser message: {message}"
                )
                print(
                    f"📋 [RAG-TOTAL] Sending {len(relevant_content)} content pieces to AI"
                )
                print(
                    f"📚 [TIMING] Found {len(relevant_content)} relevant content pieces"
                )
        else:
            print(f"⏭️  [TIMING] Skipping RAG - no relevant keywords")

        # Use atomic-agents streaming functionality
        try:
            # Create input schema for agent processing (with RAG context)
            input_data = BaseAgentInputSchema(
                chat_message=message_with_context
            )

            # Prepare original user message (without RAG context) for memory storage
            original_user_input = BaseAgentInputSchema(
                chat_message=message  # Original message only
            )

            # Log conversation memory to check for RAG compounding
            memory_history = agent.memory.get_history()
            if memory_history:
                total_memory_chars = sum(
                    len(str(msg)) for msg in memory_history
                )
                print(
                    f"🧠 [MEMORY] Conversation has {len(memory_history)} stored messages"
                )
                print(
                    f"🧠 [MEMORY] Total memory size: {total_memory_chars:,} characters"
                )

                # Check if previous messages contain RAG content
                for i, msg in enumerate(
                    memory_history[-3:]
                ):  # Last 3 messages
                    msg_str = str(msg)
                    has_rag = (
                        "Relevant portfolio content:" in msg_str
                        or "portfolio content:" in msg_str
                    )
                    print(
                        f"🧠 [MEMORY-{i}] Message {len(msg_str)} chars, contains RAG: {has_rag}"
                    )
                    if has_rag and len(msg_str) > 1000:
                        print(
                            f"⚠️ [MEMORY-COMPOUND] Previous message contains RAG content!"
                        )
            else:
                print(f"🧠 [MEMORY] No conversation memory found")

            # Log request size details
            message_chars = len(message_with_context)
            message_words = len(message_with_context.split())
            print(
                f"📏 [REQUEST-SIZE] Message length: {message_chars:,} characters, {message_words:,} words"
            )
            print(
                f"📏 [REQUEST-SIZE] Original query: '{message}' ({len(message)} chars)"
            )
            if rag_triggered:
                original_chars = len(message)
                context_chars = message_chars - original_chars
                print(
                    f"📏 [REQUEST-SIZE] Added context: {context_chars:,} characters ({context_chars/message_chars*100:.1f}% of total)"
                )

            ai_start = time.time()
            print(
                f"🤖 [TIMING] Starting {self.settings.ai_provider.upper()} call via atomic-agents..."
            )
            print(f"📋 [TIMING] Using model: {self._get_current_model()}")

            # MEMORY MANAGEMENT: Prevent RAG compounding by storing original message first
            memory_length_before = len(agent.memory.history)

            # 1. Store user's original message (no RAG) in memory FIRST
            agent.memory.add_message("user", original_user_input)

            # 2. Process with RAG-enhanced context (atomic-agents will try to store this too)
            result = agent.run(input_data)

            # 3. Clean up memory to remove any RAG-enhanced duplicates
            memory_length_after = len(agent.memory.history)
            messages_added = memory_length_after - memory_length_before

            print(
                f"🧠 [MEMORY-DEBUG] Messages before: {memory_length_before}, after: {memory_length_after}, added: {messages_added}"
            )

            # If agent.run() added extra messages, remove them (they contain RAG context)
            if messages_added > 2:  # Should only add user + assistant
                excess_messages = messages_added - 2
                print(
                    f"🗑️ [MEMORY-CLEANUP] Removing {excess_messages} excess messages with RAG context"
                )
                for _ in range(excess_messages):
                    agent.memory.history.pop(
                        -2
                    )  # Remove user messages with RAG context

            # 4. Update AI response with RAG summary if present
            if hasattr(result, "rag_summary") and result.rag_summary:
                print(
                    f"💾 [MEMORY-SAVE] Response includes RAG summary: {result.rag_summary[:100]}..."
                )

                # Find and update the assistant message
                if (
                    agent.memory.history
                    and agent.memory.history[-1].role == "assistant"
                ):
                    # Create enhanced response with RAG summary for memory
                    enhanced_response = PortfolioAgentResponse(
                        response=result.response,
                        rag_summary=result.rag_summary,
                        visitor_notes_update=getattr(
                            result, "visitor_notes_update", None
                        ),
                        is_off_topic=getattr(result, "is_off_topic", False),
                    )
                    # Update the content in memory
                    agent.memory.history[-1].content = enhanced_response
                    print(
                        f"💾 [MEMORY-UPDATE] Updated AI response with RAG summary"
                    )

                print(
                    f"📊 [CONTEXT-EFFICIENCY] RAG context ~{len(message_with_context)} chars → summary ~{len(result.rag_summary)} chars"
                )
            else:
                print(
                    f"💾 [MEMORY-SAVE] No RAG context used - standard memory storage"
                )

            # 5. Final memory validation
            final_memory = agent.memory.get_history()
            for i, msg in enumerate(
                final_memory[-2:]
            ):  # Check last 2 messages
                msg_str = str(msg)
                has_rag = "Relevant portfolio content:" in msg_str
                if has_rag:
                    print(
                        f"⚠️ [MEMORY-LEAK] Message {i} still contains RAG content!"
                    )
                else:
                    print(f"✅ [MEMORY-CLEAN] Message {i} is RAG-free")

            ai_end = time.time()
            print(
                f"✅ [TIMING] {self.settings.ai_provider.upper()} response received: {(ai_end - ai_start)*1000:.0f}ms"
            )

            # Extract response text
            if hasattr(result, "response"):
                response_text = result.response
                response = result
            elif hasattr(result, "chat_message"):
                response_text = result.chat_message
                response = PortfolioAgentResponse(
                    response=response_text,
                    visitor_notes_update=None,
                    is_off_topic=False,
                )
            else:
                response_text = str(result)
                response = PortfolioAgentResponse(
                    response=response_text,
                    visitor_notes_update=None,
                    is_off_topic=False,
                )

            # LOG FULL AI RESPONSE FOR DEBUGGING
            print("=" * 80)
            print("🤖 [FULL AI RESPONSE] Raw text from AI:")
            print("=" * 80)
            print(
                repr(response_text)
            )  # Using repr to see actual \n characters
            print("=" * 80)
            print("🖼️  [FULL AI RESPONSE] Formatted for display:")
            print("=" * 80)
            print(response_text)
            print("=" * 80)

            # Send complete response as single chunk
            send_start = time.time()
            if chunk_callback:
                await chunk_callback(response_text)
            send_end = time.time()
            print(
                f"📤 [TIMING] Response sent to frontend: {(send_end - send_start)*1000:.0f}ms"
            )

            total_time = time.time()
            print(
                f"🏁 [TIMING] TOTAL REQUEST TIME: {(total_time - start_time)*1000:.0f}ms"
            )
            print(
                f"📊 [TIMING] Response length: {len(response_text)} characters"
            )

            # Check if response meets mobile optimization
            if is_mobile:
                line_count = response_text.count("\n") + 1
                print(
                    f"📱 [MOBILE CHECK] Response has {line_count} lines (target: ≤3)"
                )
                if line_count <= 3:
                    print(f"✅ [MOBILE] Response optimized for mobile")
                else:
                    print(f"⚠️  [MOBILE] Response may be too long for mobile")

        except Exception as e:
            print(f"Error with atomic-agents: {e}")
            error_response = "I'm sorry, I encountered an error processing your message. Please try again."

            # Send error message as a chunk
            if chunk_callback:
                await chunk_callback(error_response)

            # Create error response
            response = PortfolioAgentResponse(
                response=error_response,
                visitor_notes_update=None,
                is_off_topic=False,
            )

        return response

    async def end_conversation(self, conversation_id: str):
        """End a conversation and clean up memory."""
        if conversation_id not in self.conversation_agents:
            return

        # Clean up conversation memory
        del self.conversation_agents[conversation_id]

    async def update_visitor_notes(
        self, visitor: Visitor, new_notes: str
    ) -> None:
        """Update visitor's notes."""
        if visitor.notes_by_agent:
            visitor.notes_by_agent += f"\n{new_notes}"
        else:
            visitor.notes_by_agent = new_notes

        await self.db.commit()
