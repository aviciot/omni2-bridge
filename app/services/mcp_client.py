"""
MCP Client Service

Handles communication with MCP servers using FastMCP client.
Manages tool discovery, authentication, and execution.
"""

from typing import Dict, List, Optional, Any
import httpx
from datetime import datetime

from app.config import settings
from app.utils.logger import logger


class MCPClient:
    """Client for communicating with FastMCP servers via SSE."""
    
    def __init__(self):
        """Initialize MCP client with configured servers."""
        # Convert list of MCPServerConfig to dict for easier lookup
        self.servers = {
            server.name: server.model_dump()
            for server in settings.mcps.mcps
        }
        self.timeout = httpx.Timeout(30.0, connect=5.0)
        self._client_cache: Dict[str, Any] = {}
        
    def _get_auth_headers(self, server_config: Dict) -> Dict[str, str]:
        """
        Build authentication headers for MCP server.
        
        Args:
            server_config: Server configuration dict
            
        Returns:
            Dict of HTTP headers
        """
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "OMNI2-Bridge/0.1.0",
        }
        
        # Add authentication if configured
        auth_config = server_config.get("authentication", {})
        if auth_config.get("enabled", False):
            auth_type = auth_config.get("type", "bearer")
            api_key = auth_config.get("api_key", "")
            
            if auth_type.lower() == "bearer" and api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            elif auth_type.lower() == "api_key" and api_key:
                headers["X-API-Key"] = api_key
        
        return headers
        
    async def list_tools(self, server_name: Optional[str] = None) -> Dict[str, Any]:
        """
        List available tools from one or all MCP servers.
        
        FastMCP servers expose tools via POST /sse with tools/list method.
        
        Args:
            server_name: Specific server to query, or None for all servers
            
        Returns:
            Dict with tools grouped by server
        """
        if server_name:
            # Query specific server
            server_config = self.servers.get(server_name)
            if not server_config:
                raise ValueError(f"Unknown MCP server: {server_name}")
            
            tools = await self._fetch_tools_rpc(server_name, server_config)
            return {
                "servers": {server_name: tools},
                "total_tools": len(tools.get("tools", [])),
            }
        
        # Query all servers
        all_tools = {}
        total_count = 0
        
        for name, config in self.servers.items():
            if not config.get("enabled", True):
                logger.info(f"⏭️  Skipping disabled MCP server", server=name)
                continue
                
            try:
                tools = await self._fetch_tools_rpc(name, config)
                all_tools[name] = tools
                total_count += len(tools.get("tools", []))
            except Exception as e:
                logger.error(
                    "❌ Failed to list tools from MCP server",
                    server=name,
                    error=str(e),
                )
                all_tools[name] = {
                    "error": str(e),
                    "status": "unhealthy",
                }
        
        return {
            "servers": all_tools,
            "total_tools": total_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    async def _fetch_tools_rpc(self, server_name: str, config: Dict) -> Dict[str, Any]:
        """
        Fetch tools from FastMCP server using JSON-RPC over HTTP.
        
        FastMCP exposes: POST /sse with {"method": "tools/list"}
        
        Args:
            server_name: Name of the MCP server
            config: Server configuration dict
            
        Returns:
            Dict with tools and server info
        """
        url = config.get("url", "")
        if not url:
            raise ValueError(f"No URL configured for server: {server_name}")
        
        headers = self._get_auth_headers(config)
        
        # FastMCP uses JSON-RPC 2.0 format
        rpc_endpoint = f"{url.rstrip('/')}/sse"
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        logger.info(
            "🔍 Fetching tools from FastMCP server",
            server=server_name,
            url=rpc_endpoint,
        )
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(rpc_endpoint, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract tools from JSON-RPC response
                if "result" in data:
                    tools_data = data["result"]
                    tools = tools_data.get("tools", [])
                    
                    logger.info(
                        "✅ Successfully fetched tools",
                        server=server_name,
                        tool_count=len(tools),
                    )
                    
                    return {
                        "tools": tools,
                        "server_info": tools_data.get("serverInfo", {}),
                        "status": "healthy",
                        "last_check": datetime.utcnow().isoformat(),
                    }
                elif "error" in data:
                    error_msg = data["error"].get("message", "Unknown error")
                    raise Exception(f"RPC error: {error_msg}")
                else:
                    raise Exception("Invalid RPC response format")
                
            except httpx.HTTPStatusError as e:
                logger.error(
                    "❌ HTTP error fetching tools",
                    server=server_name,
                    status_code=e.response.status_code,
                    error=str(e),
                )
                raise
                
            except httpx.TimeoutException:
                logger.error(
                    "⏱️  Timeout fetching tools",
                    server=server_name,
                )
                raise
                
            except Exception as e:
                logger.error(
                    "❌ Unexpected error fetching tools",
                    server=server_name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a tool on a FastMCP server.
        
        Uses JSON-RPC: POST /sse with {"method": "tools/call"}
        
        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        server_config = self.servers.get(server_name)
        if not server_config:
            raise ValueError(f"Unknown MCP server: {server_name}")
        
        url = server_config.get("url", "")
        if not url:
            raise ValueError(f"No URL configured for server: {server_name}")
        
        headers = self._get_auth_headers(server_config)
        
        # FastMCP uses JSON-RPC 2.0 format
        rpc_endpoint = f"{url.rstrip('/')}/sse"
        payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            }
        }
        
        logger.info(
            "🔧 Calling FastMCP tool",
            server=server_name,
            tool=tool_name,
            url=rpc_endpoint,
        )
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    rpc_endpoint,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                
                data = response.json()
                
                # Extract result from JSON-RPC response
                if "result" in data:
                    result = data["result"]
                    
                    logger.info(
                        "✅ Tool executed successfully",
                        server=server_name,
                        tool=tool_name,
                        has_content=bool(result.get("content")),
                    )
                    
                    return result
                elif "error" in data:
                    error_msg = data["error"].get("message", "Unknown error")
                    raise Exception(f"RPC error: {error_msg}")
                else:
                    raise Exception("Invalid RPC response format")
                
            except httpx.HTTPStatusError as e:
                logger.error(
                    "❌ HTTP error calling tool",
                    server=server_name,
                    tool=tool_name,
                    status_code=e.response.status_code,
                    error=str(e),
                )
                raise
                
            except httpx.TimeoutException:
                logger.error(
                    "⏱️  Timeout calling tool",
                    server=server_name,
                    tool=tool_name,
                )
                raise
                
            except Exception as e:
                logger.error(
                    "❌ Unexpected error calling tool",
                    server=server_name,
                    tool=tool_name,
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise
    
    async def health_check(self, server_name: str) -> Dict[str, Any]:
        """
        Check health of an MCP server.
        
        Args:
            server_name: Name of the MCP server
            
        Returns:
            Health status dict
        """
        server_config = self.servers.get(server_name)
        if not server_config:
            return {
                "healthy": False,
                "error": f"Unknown server: {server_name}",
            }
        
        url = server_config.get("url", "")
        if not url:
            return {
                "healthy": False,
                "error": "No URL configured",
            }
        
        # Build headers with authentication
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "OMNI2-Bridge/0.1.0",
        }
        
        # Add authentication if configured
        auth_config = server_config.get("authentication", {})
        if auth_config.get("enabled", False):
            auth_type = auth_config.get("type", "bearer")
            api_key = auth_config.get("api_key", "")
            
            if auth_type.lower() == "bearer" and api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            elif auth_type.lower() == "api_key" and api_key:
                headers["X-API-Key"] = api_key
        
        health_endpoint = f"{url.rstrip('/')}/health"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(health_endpoint, headers=headers)
                response.raise_for_status()
                
                return {
                    "healthy": True,
                    "data": response.json(),
                    "last_check": datetime.utcnow().isoformat(),
                }
                
            except Exception as e:
                return {
                    "healthy": False,
                    "error": str(e),
                    "last_check": datetime.utcnow().isoformat(),
                }


# Global MCP client instance
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """
    Get or create the global MCP client instance.
    
    Returns:
        MCPClient instance
    """
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
