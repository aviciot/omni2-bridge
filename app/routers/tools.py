"""
MCP Tools Router

Exposes MCP tool discovery and execution endpoints.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.services.mcp_client import get_mcp_client, MCPClient
from app.utils.logger import logger


router = APIRouter(prefix="/mcp/tools", tags=["mcp-tools"])


# ============================================================
# Request/Response Models
# ============================================================

class ToolCallRequest(BaseModel):
    """Request model for calling an MCP tool."""
    
    server: str = Field(..., description="MCP server name")
    tool: str = Field(..., description="Tool name to execute")
    arguments: Dict[str, Any] = Field(default={}, description="Tool arguments")


class ToolCallResponse(BaseModel):
    """Response model for tool execution."""
    
    success: bool
    server: str
    tool: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# ============================================================
# Endpoints
# ============================================================

@router.get("/list")
async def list_tools(
    server: Optional[str] = None,
    mcp_client: MCPClient = Depends(get_mcp_client),
):
    """
    List available tools from MCP servers.
    
    Args:
        server: Optional server name to filter by
        mcp_client: MCP client instance (injected)
        
    Returns:
        Dict with tools grouped by server
    """
    try:
        logger.info(
            "📋 Listing MCP tools",
            server_filter=server,
        )
        
        tools = await mcp_client.list_tools(server_name=server)
        
        return {
            "success": True,
            "data": tools,
        }
        
    except ValueError as e:
        logger.warning("⚠️  Invalid request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(
            "❌ Failed to list tools",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list tools: {str(e)}",
        )


@router.post("/call")
async def call_tool(
    request: ToolCallRequest,
    mcp_client: MCPClient = Depends(get_mcp_client),
) -> ToolCallResponse:
    """
    Execute an MCP tool.
    
    Args:
        request: Tool call request
        mcp_client: MCP client instance (injected)
        
    Returns:
        Tool execution result
    """
    try:
        logger.info(
            "🔧 Executing MCP tool",
            server=request.server,
            tool=request.tool,
            args=request.arguments,
        )
        
        result = await mcp_client.call_tool(
            server_name=request.server,
            tool_name=request.tool,
            arguments=request.arguments,
        )
        
        return ToolCallResponse(
            success=True,
            server=request.server,
            tool=request.tool,
            result=result,
        )
        
    except ValueError as e:
        logger.warning("⚠️  Invalid request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(
            "❌ Failed to execute tool",
            server=request.server,
            tool=request.tool,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Tool execution failed: {str(e)}",
        )


@router.get("/health/{server_name}")
async def check_server_health(
    server_name: str,
    mcp_client: MCPClient = Depends(get_mcp_client),
):
    """
    Check health status of an MCP server.
    
    Args:
        server_name: Name of the MCP server
        mcp_client: MCP client instance (injected)
        
    Returns:
        Health status
    """
    try:
        logger.info(
            "🏥 Checking MCP server health",
            server=server_name,
        )
        
        health = await mcp_client.health_check(server_name)
        
        return {
            "success": True,
            "server": server_name,
            "health": health,
        }
        
    except Exception as e:
        logger.error(
            "❌ Health check failed",
            server=server_name,
            error=str(e),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}",
        )
