"""
IAM Chat Configuration Router

Manage user blocking and welcome messages.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import json
import time

from app.database import get_db, get_redis
from app.utils.logger import logger
from redis.asyncio import Redis


router = APIRouter(prefix="/api/v1/iam/chat-config", tags=["IAM Chat Config"])


# ============================================================
# Request/Response Models
# ============================================================

class UserBlockStatus(BaseModel):
    user_id: int
    is_blocked: bool
    block_reason: Optional[str] = None
    custom_block_message: Optional[str] = None
    blocked_at: Optional[str] = None
    blocked_by: Optional[int] = None
    blocked_services: list[str] = []


class BlockUserRequest(BaseModel):
    is_blocked: bool
    block_reason: Optional[str] = None
    custom_block_message: Optional[str] = None
    blocked_services: list[str] = ['chat', 'mcp']


class WelcomeMessageConfig(BaseModel):
    config_type: str  # 'user', 'role', 'default'
    target_id: Optional[int] = None
    welcome_message: str
    show_usage_info: bool = True


# ============================================================
# User Blocking Endpoints
# ============================================================

@router.get("/users/{user_id}/block", response_model=UserBlockStatus)
async def get_user_block_status(
    user_id: int,
    http_request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get user block status"""
    # TODO: Add auth check - only super_admin can access
    
    query = text("""
        SELECT user_id, is_blocked, block_reason, custom_block_message, 
               blocked_at, blocked_by, blocked_services
        FROM omni2.user_blocks
        WHERE user_id = :user_id
    """)
    
    result = await db.execute(query, {"user_id": user_id})
    row = result.fetchone()
    
    if not row:
        return UserBlockStatus(user_id=user_id, is_blocked=False)
    
    return UserBlockStatus(
        user_id=row.user_id,
        is_blocked=row.is_blocked,
        block_reason=row.block_reason,
        custom_block_message=row.custom_block_message,
        blocked_at=str(row.blocked_at) if row.blocked_at else None,
        blocked_by=row.blocked_by,
        blocked_services=row.blocked_services or []
    )


@router.put("/users/{user_id}/block")
async def update_user_block_status(
    user_id: int,
    request: BlockUserRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
):
    """Block or unblock user with custom message - immediately disconnects active sessions"""
    # TODO: Add auth check - only super_admin can access
    # Get admin user_id from X-User-Id header
    admin_user_id = http_request.headers.get("X-User-Id")

    if request.is_blocked:
        # Block user
        query = text("""
            INSERT INTO omni2.user_blocks
                (user_id, is_blocked, block_reason, custom_block_message, blocked_at, blocked_by, blocked_services)
            VALUES
                (:user_id, :is_blocked, :block_reason, :custom_block_message, NOW(), :blocked_by, :blocked_services)
            ON CONFLICT (user_id)
            DO UPDATE SET
                is_blocked = :is_blocked,
                block_reason = :block_reason,
                custom_block_message = :custom_block_message,
                blocked_at = NOW(),
                blocked_by = :blocked_by,
                blocked_services = :blocked_services
        """)

        await db.execute(query, {
            "user_id": user_id,
            "is_blocked": request.is_blocked,
            "block_reason": request.block_reason,
            "custom_block_message": request.custom_block_message,
            "blocked_by": int(admin_user_id) if admin_user_id else None,
            "blocked_services": request.blocked_services
        })

        await db.commit()

        # Publish block event to Redis for instant disconnection
        block_event = {
            "user_id": user_id,
            "blocked_services": request.blocked_services,
            "custom_message": request.custom_block_message or request.block_reason or "Your access has been blocked by an administrator.",
            "blocked_by": admin_user_id,
            "timestamp": str(time.time()) if 'time' in dir() else None
        }

        try:
            await redis.publish("user_blocked", json.dumps(block_event))
            logger.info(f"[IAM] 🚫 Published block event for user {user_id}")
        except Exception as e:
            logger.error(f"[IAM] ✗ Failed to publish block event: {e}")

        logger.info(f"[IAM] User {user_id} blocked by admin {admin_user_id}")

    else:
        # Unblock user
        query = text("""
            DELETE FROM omni2.user_blocks WHERE user_id = :user_id
        """)
        await db.execute(query, {"user_id": user_id})
        await db.commit()

        logger.info(f"[IAM] User {user_id} unblocked by admin {admin_user_id}")

    return {"success": True, "message": f"User {'blocked' if request.is_blocked else 'unblocked'} successfully"}


# ============================================================
# Welcome Message Endpoints
# ============================================================

@router.get("/users/{user_id}/welcome", response_model=WelcomeMessageConfig)
async def get_user_welcome_message(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get user-specific welcome message"""
    query = text("""
        SELECT config_type, target_id, welcome_message, show_usage_info
        FROM omni2.chat_welcome_config
        WHERE config_type = 'user' AND target_id = :user_id
    """)
    
    result = await db.execute(query, {"user_id": user_id})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="User welcome message not found")
    
    return WelcomeMessageConfig(
        config_type=row.config_type,
        target_id=row.target_id,
        welcome_message=row.welcome_message,
        show_usage_info=row.show_usage_info
    )


@router.put("/users/{user_id}/welcome")
async def update_user_welcome_message(
    user_id: int,
    config: WelcomeMessageConfig,
    db: AsyncSession = Depends(get_db)
):
    """Set or update user-specific welcome message"""
    query = text("""
        INSERT INTO omni2.chat_welcome_config 
            (config_type, target_id, welcome_message, show_usage_info)
        VALUES 
            ('user', :user_id, :welcome_message, :show_usage_info)
        ON CONFLICT (config_type, target_id) 
        DO UPDATE SET 
            welcome_message = :welcome_message,
            show_usage_info = :show_usage_info
    """)
    
    await db.execute(query, {
        "user_id": user_id,
        "welcome_message": config.welcome_message,
        "show_usage_info": config.show_usage_info
    })
    await db.commit()
    
    return {"success": True, "message": "User welcome message updated"}


@router.get("/roles/{role_id}/welcome", response_model=WelcomeMessageConfig)
async def get_role_welcome_message(
    role_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get role-specific welcome message"""
    query = text("""
        SELECT config_type, target_id, welcome_message, show_usage_info
        FROM omni2.chat_welcome_config
        WHERE config_type = 'role' AND target_id = :role_id
    """)
    
    result = await db.execute(query, {"role_id": role_id})
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Role welcome message not found")
    
    return WelcomeMessageConfig(
        config_type=row.config_type,
        target_id=row.target_id,
        welcome_message=row.welcome_message,
        show_usage_info=row.show_usage_info
    )


@router.put("/roles/{role_id}/welcome")
async def update_role_welcome_message(
    role_id: int,
    config: WelcomeMessageConfig,
    db: AsyncSession = Depends(get_db)
):
    """Set or update role-specific welcome message"""
    query = text("""
        INSERT INTO omni2.chat_welcome_config 
            (config_type, target_id, welcome_message, show_usage_info)
        VALUES 
            ('role', :role_id, :welcome_message, :show_usage_info)
        ON CONFLICT (config_type, target_id) 
        DO UPDATE SET 
            welcome_message = :welcome_message,
            show_usage_info = :show_usage_info
    """)
    
    await db.execute(query, {
        "role_id": role_id,
        "welcome_message": config.welcome_message,
        "show_usage_info": config.show_usage_info
    })
    await db.commit()
    
    return {"success": True, "message": "Role welcome message updated"}


@router.get("/welcome/default", response_model=WelcomeMessageConfig)
async def get_default_welcome_message(db: AsyncSession = Depends(get_db)):
    """Get default welcome message"""
    query = text("""
        SELECT config_type, target_id, welcome_message, show_usage_info
        FROM omni2.chat_welcome_config
        WHERE config_type = 'default' AND target_id IS NULL
    """)
    
    result = await db.execute(query)
    row = result.fetchone()
    
    if not row:
        raise HTTPException(status_code=404, detail="Default welcome message not found")
    
    return WelcomeMessageConfig(
        config_type=row.config_type,
        target_id=row.target_id,
        welcome_message=row.welcome_message,
        show_usage_info=row.show_usage_info
    )


@router.put("/welcome/default")
async def update_default_welcome_message(
    config: WelcomeMessageConfig,
    db: AsyncSession = Depends(get_db)
):
    """Set or update default welcome message"""
    query = text("""
        INSERT INTO omni2.chat_welcome_config 
            (config_type, target_id, welcome_message, show_usage_info)
        VALUES 
            ('default', NULL, :welcome_message, :show_usage_info)
        ON CONFLICT (config_type, target_id) 
        DO UPDATE SET 
            welcome_message = :welcome_message,
            show_usage_info = :show_usage_info
    """)
    
    await db.execute(query, {
        "welcome_message": config.welcome_message,
        "show_usage_info": config.show_usage_info
    })
    await db.commit()
    
    return {"success": True, "message": "Default welcome message updated"}
