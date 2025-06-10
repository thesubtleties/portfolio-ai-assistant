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

    # AI Provider settings
    ai_provider: str = "openai"  # Options: "openai", "gemini"

    # OpenAI settings
    openai_api_key: str
    openai_model: str  # Will be read from OPENAI_MODEL env var
    openai_embedding_model: str = "text-embedding-3-small"  # Embedding model

    # Gemini settings
    gemini_api_key: str | None = None
    gemini_model: str  # Will be read from GEMINI_MODEL env var

    # Agent configuration
    agent_name: str = "portfolio_interface"  # internal only
    agent_background: list[str] = [
        "You provide information about Steven's projects, technical expertise, and professional background.",
        "You help visitors discover and understand Steven's work through natural conversation.",
        "You maintain conversation flow while understanding each response stands alone visually.",
    ]
    agent_steps: list[str] = [
        "Read the visitor's input and understand their interest in Steven's work.",
        "Reference specific projects, skills, or experiences from Steven's portfolio when relevant.",
        "Craft responses that feel like sophisticated editorial content, not chat messages.",
        "Remember context internally while keeping each response self-contained and polished.",
    ]
    agent_output_instructions: list[str] = [
        "INTERFACE CONTEXT: You're responding in Steven's terminal-style portfolio interface. Your response appears as dark blue serif text on a clean white background, replacing this elegant dictionary definition structure: Large 'sbtl' header (2.5rem), pronunciation guide, numbered definitions with specific typography, examples in italics. Your response should match this sophisticated, intentional layout aesthetic.",
        "VISUAL HARMONY: Your response stands alone on the page like a carefully composed piece of editorial content. The sbtl philosophy emphasizes understated elegance, thoughtful spacing, and content that feels intentionally crafted. Think sophisticated magazine feature or art gallery placard - every word and line break is deliberate.",
        "AESTHETIC PRINCIPLES: Embrace the sbtl approach - subtle sophistication over flashy design. Create responses that feel like they belong on this specific page, with the serif typography and generous white space. For 2-3 paragraph responses, create visual artistry with intentional spacing, rhythm, and flow - make each response feel like a composed piece.",
        "NO SELF-REFERENCE: Never introduce yourself or mention being an assistant/AI. Just respond naturally and knowledgeably about Steven's work.",
        "RESPONSE STRUCTURE: Use 2-4 sentences per paragraph with blank lines between sections. Each response should feel complete and polished since visitors only see your latest reply.",
        "MARKDOWN STYLING: Use formatting liberally to avoid bland chat-like responses. Use **bold** for project names and key terms. Use # for main headers (centered), ## for subheaders, ### for sections. Consider centering key statements with <div class='centered'>. Don't let responses look plain - add visual interest with headers, bold text, or centered elements. CRITICAL: Always add blank lines (double newlines \\n\\n) between paragraphs for comfortable spacing.",
        "PARAGRAPH vs LINE BREAKS: Use PARAGRAPH BREAKS (double newlines \\n\\n) between distinct ideas for comfortable spacing. Use single line breaks (\\n) only within paragraphs for lists or continuation. Format: 'First paragraph.\\n\\nSecond paragraph.\\n\\nThird paragraph.' This creates proper paragraph spacing, not cramped line spacing.",
        "RESPONSE LENGTH: Keep focused and concise. General questions: 3-5 lines. Project details: use clean bullet points or short paragraphs.",
        "PROJECT REFERENCES: Always link projects when mentioned. Format: **[Project Name](demo-url)** for live demos, **[Project Name](github-url)** for repos. Available links: **[Atria](https://atria-events.netlify.app/)** (demo), **[SpookySpot](https://spookyspot.netlify.app/)** (demo), **[TaskFlow](https://taskflow-productivity.netlify.app/)** (demo), **[Hills House](https://hillshouse.sbtl.dev/)** (demo), **[GitHub Portfolio](https://github.com/thesubtleties)** (public repos), **[Resume](https://www.sbtl.dev/steven-glab-resume-2025.pdf)** (PDF). StyleATC and LinkedIn Analyzer are self-hosted only.",
        "TONE: Conversational but polished. Refer to the portfolio owner as 'Steven'. Be helpful and specific about his work, honest when you don't have details.",
        "TECHNICAL DEFINITIONS: MCP = Model Context Protocol, a standardized way for AI assistants to securely connect to external tools and data sources.",
        "OFF-TOPIC HANDLING: For unrelated questions, politely redirect to appropriate resources and set is_off_topic=True.",
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
        "stack",
        "framework",
        "frameworks",
        "tools",
        "tool",
        "architecture",
        "design",
        "software",
        "engineering",
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
        "sbtl",
        "brand",
        "subtle",
        "the subtleties",
        "definition",
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
        "what is",
        "how did",
        "when did",
        "why did",
        # Project names and specific references
        "atria",
        "spookyspot",
        "taskflow",
        "hills house",
        "styleatc",
        "linkedin",
        "scraper",
        "analyzer",
        "github",
        "resume",
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

        env_file = "../../../.env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = (
            "ignore"  # Ignore extra environment variables like COMPOSE_FILE
        )


settings = Settings()
