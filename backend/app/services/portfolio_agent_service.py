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


class PortfolioAgentService:
    """Service for handling AI agent conversations about the portfolio."""

    def __init__(self, db: AsyncSession, redis_client):
        """Initialize the portfolio agent service."""
        self.db = db
        self.redis = redis_client
        
        # Set up OpenAI client with Instructor
        from app.core.config import settings
        
        self.async_openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.client = instructor.from_openai(openai.OpenAI(api_key=settings.openai_api_key))
        
        # Store conversation agents: {conversation_id: BaseAgent}
        self.conversation_agents = {}

    def _get_system_prompt_generator(self):
        """Get the system prompt generator for the portfolio agent."""
        from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator
        from app.core.config import settings
        
        return SystemPromptGenerator(
            background=settings.agent_background,
            steps=settings.agent_steps,
            output_instructions=settings.agent_output_instructions
        )
    
    def _create_agent_for_conversation(self, visitor, conversation_id: str) -> BaseAgent:
        """Create a new agent instance for a conversation."""
        memory = AgentMemory()
        
        # Add initial greeting message to establish conversation context
        from app.core.config import settings
        initial_message = PortfolioAgentResponse(
            response=settings.agent_greeting,
            visitor_notes_update=None
        )
        memory.add_message("assistant", initial_message)
        
        # Create agent with conversation-specific memory
        agent = BaseAgent(
            config=BaseAgentConfig(
                client=self.client,
                model=settings.openai_model,
                memory=memory,
                system_prompt_generator=self._get_system_prompt_generator(),
                output_schema=PortfolioAgentResponse
            )
        )
        
        return agent

    async def search_portfolio_content(
        self,
        query_embedding: List[float],
        content_type: Optional[str] = None,
        limit: int = 3,
    ) -> List[PortfolioContent]:
        """Search portfolio content using vector similarity."""
        query = select(PortfolioContent)

        # Filter by content type if specified
        if content_type:
            query = query.where(PortfolioContent.content_type == content_type)

        # Order by cosine similarity
        query = query.order_by(
            PortfolioContent.embedding.cosine_distance(query_embedding)
        ).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

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
        return any(keyword in message_lower for keyword in settings.portfolio_search_keywords)
    
    async def chat_with_visitor(
        self,
        visitor: Visitor,
        conversation_id: str,
        message: str
    ) -> PortfolioAgentResponse:
        """Handle a chat message from a visitor with conversation memory."""
        
        # Get or create agent for this conversation
        if conversation_id not in self.conversation_agents:
            agent = self._create_agent_for_conversation(visitor, conversation_id)
            self.conversation_agents[conversation_id] = agent
        
        agent = self.conversation_agents[conversation_id]
        
        # Build message with context
        message_with_context = message
        
        # Add quote context if available
        try:
            stored_quote = await self.redis.get(f"conversation_quote:{conversation_id}")
            if stored_quote:
                quote_context = f"\n\nNote: The visitor saw this conversation starter quote when they arrived: \"{stored_quote}\"\nThey might be responding to it, or they might be starting a completely different conversation. Either approach is fine!"
                message_with_context += quote_context
        except Exception as e:
            print(f"Error getting quote context: {e}")
        
        # Smart RAG: only search if needed
        if self._needs_portfolio_search(message):
            message_embedding = await self.get_embedding(message)
            relevant_content = await self.search_portfolio_content(
                message_embedding, limit=3
            )
            
            if relevant_content:
                portfolio_context = "\nRelevant portfolio content:\n"
                for content in relevant_content:
                    portfolio_context += f"- {content.title}: {content.content_chunk or content.content}\n"
                
                message_with_context = f"{portfolio_context}\n\nUser message: {message}"
        
        # Agent processes with conversation memory
        response = agent.run(
            BaseAgentInputSchema(chat_message=message_with_context)
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
