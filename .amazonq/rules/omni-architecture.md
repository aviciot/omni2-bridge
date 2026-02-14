# OMNI2 Architecture Rules

## 🔧 SYSTEM CONFIGURATION

### Database
- **Connection**: `postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni`
- **Schemas**: `auth_service`, `omni2`, `omni2_dashboard`, `mcp_performance`, `mcp_informatica`, `macgyver`
- **Dashboard Config**: `omni2_dashboard.dashboard_config` (keys: `alert_thresholds`, `chart_settings`, `dev_features`, `dev_mode`, `live_updates`, `refresh_interval`)

### Service Ports
- **Traefik**: 8090 (public gateway)
- **Auth Service**: 8001 (internal only)
- **OMNI2**: 8000 (internal only - NEVER expose directly)
- **Dashboard Backend**: 8500 (internal only)
- **Dashboard Frontend**: 3001 (dev only)

### Environment Variables
```env
# Dashboard Backend
DATABASE_URL=postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni
TRAEFIK_BASE_URL=http://host.docker.internal:8090

# OMNI2
DATABASE_URL=postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni
AUTH_SERVICE_URL=http://auth-service:8001
```

## 🔒 SECURITY RULES

### CRITICAL: Traefik-Only Access
1. **ALL OMNI2 requests MUST go through Traefik** (port 8090)
2. **NEVER direct OMNI2 access** (port 8000)
3. **Use TRAEFIK_BASE_URL environment variable** - NEVER hardcode URLs
4. **Auth headers required**: `X-User-Id`, `X-User-Username`, `X-User-Role`

### Request Flow
```
Dashboard Backend → Traefik (8090) → Auth Service → OMNI2 (8000)
```

### Configuration Properties
```python
settings.omni2_api_url      # -> http://host.docker.internal:8090/api/v1
settings.omni2_ws_url       # -> ws://host.docker.internal:8090/ws
settings.auth_service_url   # -> http://host.docker.internal:8090/auth/api/v1
```

## 💻 CODE PATTERNS

### ✅ Correct API Calls
```typescript
const response = await fetch(`${process.env.NEXT_PUBLIC_OMNI2_API_URL}/api/v1/endpoint`, {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

### ❌ Wrong API Calls
```typescript
// NEVER DO THESE:
fetch('http://localhost:8000/api/v1/endpoint');           // Direct OMNI2
fetch('http://host.docker.internal:8090/api/v1/endpoint'); // Hardcoded URL
```

### WebSocket Pattern
```typescript
// ✅ Correct (via Dashboard Backend proxy)
const ws = new WebSocket(`ws://localhost:8500/ws?token=${token}`);

// ❌ Wrong (direct to OMNI2)
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);
```

### Database Queries
```python
# ✅ Always use schema-qualified names
await db.execute(text("SELECT * FROM omni2_dashboard.dashboard_config"))

# ❌ Never use unqualified names
await db.execute(text("SELECT * FROM dashboard_config"))
```

## 🧪 TESTING REQUIREMENTS

### Mandatory Test Script
**`test_omni2_system.py`** - Run after EVERY change
- **Security**: Verifies OMNI2 port 8000 is blocked
- **Authentication**: Tests login flow with `avi@omni.com` / `avi123`
- **Traefik Routing**: Verifies proper request flow through gateway
- **Dashboard**: Tests all monitoring endpoints
- **Health Monitoring**: Verifies system health endpoints
- Must show 100% pass rate for system to be considered healthy

### Test Script Rules
- **NEVER use Unicode characters** (Windows cp1252 encoding)
- Use ASCII: `[OK]`, `[ERROR]`, `[INFO]` instead of emojis
- Keep output simple and readable
- Returns proper exit codes for CI/CD integration

## 🔄 DEVELOPMENT PROTOCOL

### Baby Steps Approach
1. Make small changes (1-2 files max)
2. Test immediately
3. **Run `test_omni2_system.py`** to verify system integrity
4. Verify logs:
   - Traefik: `docker-compose -f traefik-external/docker-compose.yml logs -f traefik-external`
   - Auth: `docker-compose -f auth_service/docker-compose.yml logs -f auth-service`
   - OMNI2: `docker-compose logs -f omni2`
   - Dashboard: `docker-compose logs -f dashboard-backend`
5. Only proceed if stable

### Adding New Features

#### Dashboard Configuration
1. Insert into database:
```sql
INSERT INTO omni2_dashboard.dashboard_config (key, value) 
VALUES ('your_key', '{"field": "value"}'::jsonb);
```
2. Update `CONFIG_METADATA` in `/dashboard/frontend/src/app/admin/page.tsx`
3. Access via `/api/v1/config` endpoint

#### New Endpoints
1. Add endpoint to appropriate service
2. Update `test_omni2_system.py` if monitoring-related
3. Run system test to verify integration
4. Verify Traefik routing works

### Service Responsibilities
- **Dashboard Backend**: Config, caching, WebSocket proxy
- **OMNI2**: MCP operations, circuit breaker, event broadcasting
- **Auth Service**: Authentication, authorization, user management

### Code Organization
1. **Single Source of Truth**: Use `TRAEFIK_BASE_URL` environment variable
2. **No Hardcoded URLs**: Always use configuration properties
3. **Centralized Configuration**: All URL generation in config.py
4. **Incremental Testing**: Test each change before proceeding
5. **Log Verification**: Monitor all service logs during changes

## 🌐 NETWORK CONFIGURATION

### Docker Networks
- `omni2_omni2-network`: OMNI2, Traefik, Auth
- `db-net`: Dashboard Backend, Database
- Cross-network: Use `host.docker.internal`

## 🚨 AI ASSISTANT RULES

### Rule Maintenance
**Update this file when:**
- New containers/services added
- Database schemas change
- Service ports change
- New environment variables required
- Security rules modified
- New endpoints added

**Process:**
1. AI must RAISE discrepancies found during investigation
2. Wait for user approval before updating
3. AI must SUGGEST additions for architectural changes
4. Keep this file as single source of truth

**Format for suggestions:** "🔔 RULE UPDATE NEEDED: [description] - Should I add this to omni-architecture.md?"

### Investigation Responsibilities
- If connection details don't match → RAISE discrepancy
- If new container discovered → SUGGEST adding to rules
- If schema/table structure differs → RAISE for verification
- If service ports change → RAISE for approval
