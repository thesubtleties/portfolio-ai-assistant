"""Portfolio AI Agent service using atomic-agents framework."""

from typing import List, Optional
import instructor
import openai
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

    def __init__(self):
        """Initialize the portfolio agent service."""
        # Set up OpenAI client with Instructor
        from app.core.config import settings
        
        self.client = instructor.from_openai(openai.OpenAI(api_key=settings.openai_api_key))
        
        # Store conversation agents: {conversation_id: BaseAgent}
        self.conversation_agents = {}

    def _get_system_prompt_generator(self):
        """Get the system prompt generator for the portfolio agent."""
        from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator
        
        return SystemPromptGenerator(
            background=[
                "You are Steven's AI portfolio assistant.",
                "You help visitors learn about Steven's experience, skills, and projects.",
                "You maintain conversation context and remember visitor interests."
            ],
            steps=[
                "Analyze the visitor's message and any provided context.",
                "Use relevant portfolio content when discussing Steven's work.",
                "Provide helpful, conversational responses about Steven's background.",
                "Remember important details about the visitor for future interactions."
            ],
            output_instructions=[
                "Be conversational and helpful in your responses.",
                "When discussing Steven's work, reference specific projects or skills.",
                "Keep responses concise but informative.",
                "If you can't find specific information, say so honestly."
            ]
        )
    
    def _create_agent_for_conversation(self, visitor, conversation_id: str) -> BaseAgent:
        """Create a new agent instance for a conversation."""
        memory = AgentMemory()
        
        # Add initial greeting message to establish conversation context
        initial_message = PortfolioAgentResponse(
            response="Hello! I'm Steven's AI portfolio assistant. How can I help you learn about his experience, skills, and projects?",
            visitor_notes_update=None
        )
        memory.add_message("assistant", initial_message)
        
        # Create agent with conversation-specific memory
        agent = BaseAgent(
            config=BaseAgentConfig(
                client=self.client,
                model="gpt-4o-mini",
                memory=memory,
                system_prompt_generator=self._get_system_prompt_generator(),
                output_schema=PortfolioAgentResponse
            )
        )
        
        return agent

    async def search_portfolio_content(
        self,
        session: AsyncSession,
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

        result = await session.execute(query)
        return result.scalars().all()

    async def get_embedding(self, text: str) -> List[float]:
        """Get OpenAI embedding for text."""
        # This is a placeholder - you'll need to implement actual embedding generation
        # Using OpenAI's text-embedding-3-small model
        from app.core.config import settings
        
        client = openai.OpenAI(api_key=settings.openai_api_key)
        response = client.embeddings.create(
            model="text-embedding-3-small", input=text, dimensions=1536
        )
        return response.data[0].embedding

    def _needs_portfolio_search(self, message: str) -> bool:
        """Decide if we need to search portfolio content."""
        portfolio_keywords = [
            "project", "experience", "skill", "work", "built", "technology",
            "react", "python", "database", "show me", "tell me about",
            "portfolio", "development", "programming", "code", "app"
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in portfolio_keywords)
    
    async def chat_with_visitor(
        self,
        session: AsyncSession,
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
        
        # Smart RAG: only search if needed
        if self._needs_portfolio_search(message):
            message_embedding = await self.get_embedding(message)
            relevant_content = await self.search_portfolio_content(
                session, message_embedding, limit=3
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
        self, session: AsyncSession, visitor: Visitor, new_notes: str
    ) -> None:
        """Update visitor's notes."""
        if visitor.notes_by_agent:
            visitor.notes_by_agent += f"\n{new_notes}"
        else:
            visitor.notes_by_agent = new_notes

        await session.commit()
