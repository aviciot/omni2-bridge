# Phase 3: User Management

**Duration**: 14 hours  
**Status**: ⏳ NOT STARTED  
**Progress**: 0%

---

## 3.1 User List Table (6 hours)

**Status**: ⏳ NOT STARTED

### Backend Endpoints

#### GET /api/v1/users

**Purpose**: List all users with stats

**Query Parameters**:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 50)
- `search`: Search by email/name
- `role`: Filter by role
- `status`: Filter by status (active/inactive)

**Implementation**:
```python
# Query auth_service.users
# Aggregate stats from omni2.audit_logs
# Join with omni2.user_usage_limits
```

**Response**:
```json
{
  "users": [
    {
      "id": 1,
      "email": "john@company.com",
      "name": "John Doe",
      "role": "admin",
      "status": "active",
      "queries_count": 2400,
      "cost_total": 45.67,
      "last_seen": "2026-01-26T10:30:00Z",
      "created_at": "2024-01-15T08:00:00Z"
    }
  ],
  "total": 847,
  "page": 1,
  "pages": 17
}
```

#### GET /api/v1/users/{id}/stats

**Purpose**: User statistics

**Response**:
```json
{
  "stats": {
    "total_queries": 2400,
    "total_cost": 45.67,
    "avg_response_ms": 234,
    "success_rate": 98.5,
    "favorite_mcp": "Database MCP",
    "queries_by_day": [...],
    "cost_by_mcp": [...]
  }
}
```

### Frontend Components

#### UserTable Component

**Features**:
- Sortable columns
- Pagination
- Search bar
- Role filter dropdown
- Status filter dropdown
- Bulk actions (future)
- Export to CSV (future)

**Columns**:
- Avatar + Name + Email
- Role badge
- Status badge
- Queries count
- Total cost
- Last seen
- Actions menu

#### UserFilters Component

**Features**:
- Search input (debounced)
- Role select (all, admin, user, viewer)
- Status select (all, active, inactive)
- Clear filters button

### Tasks

- [ ] Backend: Create `/api/v1/users` endpoint
- [ ] Backend: Implement pagination
- [ ] Backend: Implement search
- [ ] Backend: Implement filters
- [ ] Backend: Create `/api/v1/users/{id}/stats` endpoint
- [ ] Frontend: Create UserTable component
- [ ] Frontend: Create UserFilters component
- [ ] Frontend: Implement sorting
- [ ] Frontend: Implement pagination
- [ ] Test: Verify search works
- [ ] Test: Verify filters work
- [ ] Test: Verify pagination works

---

## 3.2 User Detail Page (8 hours)

**Status**: ⏳ NOT STARTED

### Backend Endpoints

#### GET /api/v1/users/{id}

**Purpose**: Detailed user information

**Response**:
```json
{
  "user": {
    "id": 1,
    "email": "john@company.com",
    "name": "John Doe",
    "role": "admin",
    "status": "active",
    "teams": ["Engineering", "DevOps"],
    "created_at": "2024-01-15T08:00:00Z",
    "last_seen": "2026-01-26T10:30:00Z"
  }
}
```

#### GET /api/v1/users/{id}/activity

**Purpose**: User activity timeline

**Response**:
```json
{
  "activities": [
    {
      "id": 1,
      "action": "analyzed query",
      "mcp": "Database MCP",
      "tool": "analyze_full_sql_context",
      "duration_ms": 234,
      "cost": 0.0012,
      "status": "success",
      "timestamp": "2026-01-26T10:30:00Z"
    }
  ]
}
```

#### GET /api/v1/users/{id}/permissions

**Purpose**: User MCP permissions

**Response**:
```json
{
  "permissions": [
    {
      "mcp": "Database MCP",
      "mode": "allow",
      "allowed_tools": ["analyze_full_sql_context"],
      "denied_tools": []
    }
  ]
}
```

### Frontend Pages

#### User Detail Page Layout

**Sections**:
1. **Profile Card**: Avatar, name, email, role, teams
2. **Stats Cards**: Total queries, cost, success rate
3. **Activity Timeline**: Recent activity with filters
4. **Usage Charts**: Queries over time, cost by MCP
5. **Permissions**: MCP access and tool permissions

#### Components

**ProfileCard Component**:
- Large avatar
- Name and email
- Role badge
- Teams list
- Join date
- Last seen

**ActivityTimeline Component**:
- Chronological list
- Filter by MCP
- Filter by status
- Pagination
- Expandable details

**UsageCharts Component**:
- Queries over time (line chart)
- Cost by MCP (donut chart)
- Response times (area chart)

**PermissionsEditor Component**:
- MCP list with access status
- Tool-level permissions
- Read-only for now (edit in Phase 4)

### Tasks

- [ ] Backend: Create `/api/v1/users/{id}` endpoint
- [ ] Backend: Create `/api/v1/users/{id}/activity` endpoint
- [ ] Backend: Create `/api/v1/users/{id}/permissions` endpoint
- [ ] Frontend: Create user detail page layout
- [ ] Frontend: Create ProfileCard component
- [ ] Frontend: Create ActivityTimeline component
- [ ] Frontend: Create UsageCharts component
- [ ] Frontend: Create PermissionsEditor component
- [ ] Test: Verify all data loads
- [ ] Test: Verify charts render
- [ ] Test: Verify timeline pagination

---

## Phase 3 Completion Criteria

- [ ] User table displays all users
- [ ] Search and filters work
- [ ] Pagination works
- [ ] User detail page loads
- [ ] Activity timeline displays
- [ ] Usage charts render
- [ ] Permissions display correctly
- [ ] No console errors

---

**Last Updated**: January 26, 2026  
**Dependencies**: Phase 1 complete
