from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from app.config import settings
import redis.asyncio as redis

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.is_development,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()

# Redis connection
redis_client: redis.Redis = None

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def get_redis() -> redis.Redis:
    return redis_client

async def init_db():
    global redis_client
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS omni2_dashboard"))
        await conn.run_sync(Base.metadata.create_all)
    
    # Initialize Redis
    redis_client = redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
        db=settings.REDIS_DB,
        decode_responses=True,
    )

async def close_db():
    global redis_client
    await engine.dispose()
    if redis_client:
        await redis_client.close()
