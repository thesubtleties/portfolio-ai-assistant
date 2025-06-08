import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Database settings
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str  # Use existing DATABASE_URL from .env

    # Database connection pool settings
    db_pool_size: int = 20  # Number of connections to maintain in pool
    db_max_overflow: int = 10  # Maximum overflow connections allowed
    db_pool_timeout: int = 30  # Seconds to wait before timing out
    db_pool_recycle: int = 3600  # Recycle connections after 1 hour
    db_echo: bool = False  # Set to True for SQL query logging in development

    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_decode_responses: bool = (
        True  # Decode to strings for easier handling
    )
    redis_max_connections: int = 50

    # OpenAI settings
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"  # Default AI model for conversations
    openai_embedding_model: str = "text-embedding-3-small"  # Embedding model

    # Agent configuration
    agent_name: str = "Steven's AI portfolio assistant"
    agent_background: list[str] = [
        "You are Steven's AI portfolio assistant.",
        "You help visitors learn about Steven's experience, skills, and projects.",
        "You maintain conversation context and remember visitor interests.",
    ]
    agent_steps: list[str] = [
        "Analyze the visitor's message and any provided context.",
        "Use relevant portfolio content when discussing Steven's work.",
        "Provide helpful, conversational responses about Steven's background.",
        "Remember important details about the visitor for future interactions.",
    ]
    agent_output_instructions: list[str] = [
        "Be conversational and helpful in your responses.",
        "When discussing Steven's work, reference specific projects or skills.",
        "Keep responses concise but informative.",
        "If you can't find specific information, say so honestly.",
    ]
    agent_greeting: str = (
        "Hello! I'm Steven's AI portfolio assistant. How can I help you learn about his experience, skills, and projects?"
    )

    # Portfolio search keywords for RAG triggering
    portfolio_search_keywords: list[str] = [
        # Technical keywords
        "project",
        "experience",
        "skill",
        "work",
        "built",
        "technology",
        "react",
        "python",
        "database",
        "show me",
        "tell me about",
        "portfolio",
        "development",
        "programming",
        "code",
        "app",
        # Personal & background keywords
        "about",
        "background",
        "hobby",
        "hobbies",
        "interests",
        "personal",
        "travel",
        "food",
        "entertainment",
        "gaming",
        "adventures",
        "relocation",
        "move",
        "location",
        "where",
        "live",
        "based",
        # Career & experience keywords
        "career",
        "transition",
        "leadership",
        "management",
        "team",
        "achievements",
        "accomplishments",
        "highlights",
        "story",
        # Question patterns
        "who is",
        "what does",
        "how did",
        "when did",
        "why did",
    ]

    # Application settings
    environment: str = "development"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:4321"]  # Astro dev server

    # WebSocket settings
    ws_heartbeat_interval: int = 30  # Seconds between heartbeats
    ws_connection_timeout: int = 600  # 10 minutes max connection time

    def get_async_database_url(self) -> str:
        """Convert sync database URL to async (asyncpg)."""
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
        return self.database_url

    class Config:
        """Pydantic settings configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = (
            "ignore"  # Ignore extra environment variables like COMPOSE_FILE
        )


settings = Settings()
