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

### Service Ports & Exposure

| Service | Internal Port | External Port | Exposed? |
|---------|--------------|---------------|----------|
| **Traefik** | 80 | 8090 | ✅ Public Gateway |
| **Auth Service** | 8001 | - | ❌ Internal Only |
| **OMNI2** | 8000 | - | ❌ Internal Only |
| **Dashboard Backend** | 8500 | - | ❌ Internal Only |
| **Dashboard Frontend** | 3000 | 3001 | ✅ Dev Only |

### 🚨 CRITICAL RULES

#### Rule 1: OMNI2 Never Exposes Ports
- OMNI2 runs on internal port `8000`
- **NEVER** expose OMNI2 directly to external network
- All access MUST go through Traefik

#### Rule 2: Communication Flow (Backend → OMNI2)
```
Dashboard Backend → Traefik (8090) → Auth Service → OMNI2 (8000)
```

**Steps:**
1. Dashboard Backend sends request to `http://host.docker.internal:8090` (Traefik)
2. Traefik forwards to Auth Service for authentication
3. Auth Service validates token and adds headers:
   - `X-User-Id`
   - `X-User-Username`
   - `X-User-Role`
4. Auth Service forwards to OMNI2
5. OMNI2 processes request and returns response

#### Rule 3: WebSocket Flow
```
Browser → Dashboard Backend (8500) → Traefik (8090) → OMNI2 (8000)
```

**WebSocket URLs:**
- **Development**: `ws://localhost:8500/ws` (Dashboard Backend proxy)
- **Production**: `wss://your-domain.com/ws` (via Traefik)

#### Rule 4: Database Access
- **Dashboard Backend** connects to: `postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni`
- **OMNI2** connects to: `postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni`
- Both services use schema-qualified queries (e.g., `omni2_dashboard.dashboard_config`)

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
AUTH_SERVICE_URL=http://auth-service:8001
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

## 📊 Service Responsibilities

### Traefik (Port 8090)
- API Gateway & Reverse Proxy
- Routes `/auth/*` → Auth Service
- Routes `/api/*` → OMNI2
- Routes `/ws` → OMNI2 WebSocket
- SSL/TLS termination (production)

### Auth Service (Port 8001)
- User authentication & authorization
- JWT token validation
- Role-based access control (RBAC)
- Injects user headers for downstream services

### OMNI2 (Port 8000)
- MCP registry & health monitoring
- Circuit breaker management
- WebSocket event broadcasting
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
