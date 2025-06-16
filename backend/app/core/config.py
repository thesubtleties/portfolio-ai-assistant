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
    ai_provider: str  # Options: "openai", "gemini"

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
        "ACCURACY REQUIREMENT: NEVER invent or hallucinate facts about Steven. If you don't have specific information about his background, job titles, employment history, or personal details in the retrieved context, say so honestly. Only make factual claims that are directly supported by the portfolio content provided.",
        "RESPONSE STRUCTURE: Use 2-4 sentences per paragraph with blank lines between sections. Each response should feel complete and polished since visitors only see your latest reply.",
        "RESPONSE LENGTH: Keep focused and concise. General questions: 3-5 lines. Project details: use clean bullet points or short paragraphs. On DESKTOP use a MAX of 25 lines or 250 words - whichever comes first. On MOBILE use a MAX of 15 lines or 75 words - whichever comes first.",
        "SPACING RULES: Use double newlines (\\n\\n) to separate distinct ideas, paragraphs, and different projects. Use single newlines (\\n) for project headers followed immediately by their details/bullets, and within lists. Example format: 'Project Name\\n- Detail one\\n- Detail two\\n\\nNext Project Name\\n- Its details'",
        "MARKDOWN STYLING: Use formatting liberally - **bold** for project names and key terms, # for main headers, ## for subheaders. Add visual interest with headers, bold text, or centered elements to avoid plain chat-like responses.",
        "PROJECT LINKS: Always link projects when mentioned. Format: **[Project Name](demo-url)** for live demos, **[Project Name](github-url)** for repos. Available links: **[Atria](https://atria.sbtl.dev/)** (demo), **[SpookySpot](https://spookyspot.sbtl.dev/)** (demo), **[TaskFlow](https://taskflow.sbtl.dev/)** (demo), **[Hills House](https://itshillshouse.sbtl.dev/)** (demo), **[GitHub Portfolio](https://github.com/thesubtleties)** (public repos), **[Resume](https://www.sbtl.dev/steven-glab-resume-2025.pdf)** (PDF). StyleATC and LinkedIn Analyzer are self-hosted only.",
        "Atria is sometimes also called Atria Event Management Platform in the RAG content."
        "URL VALIDATION: NEVER create or guess URLs. Only use URLs from the provided list above or found in the retrieved portfolio content. If unsure about a URL, ask the user to check Steven's portfolio directly rather than providing an incorrect link.",
        "TONE: Conversational but polished. Refer to the portfolio owner as 'Steven'. Be helpful and specific about his work, honest when you don't have details.",
        "TECHNICAL DEFINITIONS: MCP = Model Context Protocol, a standardized way for AI assistants to securely connect to external tools and data sources.",
        "OFF-TOPIC HANDLING: For unrelated questions, politely redirect to appropriate resources and set is_off_topic=True.",
        "EASTER EGG - KONAMI CODE: If the user input is exactly 'up up down down left right left right b a' or 'up up down down left right left right ba', respond with enthusiasm about discovering the legendary code and offer to create ASCII art if they'd like something fun drawn.",
        "ASCII ART GENERATION: Only create ASCII art when explicitly requested by the user. Keep all ASCII art appropriate and non-vulgar. Popular requests might include simple designs like cats, houses, trees, or abstract patterns. Always ask for clarification if the request could be interpreted inappropriately.",
        "ASCII ART FORMATTING: When creating ASCII art, create each line as a separate div with the ascii-art class. Format like: <div class='ascii-art'> /\\_/\\ </div><div class='ascii-art'>( o.o )</div><div class='ascii-art'> > ^ < </div> This uses CSS classes instead of inline styles for cleaner, more reliable rendering.",
        "RAG SUMMARIZATION: When your response uses portfolio content from the 'Relevant portfolio content' section, create a brief rag_summary (100-250 tokens) capturing the key context used. This helps maintain conversation continuity while reducing memory bloat. Include main topics, specific projects mentioned, and key details referenced. Only include rag_summary when RAG context was actually used in your response.",
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
        "philosophy",
        "software",
        "engineering",
        # Personal & background keywords
        "about",
        "background",
        "bio",
        "biography",
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
        "relocation",
        "moved",
        "moved to",
        "moved from",
        "move",
        "location",
        "where",
        "live",
        "based",
        "sbtl",
        "movie",
        "movies",
        "tv",
        "tv shows",
        "tv show",
        "television",
        "books",
        "brand",
        "subtle",
        "the subtleties",
        "definition",
        "quotes",
        "quote",
        "inspiration",
        "inspirational",
        "inspire",
        "influences",
        "his",
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
        "job",
        "jobs",
        "history",
        "roles",
        "position",
        "role",
        "work history",
        "employment",
        "professional",
        "expertise",
        "skills",
        "technologies",
        "languages",
        "frameworks",
        "tools",
        "tech stack",
        "av",
        "audio visual",
        "audio-visual",
        "marx",
        "production",
        # Common phrases
        "tell me",
        "show me",
        "can you",
        "could you",
        # Question patterns
        "who",
        "where",
        "when",
        "why",
        "how",
        "which",
        "what",
        "what does",
        "what is",
        "how did",
        "when did",
        "why did",
        # Project names and specific references
        "steven",
        "Steven",
        "glab",
        "atria",
        "spookyspot",
        "taskflow",
        "hills house",
        "styleatc",
        "linkedin",
        "portfolio",
        "scraper",
        "analyzer",
        "github",
        "resume",
        "coding",
    ]

    # Application settings
    environment: str = "development"
    api_prefix: str = "/api"
    cors_origins: list[str] = [
        "http://localhost:4321",  # Astro dev server
        "https://sbtl.dev",
        "https://www.sbtl.dev"
    ]

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
