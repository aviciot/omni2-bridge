# Phase 2: MCP Management

**Duration**: 18 hours  
**Status**: ⏳ NOT STARTED  
**Progress**: 0%

---

## 2.1 MCP Server Grid (8 hours)

**Status**: ⏳ NOT STARTED

### Backend Endpoints

#### GET /api/v1/mcps

**Purpose**: List all MCP servers with stats

**Implementation**:
```python
# Query omni2.mcp_servers
# Join with omni2.mcp_tools for tool count
# Aggregate stats from omni2.audit_logs
```

**Response**:
```json
{
  "mcps": [
    {
      "id": 1,
      "name": "Database Performance MCP",
      "url": "http://database_mcp:8300",
      "status": "healthy",
      "uptime": "99.8%",
      "requests_today": 2400,
      "avg_response_ms": 234,
      "cost_today": 3.45,
      "tool_count": 14,
      "last_health_check": "2026-01-26T10:30:00Z"
    }
  ]
}
```

#### GET /api/v1/mcps/{id}

**Purpose**: Detailed MCP information

#### GET /api/v1/mcps/{id}/tools

**Purpose**: List all tools for specific MCP

**Response**:
```json
{
  "tools": [
    {
      "name": "analyze_full_sql_context",
      "description": "Comprehensive SQL analysis",
      "usage_count": 450,
      "avg_duration_ms": 234,
      "success_rate": 98.5
    }
  ]
}
```

#### POST /api/v1/mcps/{id}/health

**Purpose**: Trigger health check

**Implementation**:
```python
# Calls omni2:8000/api/v1/mcps/{id}/health
# Updates omni2.mcp_servers.health_status
```

### Frontend Components

#### MCPCard Component

**Features**:
- Glassmorphic card design
- Status indicator (pulse animation)
- Stats display (uptime, requests, cost)
- Tool badges (first 3 + count)
- Quick actions menu
- Hover effects

**Props**:
```typescript
interface MCPCardProps {
  mcp: {
    id: number;
    name: string;
    status: 'healthy' | 'degraded' | 'unhealthy';
    uptime: string;
    requests_today: number;
    avg_response_ms: number;
    cost_today: number;
    tools: string[];
  };
  onViewDetails: () => void;
  onHealthCheck: () => void;
}
```

#### MCPGrid Component

**Features**:
- Responsive grid layout (1-3 columns)
- Search bar
- Filter by status
- Sort options
- Loading skeletons

### Tasks

- [ ] Backend: Create `/api/v1/mcps` endpoint
- [ ] Backend: Create `/api/v1/mcps/{id}` endpoint
- [ ] Backend: Create `/api/v1/mcps/{id}/tools` endpoint
- [ ] Backend: Create `/api/v1/mcps/{id}/health` endpoint
- [ ] Frontend: Create MCPCard component
- [ ] Frontend: Create MCPGrid layout
- [ ] Frontend: Add search functionality
- [ ] Frontend: Add filter functionality
- [ ] Test: Verify MCP data accuracy
- [ ] Test: Verify health check works

---

## 2.2 MCP Detail Page (10 hours)

**Status**: ⏳ NOT STARTED

### Backend Endpoints

#### GET /api/v1/mcps/{id}/logs

**Purpose**: Recent logs for MCP

**Response**:
```json
{
  "logs": [
    {
      "timestamp": "2026-01-26T10:30:00Z",
      "level": "info",
      "message": "Health check passed",
      "duration_ms": 45
    }
  ]
}
```

#### GET /api/v1/mcps/{id}/config

**Purpose**: Current MCP configuration

**Response**:
```json
{
  "config": {
    "url": "http://database_mcp:8300",
    "timeout_seconds": 30,
    "max_retries": 2,
    "auth_type": "bearer",
    "enabled": true
  }
}
```

#### GET /api/v1/mcps/{id}/analytics

**Purpose**: MCP-specific analytics

**Response**:
```json
{
  "analytics": {
    "requests_by_hour": [...],
    "tool_usage": [...],
    "error_rate": [...],
    "response_times": [...]
  }
}
```

### Frontend Pages

#### MCP Detail Page Layout

**Tabs**:
1. **Overview**: Health status, performance charts, recent activity
2. **Tools**: Tool list with usage stats
3. **Configuration**: Config editor (read-only for now)
4. **Logs**: Real-time log viewer

#### Components

**HealthStatus Component**:
- Current status badge
- Last health check time
- Error count
- Uptime percentage

**ToolsList Component**:
- Table with tool name, description, usage count
- Sort by usage
- Filter by name
- Click to see tool details

**LogViewer Component**:
- Real-time log stream
- Filter by level (info, warning, error)
- Search functionality
- Auto-scroll toggle

**ConfigEditor Component**:
- JSON editor (read-only)
- Syntax highlighting
- Copy to clipboard

### Tasks

- [ ] Backend: Create `/api/v1/mcps/{id}/logs` endpoint
- [ ] Backend: Create `/api/v1/mcps/{id}/config` endpoint
- [ ] Backend: Create `/api/v1/mcps/{id}/analytics` endpoint
- [ ] Frontend: Create MCP detail page layout
- [ ] Frontend: Create tab navigation
- [ ] Frontend: Create HealthStatus component
- [ ] Frontend: Create ToolsList component
- [ ] Frontend: Create LogViewer component
- [ ] Frontend: Create ConfigEditor component
- [ ] Test: Verify all tabs work
- [ ] Test: Verify log streaming

---

## Phase 2 Completion Criteria

- [ ] MCP grid displays all servers
- [ ] Search and filter work
- [ ] Health check triggers successfully
- [ ] Detail page loads for each MCP
- [ ] All tabs render correctly
- [ ] Logs stream in real-time
- [ ] Analytics charts display data
- [ ] No console errors

---

**Last Updated**: January 26, 2026  
**Dependencies**: Phase 1 complete
