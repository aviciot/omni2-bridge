from fastapi import APIRouter, HTTPException, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from typing import Optional, Dict, Any
from pydantic import BaseModel
from app.database import get_db
from app.config import settings

from app.config import settings

router = APIRouter()

class ToolCallRequest(BaseModel):
    server: str
    tool: str
    arguments: Dict[str, Any] = {}

def get_auth_headers(request: Request) -> Dict[str, str]:
    """Extract auth headers from request to forward to omni2"""
    headers = {}
    auth_header = request.headers.get('Authorization')
    if auth_header:
        headers['Authorization'] = auth_header
    return headers

@router.get("/servers")
async def get_mcp_servers(
    request: Request,
    enabled_only: bool = False,
    include_health: bool = False
):
    """Get all MCP servers via Traefik (secure)"""
    async with httpx.AsyncClient() as client:
        try:
            params = {}
            if enabled_only:
                params["enabled_only"] = "true"
            if include_health:
                params["include_health"] = "true"
            
            response = await client.get(
                f"{settings.omni2_api_url}/mcp/tools/servers",
                params=params,
                headers=get_auth_headers(request)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Failed to connect to omni2 via Traefik: {str(e)}")

@router.get("/capabilities")
async def get_mcp_capabilities(request: Request, server: Optional[str] = None):
    """Get MCP capabilities via Traefik (secure)"""
    async with httpx.AsyncClient() as client:
        try:
            params = {}
            if server:
                params["server"] = server
            
            response = await client.get(
                f"{settings.omni2_api_url}/mcp/tools/capabilities",
                params=params,
                headers=get_auth_headers(request)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Failed to connect to omni2 via Traefik: {str(e)}")

@router.get("/tools")
async def get_mcp_tools(request: Request, server: Optional[str] = None):
    """Get MCP tools via Traefik (secure)"""
    async with httpx.AsyncClient() as client:
        try:
            params = {}
            if server:
                params["server"] = server
            
            response = await client.get(
                f"{settings.omni2_api_url}/mcp/tools/list",
                params=params,
                headers=get_auth_headers(request)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Failed to connect to omni2 via Traefik: {str(e)}")

@router.post("/call")
async def call_mcp_tool(request: Request, tool_request: ToolCallRequest):
    """Call MCP tool via Traefik (secure)"""
    async with httpx.AsyncClient(timeout=settings.MCP_TIMEOUT_SECONDS) as client:
        try:
            print(f"\n=== DASHBOARD BACKEND MCP CALL ===")
            print(f"Request: {tool_request.dict()}")
            
            response = await client.post(
                f"{settings.omni2_api_url}/mcp/tools/call",
                json=tool_request.dict(),
                headers=get_auth_headers(request)
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            print(f"Response text: {response.text}")
            print(f"=== END DASHBOARD BACKEND CALL ===\n")
            
            if response.status_code == 200:
                try:
                    json_response = response.json()
                    print(f"Successfully parsed JSON: {json_response}")
                    return json_response
                except Exception as json_error:
                    print(f"JSON parsing error: {json_error}")
                    raise HTTPException(status_code=500, detail=f"Failed to parse response JSON: {str(json_error)}")
            else:
                print(f"Non-200 status code: {response.status_code}")
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except httpx.RequestError as e:
            print(f"Request error: {str(e)}")
            raise HTTPException(status_code=503, detail=f"Failed to connect to omni2 via Traefik: {str(e)}")
        except HTTPException:
            raise
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@router.get("/health/{server_name}")
async def check_mcp_health(request: Request, server_name: str):
    """Check MCP server health via Traefik (secure)"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.omni2_api_url}/mcp/tools/health/{server_name}",
                headers=get_auth_headers(request)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Failed to connect to omni2 via Traefik: {str(e)}")

@router.post("/reload")
async def reload_mcps(request: Request, mcp_name: Optional[str] = None):
    """Reload MCPs via Traefik (secure)"""
    async with httpx.AsyncClient() as client:
        try:
            params = {}
            if mcp_name:
                params["mcp_name"] = mcp_name
            
            response = await client.post(
                f"{settings.omni2_api_url}/mcp/tools/reload",
                params=params,
                headers=get_auth_headers(request)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Failed to connect to omni2 via Traefik: {str(e)}")

@router.post("/servers/discover")
async def discover_mcp_server(request: Request, discovery_request: dict):
    """Discover MCP server capabilities via Traefik (secure)"""
    async with httpx.AsyncClient(timeout=settings.MCP_TIMEOUT_SECONDS) as client:
        try:
            print(f"\n=== DASHBOARD BACKEND DISCOVERY REQUEST ===")
            print(f"Request: {discovery_request}")
            
            response = await client.post(
                f"{settings.omni2_api_url}/mcp/servers/discover",
                json=discovery_request,
                headers=get_auth_headers(request)
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
            
            if response.status_code == 200:
                json_response = response.json()
                print(f"Parsed JSON: {json_response}")
                print(f"=== END DASHBOARD BACKEND DISCOVERY ===\n")
                return json_response
            else:
                print(f"=== END DASHBOARD BACKEND DISCOVERY (ERROR) ===\n")
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except httpx.RequestError as e:
            print(f"Request error: {str(e)}")
            print(f"=== END DASHBOARD BACKEND DISCOVERY (ERROR) ===\n")
            raise HTTPException(status_code=503, detail=f"Failed to connect to omni2 via Traefik: {str(e)}")

@router.post("/servers")
async def create_mcp_server(request: Request, server_data: dict):
    """Create MCP server via Traefik (secure)"""
    async with httpx.AsyncClient(timeout=settings.MCP_TIMEOUT_SECONDS) as client:
        try:
            response = await client.post(
                f"{settings.omni2_api_url}/mcp/servers",
                json=server_data,
                headers=get_auth_headers(request)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Failed to connect to omni2 via Traefik: {str(e)}")

@router.get("/servers/{server_id}")
async def get_mcp_server(request: Request, server_id: int):
    """Get MCP server details via Traefik (secure)"""
    async with httpx.AsyncClient(timeout=settings.MCP_TIMEOUT_SECONDS) as client:
        try:
            response = await client.get(
                f"{settings.omni2_api_url}/mcp/servers/{server_id}",
                headers=get_auth_headers(request)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Failed to connect to omni2 via Traefik: {str(e)}")

@router.put("/servers/{server_id}")
async def update_mcp_server(request: Request, server_id: int, server_data: dict):
    """Update MCP server via Traefik (secure)"""
    async with httpx.AsyncClient(timeout=settings.MCP_TIMEOUT_SECONDS) as client:
        try:
            response = await client.put(
                f"{settings.omni2_api_url}/mcp/servers/{server_id}",
                json=server_data,
                headers=get_auth_headers(request)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Failed to connect to omni2 via Traefik: {str(e)}")

@router.delete("/servers/{server_id}")
async def delete_mcp_server(request: Request, server_id: int):
    """Delete MCP server via Traefik (secure)"""
    async with httpx.AsyncClient(timeout=settings.MCP_TIMEOUT_SECONDS) as client:
        try:
            response = await client.delete(
                f"{settings.omni2_api_url}/mcp/servers/{server_id}",
                headers=get_auth_headers(request)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Failed to connect to omni2 via Traefik: {str(e)}")

@router.get("/servers/{server_id}/logs")
async def get_mcp_server_logs(request: Request, server_id: int):
    """Get MCP server health logs via Traefik (secure)"""
    async with httpx.AsyncClient(timeout=settings.MCP_TIMEOUT_SECONDS) as client:
        try:
            response = await client.get(
                f"{settings.omni2_api_url}/mcp/servers/{server_id}/logs",
                headers=get_auth_headers(request)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Failed to connect to omni2 via Traefik: {str(e)}")

@router.get("/servers/{server_id}/audit")
async def get_mcp_server_audit_logs(request: Request, server_id: int, status: str = None, search: str = None, limit: int = 100):
    """Get MCP server audit logs via Traefik (secure)"""
    async with httpx.AsyncClient(timeout=settings.MCP_TIMEOUT_SECONDS) as client:
        try:
            params = {'limit': limit}
            if status: params['status'] = status
            if search: params['search'] = search
            
            response = await client.get(
                f"{settings.omni2_api_url}/mcp/servers/{server_id}/audit",
                params=params,
                headers=get_auth_headers(request)
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except httpx.RequestError as e:
            raise HTTPException(status_code=503, detail=f"Failed to connect to omni2 via Traefik: {str(e)}")