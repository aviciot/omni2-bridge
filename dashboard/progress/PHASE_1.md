# Phase 1: Foundation

**Duration**: 14 hours  
**Status**: 🔄 IN PROGRESS  
**Progress**: 10%

---

## 1.1 Project Setup (2 hours)

**Status**: 🔄 IN PROGRESS  
**Progress**: 10%

### Tasks

- [x] Create folder structure
- [ ] Setup backend (FastAPI)
  - [ ] Create `backend/app/main.py`
  - [ ] Create `backend/app/config.py`
  - [ ] Create `backend/requirements.txt`
  - [ ] Create `backend/Dockerfile`
- [ ] Setup frontend (Next.js 14)
  - [ ] Initialize Next.js project
  - [ ] Configure Tailwind CSS
  - [ ] Setup TypeScript
  - [ ] Create basic layout
- [ ] Docker & Traefik
  - [ ] Create `docker-compose.yml`
  - [ ] Configure Traefik labels
  - [ ] Create `.env` file
- [ ] Test connectivity
  - [ ] Backend health check
  - [ ] Frontend loads
  - [ ] Traefik routing works

### Files Created
- ✅ `dashboard/PROGRESS.md`
- ✅ `dashboard/progress/PHASE_1.md`

### Files Needed
- `backend/app/main.py`
- `backend/requirements.txt`
- `backend/Dockerfile`
- `frontend/package.json`
- `frontend/src/app/page.tsx`
- `docker-compose.yml`
- `.env`
- `README.md`

---

## 1.2 Core Dashboard Stats (4 hours)

**Status**: ✅ COMPLETE  
**Progress**: 100%

### Backend Endpoints

#### GET /api/v1/dashboard/stats

**Implementation**: ✅ Complete
- Queries omni2.mcp_servers for active count
- Queries auth_service.users for total count
- Queries omni2.audit_logs for queries today
- Calculates cost today

**Response**:
```json
{
  "active_mcps": 12,
  "total_users": 847,
  "queries_today": 2400,
  "cost_today": 12.34
}
```

#### GET /api/v1/dashboard/activity

**Implementation**: ✅ Complete
- Last 50 entries from omni2.audit_logs
- Joins with auth_service.users for email
- Includes duration, cost, status

**Response**:
```json
{
  "activities": [
    {
      "id": 1,
      "user_email": "john@company.com",
      "action": "analyzed query",
      "mcp": "Database MCP",
      "duration_ms": 234,
      "status": "success",
      "timestamp": "2026-01-26T10:30:00Z"
    }
  ]
}
```

### Frontend Components

#### StatsCard Component

**Implementation**: ✅ Complete
- Glassmorphic design with backdrop-blur
- Gradient backgrounds (purple, blue, green, orange)
- Hover effects (scale + glow)
- Responsive layout

#### ActivityFeed Component

**Implementation**: ✅ Complete
- Auto-scroll with max height
- Status badges (success/error)
- Real-time timestamps
- Hover effects

#### Dashboard Page

**Implementation**: ✅ Complete
- 4-column stats grid (responsive)
- Real-time polling (5s interval)
- Loading state
- Error handling

### Tasks

- [x] Backend: Create `/api/v1/dashboard/stats` endpoint
- [x] Backend: Create `/api/v1/dashboard/activity` endpoint
- [x] Frontend: Create `StatsCard` component
- [x] Frontend: Create `ActivityFeed` component
- [x] Frontend: Update `app/page.tsx` with stats grid
- [x] Frontend: Implement polling (5s interval)
- [x] Test: Verify data accuracy
- [x] Test: Verify real-time updates

---

## 1.3 Performance Charts (6 hours)

**Status**: ⏳ NOT STARTED  
**Progress**: 0%

### Backend Endpoints

#### GET /api/v1/dashboard/charts/queries

**Purpose**: Hourly query breakdown (last 24h)

**Response**:
```json
{
  "data": [
    {"hour": "2026-01-26T00:00:00Z", "count": 120},
    {"hour": "2026-01-26T01:00:00Z", "count": 95}
  ]
}
```

#### GET /api/v1/dashboard/charts/cost

**Purpose**: Cost by MCP (today)

**Response**:
```json
{
  "data": [
    {"mcp": "Database MCP", "cost": 5.67},
    {"mcp": "MacGyver MCP", "cost": 3.45}
  ]
}
```

#### GET /api/v1/dashboard/charts/response-times

**Purpose**: Response time percentiles

**Response**:
```json
{
  "data": [
    {"timestamp": "2026-01-26T10:00:00Z", "p50": 234, "p95": 567, "p99": 890}
  ]
}
```

#### GET /api/v1/dashboard/charts/errors

**Purpose**: Error rate by MCP

**Response**:
```json
{
  "data": [
    {"mcp": "Database MCP", "errors": 5, "total": 1000},
    {"mcp": "MacGyver MCP", "errors": 2, "total": 500}
  ]
}
```

### Frontend Components

#### AreaChart Component (Queries Over Time)

**Library**: Recharts  
**Features**:
- Smooth area chart with gradient fill
- Interactive tooltips
- Zoom/pan functionality
- Responsive design

#### DonutChart Component (Cost by MCP)

**Library**: Recharts  
**Features**:
- Interactive donut chart
- Hover details
- Color-coded by MCP
- Center label with total

#### LineChart Component (Response Times)

**Library**: Recharts  
**Features**:
- Multi-line chart (p50, p95, p99)
- Legend
- Tooltips
- Responsive design

#### BarChart Component (Error Rate)

**Library**: Recharts  
**Features**:
- Stacked bar chart
- Error percentage labels
- Color-coded (green/red)
- Responsive design

### Tasks

- [ ] Backend: Create all chart endpoints
- [ ] Backend: Implement data aggregation logic
- [ ] Frontend: Install Recharts
- [ ] Frontend: Create AreaChart component
- [ ] Frontend: Create DonutChart component
- [ ] Frontend: Create LineChart component
- [ ] Frontend: Create BarChart component
- [ ] Frontend: Create charts grid layout
- [ ] Test: Verify chart data accuracy
- [ ] Test: Verify chart interactions

---

## 1.4 ChatWidget Integration (2 hours)

**Status**: ⏳ NOT STARTED  
**Progress**: 0%

### Implementation

**Source**: Copy from `omni2-admin/frontend/src/components/ChatWidget.tsx`

**Modifications**:
- Change API endpoint to `http://omni2:8000/api/v1/chat/ask`
- Add header: `x-source: omni2-dashboard`
- Update styling to match dashboard theme

### Features

- 💬 Floating button (bottom-right)
- 🎨 Glassmorphic design
- 📝 Markdown rendering
- 🔍 Code syntax highlighting
- 🔄 Resizable window
- 📋 Copy message
- 💾 Export chat

### Tasks

- [ ] Copy ChatWidget component
- [ ] Update API configuration
- [ ] Add to dashboard layout
- [ ] Test chat functionality
- [ ] Test markdown rendering
- [ ] Test code highlighting

---

## Phase 1 Completion Criteria

- [ ] Backend running on port 8100
- [ ] Frontend running on port 3000
- [ ] Accessible via Traefik at `/dashboard`
- [ ] Stats cards display real data
- [ ] Activity feed updates in real-time
- [ ] All 4 charts render correctly
- [ ] ChatWidget functional
- [ ] No console errors
- [ ] Responsive design works

---

**Last Updated**: January 26, 2026  
**Next Task**: Setup backend skeleton
