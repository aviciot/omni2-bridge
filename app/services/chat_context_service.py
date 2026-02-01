"""
Chat Context Service

Handles user authorization, blocking, usage limits, and context loading before LLM interaction.
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import Depends

from app.database import get_db
from app.utils.logger import logger


class ChatContextService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def load_user_context(self, user_id: int) -> dict:
        """Load complete user context including profile, role, and permissions"""
        query = text("""
            SELECT 
                u.id, u.username, u.email, u.role_id, u.active,
                r.name as role_name,
                r.mcp_access,
                r.tool_restrictions,
                r.cost_limit_daily,
                r.rate_limit
            FROM auth_service.users u
            LEFT JOIN auth_service.roles r ON u.role_id = r.id
            WHERE u.id = :user_id
        """)
        
        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()
        
        if not row:
            raise ValueError(f"User {user_id} not found")
        
        return {
            "user_id": row.id,
            "username": row.username,
            "email": row.email,
            "role_id": row.role_id,
            "active": row.active,
            "role_name": row.role_name,
            "mcp_access": row.mcp_access or [],
            "tool_restrictions": row.tool_restrictions or {},
            "cost_limit_daily": float(row.cost_limit_daily) if row.cost_limit_daily else 10.0,
            "rate_limit": row.rate_limit or 100
        }
    
    async def check_user_blocked(self, user_id: int) -> tuple[bool, Optional[str]]:
        """Check if user is blocked"""
        query = text("""
            SELECT is_blocked, custom_block_message, block_reason
            FROM omni2.user_blocks
            WHERE user_id = :user_id AND is_blocked = true
        """)
        
        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()
        
        if row:
            # Use custom_block_message if available, otherwise fall back to block_reason
            message = row.custom_block_message or row.block_reason
            return True, message
        return False, None
    
    async def check_usage_limit(self, user_id: int, cost_limit_daily: float) -> dict:
        """Check if user has exceeded daily usage limit"""
        query = text("""
            SELECT 
                COALESCE(SUM(llm_tokens_used), 0) as tokens_used,
                COALESCE(SUM(cost_usd), 0) as cost_used
            FROM omni2.audit_logs
            WHERE user_id = :user_id 
            AND timestamp >= CURRENT_DATE
            AND success = true
        """)
        
        result = await self.db.execute(query, {"user_id": user_id})
        row = result.fetchone()
        
        tokens_used = int(row.tokens_used) if row else 0
        cost_used = float(row.cost_used) if row else 0.0
        remaining = max(0, cost_limit_daily - cost_used)
        exceeded = cost_used >= cost_limit_daily
        
        return {
            "allowed": not exceeded,
            "tokens_used": tokens_used,
            "cost_used": cost_used,
            "cost_limit": cost_limit_daily,
            "remaining": remaining,
            "exceeded": exceeded
        }
    
    async def get_welcome_message(self, user_id: int, role_id: Optional[int]) -> dict:
        """Get personalized welcome message (priority: user > role > default)"""
        query = text("""
            SELECT welcome_message, show_usage_info
            FROM omni2.chat_welcome_config
            WHERE 
                (config_type = 'user' AND target_id = :user_id)
                OR (config_type = 'role' AND target_id = :role_id)
                OR (config_type = 'default' AND target_id IS NULL)
            ORDER BY 
                CASE config_type
                    WHEN 'user' THEN 1
                    WHEN 'role' THEN 2
                    WHEN 'default' THEN 3
                END
            LIMIT 1
        """)
        
        result = await self.db.execute(query, {"user_id": user_id, "role_id": role_id})
        row = result.fetchone()
        
        if row:
            return {
                "message": row.welcome_message,
                "show_usage_info": row.show_usage_info
            }
        
        return {
            "message": "Welcome to OMNI2!",
            "show_usage_info": True
        }
    
    async def get_available_mcps(self, mcp_access: list) -> list:
        """Get list of available MCP servers based on user's role permissions"""
        if not mcp_access:
            return []
        
        query = text("""
            SELECT name, url, description
            FROM omni2.mcp_servers
            WHERE name = ANY(:mcp_access)
            AND status = 'active'
        """)
        
        result = await self.db.execute(query, {"mcp_access": mcp_access})
        rows = result.fetchall()
        
        return [
            {
                "name": row.name,
                "url": row.url,
                "description": row.description
            }
            for row in rows
        ]
    
    def filter_tools_by_permissions(self, mcp_name: str, all_tools: list, tool_restrictions: dict) -> list:
        """Filter tools based on role's tool_restrictions.
        
        Args:
            mcp_name: Name of the MCP
            all_tools: List of all tools from MCP
            tool_restrictions: Dict from role
                Simple format: {"MCP": ["*"]} or {"MCP": ["tool1"]}
                Extended format: {"MCP": {"tools": ["*"], "resources": [...], "prompts": [...]}}
        
        Returns:
            Filtered list of tools user can access
        """
        # If MCP not in restrictions, allow all tools
        if mcp_name not in tool_restrictions:
            return all_tools
        
        restriction = tool_restrictions[mcp_name]
        
        # Handle extended format {"tools": [...], "resources": [...], "prompts": [...]}
        if isinstance(restriction, dict):
            allowed = restriction.get('tools', ['*'])
        # Handle simple format ["tool1", "tool2"] or ["*"] or []
        else:
            allowed = restriction
        
        # ['*'] means all tools
        if allowed == ['*']:
            return all_tools
        
        # [] means no tools
        if not allowed:
            return []
        
        # Filter to specific tools
        return [t for t in all_tools if t['name'] in allowed]


async def get_chat_context_service(db: AsyncSession = Depends(get_db)) -> ChatContextService:
    """Dependency injection for ChatContextService"""
    return ChatContextService(db)
