"""Configuration for MCP PT Service."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Environment-based settings."""
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }
    
    # Application
    APP_ENV: str = "development"
    APP_PORT: int = 8200
    
    # Database
    DATABASE_HOST: str = "omni_pg_db"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "omni"
    DATABASE_USER: str = "omni"
    DATABASE_PASSWORD: str = "omni"
    DATABASE_SCHEMA: str = "omni2"
    
    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    
    # LLM Configuration
    LLM_PROVIDER: str = "anthropic"  # anthropic or gemini
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5-20250929"
    GOOGLE_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    MAX_CONCURRENT_LLM_CALLS: int = 2
    
    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()
