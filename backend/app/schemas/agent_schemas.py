"""Custom schemas for the Portfolio AI Agent following Atomic Agents patterns."""

from typing import Optional
from pydantic import Field
from atomic_agents.lib.base.base_io_schema import BaseIOSchema


class PortfolioAgentInputSchema(BaseIOSchema):
    """
    Input schema for portfolio agent conversations with visitor context.

    This schema captures the user's message along with optional context
    that helps the agent provide more personalized responses.
    """

    chat_message: str = Field(
        ...,
        description="The user's message or question about Steven's portfolio, experience, or projects",
    )

    visitor_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for the visitor to maintain conversation context",
    )

    conversation_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for this conversation thread",
    )

    is_mobile: bool = Field(
        default=False,
        description="Whether the user is on a mobile device (affects response formatting)",
    )


class PortfolioAgentOutputSchema(BaseIOSchema):
    """
    Output schema for portfolio agent responses with rich metadata.

    This schema provides structured responses that include the main message
    plus additional metadata for conversation management and analytics.
    """

    response: str = Field(
        ..., description="The agent's response to the user's message"
    )

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

    confidence_score: Optional[float] = Field(
        default=None,
        description="Confidence score for the response accuracy (0.0-1.0)",
        ge=0.0,
        le=1.0,
    )

    search_triggered: bool = Field(
        default=False,
        description="Whether portfolio content search was triggered for this response",
    )
