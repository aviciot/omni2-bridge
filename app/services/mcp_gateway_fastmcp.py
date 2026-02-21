"""
FastMCP Gateway Server
======================
HTTP Streamable implementation using FastMCP library

Note: This uses FastMCP's HTTP transport but with dynamic tool routing
similar to WS Chat - tools are filtered per-user at request time.
"""

import logging
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from typing import Any

from app.services.mcp_registry import get_mcp_registry
from app.services.mcp_permission_service import get_mcp_permission_service

logger = logging.getLogger(__name__)

# Create FastMCP instance with stateless HTTP
mcp = FastMCP("omni2-mcp-gateway-v2", stateless_http=True)

# Store user context in request state (set by middleware)
_current_user_context = None


def set_user_context(context: dict):
    """Set user context for current request"""
    global _current_user_context
    _current_user_context = context


def get_user_context() -> dict:
    """Get user context for current request"""
    return _current_user_context


@mcp.tool()
async def dynamic_tool_proxy(tool_name: str, **kwargs) -> Any:
    """
    Dynamic tool proxy - routes to actual MCP tools based on user permissions.
    This matches the WS Chat approach.
    """
    user_context = get_user_context()
    if not user_context:
        raise ToolError("Authentication required")
    
    # Parse tool name (format: mcp_name__tool_name)
    if "__" not in tool_name:
        raise ToolError("Invalid tool name format. Expected: mcp_name__tool_name")
    
    mcp_name, actual_tool_name = tool_name.split("__", 1)
    
    # Check permission
    permission_service = get_mcp_permission_service()
    if not permission_service.can_call_tool(
        mcp_name,
        actual_tool_name,
        user_context.get('tool_restrictions', {})
    ):
        raise ToolError(f"Permission denied for tool: {tool_name}")
    
    # Execute tool via registry (same as WS Chat)
    registry = get_mcp_registry()
    client = registry.mcps.get(mcp_name)
    if not client:
        raise ToolError(f"MCP server not available: {mcp_name}")
    
    result = await client.call_tool(actual_tool_name, kwargs)
    return result.content


def get_fastmcp_app():
    """Get the FastMCP ASGI application"""
    return mcp.http_app(path="/")
