# MCP Gateway Implementation - Step 1

## What Was Done

### 1. Database Changes
✅ Added `source` column to `omni2.audit_logs`:
```sql
ALTER TABLE omni2.audit_logs ADD COLUMN source VARCHAR(20) DEFAULT 'ws_chat';
```
- Tracks whether request came from 'ws_chat' or 'mcp_gateway'
- Unified logging for both endpoints

### 2. Created MCP Gateway Router
✅ File: `omni2/app/routers/mcp_gateway.py`
- Endpoint: `/mcp`
- Validates opaque tokens via auth service
- Checks user has 'mcp' in omni_services
- Returns MCP protocol response

### 3. Registered Router
✅ Updated `omni2/app/main.py`:
- Imported mcp_gateway router
- Registered with FastAPI app

### 4. Traefik Configuration
✅ Already configured:
- Port 8095 exposed
- Route `/mcp` → Omni2 (no ForwardAuth)
- MCP entrypoint defined

## Current Status

**Working:**
- Token validation
- Permission checking
- Basic MCP protocol response

**TODO (Next Steps):**
- Implement MCP protocol handling (tools list, tool execution)
- Proxy requests to actual MCP servers
- Filter tools based on user permissions
- Stream responses (SSE)
- Log to audit_logs table

## Testing

```bash
# Generate token via dashboard
# IAM → Users → Click "🔑 Token" → Generate

# Test endpoint
curl -X GET http://localhost:8095/mcp \
  -H "Authorization: Bearer omni2_mcp_YOUR_TOKEN"

# Should return MCP protocol response
```

## Next Implementation Steps

1. **Get available MCP servers** for user
2. **Filter tools** based on tool_restrictions
3. **Handle tool execution** requests
4. **Stream responses** back to client
5. **Log all requests** to audit_logs

Ready to continue?
