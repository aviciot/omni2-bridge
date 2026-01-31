"""
OMNI2 Permission Checker
========================
Enforces role-based access control for MCP servers, tools, prompts, and resources.
"""

from typing import Optional, Dict, List
from fastapi import HTTPException
import logging

logger = logging.getLogger(__name__)


class PermissionDenied(HTTPException):
    """Custom exception for permission denied"""
    def __init__(self, detail: str):
        super().__init__(status_code=403, detail=detail)


class PermissionChecker:
    """
    Checks user permissions for MCP access based on role configuration.
    """
    
    @staticmethod
    async def check_mcp_access(role: Dict, mcp_name: str) -> bool:
        """
        Check if role has access to MCP server.
        
        Args:
            role: Role object with mcp_access field
            mcp_name: Name of MCP server
            
        Returns:
            True if access allowed
            
        Raises:
            PermissionDenied: If access not allowed
        """
        mcp_access = role.get("mcp_access", [])
        
        if not mcp_access:
            raise PermissionDenied(f"Role '{role['name']}' has no MCP access configured")
        
        if mcp_name not in mcp_access:
            raise PermissionDenied(
                f"Role '{role['name']}' does not have access to MCP '{mcp_name}'. "
                f"Allowed MCPs: {', '.join(mcp_access)}"
            )
        
        logger.info(f"MCP access granted: role={role['name']}, mcp={mcp_name}")
        return True
    
    @staticmethod
    async def check_tool_access(
        role: Dict, 
        mcp_name: str, 
        tool_name: str
    ) -> bool:
        """
        Check if role has access to specific tool in MCP.
        
        Args:
            role: Role object with tool_restrictions field
            mcp_name: Name of MCP server
            tool_name: Name of tool
            
        Returns:
            True if access allowed
            
        Raises:
            PermissionDenied: If access not allowed
        """
        # First check MCP access
        await PermissionChecker.check_mcp_access(role, mcp_name)
        
        # Get tool restrictions for this MCP
        tool_restrictions = role.get("tool_restrictions", {})
        mcp_restrictions = tool_restrictions.get(mcp_name, {})
        
        # Default mode is "all" (allow all tools)
        mode = mcp_restrictions.get("mode", "all")
        restricted_tools = mcp_restrictions.get("tools", [])
        
        if mode == "none":
            raise PermissionDenied(
                f"Role '{role['name']}' has no tool access for MCP '{mcp_name}'"
            )
        
        elif mode == "allow":
            # Whitelist mode - only specified tools allowed
            if tool_name not in restricted_tools:
                raise PermissionDenied(
                    f"Tool '{tool_name}' not in allowed list for role '{role['name']}'. "
                    f"Allowed tools: {', '.join(restricted_tools)}"
                )
        
        elif mode == "deny":
            # Blacklist mode - all tools except specified
            if tool_name in restricted_tools:
                raise PermissionDenied(
                    f"Tool '{tool_name}' is denied for role '{role['name']}'"
                )
        
        # mode == "all" -> allow all tools
        logger.info(f"Tool access granted: role={role['name']}, mcp={mcp_name}, tool={tool_name}")
        return True
    
    @staticmethod
    async def filter_tools_by_permission(
        role: Dict,
        mcp_name: str,
        all_tools: List[str]
    ) -> List[str]:
        """
        Filter tool list based on role permissions.
        
        Args:
            role: Role object
            mcp_name: Name of MCP server
            all_tools: List of all available tools
            
        Returns:
            Filtered list of allowed tools
        """
        tool_restrictions = role.get("tool_restrictions", {})
        mcp_restrictions = tool_restrictions.get(mcp_name, {})
        mode = mcp_restrictions.get("mode", "all")
        restricted_tools = mcp_restrictions.get("tools", [])
        
        if mode == "all":
            return all_tools
        elif mode == "allow":
            return [t for t in all_tools if t in restricted_tools]
        elif mode == "deny":
            return [t for t in all_tools if t not in restricted_tools]
        else:  # mode == "none"
            return []


# Convenience functions for common checks

async def require_mcp_access(role: Dict, mcp_name: str):
    """Raise exception if MCP access not allowed"""
    await PermissionChecker.check_mcp_access(role, mcp_name)


async def require_tool_access(role: Dict, mcp_name: str, tool_name: str):
    """Raise exception if tool access not allowed"""
    await PermissionChecker.check_tool_access(role, mcp_name, tool_name)


async def can_access_mcp(role: Dict, mcp_name: str) -> bool:
    """Check if MCP access allowed (returns bool, no exception)"""
    try:
        await PermissionChecker.check_mcp_access(role, mcp_name)
        return True
    except PermissionDenied:
        return False


async def can_access_tool(role: Dict, mcp_name: str, tool_name: str) -> bool:
    """Check if tool access allowed (returns bool, no exception)"""
    try:
        await PermissionChecker.check_tool_access(role, mcp_name, tool_name)
        return True
    except PermissionDenied:
        return False
