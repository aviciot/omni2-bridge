# OMNI2 System Architecture Rules

## 📍 File Location
Place this file at: `/omni2/OMNI_RULES.md`

---

## 🗄️ Database Configuration

### Database Connection
- **Database Name**: `omni`
- **User**: `omni`
- **Password**: `omni`
- **Host**: `omni_pg_db` (Docker container)
- **Port**: `5432`

### Schemas & Ownership

| Schema | Owner | Purpose | Status |
|--------|-------|---------|--------|
| `auth_service` | omni | Authentication & IAM | ✅ Active |
| `omni2` | omni | OMNI2 core (MCP registry, circuit breaker) | ✅ Active |
| `omni2_dashboard` | omni | Dashboard configuration & cache | ✅ Active |
| `mcp_performance` | omni | MCP performance metrics | ✅ Active |
| `mcp_informatica` | omni | Informatica MCP data | ✅ Active |
| `macgyver` | omni | MacGyver service data | ✅ Active |
| `omni_dashboard_not_in_use` | omni | Legacy/unused | ❌ Deprecated |

### Dashboard Schema Tables (`omni2_dashboard`)
1. **dashboard_config** - System configuration (JSONB key-value store)
2. **dashboard_cache** - Cached data for performance
3. **user_preferences** - User-specific settings

### Dashboard Config Keys
```json
{
  "alert_thresholds": {"cost_daily": 100, "error_rate": 0.05, "response_time_p99": 5000},
  "chart_settings": {"cost_period": "today", "queries_hours": 24, "response_time_hours": 24},
  "dev_features": {"websocket_debug": true, "quick_login": true, "quick_login_email": "...", "quick_login_password": "..."},
  "dev_mode": "true",
  "live_updates": {"max_stored_events": 1000},
  "refresh_interval": {"stats": 5, "charts": 30, "activity": 5}
}
```

---

## 🔐 Service Architecture & Communication Flow

### Authentication Methods

| Endpoint | Auth Method | Token Type | Validated By |
|----------|-------------|------------|-------------|
| **WS Chat** (`/ws/chat`) | JWT | Bearer token | Traefik → Auth Service `/validate` |
| **MCP Gateway** (`/mcp`) | Opaque Token | `omni2_mcp_*` | Omni2 → Auth Service `/mcp/tokens/validate` |

### Service Ports & Exposure

| Service | Internal Port | External Port | Exposed? | Notes |
|---------|--------------|---------------|----------|-------|
| **Traefik** | 80, 8095 | 8090, 8095 | ✅ Public Gateway | Port 8090: API/WS, Port 8095: MCP Gateway |
| **Auth Service** | 8700 | 8700 (dev only) | ⚠️ Should be Internal | Currently exposed for debugging, should remove in production |
| **OMNI2** | 8000 | - | ❌ Internal Only | Never expose directly |
| **Dashboard Backend** | 8500 | - | ❌ Internal Only | |
| **Dashboard Frontend** | 3000 | 3001 | ✅ Dev Only | |

### 🚨 CRITICAL RULES

#### Rule 1: OMNI2 Never Exposes Ports
- OMNI2 runs on internal port `8000`
- **NEVER** expose OMNI2 directly to external network
- All access MUST go through Traefik

#### Rule 2: Communication Flow (Backend → OMNI2)
```
Dashboard Backend → Traefik (8090) → Auth Service (8700) → OMNI2 (8000)
```

**Steps:**
1. Dashboard Backend sends request to `http://host.docker.internal:8090` (Traefik)
2. Traefik forwards to Auth Service (`mcp-auth-service:8700`) for authentication
3. Auth Service validates token and adds headers:
   - `X-User-Id`
   - `X-User-Username`
   - `X-User-Role`
4. Auth Service forwards to OMNI2 (`omni2:8000`)
5. OMNI2 processes request and returns response

#### Rule 3: WebSocket Chat Flow
```
Browser → Dashboard Backend (8500) → Traefik (8090) → Auth Service → OMNI2 (8000)
```

**WebSocket URLs:**
- **Development**: `ws://localhost:8500/ws` (Dashboard Backend proxy)
- **Production**: `wss://your-domain.com/ws` (via Traefik)

**Authentication**: JWT token in query param or header

#### Rule 4: MCP Gateway Flow
```
Claude Desktop/Cursor → Traefik (8095) → OMNI2 (8000) → Auth Service (8700) → MCP Servers
```

**MCP Gateway URL**: `http://localhost:8095/mcp`

**Authentication**: Opaque token (`omni2_mcp_<32chars>`) validated by Omni2

**Token Validation Flow**:
1. OMNI2 receives request with Bearer token
2. OMNI2 calls `http://mcp-auth-service:8700/api/v1/mcp/tokens/validate`
3. Auth Service validates token and returns user context
4. OMNI2 checks permissions and executes tool

**Key Differences from WS Chat**:
- No Traefik ForwardAuth (bypasses JWT validation)
- No LLM - direct proxy to MCP tools
- Token validated by Omni2 calling Auth Service directly
- Session cache (5-min TTL) for permissions and tools list
- Redis listener for user blocking (invalidates session cache)

#### Rule 5: Database Access
- **Dashboard Backend** connects to: `postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni`
- **OMNI2** connects to: `postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni`
- Both services use schema-qualified queries (e.g., `omni2_dashboard.dashboard_config`)

---

## 🔑 MCP Gateway Authentication

### Token Management

**Generate Token** (requires JWT auth):
```bash
POST http://localhost:8090/auth/api/v1/mcp/tokens/generate
Headers:
  Authorization: Bearer <jwt_token>
Body:
  {
    "name": "Claude Desktop",
    "expires_days": 90
  }

Response:
  {
    "token": "omni2_mcp_abc123...",
    "token_id": 1,
    "expires_at": "2024-12-31T23:59:59"
  }
```

**List Tokens**:
```bash
GET http://localhost:8090/auth/api/v1/mcp/tokens
Headers:
  Authorization: Bearer <jwt_token>
```

**Revoke Token**:
```bash
DELETE http://localhost:8090/auth/api/v1/mcp/tokens/{token_id}
Headers:
  Authorization: Bearer <jwt_token>
```

### Role-Based Access Control

**roles.omni_services** controls endpoint access:
- `['chat', 'mcp']` → Can use both WS chat AND MCP gateway
- `['mcp']` → MCP gateway only (Claude Desktop users)
- `['chat']` → WS chat only (no direct MCP access)
- `[]` → No Omni2 access

**Example Roles**:
```sql
-- Full access
INSERT INTO auth_service.roles (name, omni_services, mcp_access) 
VALUES ('developer', ARRAY['chat','mcp'], ARRAY['*']);

-- MCP-only (external clients)
INSERT INTO auth_service.roles (name, omni_services, mcp_access) 
VALUES ('mcp_client', ARRAY['mcp'], ARRAY['*']);

-- Chat-only (no tools)
INSERT INTO auth_service.roles (name, omni_services, mcp_access) 
VALUES ('chat_user', ARRAY['chat'], ARRAY[]);
```

---

## 🌐 Network Configuration

### Docker Networks
- **omni2_omni2-network**: OMNI2, Traefik, Auth Service
- **db-net**: Dashboard Backend, Database
- Services on different networks communicate via `host.docker.internal`

### Environment Variables

#### Dashboard Backend (`.env`)
```env
DATABASE_URL=postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni
OMNI2_WS_URL=ws://host.docker.internal:8090/ws
OMNI2_HTTP_URL=http://host.docker.internal:8090
ENVIRONMENT=development
```

#### OMNI2 (`.env`)
```env
DATABASE_URL=postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni
AUTH_SERVICE_URL=http://mcp-auth-service:8700
```

---

## 🔧 Development Guidelines

### Adding New Configuration
1. Insert into `omni2_dashboard.dashboard_config`:
   ```sql
   INSERT INTO omni2_dashboard.dashboard_config (key, value) 
   VALUES ('your_key', '{"field": "value"}'::jsonb);
   ```
2. Update `CONFIG_METADATA` in `/dashboard/frontend/src/app/admin/page.tsx`
3. Access via `/api/v1/config` endpoint

### Making API Calls from Dashboard
```typescript
// ✅ CORRECT - Via Traefik
const response = await fetch('http://localhost:8090/api/v1/endpoint', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// ❌ WRONG - Direct to OMNI2
const response = await fetch('http://localhost:8000/api/v1/endpoint');
```

### WebSocket Connections
```typescript
// ✅ CORRECT - Via Dashboard Backend proxy
const ws = new WebSocket(`ws://localhost:8500/ws?token=${token}`);

// ❌ WRONG - Direct to OMNI2
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);
```

---

## 🔌 WebSocket Endpoints

| Endpoint | Purpose | Auth | Manager |
|----------|---------|------|----------|
| `/ws/chat` | LLM chat with conversation tracking | JWT (Traefik) | ws_connection_manager |
| `/ws` | Real-time MCP status updates | JWT (Traefik) | websocket_broadcaster |
| `/api/v1/ws/flows/{user_id}` | Flow event streaming | JWT (Traefik) | Direct Redis listener |

### WebSocket Features

**`/ws/chat` (LLM Chat)**
- Conversation tracking with conversation_id
- Tool execution via LLM
- Real-time user blocking via Redis `user_blocked` event
- Caches user permissions per connection (refreshed on reconnect)
- Session-based: permissions cached for connection lifetime

**`/ws` (MCP Status)**
- Real-time MCP health updates
- Circuit breaker state changes
- Event subscription with filters
- Role-based access (admin, developer, dba, super_admin)

**`/api/v1/ws/flows/{user_id}` (Flow Events)**
- Real-time flow execution tracking
- Redis pub/sub: `flow_events:{user_id}`
- Auth check, block check, tool calls, LLM responses

---

## 📊 Service Responsibilities

### Traefik (Port 8090, 8095)
- API Gateway & Reverse Proxy
- Port 8090: Routes `/auth/*` → Auth Service (8700), `/api/*` → OMNI2 (8000), `/ws` → OMNI2 WebSocket
- Port 8095: Routes `/mcp` → OMNI2 (8000) MCP Gateway (no ForwardAuth)
- SSL/TLS termination (production)

### Auth Service (Port 8700)
- User authentication & authorization
- JWT token validation (for WS Chat)
- Opaque token validation (for MCP Gateway)
- Role-based access control (RBAC)
- Injects user headers for downstream services
- Container name: `mcp-auth-service`
- **Security Note**: Port 8700 currently exposed for dev/debugging, should be internal-only in production

### OMNI2 (Port 8000)
- MCP registry & health monitoring
- Circuit breaker management
- WebSocket event broadcasting (3 endpoints: chat, status, flows)
- MCP gateway (direct MCP tool access)
- MCP tool execution

### Dashboard Backend (Port 8500)
- Configuration management
- WebSocket proxy to OMNI2
- Database queries for dashboard data
- Caching layer

### Dashboard Frontend (Port 3001)
- React/Next.js UI
- User interface for all services
- Real-time updates via WebSocket

---

## 🔒 Security Rules

1. **Never expose internal ports** (8000, 8001, 8500) to public
2. **Always authenticate** via Auth Service before reaching OMNI2
3. **Use HTTPS/WSS** in production
4. **Validate JWT tokens** on every request
5. **Apply RBAC** - check `X-User-Role` header
6. **Sanitize database inputs** - use parameterized queries
7. **Rate limit** API endpoints via Auth Service

---

## 🚫 User Blocking System

### Service-Specific Blocking
Admins can block users from specific services independently:

**Database**: `omni2.user_blocks.blocked_services TEXT[]`
- `['chat']` - Block WS Chat only
- `['mcp']` - Block MCP Gateway only  
- `['chat', 'mcp']` - Block both services

### Blocking Flow

**WS Chat:**
1. **Connect** → DB check (`blocked_services`) → `'chat' in list?` → Close
2. **While connected** → Cached in `ws_connection_manager`
3. **Admin blocks** → Redis event → Instant disconnect if `'chat'` blocked
4. **Reconnect** → DB check again → Still blocked? → Close

**MCP Gateway:**
1. **Request** → Token validation → DB check (`blocked_services`) → `'mcp' in list?` → 403
2. **While active** → Cached in `session_cache` (5 min)
3. **Admin blocks** → Redis event → Instant cache invalidation if `'mcp'` blocked
4. **Next request** → Cache miss → DB check again → Still blocked? → 403

### Redis Event Structure
```json
{
  "user_id": 123,
  "blocked_services": ["chat"],
  "custom_message": "Access blocked",
  "blocked_by": 456,
  "timestamp": "1234567890.123"
}
```

### API Endpoints
```bash
# Get block status
GET /api/v1/iam/chat-config/users/{user_id}/block

# Block user
PUT /api/v1/iam/chat-config/users/{user_id}/block
Body: {
  "is_blocked": true,
  "blocked_services": ["chat", "mcp"],
  "block_reason": "Policy violation",
  "custom_block_message": "Your access has been suspended"
}
```

---

## 🚀 Production Deployment

### Port Mapping
- Traefik: `443` (HTTPS) → `80` (internal)
- Dashboard Frontend: `443` (HTTPS) → `3000` (internal)
- All other services: Internal only

### Environment Variables (Production)
```env
OMNI2_WS_URL=wss://api.yourdomain.com/ws
OMNI2_HTTP_URL=https://api.yourdomain.com
DATABASE_URL=postgresql+asyncpg://omni:STRONG_PASSWORD@db-host:5432/omni
```

### Health Checks
- Traefik: `http://localhost:8090/health`
- OMNI2: `http://localhost:8000/health` (internal)
- Dashboard: `http://localhost:8500/health` (internal)

---

## 📝 Quick Reference

### Database Connection String
```
postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni
```

### Traefik Gateway
```
http://localhost:8090 (development)
https://api.yourdomain.com (production)
```

### Schema Prefix
Always use schema-qualified table names:
- `omni2_dashboard.dashboard_config`
- `auth_service.users`
- `omni2.mcp_registry`

---

**Last Updated**: 2024
**Maintained By**: Development Team
