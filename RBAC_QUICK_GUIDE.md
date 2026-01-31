# Role-Based Access Control - Implementation Guide

## What Was Done

### Frontend (Dashboard)
**File:** `omni2/dashboard/frontend/src/components/iam/PermissionBuilder.tsx`
- Fetches MCP capabilities from OMNI2: `GET /api/v1/mcp/tools/capabilities?server={mcp_name}`
- Displays tools, resources, prompts with checkboxes
- Supports 4 modes: ALL, ALLOW, DENY, NONE
- Saves to `tool_restrictions` JSONB field

### Backend (OMNI2)
**File:** `omni2/app/routers/tools.py`
- Endpoint already exists: `GET /mcp/tools/capabilities?server={mcp_name}`
- Returns: `{data: {mcp_name: {tools: [], resources: [], prompts: []}}}`
- **NOT INTEGRATED** - No permission checking yet

---

## Database Schema

### Roles Table (auth_service.roles)
```sql
mcp_access TEXT[]              -- ["database_mcp", "filesystem"]
tool_restrictions JSONB         -- See below
```

### tool_restrictions JSON Structure
```json
{
  "database_mcp": {
    "mode": "allow",
    "tools": ["query", "describe_table"],
    "resources": ["schema://public"],
    "prompts": ["generate_query"]
  },
  "filesystem": {
    "mode": "deny",
    "tools": ["delete_file", "format_disk"],
    "resources": ["/etc/*"],
    "prompts": []
  }
}
```

---

## Access Modes

| Mode | Logic | Example |
|------|-------|---------|
| **all** | Full access | Everything allowed |
| **allow** | Whitelist | Only `["query", "insert"]` allowed |
| **deny** | Blacklist | Everything except `["drop_table"]` |
| **none** | Block | Complete block |

---

## Implementation Flow (NOT DONE YET)

### 1. Get User's Role
```python
# In OMNI2 request handler
user = await get_user(user_id)
role = await get_role_from_auth_service(user.role_id)
```

### 2. Check MCP Access
```python
# Check if MCP in allowed list
if mcp_name not in role["mcp_access"]:
    raise PermissionDenied(f"No access to {mcp_name}")
```

### 3. Check Tool Access
```python
restrictions = role["tool_restrictions"].get(mcp_name, {})
mode = restrictions.get("mode", "all")

if mode == "allow":
    if tool_name not in restrictions.get("tools", []):
        raise PermissionDenied(f"Tool {tool_name} not allowed")
        
elif mode == "deny":
    if tool_name in restrictions.get("tools", []):
        raise PermissionDenied(f"Tool {tool_name} denied")
```

---

## Example Roles

### Read-Only Analyst
```json
{
  "name": "analyst",
  "mcp_access": ["database_mcp", "filesystem"],
  "tool_restrictions": {
    "database_mcp": {
      "mode": "allow",
      "tools": ["query", "describe_table"],
      "resources": ["schema://public"],
      "prompts": ["generate_query"]
    },
    "filesystem": {
      "mode": "allow",
      "tools": ["read_file", "list_directory"],
      "resources": ["/home/*"],
      "prompts": ["search_files"]
    }
  }
}
```

### Developer (Almost Full)
```json
{
  "name": "developer",
  "mcp_access": ["database_mcp", "filesystem", "github"],
  "tool_restrictions": {
    "database_mcp": {
      "mode": "deny",
      "tools": ["drop_database", "drop_table"],
      "resources": [],
      "prompts": []
    },
    "filesystem": {
      "mode": "all"
    },
    "github": {
      "mode": "all"
    }
  }
}
```

---

## TODO: Integration Steps

### Step 1: Add Permission Checker to OMNI2
**File:** `omni2/app/utils/permission_checker.py` (already created)
```python
from app.utils.permission_checker import require_tool_access

# In tool execution
await require_tool_access(role, mcp_name, tool_name)
```

### Step 2: Fetch Role in OMNI2
```python
# Add to OMNI2 middleware or request handler
async def get_user_role(user_id: int):
    # Call auth_service to get user's role
    response = await httpx.get(f"{AUTH_SERVICE}/users/{user_id}")
    user = response.json()
    
    response = await httpx.get(f"{AUTH_SERVICE}/roles/{user['role_id']}")
    return response.json()
```

### Step 3: Apply Checks
```python
# In omni2/app/routers/tools.py
@router.post("/call")
async def call_tool(request: ToolCallRequest, user_id: int):
    # Get role
    role = await get_user_role(user_id)
    
    # Check permission
    await require_tool_access(role, request.server, request.tool)
    
    # Execute tool
    result = await mcp_registry.call_tool(...)
    return result
```

---

## Key Files

**Frontend:**
- `omni2/dashboard/frontend/src/components/iam/PermissionBuilder.tsx`
- `omni2/dashboard/frontend/src/components/iam/CreateRoleModal.tsx`
- `omni2/dashboard/frontend/src/components/iam/EditRoleModal.tsx`

**Backend:**
- `auth_service/routes/roles.py` - Role CRUD
- `omni2/app/utils/permission_checker.py` - Permission logic (NOT USED YET)
- `omni2/app/routers/tools.py` - Tool execution (NO CHECKS YET)

**Database:**
- `auth_service.roles` table - Stores permissions

---

## Current Status

✅ **Done:**
- UI for creating/editing roles with MCP/tool selection
- Database schema supports JSONB permissions
- OMNI2 endpoint returns tools/resources/prompts
- Permission checker utility created

❌ **Not Done:**
- OMNI2 doesn't check permissions before tool execution
- No integration between auth_service and OMNI2
- No middleware to fetch user's role
- No enforcement of restrictions

---

## Quick Test (When Implemented)

1. Create role "analyst" with ALLOW mode for `database_mcp.query` only
2. Assign user to "analyst" role
3. Try to execute `database_mcp.drop_table` → Should get 403 Forbidden
4. Try to execute `database_mcp.query` → Should work
