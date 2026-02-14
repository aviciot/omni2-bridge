"""Database connection and configuration loading."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from typing import Dict, Any

from config import settings
from logger import logger


# Database engine
engine = None
async_session_maker = None


async def init_db():
    """Initialize database connection."""
    global engine, async_session_maker
    
    database_url = (
        f"postgresql+asyncpg://{settings.DATABASE_USER}:{settings.DATABASE_PASSWORD}"
        f"@{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"
    )
    
    engine = create_async_engine(
        database_url,
        pool_size=5,
        max_overflow=10,
        echo=False,
    )
    
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def close_db():
    """Close database connection."""
    global engine
    if engine:
        await engine.dispose()


async def get_db():
    """Get database session."""
    async with async_session_maker() as session:
        yield session


async def load_config_from_db() -> Dict[str, Any]:
    """Load prompt guard configuration from omni2_config table."""
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                text(
                    f"SELECT config_value FROM {settings.DATABASE_SCHEMA}.omni2_config "
                    "WHERE config_key = 'prompt_guard' AND is_active = true"
                )
            )
            row = result.first()
            
            if row:
                config = row[0]
                logger.info("Loaded prompt guard config from database", config=config)
                return config
            else:
                # Default configuration
                default_config = {
                    "enabled": True,
                    "threshold": 0.5,
                    "cache_ttl_seconds": 3600,
                    "behavioral_tracking": {
                        "enabled": True,
                        "warning_threshold": 3,
                        "block_threshold": 5,
                        "window_hours": 24,
                    },
                    "actions": {
                        "warn": True,
                        "filter": False,
                        "block": False,
                    },
                }
                logger.warning("No prompt guard config in database, using defaults", config=default_config)
                return default_config
                
    except Exception as e:
        logger.error(f"Failed to load config from database: {e}", exc_info=True)
        # Return safe defaults
        return {
            "enabled": True,
            "threshold": 0.5,
            "cache_ttl_seconds": 3600,
            "behavioral_tracking": {"enabled": False},
            "actions": {"warn": True, "filter": False, "block": False},
        }


async def record_detection(user_id: int, message: str, score: float, action: str):
    """Record prompt injection detection in database."""
    try:
        async with async_session_maker() as session:
            await session.execute(
                text(
                    f"INSERT INTO {settings.DATABASE_SCHEMA}.prompt_injection_log "
                    "(user_id, message, injection_score, action, detected_at) "
                    "VALUES (:user_id, :message, :score, :action, NOW())"
                ),
                {
                    "user_id": user_id,
                    "message": message[:500],  # Truncate long messages
                    "score": score,
                    "action": action,
                },
            )
            await session.commit()
            logger.info("Recorded detection", user_id=user_id, score=score, action=action)
    except Exception as e:
        logger.error(f"Failed to record detection: {e}")


async def get_user_violation_count(user_id: int, window_hours: int = 24) -> int:
    """Get user's violation count within time window."""
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                text(
                    f"SELECT COUNT(*) FROM {settings.DATABASE_SCHEMA}.prompt_injection_log "
                    "WHERE user_id = :user_id "
                    "AND detected_at > NOW() - INTERVAL '1 hour' * :hours "
                    "AND action IN ('warn', 'block')"
                ),
                {"user_id": user_id, "hours": window_hours},
            )
            count = result.scalar()
            return count or 0
    except Exception as e:
        logger.error(f"Failed to get violation count: {e}")
        return 0
