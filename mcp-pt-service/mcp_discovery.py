"""MCP Discovery - Connect to MCP servers using httpx SSE."""

import httpx
import json
from typing import Dict, Any
from logger import logger


class MCPDiscovery:
    """Discover MCP capabilities using httpx with SSE protocol."""

    def __init__(self, mcp_url: str, protocol: str, auth_token: str = None):
        self.mcp_url = mcp_url.rstrip('/')
        if not self.mcp_url.endswith('/mcp'):
            self.mcp_url = f"{self.mcp_url}/mcp"
        self.protocol = protocol.lower()
        self.auth_token = auth_token
        self.session_id = None

    def _empty_result(self, error: str) -> Dict[str, Any]:
        return {
            "server_info": {}, "tools": [], "prompts": [], "resources": [],
            "tool_count": 0, "prompt_count": 0, "resource_count": 0,
            "error": error,
        }

    @staticmethod
    def _parse_list(response_text: str, key: str) -> list:
        for line in response_text.split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if 'result' in data:
                        return data['result'].get(key, [])
                except json.JSONDecodeError:
                    continue
        return []

    async def discover_all(self) -> Dict[str, Any]:
        """Fetch ALL metadata from MCP: tools, prompts, resources."""

        auth_mode = "with token" if self.auth_token else "no auth"
        logger.info(f"Discovery starting: {self.mcp_url} ({auth_mode})")

        headers = {
            "Accept": "text/event-stream, application/json",
            "Content-Type": "application/json",
        }
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:

                # ── initialize ───────────────────────────────────────────────
                resp = await client.post(self.mcp_url, headers=headers, json={
                    "jsonrpc": "2.0", "method": "initialize", "id": 1,
                    "params": {
                        "protocolVersion": "2024-11-05", "capabilities": {},
                        "clientInfo": {"name": "pt-service", "version": "1.0"},
                    },
                })
                if resp.status_code == 401:
                    msg = ("Discovery blocked — HTTP 401 Unauthorized. "
                           "The MCP requires authentication but the token is missing or wrong. "
                           "Check auth_config in mcp_servers for this MCP.")
                    logger.error(msg)
                    return self._empty_result(msg)
                if resp.status_code == 403:
                    msg = f"Discovery blocked — HTTP 403 Forbidden. Token present but lacks permission."
                    logger.error(msg)
                    return self._empty_result(msg)
                if resp.status_code >= 400:
                    msg = f"Discovery failed — HTTP {resp.status_code} on initialize: {resp.text[:200]}"
                    logger.error(msg)
                    return self._empty_result(msg)

                self.session_id = resp.headers.get('mcp-session-id')
                if self.session_id:
                    headers['mcp-session-id'] = self.session_id

                server_info = {}
                for line in resp.text.split('\n'):
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            if 'result' in data:
                                server_info = data['result'].get('serverInfo', {})
                                break
                        except json.JSONDecodeError:
                            continue

                # ── tools/list ───────────────────────────────────────────────
                resp = await client.post(self.mcp_url, headers=headers, json={
                    "jsonrpc": "2.0", "method": "tools/list", "id": 2,
                })
                tools = self._parse_list(resp.text, "tools")

                # ── prompts/list ─────────────────────────────────────────────
                resp = await client.post(self.mcp_url, headers=headers, json={
                    "jsonrpc": "2.0", "method": "prompts/list", "id": 3,
                })
                prompts = self._parse_list(resp.text, "prompts")

                # ── resources/list ───────────────────────────────────────────
                resp = await client.post(self.mcp_url, headers=headers, json={
                    "jsonrpc": "2.0", "method": "resources/list", "id": 4,
                })
                resources = self._parse_list(resp.text, "resources")

                metadata = {
                    "server_info": server_info,
                    "tools": tools, "prompts": prompts, "resources": resources,
                    "tool_count": len(tools),
                    "prompt_count": len(prompts),
                    "resource_count": len(resources),
                }
                logger.info(
                    f"Discovery complete: {len(tools)} tools, "
                    f"{len(prompts)} prompts, {len(resources)} resources"
                )
                return metadata

        except httpx.ConnectError:
            msg = f"Discovery failed — cannot reach {self.mcp_url}. Is the MCP server running?"
            logger.error(msg)
            return self._empty_result(msg)
        except httpx.TimeoutException:
            msg = f"Discovery failed — {self.mcp_url} did not respond within 30 s."
            logger.error(msg)
            return self._empty_result(msg)
        except Exception as e:
            msg = f"Discovery failed — unexpected error: {e}"
            logger.error(msg, exc_info=True)
            return self._empty_result(msg)
    
    async def close(self):
        """Close connection (no-op for httpx)."""
        pass
