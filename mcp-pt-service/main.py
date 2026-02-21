"""MCP PT Service - Main Application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from config import settings
from logger import logger
from db import init_db, close_db, pool
from routers import pt_runs, pt_config
from redis_publisher import get_publisher
from config_service import init_config_service


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    
    logger.info("=" * 80)
    logger.info("🔍 MCP PT Service V2 - Starting Up")
    logger.info("=" * 80)
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Database: {settings.DATABASE_HOST}:{settings.DATABASE_PORT}")
    logger.info("-" * 80)
    
    try:
        # Initialize database
        logger.info("🔌 Connecting to database...")
        await init_db()
        logger.info("✅ Database connected")

        # Cleanup orphaned runs from previous container instance
        import db as _db
        async with _db.pool.acquire() as conn:
            rows = await conn.fetch("""
                UPDATE omni2.pt_runs
                SET status = 'failed',
                    completed_at = NOW(),
                    stage_details = '{"error": "Service restarted — run was orphaned"}'
                WHERE status IN ('running', 'pending', 'cancelling')
                RETURNING run_id
            """)
            if rows:
                ids = [r["run_id"] for r in rows]
                logger.warning(f"⚠️  Marked {len(ids)} orphaned run(s) as failed on startup: {ids}")
            else:
                logger.info("✅ No orphaned runs found")
        
        # Initialize configuration service
        logger.info("⚙️  Loading configuration from database...")
        from db import pool as db_pool
        await init_config_service(db_pool)
        logger.info("✅ Configuration loaded")

        # Load attack phrase cache from DB
        logger.info("📖 Loading attack phrases from database...")
        from phrase_registry import load_phrases
        await load_phrases(db_pool)
        logger.info("✅ Attack phrases loaded")
        
        # Initialize Redis publisher
        logger.info("🔌 Connecting to Redis...")
        await get_publisher()
        logger.info("✅ Redis publisher connected")
        
        logger.info("=" * 80)
        logger.info("✅ MCP PT Service V2 - Ready!")
        logger.info("=" * 80)
        
        yield
        
    finally:
        logger.info("🛑 Shutting down MCP PT Service")
        
        # Close Redis
        from redis_publisher import _publisher
        if _publisher:
            await _publisher.close()
            logger.info("✅ Redis disconnected")
        
        await close_db()
        logger.info("✅ Database disconnected")


app = FastAPI(
    title="MCP PT Service V2",
    description="MCP Penetration Testing Service with LLM Planning",
    version="2.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(pt_runs.router)
app.include_router(pt_config.router)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "mcp-pt-v2",
        "version": "2.0.0",
        "llm_provider": settings.LLM_PROVIDER
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "MCP PT Service V2",
        "version": "2.0.0",
        "status": "running",
        "health": "/health",
        "docs": "/docs"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc)},
    )
