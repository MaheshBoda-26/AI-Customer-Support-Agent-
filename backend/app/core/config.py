"""
Application configuration using Pydantic Settings.
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenRouter (replaces Anthropic direct)
    OPENROUTER_API_KEY: str = Field(..., description="OpenRouter API key")
    OPENROUTER_BASE_URL: str = Field(default="https://openrouter.ai/api/v1", description="OpenRouter API base URL")
    OPENROUTER_MODEL: str = Field(default="anthropic/claude-3.5-sonnet", description="OpenRouter model to use")
    OPENROUTER_FAST_MODEL: str = Field(default="anthropic/claude-3-haiku", description="OpenRouter fast model for classification")

    # Qdrant
    QDRANT_URL: str = Field(..., description="Qdrant cluster URL")
    QDRANT_API_KEY: str = Field(default="", description="Qdrant API key (optional for local)")

    # Supabase
    SUPABASE_URL: str = Field(..., description="Supabase project URL")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(..., description="Supabase service role key")

    # Embeddings
    EMBEDDING_MODEL: str = Field(default="voyage-3", description="Embedding model name")
    VOYAGE_API_KEY: str = Field(default="", description="Voyage AI API key")

    # Optional
    SLACK_WEBHOOK_URL: str = Field(default="", description="Slack webhook for notifications")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    ENVIRONMENT: str = Field(default="development", description="Environment name")

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        description="Allowed CORS origins"
    )

    # Agent settings
    DEFAULT_TOP_K: int = Field(default=5, description="Default number of chunks to retrieve")
    CONFIDENCE_THRESHOLD: float = Field(default=0.7, description="Confidence threshold for escalation")
    MAX_RETRIES: int = Field(default=3, description="Max retries for external API calls")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()