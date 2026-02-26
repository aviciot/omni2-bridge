"""
MCP Registry Service - Database-Driven MCP Management

Features:
- Database-driven configuration (no YAML)
- Hot reload every 30 seconds
- Protocol support: HTTP, HTTP Streamable, SSE
- Authentication: Bearer token, API key
- Configurable retry logic per MCP
- Health checking and logging
- Connection age tracking (auto-reconnect after 10 min)
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import asyncio
import time
import httpx
from fastmcp import Client
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MCPServer, MCPTool, MCPHealthLog
from app.utils.logger import logger
from app.services.circuit_breaker import get_circuit_breaker
from app.services.websocket_broadcaster import get_websocket_broadcaster

# Debug logging enabled via LOG_LEVEL env var


# Connection max age (10 minutes)
CONNECTION_MAX_AGE_SECONDS = 600


class BearerAuth(httpx.Auth):
    """Bearer token authentication for httpx."""
    def __init__(self, token: str):
        self.token = token
    
    def auth_flow(self, request):
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request


class MCPRegistry:
    """Database-driven MCP registry with hot reload."""
    
    def __init__(self):
        self.mcps: Dict[str, Client] = {}
        self.tools_cache: Dict[str, List[Dict]] = {}
        self.prompts_cache: Dict[str, List[Dict]] = {}
        self.resources_cache: Dict[str, List[Dict]] = {}
        self.client_created_at: Dict[str, float] = {}
        self.last_check: Optional[datetime] = None
        self.circuit_breaker = get_circuit_breaker()
    
    async def load_from_database(self, db: AsyncSession):
        """Load all active MCPs from database."""
        # Load circuit breaker config
        await self.circuit_breaker.load_config(db)
        
        logger.debug("🔍 Querying database for active MCPs...")
        result = await db.execute(
            select(MCPServer).where(MCPServer.status == 'active')
        )
        mcps = result.scalars().all()
        
        logger.info(f"📦 Loading {len(mcps)} active MCPs from database")
        for mcp in mcps:
            logger.debug(f"  - {mcp.name}: {mcp.url} ({mcp.protocol})")
        
        for mcp in mcps:
            await self.load_mcp(mcp, db)
    
    async def load_mcp(self, mcp: MCPServer, db: AsyncSession):
        """Connect to MCP with retry logic and cache tools."""
        # Check circuit breaker first
        if self.circuit_breaker.is_open(mcp.name):
            logger.warning(f"⚡ Circuit breaker open for {mcp.name}, skipping load attempt")
            return
        
        max_retries = mcp.max_retries or 2
        retry_delay = float(mcp.retry_delay_seconds or 1.0)
        start_time = time.time()
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.debug(f"🔌 Attempt {attempt}/{max_retries}: Connecting to {mcp.name}")
                logger.debug(f"  URL: {mcp.url}")
                logger.debug(f"  Protocol: {mcp.protocol}")
                logger.debug(f"  Auth: {mcp.auth_type}")
                logger.debug(f"  Timeout: {mcp.timeout_seconds}s")
                
                # Build authentication
                auth = None
                if mcp.auth_type and mcp.auth_config:
                    logger.debug(f"  🔐 Setting up {mcp.auth_type} authentication")
                    if mcp.auth_type == 'bearer':
                        token = mcp.auth_config.get('token') or mcp.auth_config.get('api_key')
                        if token:
                            auth = BearerAuth(token)
                            logger.debug(f"  ✅ Bearer token configured (length: {len(token)})")
                        else:
                            logger.warning(f"  ⚠️ Bearer auth configured but no token found")
                
                # Normalize URL
                url = mcp.url.rstrip('/')
                if not url.endswith('/mcp'):
                    url = f"{url}/mcp"
                    logger.debug(f"  🔗 Normalized URL: {url}")
                
                # Create client based on protocol
                protocol = (mcp.protocol or 'http').lower()
                logger.debug(f"  🌐 Creating {protocol} client...")
                
                if protocol in ('http', 'http-streamable', 'http_streamable', 'sse'):
                    # For SSE/streamable protocols, we need to use the fastmcp Client properly
                    client = Client(
                        transport=url,
                        auth=auth,
                        timeout=mcp.timeout_seconds or 30
                    )
                    logger.debug(f"  ✅ Client created")
                else:
                    raise ValueError(f"Unsupported protocol: {protocol}")
                
                # Initialize connection
                logger.debug(f"  🔌 Initializing connection...")
                await client.__aenter__()
                logger.debug(f"  ✅ Connection established")
                
                # Fetch tools
                logger.debug(f"  📋 Fetching tools...")
                tools_result = await client.list_tools()
                logger.debug(f"  ✅ Tools fetched")
                tools_list = tools_result.tools if hasattr(tools_result, 'tools') else tools_result
                
                # Convert to dict format
                tools = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema.model_dump() if hasattr(tool.inputSchema, 'model_dump') else tool.inputSchema
                    }
                    for tool in tools_list
                ]
                
                # Fetch prompts
                prompts = []
                try:
                    print(f"[DEBUG] Fetching prompts for {mcp.name}...")
                    logger.debug(f"  📋 Fetching prompts...")
                    prompts_result = await client.list_prompts()
                    print(f"[DEBUG] Prompts result type: {type(prompts_result)}")
                    print(f"[DEBUG] Prompts result: {prompts_result}")
                    prompts_list = prompts_result.prompts if hasattr(prompts_result, 'prompts') else prompts_result
                    print(f"[DEBUG] Prompts list length: {len(prompts_list) if prompts_list else 0}")
                    prompts = [
                        {
                            "name": prompt.name,
                            "description": prompt.description if hasattr(prompt, 'description') else "",
                            "arguments": [
                                {
                                    "name": arg.name,
                                    "description": arg.description if hasattr(arg, 'description') and arg.description else "",
                                    "required": arg.required if hasattr(arg, 'required') else False
                                }
                                for arg in prompt.arguments
                            ] if hasattr(prompt, 'arguments') and prompt.arguments else []
                        }
                        for prompt in prompts_list
                    ]
                    print(f"[DEBUG] Prompts converted: {prompts}")
                    logger.debug(f"  ✅ Prompts fetched: {len(prompts)}")
                except Exception as e:
                    print(f"[DEBUG] Error fetching prompts: {e}")
                    logger.debug(f"  ⚠️ No prompts available: {e}")
                
                # Fetch resources
                resources = []
                try:
                    print(f"[DEBUG] Fetching resources for {mcp.name}...")
                    logger.debug(f"  📋 Fetching resources...")
                    resources_result = await client.list_resources()
                    print(f"[DEBUG] Resources result type: {type(resources_result)}")
                    print(f"[DEBUG] Resources result: {resources_result}")
                    resources_list = resources_result.resources if hasattr(resources_result, 'resources') else resources_result
                    print(f"[DEBUG] Resources list length: {len(resources_list) if resources_list else 0}")
                    resources = [
                        {
                            "uri": resource.uri,
                            "name": resource.name if hasattr(resource, 'name') else "",
                            "description": resource.description if hasattr(resource, 'description') else "",
                            "mimeType": resource.mimeType if hasattr(resource, 'mimeType') else "text/plain"
                        }
                        for resource in resources_list
                    ]
                    print(f"[DEBUG] Resources converted: {resources}")
                    logger.debug(f"  ✅ Resources fetched: {len(resources)}")
                except Exception as e:
                    print(f"[DEBUG] Error fetching resources: {e}")
                    logger.debug(f"  ⚠️ No resources available: {e}")
                
                # Store in registry
                print(f"MCP-CACHE-TRACE: mcp={mcp.name} action=cached tools={len(tools)} prompts={len(prompts)} resources={len(resources)} timestamp={time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.debug(f"  💾 Caching {len(tools)} tools, {len(prompts)} prompts, {len(resources)} resources")
                self.mcps[mcp.name] = client
                self.tools_cache[mcp.name] = tools
                self.prompts_cache[mcp.name] = prompts
                self.resources_cache[mcp.name] = resources
                self.client_created_at[mcp.name] = time.time()
                print(f"MCP-CACHE-TRACE: action=cache_updated cached_mcps={list(self.mcps.keys())}")
                logger.debug(f"  ✅ Cached in registry")
                
                # Calculate response time
                response_time_ms = int((time.time() - start_time) * 1000)
                
                # Update database
                old_health_status = mcp.health_status
                mcp.health_status = 'healthy'
                mcp.last_health_check = datetime.now(timezone.utc)
                mcp.error_count = 0
                await db.commit()
                
                # Broadcast status change event if status changed
                if old_health_status != 'healthy':
                    broadcaster = get_websocket_broadcaster()
                    await broadcaster.broadcast_event(
                        event_type="mcp_status_change",
                        event_data={
                            "mcp_name": mcp.name,
                            "old_status": old_health_status or "unknown",
                            "new_status": "healthy",
                            "reason": "Successfully connected and loaded tools",
                            "severity": "info",
                            "tool_count": len(tools),
                            "response_time_ms": response_time_ms
                        }
                    )
                
                # Record success in circuit breaker
                self.circuit_breaker.record_success(mcp.name)
                
                # Save tools to database
                logger.debug(f"  💾 Saving tools to database...")
                await self._save_tools_to_db(mcp.id, tools, db)
                logger.debug(f"  ✅ Tools saved to database")
                
                # Log success
                await self._log_health(
                    db, mcp.id, 'healthy', 
                    response_time_ms=response_time_ms,
                    event_type='load', 
                    metadata={'tool_count': len(tools), 'attempt': attempt}
                )
                
                logger.info(
                    f"✅ MCP loaded successfully",
                    server=mcp.name,
                    tools=len(tools),
                    response_time_ms=response_time_ms,
                    attempt=attempt
                )
                
                return  # Success, exit retry loop
                
            except Exception as e:
                error_msg = str(e)
                is_connection_error = self._is_connection_error(e)
                
                logger.warning(
                    f"⚠️ MCP load failed (attempt {attempt}/{max_retries})",
                    server=mcp.name,
                    error=error_msg,
                    is_connection_error=is_connection_error
                )
                
                # If last attempt or not a connection error, fail
                if attempt >= max_retries or not is_connection_error:
                    # Record failure in circuit breaker
                    self.circuit_breaker.record_failure(mcp.name)
                    
                    # Get fresh MCP object from database for update
                    result_fresh = await db.execute(
                        select(MCPServer).where(MCPServer.id == mcp.id)
                    )
                    mcp_fresh = result_fresh.scalar_one_or_none()
                    
                    if mcp_fresh:
                        # Check if should auto-disable after max failure cycles
                        if self.circuit_breaker.should_auto_disable(mcp.name):
                            old_status = mcp_fresh.status
                            mcp_fresh.status = 'inactive'
                            mcp_fresh.auto_disabled_at = datetime.now(timezone.utc)
                            mcp_fresh.auto_disabled_reason = f"Auto-disabled after {self.circuit_breaker.max_failure_cycles} failure cycles. Last error: {error_msg}"
                            mcp_fresh.failure_cycle_count = self.circuit_breaker.get_failure_cycles(mcp.name)
                            
                            logger.error(
                                f"🚫 MCP auto-disabled after {mcp_fresh.failure_cycle_count} failure cycles",
                                server=mcp.name,
                                reason=mcp_fresh.auto_disabled_reason
                            )
                            
                            # Broadcast auto-disable event
                            broadcaster = get_websocket_broadcaster()
                            await broadcaster.broadcast_event(
                                event_type="mcp_auto_disabled",
                                event_data={
                                    "mcp_name": mcp.name,
                                    "reason": mcp_fresh.auto_disabled_reason,
                                    "failure_cycles": mcp_fresh.failure_cycle_count,
                                    "severity": "critical",
                                    "timestamp": mcp_fresh.auto_disabled_at.isoformat()
                                }
                            )
                        else:
                            # Update database with error status
                            old_health_status = mcp_fresh.health_status
                            mcp_fresh.health_status = 'unhealthy'
                            mcp_fresh.error_count = (mcp_fresh.error_count or 0) + 1
                            mcp_fresh.last_health_check = datetime.now(timezone.utc)
                            
                            # Broadcast status change event if status changed
                            if old_health_status != 'unhealthy':
                                broadcaster = get_websocket_broadcaster()
                                await broadcaster.broadcast_event(
                                    event_type="mcp_status_change",
                                    event_data={
                                        "mcp_name": mcp.name,
                                        "old_status": old_health_status or "unknown",
                                        "new_status": "unhealthy",
                                        "reason": error_msg,
                                        "severity": "high",
                                        "error_count": mcp_fresh.error_count
                                    }
                                )
                        
                        await db.commit()
                    
                    # Remove from cache if it was loaded
                    if mcp.name in self.mcps:
                        try:
                            await self.mcps[mcp.name].__aexit__(None, None, None)
                        except:
                            pass
                        del self.mcps[mcp.name]
                        self.tools_cache.pop(mcp.name, None)
                        self.client_created_at.pop(mcp.name, None)
                    
                    # Log error
                    await self._log_health(
                        db, mcp.id, 'unhealthy', 
                        error_message=error_msg, 
                        event_type='load_failed',
                        metadata={'attempts': attempt, 'circuit_state': self.circuit_breaker.get_state(mcp.name)}
                    )
                    
                    logger.error(
                        f"❌ MCP load failed after {attempt} attempts",
                        server=mcp.name,
                        error=error_msg
                    )
                    return
                
                # Wait before retry
                await asyncio.sleep(retry_delay)
    
    async def unload_mcp(self, mcp_name: str, db: AsyncSession):
        """Disconnect and remove MCP from registry."""
        if mcp_name in self.mcps:
            try:
                client = self.mcps[mcp_name]
                await client.__aexit__(None, None, None)
                logger.info(f"🔌 Disconnected MCP", server=mcp_name)
            except Exception as e:
                logger.warning(f"⚠️ Error disconnecting MCP", server=mcp_name, error=str(e))
            finally:
                del self.mcps[mcp_name]
                self.tools_cache.pop(mcp_name, None)
                self.prompts_cache.pop(mcp_name, None)
                self.resources_cache.pop(mcp_name, None)
                self.client_created_at.pop(mcp_name, None)
    
    async def reload_if_changed(self, db: AsyncSession):
        """Check database for changes and hot reload."""
        from sqlalchemy import text
        
        # Use raw SQL to avoid greenlet issues in background tasks
        result = await db.execute(text(
            "SELECT id, name, url, protocol, timeout_seconds, auth_type, auth_config, "
            "status, updated_at FROM omni2.mcp_servers WHERE status = 'active'"
        ))
        rows = result.fetchall()
        
        # Convert to dict for easier handling
        db_mcps_data = [
            {
                'id': row[0], 'name': row[1], 'url': row[2], 'protocol': row[3],
                'timeout_seconds': row[4], 'auth_type': row[5], 'auth_config': row[6],
                'status': row[7], 'updated_at': row[8]
            }
            for row in rows
        ]
        
        current_names = set(self.mcps.keys())
        db_names = set(mcp['name'] for mcp in db_mcps_data)
        
        # Load new MCPs
        new_mcps = db_names - current_names
        for mcp_data in db_mcps_data:
            if mcp_data['name'] in new_mcps:
                print(f"MCP-CACHE-TRACE: mcp={mcp_data['name']} action=new_mcp_detected url={mcp_data['url']}")
                logger.info(f"🆕 New MCP detected", server=mcp_data['name'])
                
                # Broadcast new MCP event BEFORE loading
                broadcaster = get_websocket_broadcaster()
                await broadcaster.broadcast_event(
                    event_type="mcp_status_change",
                    event_data={
                        "mcp_name": mcp_data['name'],
                        "old_status": "not_loaded",
                        "new_status": "loading",
                        "reason": "New MCP server detected in database",
                        "severity": "info",
                        "url": mcp_data['url'],
                        "protocol": mcp_data['protocol']
                    }
                )
                
                # Create MCPServer object from dict and load
                from app.models import MCPServer
                mcp = MCPServer(**mcp_data)
                await self.load_mcp(mcp, db)
        
        # Unload removed MCPs
        removed_mcps = current_names - db_names
        for name in removed_mcps:
            print(f"MCP-CACHE-TRACE: mcp={name} action=removed_from_cache")
            logger.info(f"🗑️ MCP removed", server=name)
            await self.unload_mcp(name, db)
        
        # Reload changed MCPs (check updated_at)
        if self.last_check:
            for mcp_data in db_mcps_data:
                if mcp_data['updated_at'] > self.last_check and mcp_data['name'] in current_names:
                    print(f"MCP-CACHE-TRACE: mcp={mcp_data['name']} action=config_changed updated_at={mcp_data['updated_at']} last_check={self.last_check}")
                    logger.info(f"🔄 MCP config changed", server=mcp_data['name'])
                    await self.unload_mcp(mcp_data['name'], db)
                    from app.models import MCPServer
                    mcp = MCPServer(**mcp_data)
                    await self.load_mcp(mcp, db)
        
        # Check connection age and reconnect if stale
        current_time = time.time()
        for mcp_data in db_mcps_data:
            if mcp_data['name'] in self.client_created_at:
                age = current_time - self.client_created_at[mcp_data['name']]
                if age > CONNECTION_MAX_AGE_SECONDS:
                    print(f"MCP-CACHE-TRACE: mcp={mcp_data['name']} action=connection_stale age_seconds={int(age)} max_age={CONNECTION_MAX_AGE_SECONDS}")
                    logger.info(
                        f"🔄 Connection too old, reconnecting",
                        server=mcp_data['name'],
                        age_seconds=int(age)
                    )
                    await self.unload_mcp(mcp_data['name'], db)
                    from app.models import MCPServer
                    mcp = MCPServer(**mcp_data)
                    await self.load_mcp(mcp, db)
        
        self.last_check = datetime.now(timezone.utc)
    
    async def call_tool(self, mcp_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool on MCP."""
        # Check circuit breaker first
        if self.circuit_breaker.is_open(mcp_name):
            retry_after = self.circuit_breaker.get_retry_after(mcp_name)
            return {
                "status": "unavailable",
                "error": f"MCP '{mcp_name}' temporarily unavailable (circuit breaker open)",
                "circuit_state": self.circuit_breaker.get_state(mcp_name),
                "retry_after_seconds": retry_after
            }
        
        if mcp_name not in self.mcps:
            return {
                "status": "error",
                "error": f"MCP '{mcp_name}' not loaded"
            }
        
        try:
            client = self.mcps[mcp_name]
            result = await client.call_tool(tool_name, arguments)
            
            # Record success
            self.circuit_breaker.record_success(mcp_name)
            
            return {
                "status": "success",
                "result": result.content if hasattr(result, 'content') else result,
                "server": mcp_name,
                "tool": tool_name
            }
        except Exception as e:
            # Record failure
            self.circuit_breaker.record_failure(mcp_name)
            
            logger.error(f"❌ Tool call failed", server=mcp_name, tool=tool_name, error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "server": mcp_name,
                "tool": tool_name,
                "circuit_state": self.circuit_breaker.get_state(mcp_name)
            }
    
    async def health_check(self, mcp_name: str, db: AsyncSession) -> Dict[str, Any]:
        """Check health of MCP by attempting to list tools."""
        if mcp_name not in self.mcps:
            # Try to get server info from database
            result = await db.execute(
                select(MCPServer).where(MCPServer.name == mcp_name)
            )
            mcp = result.scalar_one_or_none()
            
            if mcp:
                # Update health status to reflect disconnected state
                mcp.health_status = 'unhealthy'
                mcp.last_health_check = datetime.now(timezone.utc)
                await db.commit()
                
                await self._log_health(
                    db, mcp.id, 'unhealthy',
                    error_message=f"MCP '{mcp_name}' not loaded/connected",
                    event_type='health_check'
                )
            
            return {
                "healthy": False,
                "error": f"MCP '{mcp_name}' not loaded",
                "circuit_state": self.circuit_breaker.get_state(mcp_name)
            }
        
        try:
            start_time = time.time()
            client = self.mcps[mcp_name]
            tools_result = await client.list_tools()
            response_time_ms = int((time.time() - start_time) * 1000)
            
            tool_count = len(tools_result.tools) if hasattr(tools_result, 'tools') else 0
            
            # Get MCP from database
            result = await db.execute(
                select(MCPServer).where(MCPServer.name == mcp_name)
            )
            mcp = result.scalar_one_or_none()
            
            if mcp:
                # Log health check
                await self._log_health(
                    db, mcp.id, 'healthy',
                    response_time_ms=response_time_ms,
                    event_type='health_check',
                    metadata={'tool_count': tool_count}
                )
            
            return {
                "healthy": True,
                "tool_count": tool_count,
                "response_time_ms": response_time_ms,
                "last_check": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Health check failed", server=mcp_name, error=str(e))
            
            # Update database health status
            result = await db.execute(
                select(MCPServer).where(MCPServer.name == mcp_name)
            )
            mcp = result.scalar_one_or_none()
            
            if mcp:
                mcp.health_status = 'unhealthy'
                mcp.last_health_check = datetime.now(timezone.utc)
                await db.commit()
                
                await self._log_health(
                    db, mcp.id, 'unhealthy',
                    error_message=str(e),
                    event_type='health_check_failed'
                )
            
            return {
                "healthy": False,
                "error": str(e),
                "last_check": datetime.now(timezone.utc).isoformat(),
                "circuit_state": self.circuit_breaker.get_state(mcp_name)
            }
    
    def get_tools(self, mcp_name: Optional[str] = None) -> Dict[str, List[Dict]]:
        """Get cached tools."""
        if mcp_name:
            return {mcp_name: self.tools_cache.get(mcp_name, [])}
        return self.tools_cache
    
    def get_prompts(self, mcp_name: Optional[str] = None) -> Dict[str, List[Dict]]:
        """Get cached prompts."""
        if mcp_name:
            return {mcp_name: self.prompts_cache.get(mcp_name, [])}
        return self.prompts_cache
    
    def get_resources(self, mcp_name: Optional[str] = None) -> Dict[str, List[Dict]]:
        """Get cached resources."""
        if mcp_name:
            return {mcp_name: self.resources_cache.get(mcp_name, [])}
        return self.resources_cache
    
    def get_loaded_mcps(self) -> List[str]:
        """Get list of loaded MCP names."""
        return list(self.mcps.keys())
    
    def _is_connection_error(self, error: Exception) -> bool:
        """Check if error is connection-related (worth retrying)."""
        connection_error_types = (
            ConnectionError,
            ConnectionRefusedError,
            ConnectionResetError,
            TimeoutError,
            OSError,
        )
        
        if isinstance(error, connection_error_types):
            return True
        
        error_msg = str(error).lower()
        connection_keywords = [
            "connection refused", "connection reset", "connection closed",
            "connect timeout", "timed out", "network unreachable",
            "host unreachable", "no route to host", "broken pipe",
            "all connection attempts failed", "client is not connected"
        ]
        
        return any(keyword in error_msg for keyword in connection_keywords)
    
    async def _save_tools_to_db(self, mcp_id: int, tools: List[Dict], db: AsyncSession):
        """Save tools to database."""
        try:
            # Delete old tools
            await db.execute(
                delete(MCPTool).where(MCPTool.mcp_server_id == mcp_id)
            )
            
            # Insert new tools
            for tool in tools:
                db_tool = MCPTool(
                    mcp_server_id=mcp_id,
                    name=tool['name'],
                    description=tool.get('description'),
                    input_schema=tool.get('inputSchema')
                )
                db.add(db_tool)
            
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save tools to database", mcp_id=mcp_id, error=str(e))
            try:
                await db.rollback()
            except:
                pass
    
    async def _log_health(
        self, 
        db: AsyncSession, 
        mcp_id: int, 
        status: str,
        response_time_ms: Optional[int] = None,
        error_message: Optional[str] = None,
        event_type: str = 'health_check',
        metadata: Optional[Dict] = None
    ):
        """Log health event."""
        try:
            log = MCPHealthLog(
                mcp_server_id=mcp_id,
                status=status,
                response_time_ms=response_time_ms,
                error_message=error_message,
                event_type=event_type,
                metadata=metadata
            )
            db.add(log)
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to log health event", mcp_id=mcp_id, error=str(e))
            try:
                await db.rollback()
            except:
                pass
    
    async def close_all(self):
        """Close all MCP connections."""
        logger.info("🔌 Closing all MCP connections")
        for name, client in self.mcps.items():
            try:
                await client.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error closing {name}", error=str(e))
        self.mcps.clear()
        self.tools_cache.clear()
        self.prompts_cache.clear()
        self.resources_cache.clear()
        self.client_created_at.clear()


# Global instance
mcp_registry = MCPRegistry()


def get_mcp_registry() -> MCPRegistry:
    """Get global MCP registry instance."""
    return mcp_registry
