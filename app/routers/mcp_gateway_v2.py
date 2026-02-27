"""
MCP Gateway V2 - HTTP Streamable Transport
===========================================
Implements MCP protocol over HTTP with newline-delimited JSON streaming
"""

import json
import asyncio
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Header, Request, Depends
from fastapi.responses import StreamingResponse
import httpx
from typing import Optional
from sqlalchemy import text

from app.services.mcp_permission_service import get_mcp_permission_service, MCPPermissionService
from app.services.mcp_registry import get_mcp_registry
from app.services.mcp_gateway_session_cache import get_session_cache
from app.services.flow_tracker import get_flow_tracker, FlowTracker
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.logger import logger

router = APIRouter()
logger = logger.bind(service="MCPGateway")


async def validate_mcp_token(token: str) -> dict:
    """Validate MCP token via auth service with caching"""
    session_cache = get_session_cache()
    cached_session = session_cache.get(token)
    
    if cached_session and cached_session.user_context:
        logger.debug(f"Token validation cache hit for user {cached_session.user_id}")
        return cached_session.user_context
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://mcp-auth-service:8700/api/v1/mcp/tokens/validate",
                json={"token": token},
                timeout=5.0
            )
            
            if response.status_code != 200:
                return None
            
            user_context = response.json()
            
            session_cache.set(
                token=token,
                user_id=user_context["user_id"],
                user_context=user_context,
                available_mcps=[],
                filtered_tools=[]
            )
            
            logger.debug(f"Token validated and cached for user {user_context['user_id']}")
            return user_context
    except Exception as e:
        logger.error(f"Token validation failed: {e}")
        return None


async def streamable_generator(user_context: dict, body: dict, mcp_permission_service: MCPPermissionService, token: str, flow_tracker: FlowTracker = None, db: AsyncSession = None, session_id: str = None):
    """Generate HTTP streamable responses for MCP protocol"""
    method = body.get("method")
    params = body.get("params", {})
    request_id = body.get("id")
    
    logger.debug("MCP-V2 request", method=method, user_id=user_context['user_id'])
    
    # Handle initialize
    if method == "initialize":
        response = {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "omni2-mcp-gateway-v2", "version": "1.0.0"}
            },
            "id": request_id
        }
        yield json.dumps(response) + "\n"
    
    # Handle tools/list
    elif method == "tools/list":
        mcp_access = user_context.get("mcp_access", [])
        tool_restrictions = user_context.get("tool_restrictions", {})
        
        available_mcps = await mcp_permission_service.get_available_mcps(mcp_access)
        registry = get_mcp_registry()
        all_tools = []
        for mcp in available_mcps:
            mcp_name = mcp["name"]
            mcp_tools = registry.get_tools(mcp_name).get(mcp_name, [])
            filtered_tools = mcp_permission_service.filter_tools(mcp_name, mcp_tools, tool_restrictions)
            for tool in filtered_tools:
                all_tools.append({
                    "name": f"{mcp_name}__{tool['name']}",
                    "description": f"[{mcp_name}] {tool['description']}",
                    "inputSchema": tool["inputSchema"]
                })
        logger.debug("tools/list", user_id=user_context['user_id'], total=len(all_tools))
        
        response = {"jsonrpc": "2.0", "result": {"tools": all_tools}, "id": request_id}
        yield json.dumps(response) + "\n"
    
    # Handle prompts/list
    elif method == "prompts/list":
        mcp_access = user_context.get("mcp_access", [])
        tool_restrictions = user_context.get("tool_restrictions", {})
        
        available_mcps = await mcp_permission_service.get_available_mcps(mcp_access)
        registry = get_mcp_registry()
        all_prompts = []
        for mcp in available_mcps:
            mcp_name = mcp["name"]
            mcp_prompts = registry.get_prompts(mcp_name).get(mcp_name, [])
            filtered_prompts = mcp_permission_service.filter_prompts(mcp_name, mcp_prompts, tool_restrictions)
            for prompt in filtered_prompts:
                prompt_data = {
                    "name": f"{mcp_name}__{prompt['name']}",
                    "description": prompt.get('description', '')
                }
                if 'arguments' in prompt:
                    prompt_data['arguments'] = [
                        {**arg, 'required': bool(arg.get('required'))} for arg in prompt['arguments']
                    ]
                all_prompts.append(prompt_data)
        
        logger.debug("prompts/list", user_id=user_context['user_id'], total=len(all_prompts))
        
        response = {"jsonrpc": "2.0", "result": {"prompts": all_prompts}, "id": request_id}
        yield json.dumps(response) + "\n"
    
    # Handle resources/list
    elif method == "resources/list":
        mcp_access = user_context.get("mcp_access", [])
        tool_restrictions = user_context.get("tool_restrictions", {})
        
        available_mcps = await mcp_permission_service.get_available_mcps(mcp_access)
        registry = get_mcp_registry()
        all_resources = []
        for mcp in available_mcps:
            mcp_name = mcp["name"]
            mcp_resources = registry.get_resources(mcp_name).get(mcp_name, [])
            filtered_resources = mcp_permission_service.filter_resources(mcp_name, mcp_resources, tool_restrictions)
            
            for resource in filtered_resources:
                uri_str = str(resource['uri'])
                all_resources.append({
                    "uri": uri_str,
                    "name": f"{mcp_name}__{resource.get('name') or uri_str}",
                    "description": resource.get('description') or '',
                    "mimeType": resource.get('mimeType') or 'text/plain'
                })
        
        logger.debug("resources/list", user_id=user_context['user_id'], total=len(all_resources))
        
        response = {"jsonrpc": "2.0", "result": {"resources": all_resources}, "id": request_id}
        yield json.dumps(response) + "\n"
    
    # Handle prompts/get
    elif method == "prompts/get":
        prompt_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not prompt_name or "__" not in prompt_name:
            response = {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid prompt name"}, "id": request_id}
            yield json.dumps(response) + "\n"
        else:
            mcp_name, actual_prompt_name = prompt_name.split("__", 1)
            
            try:
                registry = get_mcp_registry()
                client = registry.mcps.get(mcp_name)
                if not client:
                    response = {"jsonrpc": "2.0", "error": {"code": -32603, "message": "MCP not available"}, "id": request_id}
                    yield json.dumps(response) + "\n"
                else:
                    result = await client.get_prompt(actual_prompt_name, arguments)
                    logger.debug("prompts/get", user_id=user_context['user_id'], mcp=mcp_name, prompt=actual_prompt_name)
                    messages = [{"role": m.role, "content": {"type": "text", "text": m.content.text}} for m in result.messages]
                    response = {"jsonrpc": "2.0", "result": {"messages": messages}, "id": request_id}
                    yield json.dumps(response) + "\n"
            except Exception as e:
                logger.error("Prompt execution error", mcp=mcp_name, prompt=actual_prompt_name, error=str(e))
                response = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": request_id}
                yield json.dumps(response) + "\n"
    
    # Handle tools/call
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if not tool_name or "__" not in tool_name:
            response = {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid tool name"}, "id": request_id}
            yield json.dumps(response) + "\n"
        else:
            mcp_name, actual_tool_name = tool_name.split("__", 1)
            
            can_call = mcp_permission_service.can_call_tool(mcp_name, actual_tool_name, user_context.get("tool_restrictions", {}))
            if not can_call:
                logger.warning("Tool call denied", user_id=user_context['user_id'], tool=f"{mcp_name}__{actual_tool_name}")
                response = {"jsonrpc": "2.0", "error": {"code": -32603, "message": "Permission denied"}, "id": request_id}
                yield json.dumps(response) + "\n"
            else:
                try:
                    registry = get_mcp_registry()
                    client = registry.mcps.get(mcp_name)
                    if not client:
                        response = {"jsonrpc": "2.0", "error": {"code": -32603, "message": "MCP not available"}, "id": request_id}
                        yield json.dumps(response) + "\n"
                    else:
                        result = await client.call_tool(actual_tool_name, arguments)
                        logger.info("tools/call", user_id=user_context['user_id'], mcp=mcp_name, tool=actual_tool_name)
                        if flow_tracker and db and session_id:
                            await flow_tracker.log_event(session_id, user_context['user_id'], 'tool_call', db, mcp=mcp_name, tool=actual_tool_name, source="mcp_gateway")
                            await flow_tracker.save_to_db(session_id, user_context['user_id'], db, source="mcp_gateway")
                        content = [{"type": "text", "text": c.text} for c in result.content]
                        response = {"jsonrpc": "2.0", "result": {"content": content}, "id": request_id}
                        yield json.dumps(response) + "\n"
                except Exception as e:
                    logger.error("Tool execution error", mcp=mcp_name, tool=actual_tool_name, error=str(e))
                    response = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": request_id}
                    yield json.dumps(response) + "\n"
    
    # Handle resources/read
    elif method == "resources/read":
        uri = params.get("uri")
        
        if not uri:
            response = {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Missing resource URI"}, "id": request_id}
            yield json.dumps(response) + "\n"
        else:
            # Find which MCP owns this URI by scanning the registry
            mcp_access = user_context.get("mcp_access", [])
            available_mcps = await mcp_permission_service.get_available_mcps(mcp_access)
            registry = get_mcp_registry()
            
            mcp_name = None
            for mcp in available_mcps:
                mcp_resources_dict = registry.get_resources(mcp["name"])
                mcp_resources = mcp_resources_dict.get(mcp["name"], [])
                if any(str(r["uri"]) == uri for r in mcp_resources):
                    mcp_name = mcp["name"]
                    break
            
            if not mcp_name:
                response = {"jsonrpc": "2.0", "error": {"code": -32602, "message": f"Resource not found: {uri}"}, "id": request_id}
                yield json.dumps(response) + "\n"
            else:
                try:
                    client = registry.mcps.get(mcp_name)
                    result = await client.read_resource(uri)
                    contents = [{"uri": uri, "mimeType": str(c.mimeType) if hasattr(c, 'mimeType') else "text/plain", "text": c.text} for c in result.contents]
                    response = {"jsonrpc": "2.0", "result": {"contents": contents}, "id": request_id}
                    yield json.dumps(response) + "\n"
                except Exception as e:
                    logger.error("Resource read error", uri=uri, error=str(e))
                    response = {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": request_id}
                    yield json.dumps(response) + "\n"
    
    # Handle ping
    elif method == "ping":
        response = {"jsonrpc": "2.0", "result": {}, "id": request_id}
        yield json.dumps(response) + "\n"
    
    # Handle notifications (no response needed)
    elif method in ["notifications/initialized", "notifications/cancelled", "notifications/progress"]:
        pass
    
    # Handle logging/setLevel (acknowledge but don't change anything)
    elif method == "logging/setLevel":
        response = {"jsonrpc": "2.0", "result": {}, "id": request_id}
        yield json.dumps(response) + "\n"
    
    # Handle resources/templates/list (return empty for now)
    elif method == "resources/templates/list":
        response = {"jsonrpc": "2.0", "result": {"resourceTemplates": []}, "id": request_id}
        yield json.dumps(response) + "\n"
    
    # Unknown method
    else:
        response = {"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": request_id}
        yield json.dumps(response) + "\n"


@router.post("/mcp-v2")
async def mcp_gateway_v2(
    request: Request,
    authorization: Optional[str] = Header(None),
    mcp_permission_service: MCPPermissionService = Depends(get_mcp_permission_service),
    db: AsyncSession = Depends(get_db),
    flow_tracker: FlowTracker = Depends(get_flow_tracker)
):
    """MCP Gateway V2 - HTTP Streamable Transport"""
    
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
    
    # Check if user is blocked
    block_query = await db.execute(
        text("SELECT blocked_services FROM omni2.user_blocks WHERE user_id = :user_id AND is_blocked = true"),
        {"user_id": user_context["user_id"]}
    )
    block_row = block_query.fetchone()
    if block_row and "mcp" in (block_row.blocked_services or []):
        raise HTTPException(403, "MCP gateway access blocked by administrator")
    
    # Parse JSON-RPC request
    try:
        body = await request.json()
    except:
        raise HTTPException(400, "Invalid JSON")
    
    session_id = str(uuid4())
    # Use stable flow_session_id from token cache so all tool calls group into one session
    cached = get_session_cache().get(token)
    flow_session_id = cached.flow_session_id if cached and cached.flow_session_id else session_id
    # Return HTTP streamable response
    return StreamingResponse(
        streamable_generator(user_context, body, mcp_permission_service, token, flow_tracker, db, flow_session_id),
        media_type="application/json",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
