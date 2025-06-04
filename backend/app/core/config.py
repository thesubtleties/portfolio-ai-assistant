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
    redis_decode_responses: bool = True  # Decode to strings for easier handling
    redis_max_connections: int = 50

    # Application settings
    environment: str = "development"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:4321"]  # Astro dev server

    # WebSocket settings
    ws_heartbeat_interval: int = 30  # Seconds between heartbeats
    ws_connection_timeout: int = 300  # 5 minutes max connection time

    @property
    def database_url(self) -> str:
        """Construct the database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:"
            f"{self.postgres_password}@{self.postgres_host}:"
            f"{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        """Pydantic settings configuration."""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
