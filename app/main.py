"""
OMNI2 FastAPI Application Entry Point

This is the main application module that initializes the FastAPI app,
configures middleware, registers routers, and sets up startup/shutdown events.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.config import settings
from app.database import init_db, close_db, get_db
from app.routers import health
from app.utils.logger import setup_logging, logger
from app.services.mcp_registry import get_mcp_registry
from app.services.mcp_coordinator import start_mcp_coordinator, stop_mcp_coordinator
from app.services.websocket_broadcaster import start_websocket_broadcaster, stop_websocket_broadcaster
from app.services.tool_cache import start_tool_cache, stop_tool_cache
from app.models import Omni2Config
from sqlalchemy import select
import asyncio


import asyncio


# ============================================================
# Background Tasks
# ============================================================

async def health_check_loop():
    """Background task for proactive health monitoring."""
    interval = 60  # Default interval
    
    while True:
        try:
            async for db in get_db():
                # Load config
                result = await db.execute(
                    select(Omni2Config).where(Omni2Config.config_key == 'health_check')
                )
                config = result.scalar_one_or_none()
                interval = config.config_value.get('interval_seconds', 60) if config else 60
                
                # Check health of all MCPs
                mcp_registry = get_mcp_registry()
                for mcp_name in mcp_registry.get_loaded_mcps():
                    await mcp_registry.health_check(mcp_name, db)
                
                break
            
            await asyncio.sleep(interval)
        except Exception as e:
            logger.error("Health check loop error", app="omni2", error=str(e))
            await asyncio.sleep(interval)  # Use last known interval instead of hardcoded 60


async def hot_reload_loop():
    """Background task for hot reload."""
    from app.database import engine
    from sqlalchemy import text
    import json
    import psutil
    
    interval = 30
    
    while True:
        try:
            # Get config using raw connection (no greenlet issues)
            async with engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT config_value FROM omni2.omni2_config WHERE config_key = 'hot_reload'")
                )
                row = result.first()
                if row:
                    config_value = row[0]
                    if isinstance(config_value, str):
                        config = json.loads(config_value)
                    else:
                        config = config_value
                    interval = config.get('interval_seconds', 30)
            
            # Reload MCPs using proper async context
            async for db in get_db():
                mcp_registry = get_mcp_registry()
                await mcp_registry.reload_if_changed(db)
                break
            
            # Broadcast system health metrics
            try:
                from app.services.websocket_broadcaster import get_websocket_broadcaster
                broadcaster = get_websocket_broadcaster()
                
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                
                await broadcaster.broadcast_event(
                    event_type="system_health",
                    event_data={
                        "cpu_percent": round(cpu_percent, 1),
                        "memory_percent": round(memory.percent, 1),
                        "memory_used_mb": round(memory.used / 1024 / 1024, 0),
                        "memory_total_mb": round(memory.total / 1024 / 1024, 0),
                        "active_mcps": len(mcp_registry.get_loaded_mcps()),
                        "severity": "info"
                    }
                )
            except Exception as e:
                logger.debug(f"Failed to broadcast system health: {e}")
            
            await asyncio.sleep(interval)
        except Exception as e:
            logger.error("Hot reload loop error", app="omni2", error=str(e))
            await asyncio.sleep(interval)


# ============================================================
# Application Lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager for startup and shutdown events.
    
    Handles:
    - Database connection initialization
    - Configuration loading
    - Resource cleanup on shutdown
    """
    # Startup
    logger.info("=" * 80)
    logger.info("🚀 OMNI2 Bridge Application - Starting Up")
    logger.info("=" * 80)
    logger.info(f"📦 Version: {__version__}")
    logger.info(f"🌍 Environment: {settings.app.environment}")
    logger.info(f"🐛 Debug Mode: {settings.app.debug}")
    logger.info(f"🔄 Auto-Reload: {settings.app.reload}")
    logger.info(f"🌐 Host: {settings.app.host}:{settings.app.port}")
    logger.info("-" * 80)
    logger.info("🤖 Anthropic Claude Configuration:")
    logger.info(f"   Model: {settings.llm.model}")
    logger.info(f"   Max Tokens: {settings.llm.max_tokens}")
    logger.info(f"   Timeout: {settings.llm.timeout}s")
    logger.info(f"   API Key: {'✅ Configured' if settings.llm.api_key else '❌ Missing'}")
    logger.info("-" * 80)
    logger.info("🗄️  Database Configuration:")
    logger.info(f"   Host: {settings.database.host}:{settings.database.port}")
    logger.info(f"   Database: {settings.database.database}")
    logger.info(f"   User: {settings.database.user}")
    logger.info(f"   Pool Size: {settings.database.pool_size} (max overflow: {settings.database.max_overflow})")
    logger.info("-" * 80)
    logger.info("🔐 Security:")
    logger.info(f"   CORS Enabled: {settings.security.cors_enabled}")
    logger.info(f"   Secret Key: {'✅ Configured' if settings.security.secret_key != 'change-this-in-production' else '⚠️  Using Default (Change in Production!)'}")
    logger.info("-" * 80)
    
    try:
        # Initialize database connection
        logger.info("🔌 Connecting to database...")
        await init_db()
        logger.info("✅ Database connection established")
        
        # Load MCPs from database
        logger.info("📦 Loading MCPs from database...")
        mcp_registry = get_mcp_registry()
        async for db in get_db():
            await mcp_registry.load_from_database(db)
            break
        logger.info(f"✅ Loaded {len(mcp_registry.get_loaded_mcps())} MCPs")
        
        # Start background tasks
        logger.info("🔄 Starting background tasks...")
        asyncio.create_task(health_check_loop())
        asyncio.create_task(hot_reload_loop())
        
        # Start MCP Coordinator
        logger.info("🎯 Starting MCP Coordinator...")
        await start_mcp_coordinator()
        
        # Start Phase 2 services
        logger.info("🚀 Starting Phase 2 services...")
        await start_tool_cache()
        await start_websocket_broadcaster()
        
        # Load logging configuration from database
        logger.info("📝 Loading logging configuration...")
        from app.services.websocket_broadcaster import get_websocket_broadcaster
        broadcaster = get_websocket_broadcaster()
        async for db in get_db():
            await broadcaster.load_logging_config(db)
            break
        logger.info(f"✅ Logging config loaded (verbose: {broadcaster.verbose_logging})")
        
        logger.info("✅ Background tasks started")
        
        # Log configuration summary
        logger.info("✅ Configuration loaded successfully")
        
        # TODO: Initialize MCP discovery service
        # TODO: Load users from database
        # TODO: Start health check scheduler
        
        logger.info("=" * 80)
        logger.info("✅ OMNI2 Bridge Application - Ready!")
        logger.info(f"📖 API Documentation: http://{settings.app.host}:{settings.app.port}/docs")
        logger.info(f"🏥 Health Check: http://{settings.app.host}:{settings.app.port}/health")
        logger.info("=" * 80)
        
        yield
        
    finally:
        # Shutdown
        logger.info("🛑 Shutting down OMNI2 Bridge Application")
        
        # Stop MCP Coordinator
        await stop_mcp_coordinator()
        logger.info("✅ MCP Coordinator stopped")
        
        # Stop Phase 2 services
        await stop_tool_cache()
        await stop_websocket_broadcaster()
        logger.info("✅ Phase 2 services stopped")
        
        # Close MCP connections
        mcp_registry = get_mcp_registry()
        await mcp_registry.close_all()
        logger.info("✅ MCP connections closed")
        
        # Close database connections
        await close_db()
        logger.info("✅ Database connections closed")


# Initialize FastAPI application
app = FastAPI(
    title="OMNI2 Bridge",
    description=(
        "Intelligent MCP orchestration layer with LLM-based routing. "
        "Routes natural language queries to appropriate Model Context Protocol servers."
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


# ============================================================
# CORS Middleware
# ============================================================
if settings.security.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("✅ CORS middleware enabled", origins=settings.security.cors_origins)


# ============================================================
# Global Exception Handler
# ============================================================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(
        "❌ Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.app.debug else "An unexpected error occurred",
            "path": request.url.path,
        },
    )


# ============================================================
# Register Routers
# ============================================================
from app.routers import tools, chat, audit, users, cache, admin, mcp_servers, websocket, circuit_breaker, events, iam_chat_config, monitoring

app.include_router(health.router, tags=["Health"])
app.include_router(tools.router, prefix="/api/v1", tags=["MCP Tools"])
app.include_router(mcp_servers.router, prefix="/api/v1", tags=["MCP Servers"])
app.include_router(circuit_breaker.router, prefix="/api/v1", tags=["Circuit Breaker"])
app.include_router(chat.router, tags=["Chat"])
app.include_router(audit.router, tags=["Audit"])
app.include_router(users.router, tags=["Users"])
app.include_router(cache.router, tags=["Cache"])
app.include_router(admin.router, tags=["Admin"])
app.include_router(websocket.router, tags=["WebSocket"])
app.include_router(events.router, prefix="/api/v1", tags=["Events"])
app.include_router(iam_chat_config.router, tags=["IAM Chat Config"])
app.include_router(monitoring.router, tags=["Monitoring"])

# TODO: Add more routers as we build them
# app.include_router(query.router, prefix="/query", tags=["Query"])
# app.include_router(admin.router, prefix="/admin", tags=["Admin"])
# app.include_router(slack.router, prefix="/slack", tags=["Slack"])


# ============================================================
# Root Endpoint
# ============================================================
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "OMNI2 Bridge",
        "version": __version__,
        "description": "Intelligent MCP orchestration with LLM routing",
        "docs": "/docs",
        "health": "/health",
        "status": "running",
    }


# ============================================================
# Setup Logging
# ============================================================
# Initialize logging when module is imported
setup_logging()

logger.info("✅ OMNI2 application module loaded")
