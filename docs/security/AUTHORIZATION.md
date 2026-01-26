# Authorization

**Role-Based Access Control (RBAC)**

---

## 🔑 Overview

Omni2 implements **Role-Based Access Control (RBAC)** to manage user permissions.

---

## Roles

| Role | Permissions | Use Case |
|------|-------------|----------|
| **super_admin** | Full system access | System administrators |
| **admin** | Manage users, MCPs, settings | Team leads |
| **user** | Use MCPs, view own data | Regular users |
| **read_only** | View-only access | Auditors, observers |

---

## Permissions

### User Management
- `users:create` - Create new users
- `users:read` - View user list
- `users:update` - Modify user details
- `users:delete` - Delete users

### MCP Management
- `mcps:create` - Add new MCPs
- `mcps:read` - View MCP list
- `mcps:update` - Modify MCP config
- `mcps:delete` - Remove MCPs
- `mcps:execute` - Call MCP tools

### System Management
- `system:settings` - Modify system settings
- `system:logs` - View audit logs
- `system:health` - View system health

---

## Permission Checks

```python
@require_permission("mcps:create")
async def create_mcp(mcp_data: MCPCreate, user: User):
    # User has permission, proceed
    pass
```

**[Back to Security Overview](./SECURITY_OVERVIEW)**
