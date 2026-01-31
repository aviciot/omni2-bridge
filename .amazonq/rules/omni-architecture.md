# OMNI2 Architecture Rules

## ⚠️ RULE MAINTENANCE PROTOCOL

**When to Update This File:**
1. Discovery of incorrect information during investigation
2. New containers/services added to the system
3. Database connection details change
4. New schemas or tables created
5. Service communication patterns change
6. New environment variables required
7. Security rules modified

**Process:**
1. AI must RAISE any discrepancies found during investigation
2. Wait for user approval before updating
3. AI must SUGGEST additions for important architectural changes
4. Keep this file as single source of truth

---

### Connection Details
- **Database**: `omni`
- **User**: `omni`
- **Password**: `omni`
- **Host**: `omni_pg_db`
- **Connection String**: `postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni`

### Active Schemas
- `auth_service` - Authentication & IAM
- `omni2` - MCP registry & circuit breaker
- `omni2_dashboard` - Dashboard config (use this for dashboard features)
- `mcp_performance` - Performance metrics
- `mcp_informatica` - Informatica data
- `macgyver` - MacGyver service

### Dashboard Config Table
Location: `omni2_dashboard.dashboard_config`
Keys: `alert_thresholds`, `chart_settings`, `dev_features`, `dev_mode`, `live_updates`, `refresh_interval`

## Service Communication Rules

### CRITICAL: OMNI2 Never Exposes Ports
- OMNI2 runs on internal port 8000
- NEVER expose OMNI2 directly
- All access MUST go through Traefik

### Communication Flow
```
Dashboard Backend → Traefik (8090) → Auth Service → OMNI2 (8000)
```

### Service Ports
- Traefik: 8090 (public gateway)
- Auth Service: 8001 (internal only)
- OMNI2: 8000 (internal only)
- Dashboard Backend: 8500 (internal only)
- Dashboard Frontend: 3001 (dev only)

## API Call Pattern

### Correct Way (via Traefik)
```typescript
const response = await fetch('http://localhost:8090/api/v1/endpoint', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

### Wrong Way (direct to OMNI2)
```typescript
// ❌ NEVER DO THIS
const response = await fetch('http://localhost:8000/api/v1/endpoint');
```

## WebSocket Pattern

### Correct (via Dashboard Backend proxy)
```typescript
const ws = new WebSocket(`ws://localhost:8500/ws?token=${token}`);
```

### Wrong (direct to OMNI2)
```typescript
// ❌ NEVER DO THIS
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);
```

## Environment Variables

### Dashboard Backend
```env
DATABASE_URL=postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni
OMNI2_WS_URL=ws://host.docker.internal:8090/ws
OMNI2_HTTP_URL=http://host.docker.internal:8090
```

### OMNI2
```env
DATABASE_URL=postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni
AUTH_SERVICE_URL=http://auth-service:8001
```

## Database Query Rules

### Always Use Schema-Qualified Names
```python
# ✅ CORRECT
await db.execute(text("SELECT * FROM omni2_dashboard.dashboard_config"))

# ❌ WRONG
await db.execute(text("SELECT * FROM dashboard_config"))
```

## Security Rules

1. All requests to OMNI2 must go through Traefik
2. Auth Service validates JWT and adds headers: `X-User-Id`, `X-User-Username`, `X-User-Role`
3. Never expose internal ports (8000, 8001, 8500)
4. Use parameterized queries for database operations
5. Check `X-User-Role` header for admin operations

## Network Configuration

### Docker Networks
- `omni2_omni2-network`: OMNI2, Traefik, Auth
- `db-net`: Dashboard Backend, Database
- Cross-network: Use `host.docker.internal`

## Development Guidelines

### Adding Dashboard Configuration
1. Insert into database:
```sql
INSERT INTO omni2_dashboard.dashboard_config (key, value) 
VALUES ('your_key', '{"field": "value"}'::jsonb);
```
2. Update `CONFIG_METADATA` in `/dashboard/frontend/src/app/admin/page.tsx`
3. Access via `/api/v1/config` endpoint

### Writing Test Scripts
- **NEVER use Unicode characters** (emojis, checkmarks, etc.) in test scripts
- Windows console (cp1252) cannot encode Unicode characters
- Use plain ASCII: `[OK]`, `[ERROR]`, `[INFO]` instead of ✅ ❌ ℹ️
- Keep test output simple and readable

### Making Backend Changes
- Dashboard Backend handles config, caching, WebSocket proxy
- OMNI2 handles MCP operations, circuit breaker, event broadcasting
- Auth Service handles authentication, authorization, user management
- Never bypass Traefik for OMNI2 access

---

## 🚨 AI ASSISTANT RESPONSIBILITIES

### During Investigation
- If connection details don't match rules → RAISE discrepancy
- If new container discovered → SUGGEST adding to rules
- If schema/table structure differs → RAISE for verification
- If service ports change → RAISE for approval

### Suggesting Rule Updates
When encountering:
- New database schemas
- New Docker containers
- New environment variables
- New service endpoints
- Changed communication patterns
- New security requirements

**Format:** "🔔 RULE UPDATE NEEDED: [description] - Should I add this to omni-architecture.md?"

### After Approval
- Update this file immediately
- Maintain consistent formatting
- Add timestamp to changelog section below

---

## 📋 CHANGELOG

### 2024-01-XX - Initial Creation
- Database configuration documented
- Service communication flow established
- Security rules defined
- Development guidelines added
