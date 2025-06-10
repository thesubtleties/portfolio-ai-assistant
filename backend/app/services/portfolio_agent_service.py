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
        # Use default output schema for streaming compatibility
        agent = BaseAgent(
            config=BaseAgentConfig(
                client=self.client,
                model=self._get_current_model(),
                memory=memory,
                system_prompt_generator=self._get_system_prompt_generator(),
                # output_schema=PortfolioAgentResponse,  # Commented out for streaming
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
            return await self._semantic_search(query_embedding, content_types, limit)
        elif strategy == "pure_content":
            return await self._pure_content_search(query_embedding, content_types, limit)
        else:  # hybrid
            return await self._hybrid_search(query_embedding, content_types, limit)
    
    async def _semantic_search(self, query_embedding: List[float], content_types: Optional[List[str]], limit: int) -> List[PortfolioContent]:
        """Search using semantic embeddings only."""
        query = select(PortfolioContent).where(
            PortfolioContent.content_metadata['embedding_type'].astext == 'semantic'
        )
        
        if content_types:
            query = query.where(PortfolioContent.content_type.in_(content_types))
        
        query = query.order_by(
            PortfolioContent.embedding.cosine_distance(query_embedding)
        ).limit(limit)
        
        result = await self.db.execute(query)
        initial_results = result.scalars().all()
        
        # Add nearby chunks for better context
        return await self._expand_with_nearby_chunks(initial_results, limit)
    
    async def _pure_content_search(self, query_embedding: List[float], content_types: Optional[List[str]], limit: int) -> List[PortfolioContent]:
        """Search using pure content embeddings only."""
        query = select(PortfolioContent).where(
            PortfolioContent.content_metadata['embedding_type'].astext == 'pure_content'
        )
        
        if content_types:
            query = query.where(PortfolioContent.content_type.in_(content_types))
        
        query = query.order_by(
            PortfolioContent.embedding.cosine_distance(query_embedding)
        ).limit(limit)
        
        result = await self.db.execute(query)
        initial_results = result.scalars().all()
        
        # Add nearby chunks for better context
        return await self._expand_with_nearby_chunks(initial_results, limit)
    
    async def _hybrid_search(self, query_embedding: List[float], content_types: Optional[List[str]], limit: int) -> List[PortfolioContent]:
        """Hybrid search combining both embedding types with intelligent merging."""
        # Get results from both methods
        semantic_query = select(PortfolioContent).where(
            PortfolioContent.content_metadata['embedding_type'].astext == 'semantic'
        )
        pure_query = select(PortfolioContent).where(
            PortfolioContent.content_metadata['embedding_type'].astext == 'pure_content'
        )
        
        if content_types:
            semantic_query = semantic_query.where(PortfolioContent.content_type.in_(content_types))
            pure_query = pure_query.where(PortfolioContent.content_type.in_(content_types))
        
        semantic_query = semantic_query.order_by(
            PortfolioContent.embedding.cosine_distance(query_embedding)
        ).limit(limit * 2)
        
        pure_query = pure_query.order_by(
            PortfolioContent.embedding.cosine_distance(query_embedding)
        ).limit(limit * 2)
        
        semantic_results = (await self.db.execute(semantic_query)).scalars().all()
        pure_results = (await self.db.execute(pure_query)).scalars().all()
        
        # Merge and deduplicate
        return self._merge_and_deduplicate(semantic_results, pure_results, limit)
    
    def _merge_and_deduplicate(self, semantic_results: List[PortfolioContent], pure_results: List[PortfolioContent], limit: int) -> List[PortfolioContent]:
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
        """Classify query type to inform search strategy."""
        query_lower = query.lower()
        
        # Technical framework/architecture queries
        if any(tech in query_lower for tech in [
            'fastapi', 'react', 'architecture', 'pattern', 'implementation',
            'framework', 'design', 'approach', 'methodology'
        ]):
            return 'technical_conceptual'
        
        # Broad overview queries
        elif any(broad in query_lower for broad in [
            'all projects', 'tell me about', 'overview', 'everything',
            'what has steven', 'show me all', 'complete list'
        ]):
            return 'broad_overview'
        
        # Specific content searches
        elif any(specific in query_lower for specific in [
            'code example', 'database', 'what databases', 'which database',
            'technologies', 'tools', 'languages', 'specific'
        ]):
            return 'specific_content'
        
        # Personal/background queries
        elif any(personal in query_lower for personal in [
            'background', 'personal', 'interests', 'experience', 'career'
        ]):
            return 'personal_background'
        
        return 'general'
    
    def _choose_search_strategy(self, query_type: str) -> str:
        """Choose optimal search strategy based on query type."""
        strategy_map = {
            'technical_conceptual': 'semantic',    # Benefits from contextual understanding
            'broad_overview': 'hybrid',            # Needs diversity and coverage
            'specific_content': 'pure_content',    # Direct content matching
            'personal_background': 'pure_content', # Often in descriptive sections
            'general': 'hybrid'                    # Safe fallback
        }
        
        return strategy_map.get(query_type, 'hybrid')
    
    async def _expand_with_nearby_chunks(self, initial_results: List[PortfolioContent], limit: int) -> List[PortfolioContent]:
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
            nearby_query = select(PortfolioContent).where(
                PortfolioContent.knowledge_source_id == source_id,
                PortfolioContent.chunk_index.between(current_index - 4, current_index + 4),
                PortfolioContent.chunk_index != current_index
            ).order_by(PortfolioContent.chunk_index)
            
            nearby_result = await self.db.execute(nearby_query)
            nearby_chunks = nearby_result.scalars().all()
            
            # Add nearby chunks that aren't already included
            for nearby_chunk in nearby_chunks:
                nearby_id = f"{nearby_chunk.knowledge_source_id}_{nearby_chunk.chunk_index}"
                if nearby_id not in seen_chunks and len(expanded_results) < limit * 2:
                    expanded_results.append(nearby_chunk)
                    seen_chunks.add(nearby_id)
        
        # Return up to the limit, prioritizing original results
        return expanded_results[:limit * 2]

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
        ]

        # Check if this is a comprehensive query
        if any(keyword in message_lower for keyword in comprehensive_keywords):
            return 40  # Much higher limit for comprehensive queries
        else:
            return 15  # Significantly increased from 3 to 15

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
            ]
        ):
            content_types.append("project")

        # Experience/career keywords
        if any(
            word in message_lower
            for word in [
                "experience",
                "career",
                "job",
                "work history",
                "worked",
                "leadership",
            ]
        ):
            content_types.append("experience")

        # Personal/about keywords
        if any(
            word in message_lower
            for word in [
                "about",
                "personal",
                "background",
                "interests",
                "hobbies",
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
            message_embedding = await self.get_embedding(message)

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
            embedding_start = time.time()
            message_embedding = await self.get_embedding(message)
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
            )
            search_time = time.time()
            print(
                f"🔎 [TIMING] Vector search: {(search_time - search_start)*1000:.0f}ms"
            )

            if relevant_content:
                portfolio_context = "\nRelevant portfolio content:\n"
                for content in relevant_content:
                    portfolio_context += f"- {content.title}: {content.content_chunk or content.content}\n"

                message_with_context = (
                    f"{portfolio_context}\n\nUser message: {message}"
                )
                print(
                    f"📚 [TIMING] Found {len(relevant_content)} relevant content pieces"
                )
        else:
            print(f"⏭️  [TIMING] Skipping RAG - no relevant keywords")

        # Use atomic-agents streaming functionality
        try:
            # Create input schema for agent
            input_data = BaseAgentInputSchema(
                chat_message=message_with_context
            )

            ai_start = time.time()
            print(
                f"🤖 [TIMING] Starting {self.settings.ai_provider.upper()} call via atomic-agents..."
            )
            print(f"📋 [TIMING] Using model: {self._get_current_model()}")

            # Use synchronous execution to avoid async generator issues
            result = agent.run(input_data)

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
            print(repr(response_text))  # Using repr to see actual \n characters
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
