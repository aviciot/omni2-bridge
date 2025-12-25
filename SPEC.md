# OMNI2 Bridge - Phase 1 Specification

**Project Name:** OMNI2 (Orchestration & Management for Natural Intelligence Integration)  
**Version:** 1.0.0  
**Date:** December 25, 2025  
**Author:** Avi Cohen

---

## Executive Summary

OMNI2 is a centralized orchestration layer that routes requests from Slack (and future clients) to multiple MCP servers. It provides:
- Auto-discovery of tools from MCP servers
- LLM-powered intelligent routing
- Role-based access control (RBAC)
- Tool filtering and security policies
- Audit logging and user management
- Hot-reloadable configuration

---

## Architecture Overview

```
┌─────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   Slack     │────▶│  OMNI2 Bridge        │────▶│  Oracle MCP     │
│   Bot       │     │  (FastAPI)           │     │  (Port 8300)    │
└─────────────┘     │  Port 8000           │     └─────────────────┘
                    │                      │     ┌─────────────────┐
                    │  - Tool Discovery    │────▶│  Smoke Test MCP │
                    │  - LLM Routing       │     │  (Port 8301)    │
                    │  - RBAC Filtering    │     └─────────────────┘
                    │  - Audit Logging     │     ┌─────────────────┐
                    │  - User Management   │────▶│  Future MCPs    │
                    └──────────────────────┘     └─────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  PostgreSQL      │
                    │  - Users/Roles   │
                    │  - Audit Logs    │
                    └──────────────────┘
```

---

## Technology Stack

- **Framework:** FastAPI 0.104+
- **Database:** PostgreSQL 16 (existing: `host.docker.internal:5432/omni`)
- **LLM:** Anthropic Claude 3.5 Sonnet
- **HTTP Client:** httpx (async)
- **Package Manager:** uv
- **Config:** YAML files (hot-reloadable)
- **Container:** Docker with hot-reload enabled

---

## Core Features - Phase 1

### 1. MCP Discovery & Aggregation
- Config-driven MCP registry (`config/mcps.yaml`)
- Auto-discovery on startup via `/mcp tools/list` endpoint
- Periodic health checks (configurable interval)
- In-memory tool cache with automatic refresh
- Mark unhealthy MCPs as unavailable

### 2. User Authentication & RBAC
- PostgreSQL user database
- 5 Role types:
  - `admin` - Full access, can manage users
  - `dba` - Database operations, all DB tools
  - `power_user` - Most tools except destructive ops
  - `qa_tester` - Testing tools + read access
  - `read_only` - View-only access
- Slack user ID mapping
- Auto-provisioning for new users

### 3. Tool Filtering Engine
- Multiple policy modes per MCP:
  - `allow_all` - Expose all tools
  - `allow_all_except` - Blacklist specific tools
  - `allow_only` - Whitelist specific tools
- Pattern matching with wildcards (`get_*`, `delete_*`)
- Layered filtering:
  1. Global blocks
  2. MCP-specific policies
  3. Role-based restrictions
  4. Pattern matching rules
- Admin bypass capability

### 4. LLM Integration
- Anthropic Claude API for tool selection
- Conversation flow:
  1. User asks question via Slack
  2. Bridge authenticates user
  3. Get filtered tools for user's role
  4. Send tools + question to Claude
  5. Claude selects appropriate tool
  6. Bridge routes to correct MCP
  7. Return formatted response
- Configurable model, timeout, max_tokens

### 5. Request Routing
- Tool → MCP URL lookup from registry
- Async HTTP forwarding with httpx
- Timeout handling per MCP
- Error handling and fallbacks
- Result caching (future)

### 6. Audit Logging
- Log every interaction to PostgreSQL
- Fields: user_id, timestamp, question, tool_called, mcp_target, duration_ms, success, error_message
- Retention policy (configurable days)
- Admin query API with filters
- Export capabilities (future)

### 7. Slack Integration
- Reuse existing slack_bot code
- Slash commands:
  - `/omni <question>` - Main command
  - `/omni-help` - Show available tools
  - `/omni-admin` - Admin panel
  - `/omni-status` - Health check
- Interactive buttons and menus
- Thread replies
- Rate limiting per user/channel

### 8. Admin API
- `GET /admin/users` - List users
- `POST /admin/users/{id}/role` - Change role
- `GET /admin/tools` - List all tools
- `POST /admin/tools/refresh` - Rediscover MCPs
- `GET /admin/logs` - Query audit logs
- `GET /admin/mcps` - MCP health status
- All endpoints fully documented in Swagger

---

## Database Schema

```sql
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'read_only',
    slack_user_id VARCHAR(50) UNIQUE,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_slack_id ON users(slack_user_id);
CREATE INDEX idx_users_email ON users(email);

-- Audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    timestamp TIMESTAMP DEFAULT NOW(),
    question TEXT NOT NULL,
    tool_called VARCHAR(255),
    mcp_target VARCHAR(255),
    duration_ms INT,
    success BOOLEAN,
    error_message TEXT,
    slack_channel VARCHAR(100)
);

CREATE INDEX idx_audit_user_timestamp ON audit_logs(user_id, timestamp);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
CREATE INDEX idx_audit_tool ON audit_logs(tool_called);

-- Initial super admin
INSERT INTO users (email, name, role, slack_user_id) 
VALUES ('avicoiot@gmail.com', 'Avi Cohen', 'admin', NULL)
ON CONFLICT (email) DO NOTHING;
```

---

## Configuration Files

### settings.yaml
Main application configuration:
- App settings (host, port, debug, reload)
- Database connection
- LLM settings (provider, model, API key)
- MCP discovery intervals
- Audit settings

### mcps.yaml
MCP server registry and policies:
- Global settings (timeout, blocked tools)
- MCP definitions (url, enabled, timeout)
- Tool policies (allow_all, allow_all_except, allow_only)
- Role restrictions per MCP
- Rate limiting
- Pattern matching rules

### users.yaml
User and role management:
- Super admins list
- Predefined users with roles
- Role definitions with permissions
- Team definitions
- Auto-provisioning rules
- Session settings

### slack.yaml
Slack integration configuration:
- App credentials (from env vars)
- Slash commands
- Bot behavior
- Channel restrictions
- Interactive components
- Rate limiting
- Message templates
- Logging settings

---

## API Endpoints

### Chat Endpoint
```
POST /chat
Body: {
  "question": "Show slow queries on way4_docker7",
  "slack_user_id": "U1234567890",
  "channel_id": "C9876543210"
}
Response: {
  "answer": "Found 5 slow queries...",
  "tool_called": "get_top_queries",
  "mcp_source": "oracle_mcp",
  "execution_time_ms": 1250
}
```

### Health Check
```
GET /health
Response: {
  "status": "healthy",
  "mcps": [
    {"name": "oracle_mcp", "status": "healthy", "tools": 24},
    {"name": "smoketest_mcp", "status": "unavailable", "tools": 0}
  ]
}
```

### Admin Endpoints
All require admin role authentication:
- `GET /admin/users?role=power_user&limit=50`
- `POST /admin/users/{id}/role` (body: `{"role": "dba"}`)
- `GET /admin/tools?mcp=oracle_mcp`
- `POST /admin/tools/refresh`
- `GET /admin/logs?user_id=123&start_date=2025-12-01&limit=100`
- `GET /admin/mcps`

---

## Development Setup

### Prerequisites
- Python 3.12+
- uv package manager
- Docker & docker-compose
- PostgreSQL (via existing PS_db container)

### Installation
```bash
cd omni2
uv sync
```

### Environment Variables
```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql+asyncpg://omni:devpass@host.docker.internal:5432/omni
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
```

### Run Development Server
```bash
# With hot-reload
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or via Docker
docker compose up omni2
```

---

## Docker Configuration

### Dockerfile
- Python 3.12 slim base
- Install uv
- Copy pyproject.toml and install dependencies
- Copy application code
- Hot-reload enabled via volume mounts
- Command: `uvicorn app.main:app --reload`

### docker-compose.yml Addition
```yaml
services:
  omni2:
    build: ./omni2
    container_name: omni2-bridge
    ports:
      - "8000:8000"
    volumes:
      - ./omni2/app:/app/app:ro        # Hot-reload code
      - ./omni2/config:/app/config:ro  # Hot-reload config
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DATABASE_URL=postgresql+asyncpg://omni:devpass@host.docker.internal:5432/omni
    networks:
      - mcp-network
    restart: unless-stopped
```

---

## Success Criteria

✅ Bridge discovers all tools from oracle_mcp automatically  
✅ User asks "Show slow queries" → Routes correctly via LLM  
✅ Admin sees all tools, read_only user sees filtered list  
✅ All interactions logged to PostgreSQL audit_logs  
✅ Slack bot routes through bridge successfully  
✅ Admin can change user roles via API  
✅ Unhealthy MCPs removed from tool registry  
✅ Hot-reload works for code and config changes  
✅ All settings configurable via YAML  
✅ Swagger documentation complete and accurate  

---

## Phase 1 Timeline

- **Day 1:** Project scaffold, database setup, config loading
- **Day 2:** MCP discovery, tool filtering, RBAC
- **Day 3:** LLM integration, routing logic
- **Day 4:** Slack integration, admin APIs
- **Day 5:** Testing, documentation, deployment

**Total: 5 days for Phase 1 MVP**

---

## Out of Scope - Phase 1

❌ Multi-turn conversation context (Phase 2)  
❌ Redis caching layer (Phase 2)  
❌ Web UI dashboard (Phase 2)  
❌ OAuth/SSO integration (Phase 2)  
❌ Request queuing for long queries (Phase 2)  
❌ Webhook notifications (Phase 2)  
❌ Multi-tenancy (Phase 3)  
❌ Advanced analytics dashboard (Phase 3)  

---

## Future Enhancements - Phase 2

- Conversation context storage (Redis)
- Query result caching
- Web UI for admin operations
- OAuth integration
- Async job queue (Celery)
- Advanced rate limiting
- Prometheus metrics
- Grafana dashboards

---

## Security Considerations

1. **API Keys:** Store in environment variables, never in code
2. **Database:** Use connection pooling, parameterized queries
3. **Tool Filtering:** Multiple layers, admin bypass logged
4. **Audit Logging:** All tool calls logged with user info
5. **Rate Limiting:** Per user, per channel, per MCP
6. **Input Validation:** Pydantic models for all requests
7. **Error Handling:** Never expose internal errors to users

---

## Testing Strategy

- Unit tests: Tool filtering, role checks, config loading
- Integration tests: MCP discovery, database operations
- E2E tests: Full flow from Slack to MCP and back
- Load tests: Concurrent users, rate limiting
- Security tests: Permission bypasses, SQL injection

---

## Monitoring & Observability

- Health check endpoint for load balancers
- Structured logging (JSON format)
- MCP availability tracking
- Tool usage metrics
- Error rate monitoring
- User activity tracking

---

## Support & Maintenance

- Config hot-reload: No restart needed for changes
- Database migrations: Manual SQL scripts (Alembic later)
- Log retention: Auto-cleanup after N days
- Backup strategy: PostgreSQL dumps
- Rollback plan: Docker image tags

---

## Glossary

- **MCP:** Model Context Protocol server
- **RBAC:** Role-Based Access Control
- **Tool:** Capability exposed by an MCP (function/command)
- **Super Admin:** User who can't be demoted (hardcoded)
- **Tool Filtering:** Process of removing tools based on role/policy
- **Hot-Reload:** Auto-restart on code/config changes

---

## Contact

- **Project Owner:** Avi Cohen (avicoiot@gmail.com)
- **Repository:** aviciot/MetaQuery-MCP
- **Documentation:** See README.md for quick start

---

**Last Updated:** December 25, 2025
