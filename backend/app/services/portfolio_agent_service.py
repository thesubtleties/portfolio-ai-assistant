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

from app.models.database import Visitor
from app.services.security.content_safety_service import ContentSafetyService
from app.services.search.portfolio_search_service import PortfolioSearchService
from app.schemas.agent_schemas import (
    PortfolioAgentInputSchema,
    PortfolioAgentOutputSchema,
)

# Keep the old name for backwards compatibility
PortfolioAgentResponse = PortfolioAgentOutputSchema


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

        # Initialize content safety service
        self.content_safety_service = ContentSafetyService(
            safety_patterns=settings.content_safety_patterns,
            safety_message=settings.content_safety_message,
        )

        # Initialize portfolio search service
        self.search_service = PortfolioSearchService(db)

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

    def _check_content_safety(
        self, message: str
    ) -> tuple[bool, Optional[str]]:
        """
        Check if message contains content that could violate API terms.

        Returns:
            tuple[bool, Optional[str]]: (is_safe, violation_reason)
        """
        return self.content_safety_service.check_content_safety(message)

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
                input_schema=PortfolioAgentInputSchema,
                output_schema=PortfolioAgentOutputSchema,
            )
        )

        return agent

    async def get_embedding(self, text: str) -> List[float]:
        """Get OpenAI embedding for text."""
        from app.core.config import settings

        response = await self.async_openai_client.embeddings.create(
            model=settings.openai_embedding_model, input=text, dimensions=1536
        )
        return response.data[0].embedding

    async def chat_with_visitor(
        self, visitor: Visitor, conversation_id: str, message: str
    ) -> PortfolioAgentResponse:
        """Handle a chat message from a visitor with conversation memory."""

        # Content safety filter - check BEFORE any API calls
        is_safe, safety_message = self._check_content_safety(message)
        if not is_safe:
            print(f"🚨 [SAFETY] Message blocked by content filter")
            return PortfolioAgentResponse(
                response=safety_message,
                is_off_topic=True,  # Mark as off-topic for rate limiting
                visitor_notes_update=None,
                rag_summary=None,
            )

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
                quote_context = f'\n\nNote: The visitor saw this conversation starter quote when they arrived: "{stored_quote}"\nIf they ask about "the quote" or reference it directly, this is the quote they are referring to. You should explain or discuss this specific quote when asked. Otherwise, do not reference it unless relevant.\n\n'
                message_with_context += quote_context
        except Exception as e:
            print(f"Error getting quote context: {e}")

        # Smart RAG: only search if needed
        if self.search_service.needs_portfolio_search(message):
            # Expand query for better search results
            expanded_query = (
                await self.search_service.expand_query_for_better_search(
                    message
                )
            )
            message_embedding = await self.get_embedding(expanded_query)

            # Dynamic search limit based on query type
            search_limit = self.search_service.get_search_limit(message)

            # Content type filtering based on keywords
            content_types = self.search_service.detect_content_types(message)

            relevant_content = (
                await self.search_service.search_portfolio_content(
                    message_embedding,
                    content_types=content_types,
                    limit=search_limit,
                    query_text=message,
                )
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
        viewport_height: int = 0,
        is_laptop_screen: bool = False,
    ) -> PortfolioAgentResponse:
        """Handle a chat message with streaming response using atomic-agents."""
        import time

        start_time = time.time()
        print(f"🚀 [TIMING] Chat request started: {message[:50]}...")

        # Content safety filter - check BEFORE any API calls
        is_safe, safety_message = self._check_content_safety(message)
        if not is_safe:
            print(f"🚨 [SAFETY] Message blocked by content filter")

            # Send the safety message through the chunk callback if provided
            if chunk_callback:
                await chunk_callback(safety_message)

            return PortfolioAgentResponse(
                response=safety_message,
                is_off_topic=True,  # Mark as off-topic for rate limiting
                visitor_notes_update=None,
                rag_summary=None,
            )

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
            message_with_context += "\n\n[MOBILE CONTEXT: User is on mobile device - keep response extra concise (2-3 lines max for general questions or a SHORT list of concise bullet points)]"
        elif is_laptop_screen:
            print(
                f"💻 [LAPTOP] Laptop/MacBook screen detected (height: {viewport_height}px) - requesting shorter response"
            )
            message_with_context += f"\n\n[LAPTOP CONTEXT: User is on a laptop/MacBook with limited screen height ({viewport_height}px). Keep responses moderately concise - aim for 4-6 lines max for general questions, or a SHORT list of concise bullet points. Avoid lengthy explanations.]"
        else:
            print(f"🖥️  [DESKTOP] Desktop device - normal response length")

        # Add quote context if available
        try:
            stored_quote = await self.redis.get(
                f"conversation_quote:{conversation_id}"
            )
            if stored_quote:
                quote_context = f'\n\nNote: The visitor saw this conversation starter quote when they arrived: "{stored_quote}"\nIf they ask about "the quote" or reference it directly, this is the quote they are referring to. You should explain or discuss this specific quote when asked. Otherwise, do not reference it unless relevant.\n\n'
                message_with_context += quote_context
        except Exception as e:
            print(f"Error getting quote context: {e}")

        context_time = time.time()
        print(
            f"📝 [TIMING] Context setup: {(context_time - setup_time)*1000:.0f}ms"
        )

        # Smart RAG: only search if needed
        rag_triggered = self.search_service.needs_portfolio_search(message)
        print(f"🔍 [TIMING] RAG triggered: {rag_triggered}")

        if rag_triggered:
            # Expand query for better search results
            expanded_query = (
                await self.search_service.expand_query_for_better_search(
                    message
                )
            )

            embedding_start = time.time()
            message_embedding = await self.get_embedding(expanded_query)
            embedding_time = time.time()
            print(
                f"🧮 [TIMING] OpenAI embedding: {(embedding_time - embedding_start)*1000:.0f}ms"
            )

            # Dynamic search limit based on query type
            search_limit = self.search_service.get_search_limit(message)

            # Content type filtering based on keywords
            content_types = self.search_service.detect_content_types(message)

            search_start = time.time()
            relevant_content = (
                await self.search_service.search_portfolio_content(
                    message_embedding,
                    content_types=content_types,
                    limit=search_limit,
                    query_text=message,
                )
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
