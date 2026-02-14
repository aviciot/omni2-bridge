from fastapi import APIRouter, HTTPException, Header
from typing import Optional, Dict, Any
import httpx
import structlog
from app.config import settings

router = APIRouter()
logger = structlog.get_logger()

# Use centralized Traefik URL - NEVER bypass Traefik!
OMNI2_BASE = settings.omni2_api_url
AUTH_BASE = settings.auth_service_url

async def proxy_to_omni2(
    method: str,
    path: str,
    token: str,
    json_data: Optional[Dict[str, Any]] = None
):
    """Proxy request to OMNI2 via Traefik"""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{OMNI2_BASE}{path}"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url, headers=headers)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=json_data)
            elif method == "PUT":
                response = await client.put(url, headers=headers, json=json_data)
            elif method == "DELETE":
                response = await client.delete(url, headers=headers)
            else:
                raise HTTPException(status_code=405, detail="Method not allowed")
            
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            
            return response.json()
    except httpx.HTTPError as e:
        logger.error("OMNI2 proxy error", error=str(e), path=path)
        raise HTTPException(status_code=500, detail=f"Failed to connect to OMNI2: {str(e)}")

# Role Permissions
@router.get("/admin/permissions/roles")
async def get_role_permissions(authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("GET", "/admin/permissions/roles", token)

@router.get("/admin/permissions/roles/{role_name}")
async def get_role_permissions_by_role(role_name: str, authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("GET", f"/admin/permissions/roles/{role_name}", token)

@router.post("/admin/permissions/roles")
async def create_role_permission(data: Dict[str, Any], authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("POST", "/admin/permissions/roles", token, data)

@router.delete("/admin/permissions/roles/{role_name}/{mcp_name}")
async def delete_role_permission(role_name: str, mcp_name: str, authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("DELETE", f"/admin/permissions/roles/{role_name}/{mcp_name}", token)

# Team Roles
@router.get("/admin/permissions/teams")
async def get_team_roles(authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("GET", "/admin/permissions/teams", token)

@router.post("/admin/permissions/teams")
async def create_team_role(data: Dict[str, Any], authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("POST", "/admin/permissions/teams", token, data)

@router.delete("/admin/permissions/teams/{team_name}")
async def delete_team_role(team_name: str, authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("DELETE", f"/admin/permissions/teams/{team_name}", token)

# MCP List
@router.get("/events/mcp-list")
async def get_mcp_list(authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("GET", "/events/mcp-list", token)

# Tools
@router.get("/tools")
async def get_tools(mcp: str, authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("GET", f"/tools?mcp={mcp}", token)

# Users (from auth service)
@router.get("/users")
async def get_users(
    search: Optional[str] = None,
    role_id: Optional[int] = None,
    active: Optional[bool] = None,
    authorization: str = Header(None)
):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    headers = {"Authorization": f"Bearer {token}"}
    params = {}
    if search:
        params["search"] = search
    if role_id is not None:
        params["role_id"] = role_id
    if active is not None:
        params["active"] = active
    
    url = f"{AUTH_BASE}/users/users"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers, params=params)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.HTTPError as e:
        logger.error("Auth service proxy error", error=str(e), path="/users/users")
        raise HTTPException(status_code=500, detail=f"Failed to connect to auth service: {str(e)}")

# Roles (from auth service)
@router.get("/roles")
async def get_roles(authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{AUTH_BASE}/roles"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.HTTPError as e:
        logger.error("Auth service proxy error", error=str(e), path="/roles")
        raise HTTPException(status_code=500, detail=f"Failed to connect to auth service: {str(e)}")

@router.get("/roles/{role_id}")
async def get_role(role_id: int, authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{AUTH_BASE}/roles/{role_id}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.HTTPError as e:
        logger.error("Auth service proxy error", error=str(e), path=f"/roles/{role_id}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to auth service: {str(e)}")

@router.post("/roles")
async def create_role(data: Dict[str, Any], authorization: str = Header(None), x_user_role: str = Header(None, alias="X-User-Role")):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-User-Role": x_user_role or "super_admin"
    }
    url = f"{AUTH_BASE}/roles"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=data)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.HTTPError as e:
        logger.error("Auth service proxy error", error=str(e), path="/roles")
        raise HTTPException(status_code=500, detail=f"Failed to connect to auth service: {str(e)}")

@router.put("/roles/{role_id}")
async def update_role(role_id: int, data: Dict[str, Any], authorization: str = Header(None), x_user_role: str = Header(None, alias="X-User-Role")):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-User-Role": x_user_role or "super_admin"
    }
    url = f"{AUTH_BASE}/roles/{role_id}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(url, headers=headers, json=data)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.HTTPError as e:
        logger.error("Auth service proxy error", error=str(e), path=f"/roles/{role_id}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to auth service: {str(e)}")

@router.delete("/roles/{role_id}")
async def delete_role(role_id: int, authorization: str = Header(None), x_user_role: str = Header(None, alias="X-User-Role")):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-User-Role": x_user_role or "super_admin"
    }
    url = f"{AUTH_BASE}/roles/{role_id}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=headers)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.HTTPError as e:
        logger.error("Auth service proxy error", error=str(e), path=f"/roles/{role_id}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to auth service: {str(e)}")

# Teams (from auth service)
@router.get("/teams")
async def get_teams(authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{AUTH_BASE}/teams"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.HTTPError as e:
        logger.error("Auth service proxy error", error=str(e), path="/teams")
        raise HTTPException(status_code=500, detail=f"Failed to connect to auth service: {str(e)}")

@router.post("/teams")
async def create_team(data: Dict[str, Any], authorization: str = Header(None), x_user_role: str = Header(None, alias="X-User-Role")):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-User-Role": x_user_role or "super_admin"
    }
    url = f"{AUTH_BASE}/teams"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=data)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.HTTPError as e:
        logger.error("Auth service proxy error", error=str(e), path="/teams")
        raise HTTPException(status_code=500, detail=f"Failed to connect to auth service: {str(e)}")

@router.delete("/teams/{team_id}")
async def delete_team(team_id: int, authorization: str = Header(None), x_user_role: str = Header(None, alias="X-User-Role")):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-User-Role": x_user_role or "super_admin"
    }
    url = f"{AUTH_BASE}/teams/{team_id}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=headers)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.HTTPError as e:
        logger.error("Auth service proxy error", error=str(e), path=f"/teams/{team_id}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to auth service: {str(e)}")

@router.get("/teams/{team_id}")
async def get_team(team_id: int, authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{AUTH_BASE}/teams/{team_id}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.HTTPError as e:
        logger.error("Auth service proxy error", error=str(e), path=f"/teams/{team_id}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to auth service: {str(e)}")

@router.put("/teams/{team_id}")
async def update_team(team_id: int, data: Dict[str, Any], authorization: str = Header(None), x_user_role: str = Header(None, alias="X-User-Role")):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-User-Role": x_user_role or "super_admin"
    }
    url = f"{AUTH_BASE}/teams/{team_id}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(url, headers=headers, json=data)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.HTTPError as e:
        logger.error("Auth service proxy error", error=str(e), path=f"/teams/{team_id}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to auth service: {str(e)}")

@router.post("/teams/{team_id}/members/{user_id}")
async def add_team_member(team_id: int, user_id: int, authorization: str = Header(None), x_user_role: str = Header(None, alias="X-User-Role")):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-User-Role": x_user_role or "super_admin"
    }
    url = f"{AUTH_BASE}/teams/{team_id}/members/{user_id}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.HTTPError as e:
        logger.error("Auth service proxy error", error=str(e), path=f"/teams/{team_id}/members/{user_id}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to auth service: {str(e)}")

@router.delete("/teams/{team_id}/members/{user_id}")
async def remove_team_member(team_id: int, user_id: int, authorization: str = Header(None), x_user_role: str = Header(None, alias="X-User-Role")):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-User-Role": x_user_role or "super_admin"
    }
    url = f"{AUTH_BASE}/teams/{team_id}/members/{user_id}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.delete(url, headers=headers)
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.HTTPError as e:
        logger.error("Auth service proxy error", error=str(e), path=f"/teams/{team_id}/members/{user_id}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to auth service: {str(e)}")

# Chat Configuration
@router.get("/chat-config/users/{user_id}/block")
async def get_user_block_status(user_id: int, authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("GET", f"/iam/chat-config/users/{user_id}/block", token)

@router.put("/chat-config/users/{user_id}/block")
async def update_user_block_status(user_id: int, data: Dict[str, Any], authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("PUT", f"/iam/chat-config/users/{user_id}/block", token, data)

@router.get("/chat-config/users/{user_id}/welcome")
async def get_user_welcome_message(user_id: int, authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("GET", f"/iam/chat-config/users/{user_id}/welcome", token)

@router.put("/chat-config/users/{user_id}/welcome")
async def update_user_welcome_message(user_id: int, data: Dict[str, Any], authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("PUT", f"/iam/chat-config/users/{user_id}/welcome", token, data)

@router.get("/chat-config/roles/{role_id}/welcome")
async def get_role_welcome_message(role_id: int, authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("GET", f"/iam/chat-config/roles/{role_id}/welcome", token)

@router.put("/chat-config/roles/{role_id}/welcome")
async def update_role_welcome_message(role_id: int, data: Dict[str, Any], authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("PUT", f"/iam/chat-config/roles/{role_id}/welcome", token, data)

@router.get("/chat-config/welcome/default")
async def get_default_welcome_message(authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("GET", "/iam/chat-config/welcome/default", token)

@router.put("/chat-config/welcome/default")
async def update_default_welcome_message(data: Dict[str, Any], authorization: str = Header(None)):
    token = authorization.replace("Bearer ", "") if authorization else None
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    return await proxy_to_omni2("PUT", "/iam/chat-config/welcome/default", token, data)
