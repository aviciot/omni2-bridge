"""
Prompt Guard Service - Main Application

Detects prompt injection attacks using Llama-Prompt-Guard-2-86M.
Communicates with omni2 via Redis pub/sub for real-time protection.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import asyncio

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from config import settings
from logger import logger
from guard import PromptGuardService
from redis_handler import RedisHandler
from db import init_db, close_db, load_config_from_db


# Global instances
guard_service: PromptGuardService = None
redis_handler: RedisHandler = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    global guard_service, redis_handler
    
    logger.info("=" * 80)
    logger.info("🛡️  Prompt Guard Service - Starting Up")
    logger.info("=" * 80)
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    logger.info(f"Database: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}")
    logger.info("-" * 80)
    
    try:
        # Initialize database
        logger.info("🔌 Connecting to database...")
        await init_db()
        logger.info("✅ Database connected")
        
        # Load configuration from database
        logger.info("📝 Loading configuration from database...")
        config = await load_config_from_db()
        logger.info(f"✅ Config loaded - Enabled: {config.get('enabled', True)}")
        
        # Initialize guard service
        logger.info("🤖 Loading Llama-Prompt-Guard-2-86M model...")
        guard_service = PromptGuardService(config)
        logger.info("✅ Model loaded successfully")
        
        # Initialize Redis handler
        logger.info("🔌 Connecting to Redis...")
        redis_handler = RedisHandler(guard_service)
        await redis_handler.connect()
        logger.info("✅ Redis connected")
        
        # Start listening for requests
        logger.info("🎧 Starting Redis listener...")
        asyncio.create_task(redis_handler.listen_for_requests())
        logger.info("✅ Listener started")
        
        logger.info("=" * 80)
        logger.info("✅ Prompt Guard Service - Ready!")
        logger.info("=" * 80)
        
        yield
        
    finally:
        logger.info("🛑 Shutting down Prompt Guard Service")
        
        if redis_handler:
            await redis_handler.close()
            logger.info("✅ Redis disconnected")
        
        await close_db()
        logger.info("✅ Database disconnected")


app = FastAPI(
    title="Prompt Guard Service",
    description="Real-time prompt injection detection using Llama-Prompt-Guard-2-86M",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "prompt-guard",
        "model": "meta-llama/Llama-Prompt-Guard-2-86M",
        "redis_connected": redis_handler.is_connected() if redis_handler else False,
        "guard_enabled": guard_service.enabled if guard_service else False,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Prompt Guard Service",
        "version": "1.0.0",
        "status": "running",
        "health": "/health",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc)},
    )
