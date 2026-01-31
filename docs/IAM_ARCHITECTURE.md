# IAM Architecture - Separation of Concerns

## Schema Ownership

### auth_service Schema (Identity & Access)
**Owner**: auth_service microservice  
**Purpose**: User identity, roles, teams, permissions  
**Tables**:
- `roles` - Role definitions with MCP/tool permissions
- `teams` - Team definitions with shared resources
- `users` - User accounts with role assignment
- `team_members` - User-team membership
- `user_overrides` - User-specific permission overrides
- `auth_audit` - Authentication/authorization audit log
- `user_sessions` - Active JWT sessions
- `blacklisted_tokens` - Revoked tokens

**Access**: Direct database access (asyncpg)

---

### omni2_dashboard Schema (Dashboard Data)
**Owner**: dashboard backend  
**Purpose**: Dashboard-specific data (preferences, cache, analytics)  
**Tables**:
- `dashboard_config` - App-wide settings
- `user_preferences` - Per-user dashboard preferences
- `dashboard_cache` - Temporary cache for expensive queries
- `activity_feed` - Recent user actions (for display)
- `mcp_usage_stats` - MCP usage analytics

**Access**: Direct database access (SQLAlchemy or asyncpg)

**User Data**: Fetched from auth_service via HTTP API (no direct DB access)

---

## Data Flow

### Dashboard Needs User Info

```
Dashboard Frontend
    ↓ GET /api/users (with JWT)
Dashboard Backend
    ↓ HTTP GET http://auth_service:8700/api/v1/users
    ↓ (includes JWT in Authorization header)
auth_service
    ↓ Query auth_service.users table
    ↓ Return user data
Dashboard Backend
    ↓ Return to frontend
```

**Why HTTP not direct DB?**
- Microservice pattern - each service owns its data
- auth_service can enforce permissions
- auth_service can add business logic (e.g., filter inactive users)
- Easier to scale/deploy independently

---

## IAM Tab Implementation

### Where Does IAM Live?

**Option 1: Dashboard calls auth_service APIs** ✅ RECOMMENDED
```
Dashboard IAM Tab (localhost:3001/iam)
    ↓ GET /auth/api/v1/roles
    ↓ POST /auth/api/v1/teams
    ↓ PUT /auth/api/v1/users/{id}
auth_service (localhost:8700)
    ↓ Validates JWT (admin only)
    ↓ Queries auth_service schema
    ↓ Returns data
```

**Benefits**:
- auth_service owns identity data
- Dashboard is just a UI
- Can add CLI/API clients later
- Consistent with microservice pattern

---

## Database Initialization

### auth_service
```bash
cd auth_service
python init_iam.py --drop  # Drop and recreate
python init_iam.py         # Create/update only
```

**Creates**:
- auth_service schema
- 8 tables (roles, teams, users, etc.)
- Default roles (super_admin, developer, analyst, viewer)
- Admin users (avi, admin, user)

---

### Dashboard
```bash
cd omni2/dashboard/backend
python init_dashboard.py --drop  # Drop and recreate
python init_dashboard.py         # Create/update only
```

**Creates**:
- omni2_dashboard schema
- 5 tables (config, preferences, cache, activity, stats)
- Default config values

---

## Code Synchronization

### auth_service
**Schema**: `auth_service/init_iam.py`  
**Models**: `auth_service/models/iam_schemas.py`  

**Rule**: When you change init_iam.py, update iam_schemas.py immediately!

---

### Dashboard
**Schema**: `omni2/dashboard/backend/init_dashboard.py`  
**Models**: `omni2/dashboard/backend/app/schemas/dashboard_models.py`  

**Rule**: When you change init_dashboard.py, update dashboard_models.py immediately!

---

## API Endpoints Needed

### auth_service (IAM APIs)

**Roles**:
- GET /api/v1/roles - List all roles
- POST /api/v1/roles - Create role
- PUT /api/v1/roles/{id} - Update role
- DELETE /api/v1/roles/{id} - Delete role

**Teams**:
- GET /api/v1/teams - List all teams
- POST /api/v1/teams - Create team
- PUT /api/v1/teams/{id} - Update team
- DELETE /api/v1/teams/{id} - Delete team
- POST /api/v1/teams/{id}/members - Add user to team
- DELETE /api/v1/teams/{id}/members/{user_id} - Remove user from team

**Users** (already exists):
- GET /api/v1/users - List users
- POST /api/v1/users - Create user
- PUT /api/v1/users/{id} - Update user
- DELETE /api/v1/users/{id} - Delete user

**Permissions**:
- GET /api/v1/users/{id}/permissions - Get effective permissions
- GET /api/v1/permissions/check - Check if user can do action

---

### Dashboard Backend (UI APIs)

**Stats**:
- GET /api/stats - Hero stats
- GET /api/activity - Recent activity
- GET /api/charts/queries - Query chart data
- GET /api/charts/cost - Cost chart data

**User Preferences**:
- GET /api/preferences - Get my preferences
- PUT /api/preferences - Update my preferences

**Cache Management**:
- DELETE /api/cache - Clear cache

---

## Permission Calculation

### Effective Permissions Formula

```python
def get_effective_permissions(user_id):
    # 1. Get user's role
    role = get_user_role(user_id)
    
    # 2. Get user's teams
    teams = get_user_teams(user_id)
    
    # 3. Get user overrides
    overrides = get_user_overrides(user_id)
    
    # 4. Calculate effective permissions
    effective = {
        "mcp_access": role.mcp_access,
        "tool_access": role.tool_restrictions,
        "rate_limit": role.rate_limit,
        "cost_limit": role.cost_limit_daily
    }
    
    # 5. Apply team restrictions (intersection)
    for team in teams:
        if team.mcp_access:
            effective["mcp_access"] = intersection(
                effective["mcp_access"], 
                team.mcp_access
            )
    
    # 6. Apply user overrides (most restrictive)
    if overrides:
        if overrides.mcp_restrictions:
            effective["mcp_access"] = remove(
                effective["mcp_access"],
                overrides.mcp_restrictions
            )
        if overrides.custom_rate_limit:
            effective["rate_limit"] = min(
                effective["rate_limit"],
                overrides.custom_rate_limit
            )
    
    return effective
```

---

## Summary

**auth_service**:
- Owns user identity, roles, teams, permissions
- Provides IAM APIs
- Uses asyncpg (raw SQL)
- Schema: auth_service

**Dashboard**:
- Owns dashboard-specific data
- Calls auth_service APIs for user data
- Uses SQLAlchemy or asyncpg
- Schema: omni2_dashboard

**IAM Tab**:
- Lives in dashboard frontend
- Calls auth_service APIs
- Admin-only access
- 3 sub-tabs: Users, Roles, Teams
