# Role-Based MCP Access Control System

## Overview
This system provides granular access control for MCP (Model Context Protocol) servers, tools, prompts, and resources based on user roles.

## Architecture

### 1. Role Structure
Each role contains:
- **Basic Info**: name, description
- **MCP Access**: Array of allowed MCP server names
- **Tool Restrictions**: Per-MCP tool access control (JSONB)
- **Dashboard Access**: Dashboard permission level (none/read/full)
- **Rate Limits**: Requests per minute
- **Cost Limits**: Daily spending limit
- **Token Expiry**: Session token lifetime

### 2. Access Control Levels

#### Level 1: MCP Server Access
```json
{
  "mcp_access": ["filesystem", "database", "github"]
}
```
- Controls which MCP servers a role can access
- Empty array = no MCP access
- Used as first-level filter in OMNI2

#### Level 2: Tool Restrictions (Per-MCP)
```json
{
  "tool_restrictions": {
    "filesystem": {
      "mode": "allow",
      "tools": ["read_file", "list_directory"],
      "resources": ["/home/*"],
      "prompts": ["search_files"]
    },
    "database": {
      "mode": "deny",
      "tools": ["drop_table", "delete_database"],
      "resources": [],
      "prompts": []
    },
    "github": {
      "mode": "all"
    }
  }
}
```

**Modes:**
- `all`: Access to all tools/resources/prompts in this MCP
- `allow`: Only specified items allowed (whitelist)
- `deny`: All items except specified (blacklist)
- `none`: No access (block MCP entirely)

**Fields per MCP:**
- `mode`: Access mode (all/allow/deny/none)
- `tools`: Array of tool names
- `resources`: Array of resource URIs
- `prompts`: Array of prompt names

#### Level 3: Resource Access (Future)
```json
{
  "resource_access": {
    "filesystem": {
      "allowed_paths": ["/home/user/projects", "/tmp"],
      "denied_paths": ["/etc", "/root"]
    },
    "database": {
      "allowed_schemas": ["public", "analytics"],
      "denied_tables": ["users.passwords"]
    }
  }
}
```

#### Level 4: Prompt Restrictions (Future)
```json
{
  "prompt_restrictions": {
    "filesystem": {
      "allowed_prompts": ["analyze_code", "search_files"],
      "max_prompt_length": 1000
    }
  }
}
```

## Implementation in OMNI2

### Permission Check Flow
```python
# In OMNI2 request handler
async def check_permission(user_id: int, mcp_name: str, tool_name: str):
    # 1. Get user's role
    user = await get_user(user_id)
    role = await get_role(user.role_id)
    
    # 2. Check MCP access
    if mcp_name not in role.mcp_access:
        raise PermissionError(f"No access to MCP: {mcp_name}")
    
    # 3. Check tool restrictions
    restrictions = role.tool_restrictions.get(mcp_name, {})
    mode = restrictions.get("mode", "all")
    
    if mode == "none":
        raise PermissionError(f"MCP {mcp_name} blocked")
    elif mode == "allow":
        if tool_name not in restrictions.get("tools", []):
            raise PermissionError(f"Tool {tool_name} not allowed")
    elif mode == "deny":
        if tool_name in restrictions.get("tools", []):
            raise PermissionError(f"Tool {tool_name} denied")
    # mode == "all" -> allow
    
    return True
```

### Integration Points

#### 1. MCP Request Middleware
```python
# omni2/middleware/permission_check.py
@app.middleware("http")
async def permission_middleware(request: Request, call_next):
    if request.url.path.startswith("/mcp/"):
        user_id = request.state.user_id
        mcp_name = request.path_params.get("mcp_name")
        tool_name = request.json().get("tool")
        
        await check_permission(user_id, mcp_name, tool_name)
    
    return await call_next(request)
```

#### 2. Tool Execution Filter
```python
# omni2/services/mcp_service.py
async def execute_tool(user_id: int, mcp_name: str, tool_name: str, params: dict):
    # Check permission
    await check_permission(user_id, mcp_name, tool_name)
    
    # Execute tool
    result = await mcp_client.call_tool(mcp_name, tool_name, params)
    return result
```

#### 3. MCP List Filter
```python
# omni2/routes/mcp.py
@router.get("/mcps")
async def list_mcps(user_id: int):
    user = await get_user(user_id)
    role = await get_role(user.role_id)
    
    # Only return MCPs user has access to
    all_mcps = await get_all_mcps()
    allowed_mcps = [
        mcp for mcp in all_mcps 
        if mcp.name in role.mcp_access
    ]
    
    return {"mcps": allowed_mcps}
```

## Usage Examples

### Example 1: Read-Only Analyst
```json
{
  "name": "analyst",
  "mcp_access": ["filesystem", "database", "github"],
  "tool_restrictions": {
    "filesystem": {
      "mode": "allow",
      "tools": ["read_file", "list_directory", "search_files"],
      "resources": ["/home/*", "/projects/*"],
      "prompts": ["analyze_code", "search_files"]
    },
    "database": {
      "mode": "allow",
      "tools": ["query", "describe_table"],
      "resources": ["schema://public"],
      "prompts": ["generate_query"]
    },
    "github": {
      "mode": "allow",
      "tools": ["list_repos", "get_file", "search_code"],
      "resources": [],
      "prompts": []
    }
  },
  "dashboard_access": "read",
  "rate_limit": 50,
  "cost_limit_daily": 5.00
}
```

### Example 2: Full Developer
```json
{
  "name": "developer",
  "mcp_access": ["filesystem", "database", "github", "docker"],
  "tool_restrictions": {
    "filesystem": {"mode": "all"},
    "database": {
      "mode": "deny",
      "tools": ["drop_database", "drop_schema"],
      "resources": [],
      "prompts": []
    },
    "github": {"mode": "all"},
    "docker": {"mode": "all"}
  },
  "dashboard_access": "full",
  "rate_limit": 200,
  "cost_limit_daily": 50.00
}
```

### Example 3: Restricted QA
```json
{
  "name": "qa_tester",
  "mcp_access": ["filesystem", "database"],
  "tool_restrictions": {
    "filesystem": {
      "mode": "allow",
      "tools": ["read_file", "list_directory"],
      "resources": ["/test/*"],
      "prompts": []
    },
    "database": {
      "mode": "allow",
      "tools": ["query", "insert", "update"],
      "resources": ["schema://test"],
      "prompts": []
    }
  },
  "dashboard_access": "read",
  "rate_limit": 100,
  "cost_limit_daily": 10.00
}
```

## Team-Level Overrides

Teams can further restrict role permissions:
```python
# Permission calculation
effective_permissions = role.permissions
if user.teams:
    for team in user.teams:
        # Intersect team restrictions with role permissions
        effective_permissions = intersect(
            effective_permissions,
            team.permissions
        )
```

## API Endpoints

### Dashboard Backend
- `GET /api/v1/roles` - List all roles
- `GET /api/v1/roles/{id}` - Get role details
- `POST /api/v1/roles` - Create role (admin)
- `PUT /api/v1/roles/{id}` - Update role (admin)
- `DELETE /api/v1/roles/{id}` - Delete role (admin)

### Auth Service
- Same endpoints, proxied through dashboard

## Frontend Components

### RolesTab
- Card-based role display
- Shows user count per role
- Create/Edit/Delete actions
- Delete protection for assigned roles

### CreateRoleModal
- Role name & description
- MCP access selector
- Dashboard access level
- Rate & cost limits

### EditRoleModal
- Update all role fields
- Warning for assigned users
- MCP access management

### RoleDetailsModal
- Full role configuration
- MCP access badges
- Tool restrictions JSON
- List of assigned users

## Security Considerations

1. **Admin-Only Operations**: All CUD operations require `X-User-Role: super_admin`
2. **Delete Protection**: Cannot delete roles with assigned users
3. **Immediate Effect**: Role changes affect users immediately
4. **Audit Logging**: All role changes should be logged
5. **Default Deny**: If no permission specified, deny access

## Future Enhancements

1. **Resource-Level Access**: File paths, DB schemas, API endpoints
2. **Prompt Restrictions**: Max length, allowed templates
3. **Time-Based Access**: Temporary permissions, scheduled access
4. **Conditional Access**: Based on IP, time, resource state
5. **Permission Templates**: Pre-configured role templates
6. **Bulk Operations**: Assign multiple users to roles
7. **Role Inheritance**: Parent-child role relationships
8. **Audit Trail**: Detailed permission check logs
