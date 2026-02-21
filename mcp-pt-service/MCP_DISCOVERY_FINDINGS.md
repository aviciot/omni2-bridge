# MCP Discovery Findings

## Problem
PT service was trying to call MCP servers using raw HTTP POST with JSON-RPC, but getting 404 errors.

## Root Cause
The docker-control-mcp server uses **FastMCP framework** which requires:
1. **SSE (Server-Sent Events) protocol** - not plain HTTP POST
2. Client must accept BOTH `application/json` AND `text/event-stream` headers
3. Endpoint is `/mcp` (not `/` or `/messages`)

## Test Results

### ❌ Failed Attempts
```bash
# Plain JSON-RPC POST to root
curl -X POST http://localhost:8350/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
# Result: 404 Not Found

# JSON-RPC POST to /mcp without SSE headers
curl -X POST http://localhost:8350/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
# Result: {"error":{"code":-32600,"message":"Not Acceptable: Client must accept both application/json and text/event-stream"}}
```

### ✅ Working Solution
**Use FastMCP Client** (same as Omni2 uses):

```python
from fastmcp import Client

# Create client with /mcp endpoint
client = Client(
    transport="http://host.docker.internal:8350/mcp",
    timeout=30
)

# Initialize connection
await client.__aenter__()

# List tools
tools_result = await client.list_tools()
tools = tools_result.tools

# List prompts
prompts_result = await client.list_prompts()
prompts = prompts_result.prompts

# List resources
resources_result = await client.list_resources()
resources = resources_result.resources

# Call tool
result = await client.call_tool("tool_name", {"arg": "value"})
```

## How Omni2 Does It
From `omni2/app/services/mcp_registry.py`:

```python
# Normalize URL to end with /mcp
url = mcp.url.rstrip('/')
if not url.endswith('/mcp'):
    url = f"{url}/mcp"

# Create FastMCP client
client = Client(
    transport=url,
    auth=auth,  # Optional Bearer token
    timeout=mcp.timeout_seconds or 30
)

# Initialize
await client.__aenter__()

# Fetch metadata
tools_result = await client.list_tools()
prompts_result = await client.list_prompts()
resources_result = await client.list_resources()
```

## Solution for PT Service
**Replace custom HTTP client with FastMCP Client**:

1. Update `mcp_discovery.py` to use FastMCP Client
2. Update `mcp_client.py` to use FastMCP Client
3. Add `/mcp` suffix to URLs from database
4. Handle SSE protocol properly

## Database URL Format
- Database stores: `http://host.docker.internal:8350`
- PT service should use: `http://host.docker.internal:8350/mcp`
- Protocol: `http-streamable` or `sse`

## Dependencies
PT service already has `fastmcp` in requirements.txt ✅
