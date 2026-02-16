"""
MCP Gateway Router
==================
Direct MCP access for external clients (Claude Desktop, Cursor)
Uses opaque token authentication, no LLM involved
"""

import logging
from fastapi import APIRouter, HTTPException, Header, Request, Depends
from fastapi.responses import JSONResponse
import httpx
from typing import Optional
import json
from sqlalchemy import text

from app.services.mcp_permission_service import get_mcp_permission_service, MCPPermissionService
from app.services.mcp_registry import get_mcp_registry
from app.services.mcp_gateway_session_cache import get_session_cache
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
logger = logging.getLogger(__name__)


async def validate_mcp_token(token: str) -> dict:
    """Validate MCP token via auth service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://mcp-auth-service:8700/api/v1/mcp/tokens/validate",
                json={"token": token},
                timeout=5.0
            )
            
            if response.status_code != 200:
                return None
            
            return response.json()
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        return None


@router.api_route("/mcp", methods=["POST"])
async def mcp_gateway(
    request: Request,
    authorization: Optional[str] = Header(None),
    mcp_permission_service: MCPPermissionService = Depends(get_mcp_permission_service),
    db: AsyncSession = Depends(get_db)
):
    """
    MCP Gateway Endpoint - Phase 1
    
    Implements MCP JSON-RPC 2.0 protocol:
    - initialize: Handshake and capability negotiation
    - tools/list: Return filtered tools based on user permissions
    - ping: Health check
    """
    
    # Extract token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid authorization header")
    
    token = authorization.replace("Bearer ", "").strip()
    
    # Validate token
    user_context = await validate_mcp_token(token)
    if not user_context:
        raise HTTPException(401, "Invalid or expired token")
    
    # Check MCP access
    if "mcp" not in user_context.get("omni_services", []):
        raise HTTPException(403, "Role does not have MCP gateway access")
    
    # Check if user is blocked for MCP service
    block_query = await db.execute(
        text("""
            SELECT blocked_services 
            FROM omni2.user_blocks 
            WHERE user_id = :user_id AND is_blocked = true
        """),
        {"user_id": user_context["user_id"]}
    )
    block_row = block_query.fetchone()
    if block_row:
        blocked_services = block_row.blocked_services or []
        if "mcp" in blocked_services:
            raise HTTPException(403, "MCP gateway access blocked by administrator")
    
    # Parse JSON-RPC request
    try:
        body = await request.json()
    except:
        return {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}
    
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")
    
    logger.info(f"MCP request: method={method}, user_id={user_context['user_id']}, mcp_access={user_context.get('mcp_access')}")
    
    # Handle initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "omni2-mcp-gateway",
                    "version": "1.0.0"
                }
            },
            "id": request_id
        }
    
    # Handle tools/list
    if method == "tools/list":
        # Check session cache first
        session_cache = get_session_cache()
        cached_session = session_cache.get(token)
        
        if cached_session:
            logger.info(f"Using cached session for user {cached_session.user_id}")
            return {
                "jsonrpc": "2.0",
                "result": {
                    "tools": cached_session.filtered_tools
                },
                "id": request_id
            }
        
        # Cache miss - build tools list
        mcp_access = user_context.get("mcp_access", [])
        tool_restrictions = user_context.get("tool_restrictions", {})
        
        logger.info(f"Cache miss - building tools list for user {user_context['user_id']}")
        
        # Get available MCPs for user
        available_mcps = await mcp_permission_service.get_available_mcps(mcp_access)
        
        # Get all tools from registry and filter by permissions
        registry = get_mcp_registry()
        all_tools = []
        
        for mcp in available_mcps:
            mcp_name = mcp["name"]
            mcp_tools_dict = registry.get_tools(mcp_name)
            mcp_tools = mcp_tools_dict.get(mcp_name, [])
            
            # Filter tools by user permissions
            filtered_tools = mcp_permission_service.filter_tools(mcp_name, mcp_tools, tool_restrictions)
            
            # Add to result with MCP prefix
            for tool in filtered_tools:
                all_tools.append({
                    "name": f"{mcp_name}__{tool['name']}",
                    "description": f"[{mcp_name}] {tool['description']}",
                    "inputSchema": tool["inputSchema"]
                })
        
        # Cache the result
        session_cache.set(
            token=token,
            user_id=user_context['user_id'],
            user_context=user_context,
            available_mcps=available_mcps,
            filtered_tools=all_tools
        )
        
        logger.info(f"Cached {len(all_tools)} tools for user {user_context['user_id']}")
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": all_tools
            },
            "id": request_id
        }
    
    # Handle ping
    if method == "ping":
        return {
            "jsonrpc": "2.0",
            "result": {},
            "id": request_id
        }
    
    # Handle tools/call
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": "Missing tool name"},
                "id": request_id
            }
        
        # Parse tool name (format: mcp_name__tool_name)
        if "__" not in tool_name:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": "Invalid tool name format. Expected: mcp_name__tool_name"},
                "id": request_id
            }
        
        mcp_name, actual_tool_name = tool_name.split("__", 1)
        
        # Check permission to call this tool
        if not mcp_permission_service.can_call_tool(
            mcp_name,
            actual_tool_name,
            user_context.get("tool_restrictions", {})
        ):
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Permission denied for tool: {tool_name}"},
                "id": request_id
            }
        
        # Execute tool via registry
        try:
            registry = get_mcp_registry()
            mcp_result = await registry.call_tool(mcp_name, actual_tool_name, arguments)
            
            if mcp_result.get("status") == "error":
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32000, "message": mcp_result.get("error", "Tool execution failed")},
                    "id": request_id
                }
            
            # Get the MCP client directly and call tool to get raw response
            client = registry.mcps.get(mcp_name)
            if not client:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -32000, "message": f"MCP {mcp_name} not loaded"},
                    "id": request_id
                }
            
            # Call tool directly to get CallToolResult
            tool_result = await client.call_tool(actual_tool_name, arguments)
            
            # Convert CallToolResult to dict
            # CallToolResult has .content attribute which is a list of TextContent objects
            content_list = []
            for item in tool_result.content:
                item_dict = {"type": item.type, "text": item.text}
                # Only add optional fields if they exist and are not None
                if hasattr(item, 'annotations') and item.annotations:
                    item_dict["annotations"] = item.annotations
                if hasattr(item, 'meta') and item.meta:
                    item_dict["meta"] = item.meta
                content_list.append(item_dict)
            
            result_dict = {"content": content_list}
            
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "result": result_dict,
                    "id": request_id
                }
            )
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": str(e)},
                "id": request_id
            }
    
    # Method not found
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        },
        "id": request_id
    }
