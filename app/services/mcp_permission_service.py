"""
MCP Permission Service

Centralized service for filtering MCP servers, tools, resources, and prompts
based on user permissions. Used by both WebSocket chat and MCP gateway.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from fastapi import Depends
from app.database import get_db


class MCPPermissionService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_available_mcps(self, mcp_access: list) -> list:
        """Get list of available MCP servers based on user's mcp_access"""
        if not mcp_access:
            return []
        
        # Handle wildcard - return all active MCPs
        if '*' in mcp_access:
            query = text("""
                SELECT name, url, description
                FROM omni2.mcp_servers
                WHERE status = 'active'
            """)
            result = await self.db.execute(query)
        else:
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
    
    def filter_tools(self, mcp_name: str, all_tools: list, tool_restrictions) -> list:
        """Filter tools based on role's tool_restrictions.
        
        Args:
            mcp_name: Name of the MCP
            all_tools: List of all tools from MCP
            tool_restrictions: Dict from role (can be None, string, or dict)
                Simple format: {"MCP": ["*"]} or {"MCP": ["tool1"]}
                Extended format: {"MCP": {"tools": ["*"], "resources": [...], "prompts": [...]}}
        
        Returns:
            Filtered list of tools user can access
        """
        # Handle string (JSON from DB)
        if isinstance(tool_restrictions, str):
            import json
            try:
                tool_restrictions = json.loads(tool_restrictions)
            except:
                return all_tools
        
        # If no restrictions, allow all tools
        if not tool_restrictions or mcp_name not in tool_restrictions:
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
    
    def filter_resources(self, mcp_name: str, all_resources: list, tool_restrictions) -> list:
        """Filter resources based on role's tool_restrictions (extended format)"""
        # Handle string (JSON from DB)
        if isinstance(tool_restrictions, str):
            import json
            try:
                tool_restrictions = json.loads(tool_restrictions)
            except:
                return all_resources
        
        if not tool_restrictions or mcp_name not in tool_restrictions:
            return all_resources
        
        restriction = tool_restrictions[mcp_name]
        
        # Only extended format has resources
        if not isinstance(restriction, dict):
            return all_resources
        
        allowed = restriction.get('resources', ['*'])
        
        if allowed == ['*']:
            return all_resources
        
        if not allowed:
            return []
        
        return [r for r in all_resources if r['uri'] in allowed]
    
    def filter_prompts(self, mcp_name: str, all_prompts: list, tool_restrictions) -> list:
        """Filter prompts based on role's tool_restrictions (extended format)"""
        # Handle string (JSON from DB)
        if isinstance(tool_restrictions, str):
            import json
            try:
                tool_restrictions = json.loads(tool_restrictions)
            except:
                return all_prompts
        
        if not tool_restrictions or mcp_name not in tool_restrictions:
            return all_prompts
        
        restriction = tool_restrictions[mcp_name]
        
        # Only extended format has prompts
        if not isinstance(restriction, dict):
            return all_prompts
        
        allowed = restriction.get('prompts', ['*'])
        
        if allowed == ['*']:
            return all_prompts
        
        if not allowed:
            return []
        
        return [p for p in all_prompts if p['name'] in allowed]
    
    def can_call_tool(self, mcp_name: str, tool_name: str, tool_restrictions) -> bool:
        """Check if user can call specific tool"""
        # Handle string (JSON from DB)
        if isinstance(tool_restrictions, str):
            import json
            try:
                tool_restrictions = json.loads(tool_restrictions)
            except:
                return True
        
        if not tool_restrictions or mcp_name not in tool_restrictions:
            return True
        
        restriction = tool_restrictions[mcp_name]
        
        if isinstance(restriction, dict):
            allowed = restriction.get('tools', ['*'])
        else:
            allowed = restriction
        
        if allowed == ['*']:
            return True
        
        return tool_name in allowed


async def get_mcp_permission_service(db: AsyncSession = Depends(get_db)) -> MCPPermissionService:
    """Dependency injection for MCPPermissionService"""
    return MCPPermissionService(db)
