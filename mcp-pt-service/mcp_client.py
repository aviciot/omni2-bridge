"""MCP Client - Direct httpx implementation for HTTP Streamable protocol."""

import json
import httpx
from typing import Dict, Any, Optional
from logger import logger


class MCPConnectionError(Exception):
    """MCP server is unreachable or a session could not be established.

    Raised by _ensure_session() so that test functions (and the @mcp_test
    decorator) can distinguish "can't reach the server at all" from
    "reached the server but the tool call was rejected".
    """


class MCPError(Exception):
    """JSON-RPC error returned by the MCP server (e.g. -32602 Invalid params).

    Carries the numeric code so @mcp_test can map it to the correct test outcome:
      -32600 Invalid Request   → server validated the request envelope
      -32601 Method Not Found  → tool/prompt/resource doesn't exist (inconclusive)
      -32602 Invalid Params    → server validated input arguments (good)
      -32603 Internal Error    → server crashed on this input
    """

    def __init__(self, code: int, message: str):
        super().__init__(f"MCP error {code}: {message}")
        self.code = code
        self.message = message


class MCPClient:
    """MCP client using direct httpx calls (HTTP Streamable / SSE protocols)."""

    def __init__(self, mcp_url: str, protocol: str = "http-streamable",
                 auth_token: Optional[str] = None):
        self.protocol = protocol.lower()
        self.auth_token = auth_token
        self.session_id: Optional[str] = None

        # Resolve base endpoint URL
        base = mcp_url.rstrip('/')
        if self.protocol in ('http-streamable', 'http'):
            self._endpoint = base if base.endswith('/mcp') else f"{base}/mcp"
        else:
            # Legacy SSE: connect via GET /sse, but we still POST for tool calls
            self._endpoint = base if base.endswith('/sse') else f"{base}/sse"

        logger.info(f"MCPClient: {self._endpoint} (protocol: {self.protocol})")

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _headers(self, token: Optional[str] = None, include_session: bool = True) -> dict:
        """Build request headers."""
        h = {
            "Accept": "text/event-stream, application/json",
            "Content-Type": "application/json",
        }
        t = token or self.auth_token
        if t:
            h["Authorization"] = f"Bearer {t}"
        if include_session and self.session_id:
            h["mcp-session-id"] = self.session_id
        return h

    @staticmethod
    def _parse_response(text: str) -> Any:
        """Parse SSE-wrapped or plain JSON MCP response, return result payload."""
        for line in text.split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if 'error' in data:
                        err = data['error']
                        raise MCPError(
                            code=err.get('code', -1) if isinstance(err, dict) else -1,
                            message=err.get('message', str(err)) if isinstance(err, dict) else str(err),
                        )
                    return data.get('result')
                except json.JSONDecodeError:
                    continue
        # Fallback: try raw JSON
        try:
            data = json.loads(text)
            if 'error' in data:
                err = data['error']
                raise MCPError(
                    code=err.get('code', -1) if isinstance(err, dict) else -1,
                    message=err.get('message', str(err)) if isinstance(err, dict) else str(err),
                )
            return data.get('result')
        except MCPError:
            raise
        except (json.JSONDecodeError, KeyError):
            return text

    async def _ensure_session(self):
        """Initialize MCP session if not already done.

        Raises MCPConnectionError if the server is unreachable or rejects
        the initialize handshake — so callers never see raw httpx errors
        for a connection-level failure.
        """
        if self.session_id is not None:
            return
        headers = self._headers(include_session=False)
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(self._endpoint, headers=headers, json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "id": 1,
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "pt-client", "version": "1.0"}
                    }
                })
                resp.raise_for_status()
                self.session_id = resp.headers.get('mcp-session-id', '')
                logger.debug(f"MCP session initialized: session_id={self.session_id!r}")
        except MCPConnectionError:
            raise
        except Exception as e:
            raise MCPConnectionError(
                f"Cannot connect to MCP at {self._endpoint}: {e}"
            ) from e

    async def _post_rpc(self, payload: dict, token: Optional[str] = None,
                        timeout: float = 30.0) -> Any:
        """Send an authenticated JSON-RPC request and return the result."""
        await self._ensure_session()
        headers = self._headers(token=token)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(self._endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            return self._parse_response(resp.text)

    # ── Public API ────────────────────────────────────────────────────────────

    async def call_tool(self, tool: str, arguments: Dict) -> Any:
        """Call an MCP tool with normal authentication."""
        logger.debug(f"call_tool tool={tool} args={arguments}")
        return await self._post_rpc({
            "jsonrpc": "2.0", "method": "tools/call", "id": 10,
            "params": {"name": tool, "arguments": arguments}
        })

    async def call_tool_raw(self, tool: str, raw_payload) -> Any:
        """Send a raw (possibly malformed) payload — for protocol-robustness tests."""
        await self._ensure_session()
        headers = self._headers()
        body = raw_payload if isinstance(raw_payload, bytes) else str(raw_payload).encode()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self._endpoint, headers=headers, content=body)
            resp.raise_for_status()
            return resp.text

    async def call_tool_no_auth(self, tool: str, arguments: Dict) -> Any:
        """Call an MCP tool without any authentication header."""
        await self._ensure_session()
        # Build headers with no auth token
        headers = {
            "Accept": "text/event-stream, application/json",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self._endpoint, headers=headers, json={
                "jsonrpc": "2.0", "method": "tools/call", "id": 20,
                "params": {"name": tool, "arguments": arguments}
            })
            resp.raise_for_status()
            return self._parse_response(resp.text)

    async def call_tool_with_token(self, tool: str, arguments: Dict, token: str) -> Any:
        """Call an MCP tool with a specific auth token (e.g. expired/invalid JWT)."""
        return await self._post_rpc({
            "jsonrpc": "2.0", "method": "tools/call", "id": 30,
            "params": {"name": tool, "arguments": arguments}
        }, token=token)

    async def call_tool_partial(self, tool: str, arguments: Dict) -> Any:
        """Send a truncated / partial request body — for protocol-robustness tests."""
        await self._ensure_session()
        headers = self._headers()
        full = json.dumps({
            "jsonrpc": "2.0", "method": "tools/call", "id": 40,
            "params": {"name": tool, "arguments": arguments}
        })
        partial = full[:len(full) // 2]  # Send first half only
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                self._endpoint, headers=headers, content=partial.encode()
            )
            resp.raise_for_status()
            return resp.text

    async def get_prompt(self, prompt_name: str, arguments: Dict = None) -> Any:
        """Call prompts/get with normal authentication."""
        return await self._post_rpc({
            "jsonrpc": "2.0", "method": "prompts/get", "id": 50,
            "params": {"name": prompt_name, "arguments": arguments or {}}
        })

    async def get_prompt_no_auth(self, prompt_name: str, arguments: Dict = None) -> Any:
        """Call prompts/get without any authentication header."""
        await self._ensure_session()
        headers = {
            "Accept": "text/event-stream, application/json",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self._endpoint, headers=headers, json={
                "jsonrpc": "2.0", "method": "prompts/get", "id": 60,
                "params": {"name": prompt_name, "arguments": arguments or {}}
            })
            resp.raise_for_status()
            return self._parse_response(resp.text)

    async def list_resources(self) -> Any:
        """Call resources/list with normal authentication."""
        return await self._post_rpc({
            "jsonrpc": "2.0", "method": "resources/list", "id": 70,
            "params": {}
        })

    async def list_resources_no_auth(self) -> Any:
        """Call resources/list without any authentication header."""
        await self._ensure_session()
        headers = {
            "Accept": "text/event-stream, application/json",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self._endpoint, headers=headers, json={
                "jsonrpc": "2.0", "method": "resources/list", "id": 80,
                "params": {}
            })
            resp.raise_for_status()
            return self._parse_response(resp.text)

    async def read_resource(self, uri: str) -> Any:
        """Call resources/read with normal authentication."""
        return await self._post_rpc({
            "jsonrpc": "2.0", "method": "resources/read", "id": 90,
            "params": {"uri": uri}
        })

    async def read_resource_no_auth(self, uri: str) -> Any:
        """Call resources/read without any authentication header."""
        await self._ensure_session()
        headers = {
            "Accept": "text/event-stream, application/json",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self._endpoint, headers=headers, json={
                "jsonrpc": "2.0", "method": "resources/read", "id": 100,
                "params": {"uri": uri}
            })
            resp.raise_for_status()
            return self._parse_response(resp.text)

    async def close(self):
        """Release session (no persistent connection to close)."""
        self.session_id = None
