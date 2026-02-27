from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db, close_db, get_redis
from app.services.flow_listener import init_flow_listener, shutdown_flow_listener
import structlog

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[DASHBOARD] 🚀 Starting Dashboard API", dev_mode=settings.DEV_MODE)
    await init_db()
    redis = await get_redis()
    logger.info("[DASHBOARD] ✓ Redis connected")
    await init_flow_listener(redis)
    yield
    logger.info("[DASHBOARD] 🛑 Shutting down...")
    await shutdown_flow_listener()
    await close_db()

app = FastAPI(
    title="Omni2 Dashboard API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "dev_mode": settings.DEV_MODE,
        "environment": settings.ENVIRONMENT
    }

@app.get("/")
async def root():
    return {
        "name": "Omni2 Dashboard API",
        "version": "0.1.0",
        "dev_mode": settings.DEV_MODE
    }

# Include routers
from app.routers import dashboard, charts, mcp, config, websocket, iam, events, chat, flows, activities, prompt_guard_proxy, mcp_pt_proxy, security, mcp_analytics
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(charts.router, prefix="/api/v1/dashboard", tags=["Charts"])
app.include_router(mcp.router, prefix="/api/v1/mcp/tools", tags=["MCP"])
app.include_router(config.router, prefix="/api/v1", tags=["Config"])
app.include_router(iam.router, prefix="/api/v1", tags=["IAM"])
app.include_router(events.router, prefix="/api/v1", tags=["Events"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(flows.router, prefix="/api/v1", tags=["Flows"])
app.include_router(activities.router, prefix="/api/v1", tags=["Activities"])
app.include_router(security.router, prefix="/api/v1", tags=["Security"])
app.include_router(prompt_guard_proxy.router, tags=["Prompt Guard"])
app.include_router(mcp_pt_proxy.router, tags=["MCP PT"])
app.include_router(mcp_analytics.router, prefix="/api/v1", tags=["MCP Analytics"])
app.include_router(websocket.router, tags=["WebSocket"])
