"""
MCP Server Management Router

CRUD operations for managing MCP servers:
- Create new MCP server
- Update existing MCP server  
- Delete MCP server
- Test MCP server connection and discover capabilities
"""

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, field_validator
import httpx
import asyncio

from app.database import get_db
from app.models import MCPServer
from app.services.mcp_registry import get_mcp_registry
from app.utils.logger import logger

router = APIRouter(prefix="/mcp/servers")

# ============================================================
# Request/Response Models
# ============================================================

class MCPServerCreate(BaseModel):
    """Request model for creating MCP server."""
    
    name: str = Field(..., description="Unique server name", min_length=1, max_length=100)
    url: str = Field(..., description="MCP server URL", min_length=1, max_length=500)
    description: Optional[str] = Field(None, description="Server description", max_length=1000)
    protocol: str = Field("http", description="Protocol type")
    timeout_seconds: int = Field(30, description="Request timeout", ge=5, le=300)
    auth_type: Optional[str] = Field(None, description="Authentication type")
    auth_config: Optional[Dict[str, Any]] = Field(None, description="Authentication configuration")
    
    @field_validator('protocol')
    @classmethod
    def validate_protocol(cls, v):
        allowed = ['http', 'sse', 'http-streamable']
        if v not in allowed:
            raise ValueError(f'Protocol must be one of: {allowed}')
        return v
    
    @field_validator('auth_type')
    @classmethod
    def validate_auth_type(cls, v):
        if v is not None:
            allowed = ['bearer', 'api_key', 'custom_headers']
            if v not in allowed:
                raise ValueError(f'Auth type must be one of: {allowed}')
        return v

class MCPServerUpdate(BaseModel):
    """Request model for updating MCP server."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    url: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=1000)
    protocol: Optional[str] = Field(None)
    timeout_seconds: Optional[int] = Field(None, ge=5, le=300)
    status: Optional[str] = Field(None)
    auth_type: Optional[str] = Field(None)
    auth_config: Optional[Dict[str, Any]] = Field(None)
    
    @field_validator('protocol')
    @classmethod
    def validate_protocol(cls, v):
        if v is not None:
            allowed = ['http', 'sse', 'http-streamable']
            if v not in allowed:
                raise ValueError(f'Protocol must be one of: {allowed}')
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        if v is not None:
            allowed = ['active', 'inactive', 'error']
            if v not in allowed:
                raise ValueError(f'Status must be one of: {allowed}')
        return v

class MCPDiscoveryRequest(BaseModel):
    """Request model for MCP server discovery."""
    
    url: str = Field(..., description="MCP server URL")
    protocol: str = Field("http", description="Protocol type")
    timeout_seconds: int = Field(30, ge=5, le=300)
    auth_type: Optional[str] = Field(None)
    auth_config: Optional[Dict[str, Any]] = Field(None)

class MCPDiscoveryResponse(BaseModel):
    """Response model for MCP server discovery."""
    
    success: bool
    health_status: str
    response_time_ms: int
    capabilities: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tools_count: int = 0
    prompts_count: int = 0
    resources_count: int = 0

# ============================================================
# Helper Functions
# ============================================================

def build_auth_headers(auth_type: Optional[str], auth_config: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """Build authentication headers from config."""
    headers = {}
    
    if not auth_type or not auth_config:
        return headers
    
    if auth_type == 'bearer' and 'token' in auth_config:
        headers['Authorization'] = f"Bearer {auth_config['token']}"
    elif auth_type == 'api_key':
        if 'header_name' in auth_config and 'api_key' in auth_config:
            headers[auth_config['header_name']] = auth_config['api_key']
    elif auth_type == 'custom_headers' and 'headers' in auth_config:
        headers.update(auth_config['headers'])
    
    return headers

async def test_mcp_connection(
    url: str, 
    protocol: str = "http", 
    timeout_seconds: int = 30,
    auth_type: Optional[str] = None,
    auth_config: Optional[Dict[str, Any]] = None
) -> MCPDiscoveryResponse:
    """Test MCP server connection and discover capabilities."""
    
    import time
    start_time = time.time()
    
    try:
        headers = build_auth_headers(auth_type, auth_config)
        
        # Add required headers for SSE/streamable protocols
        if protocol in ['sse', 'http-streamable']:
            headers.update({
                'Accept': 'application/json, text/event-stream',
                'Content-Type': 'application/json'
            })
        
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            # For SSE/streamable protocols, try MCP initialization
            if protocol in ['sse', 'http-streamable']:
                test_url = f"{url.rstrip('/')}/mcp"
                
                # Try MCP initialize request
                try:
                    init_payload = {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {},
                            "clientInfo": {"name": "omni2-discovery", "version": "1.0.0"}
                        }
                    }
                    
                    test_response = await client.post(test_url, json=init_payload, headers=headers)
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    if test_response.status_code == 200:
                        # Try to get tools count from initialize response
                        try:
                            init_data = test_response.json()
                            print(f"\n=== MCP INITIALIZE RESPONSE ===")
                            print(f"Full init response: {init_data}")
                            
                            if 'result' in init_data and 'capabilities' in init_data['result']:
                                server_caps = init_data['result']['capabilities']
                                print(f"Server capabilities: {server_caps}")
                                # If server supports tools capability, show estimated count
                                tools_count = 1 if 'tools' in server_caps else 0
                                print(f"Tools capability detected: {'tools' in server_caps}, count: {tools_count}")
                            else:
                                tools_count = 0
                                print(f"No capabilities found, tools_count: {tools_count}")
                            print(f"=== END MCP INITIALIZE ===\n")
                        except Exception as e:
                            print(f"Error parsing init response: {e}")
                            tools_count = 0
                        
                        return MCPDiscoveryResponse(
                            success=True,
                            health_status="healthy",
                            response_time_ms=response_time_ms,
                            tools_count=tools_count,
                            prompts_count=0,
                            resources_count=0
                        )
                    else:
                        return MCPDiscoveryResponse(
                            success=False,
                            health_status="unhealthy",
                            response_time_ms=response_time_ms,
                            error=f"MCP initialize failed: {test_response.status_code} - {test_response.text}"
                        )
                        
                except Exception as e:
                    return MCPDiscoveryResponse(
                        success=False,
                        health_status="error",
                        response_time_ms=int((time.time() - start_time) * 1000),
                        error=f"MCP connection failed: {str(e)}"
                    )
            else:
                # For HTTP, try health endpoint
                test_url = f"{url.rstrip('/')}/health" if not url.endswith('/health') else url
                
                try:
                    test_response = await client.get(test_url, headers=headers)
                    response_time_ms = int((time.time() - start_time) * 1000)
                    
                    if test_response.status_code == 200:
                        health_status = "healthy"
                    else:
                        return MCPDiscoveryResponse(
                            success=False,
                            health_status="unhealthy",
                            response_time_ms=response_time_ms,
                            error=f"Server check failed: {test_response.status_code}"
                        )
                except Exception as e:
                    return MCPDiscoveryResponse(
                        success=False,
                        health_status="error",
                        response_time_ms=int((time.time() - start_time) * 1000),
                        error=f"Connection failed: {str(e)}"
                    )
                
                # Try to discover capabilities for HTTP servers
                tools_count = prompts_count = resources_count = 0
                capabilities = {}
                
                try:
                    base_url = url.rstrip('/health').rstrip('/')
                    
                    # List tools
                    try:
                        tools_response = await client.get(f"{base_url}/tools", headers=headers)
                        if tools_response.status_code == 200:
                            tools_data = tools_response.json()
                            capabilities['tools'] = tools_data
                            tools_count = len(tools_data.get('tools', []))
                    except:
                        pass
                    
                    # List prompts
                    try:
                        prompts_response = await client.get(f"{base_url}/prompts", headers=headers)
                        if prompts_response.status_code == 200:
                            prompts_data = prompts_response.json()
                            capabilities['prompts'] = prompts_data
                            prompts_count = len(prompts_data.get('prompts', []))
                    except:
                        pass
                    
                    # List resources
                    try:
                        resources_response = await client.get(f"{base_url}/resources", headers=headers)
                        if resources_response.status_code == 200:
                            resources_data = resources_response.json()
                            capabilities['resources'] = resources_data
                            resources_count = len(resources_data.get('resources', []))
                    except:
                        pass
                        
                except Exception as e:
                    logger.warning(f"Failed to discover capabilities: {str(e)}")
                
                return MCPDiscoveryResponse(
                    success=True,
                    health_status="healthy",
                    response_time_ms=response_time_ms,
                    capabilities=capabilities if capabilities else None,
                    tools_count=tools_count,
                    prompts_count=prompts_count,
                    resources_count=resources_count
                )
            
    except httpx.TimeoutException:
        return MCPDiscoveryResponse(
            success=False,
            health_status="timeout",
            response_time_ms=int((time.time() - start_time) * 1000),
            error="Connection timeout"
        )
    except Exception as e:
        return MCPDiscoveryResponse(
            success=False,
            health_status="error",
            response_time_ms=int((time.time() - start_time) * 1000),
            error=str(e)
        )

# ============================================================
# Endpoints
# ============================================================

@router.post("/discover")
async def discover_mcp_server(request: MCPDiscoveryRequest) -> MCPDiscoveryResponse:
    """
    Test MCP server connection and discover capabilities.
    Does not save to database - used for validation during setup.
    """
    logger.info("🔍 Discovering MCP server", url=request.url, protocol=request.protocol)
    
    result = await test_mcp_connection(
        url=request.url,
        protocol=request.protocol,
        timeout_seconds=request.timeout_seconds,
        auth_type=request.auth_type,
        auth_config=request.auth_config
    )
    
    logger.info("✅ MCP discovery completed", 
                url=request.url, 
                success=result.success, 
                tools=result.tools_count)
    
    print(f"\n=== OMNI2 DISCOVERY RESPONSE ===")
    print(f"URL: {request.url}")
    print(f"Protocol: {request.protocol}")
    print(f"Success: {result.success}")
    print(f"Tools Count: {result.tools_count}")
    print(f"Full Response: {result.model_dump()}")
    print(f"=== END OMNI2 DISCOVERY ===\n")
    
    return result

@router.post("")
async def create_mcp_server(
    server: MCPServerCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new MCP server."""
    try:
        logger.info("➕ Creating MCP server", name=server.name, url=server.url)
        
        # Check if name already exists
        result = await db.execute(
            select(MCPServer).where(MCPServer.name == server.name)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail=f"MCP server '{server.name}' already exists")
        
        # Create new server
        new_server = MCPServer(
            name=server.name,
            url=server.url,
            description=server.description,
            protocol=server.protocol,
            timeout_seconds=server.timeout_seconds,
            auth_type=server.auth_type,
            auth_config=server.auth_config,
            status='active'
        )
        
        db.add(new_server)
        await db.commit()
        await db.refresh(new_server)
        
        logger.info("✅ MCP server created", name=server.name, id=new_server.id)
        
        return {
            "success": True,
            "message": f"MCP server '{server.name}' created successfully",
            "server": {
                "id": new_server.id,
                "name": new_server.name,
                "url": new_server.url,
                "status": new_server.status
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to create MCP server", name=server.name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to create server: {str(e)}")

@router.put("/{server_id}")
async def update_mcp_server(
    server_id: int,
    updates: MCPServerUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update existing MCP server."""
    try:
        logger.info("✏️ Updating MCP server", server_id=server_id)
        
        # Get existing server
        result = await db.execute(
            select(MCPServer).where(MCPServer.id == server_id)
        )
        server = result.scalar_one_or_none()
        
        if not server:
            raise HTTPException(status_code=404, detail=f"MCP server {server_id} not found")
        
        # Check name uniqueness if changing name
        if updates.name and updates.name != server.name:
            result = await db.execute(
                select(MCPServer).where(MCPServer.name == updates.name)
            )
            if result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail=f"MCP server '{updates.name}' already exists")
        
        # Update fields
        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(server, field, value)
        
        await db.commit()
        await db.refresh(server)
        
        logger.info("✅ MCP server updated", server_id=server_id, name=server.name)
        
        return {
            "success": True,
            "message": f"MCP server '{server.name}' updated successfully",
            "server": {
                "id": server.id,
                "name": server.name,
                "url": server.url,
                "status": server.status
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to update MCP server", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to update server: {str(e)}")

@router.delete("/{server_id}")
async def delete_mcp_server(
    server_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete MCP server."""
    try:
        logger.info("🗑️ Deleting MCP server", server_id=server_id)
        
        # Get existing server
        result = await db.execute(
            select(MCPServer).where(MCPServer.id == server_id)
        )
        server = result.scalar_one_or_none()
        
        if not server:
            raise HTTPException(status_code=404, detail=f"MCP server {server_id} not found")
        
        server_name = server.name
        
        # Delete server (cascade will handle related records)
        from sqlalchemy import delete
        await db.execute(delete(MCPServer).where(MCPServer.id == server_id))
        await db.commit()
        
        logger.info("✅ MCP server deleted", server_id=server_id, name=server_name)
        
        return {
            "success": True,
            "message": f"MCP server '{server_name}' deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to delete MCP server", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete server: {str(e)}")

@router.get("/{server_id}")
async def get_mcp_server(
    server_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get MCP server details."""
    try:
        result = await db.execute(
            select(MCPServer).where(MCPServer.id == server_id)
        )
        server = result.scalar_one_or_none()
        
        if not server:
            raise HTTPException(status_code=404, detail=f"MCP server {server_id} not found")
        
        return {
            "success": True,
            "server": {
                "id": server.id,
                "name": server.name,
                "url": server.url,
                "description": server.description,
                "protocol": server.protocol,
                "timeout_seconds": server.timeout_seconds,
                "status": server.status,
                "auth_type": server.auth_type,
                "auth_config": server.auth_config,
                "health_status": server.health_status,
                "last_health_check": server.last_health_check.isoformat() if server.last_health_check else None,
                "created_at": server.created_at.isoformat(),
                "updated_at": server.updated_at.isoformat()
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get MCP server", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get server: {str(e)}")

@router.get("/{server_id}/logs")
async def get_mcp_server_logs(
    server_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get MCP server health logs."""
    try:
        # Get server info
        result = await db.execute(
            select(MCPServer).where(MCPServer.id == server_id)
        )
        server = result.scalar_one_or_none()
        
        if not server:
            raise HTTPException(status_code=404, detail=f"MCP server {server_id} not found")
        
        # Get health logs
        from app.models import MCPHealthLog
        result = await db.execute(
            select(MCPHealthLog)
            .where(MCPHealthLog.mcp_server_id == server_id)
            .order_by(MCPHealthLog.timestamp.desc())
            .limit(100)
        )
        logs = result.scalars().all()
        
        return {
            "success": True,
            "server": {
                "id": server.id,
                "name": server.name,
                "url": server.url
            },
            "logs": [
                {
                    "id": log.id,
                    "timestamp": log.timestamp.isoformat(),
                    "status": log.status,
                    "response_time_ms": log.response_time_ms,
                    "error_message": log.error_message,
                    "event_type": log.event_type,
                    "meta_data": log.meta_data
                }
                for log in logs
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get MCP server logs", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get server logs: {str(e)}")

@router.post("/{server_id}/health-check")
async def trigger_health_check(
    server_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Trigger immediate health check for MCP server."""
    try:
        from datetime import datetime, timezone
        
        logger.info("🏥 Triggering health check", server_id=server_id)
        
        # Get server
        result = await db.execute(
            select(MCPServer).where(MCPServer.id == server_id)
        )
        server = result.scalar_one_or_none()
        
        if not server:
            raise HTTPException(status_code=404, detail=f"MCP server {server_id} not found")
        
        # Run health check
        registry = get_mcp_registry()
        health_result = await registry.health_check(server.name, db)
        
        # Refresh server data from DB to get updated health status
        await db.refresh(server)
        
        logger.info("✅ Health check completed", 
                   server_id=server_id, 
                   name=server.name,
                   healthy=health_result.get('healthy', False))
        
        return {
            "success": True,
            "server_id": server_id,
            "server_name": server.name,
            "health_result": health_result,
            "health_status": server.health_status,
            "last_check": server.last_health_check.isoformat() if server.last_health_check else None,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to trigger health check", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to trigger health check: {str(e)}")

@router.get("/{server_id}/audit")
async def get_mcp_server_audit_logs(
    server_id: int,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get MCP server audit logs with filtering."""
    try:
        # Get server info
        result = await db.execute(
            select(MCPServer).where(MCPServer.id == server_id)
        )
        server = result.scalar_one_or_none()
        
        if not server:
            raise HTTPException(status_code=404, detail=f"MCP server {server_id} not found")
        
        # Build query for audit logs from mcp_informatica schema
        from sqlalchemy import text
        query = """
            SELECT id, tool_name, user_id, environment, parameters, result_status, 
                   result_summary, error_message, execution_time_ms, workflow_run_id, 
                   session_id, created_at
            FROM mcp_informatica.mcp_audit_logs 
            WHERE 1=1
        """
        
        params = {}
        
        # Add filters
        if status:
            query += " AND result_status = :status"
            params['status'] = status
            
        if search:
            query += " AND (tool_name ILIKE :search OR result_summary ILIKE :search OR error_message ILIKE :search)"
            params['search'] = f"%{search}%"
        
        query += " ORDER BY created_at DESC LIMIT :limit"
        params['limit'] = limit
        
        result = await db.execute(text(query), params)
        logs = result.fetchall()
        
        return {
            "success": True,
            "server": {
                "id": server.id,
                "name": server.name,
                "url": server.url
            },
            "logs": [
                {
                    "id": log.id,
                    "tool_name": log.tool_name,
                    "user_id": log.user_id,
                    "environment": log.environment,
                    "parameters": log.parameters,
                    "result_status": log.result_status,
                    "result_summary": log.result_summary,
                    "error_message": log.error_message,
                    "execution_time_ms": log.execution_time_ms,
                    "workflow_run_id": log.workflow_run_id,
                    "session_id": log.session_id,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                for log in logs
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ Failed to get MCP server audit logs", server_id=server_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get audit logs: {str(e)}")