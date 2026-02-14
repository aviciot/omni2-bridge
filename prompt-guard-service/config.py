"""Configuration for Prompt Guard Service."""

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
    APP_PORT: int = 8100
    
    # Database
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "omni"
    DATABASE_USER: str = "omni"
    DATABASE_PASSWORD: str
    DATABASE_SCHEMA: str = "omni2"
    
    # Redis
    REDIS_HOST: str = "omni2-redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    
    # Model
    MODEL_NAME: str = "meta-llama/Llama-Prompt-Guard-2-86M"
    MODEL_CACHE_DIR: str = "/app/models"
    
    # Logging
    LOG_LEVEL: str = "INFO"


settings = Settings()
