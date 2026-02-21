# MCP PT Service - Endpoint Flow Map

## Architecture Overview
```
Dashboard Frontend (React)
    ↓ HTTP REST
Dashboard Backend (FastAPI :8001)
    ↓ HTTP Proxy
PT Service (FastAPI :8200)
    ↓ Redis Pub/Sub
WebSocket Broadcaster (OMNI2 :8000)
    ↓ WebSocket
Dashboard Frontend (React)
```

---

## 1. START PT RUN

### Frontend → Dashboard Backend
**Endpoint**: `POST http://localhost:8001/api/v1/mcp-pt/run`
**Component**: `MCPPTDashboardV2.tsx` → `startPTRun()`
**Request Body**:
```json
{
  "mcp_id": "docker_controller",
  "preset": "quick",
  "categories": ["auth_validation", "data_leakage"],
  "created_by": 1
}
```

### Dashboard Backend → PT Service
**Proxy**: `dashboard/backend/app/routers/mcp_pt_proxy.py`
**Endpoint**: `POST http://omni2-mcp-pt:8200/api/v1/mcp-pt/run`
**Handler**: `mcp-pt-service/routers/pt_runs.py` → `run_pt()`

**Response**:
```json
{
  "run_id": 23,
  "status": "pending",
  "message": "PT run started for docker_controller"
}
```

---

## 2. BACKGROUND EXECUTION (PT Service)

### Execution Flow
**Function**: `pt_runs.py` → `execute_pt_run()`

#### Stage 1: Discovery
- **Action**: Connect to MCP, discover tools/prompts/resources
- **Redis Key**: `pt_run:23:discovery` (TTL: 3600s)
- **Redis Publish**: Channel `pt_events`
```json
{
  "type": "pt_discovery_complete",
  "run_id": 23,
  "data": {
    "tools": [...],
    "prompts": [...],
    "resources": [...],
    "tool_count": 12,
    "prompt_count": 5,
    "resource_count": 1
  }
}
```

#### Stage 2: LLM Analysis
- **Action**: LLM generates security profile + test plan
- **Redis Key**: `pt_run:23:test_plan` (TTL: 3600s)
- **Redis Publish**: Channel `pt_events`
```json
{
  "type": "pt_test_plan_ready",
  "run_id": 23,
  "data": {
    "security_profile": {
      "risk_score": 7,
      "high_risk_tools": ["restart_container", "stop_container"],
      "attack_vectors": [...]
    },
    "selected_categories": ["auth_validation", "tool_boundary"],
    "total_tests": 8,
    "tests": [...]
  }
}
```

#### Stage 3: Test Execution
- **Action**: Execute tests, publish results
- **Redis Publish**: Channel `pt_events` (per test)
```json
{
  "type": "pt_test_result",
  "run_id": 23,
  "data": {
    "category": "auth_validation",
    "test_name": "test_unauthorized_access",
    "status": "fail",
    "severity": "high",
    "evidence": "Unauthorized access detected"
  }
}
```

#### Stage 4: Completion
- **Redis Publish**: Channel `pt_events`
```json
{
  "type": "pt_complete",
  "run_id": 23,
  "status": "completed",
  "summary": {
    "total_tests": 8,
    "passed": 5,
    "failed": 3,
    "critical": 1,
    "high": 2
  }
}
```

---

## 3. WEBSOCKET NOTIFICATIONS (Real-time)

### Frontend WebSocket Connection
**Component**: `PTRunDetails.tsx` → `connectWebSocket()`
**Endpoint**: `ws://localhost:8001/ws?token={access_token}`
**Handler**: `dashboard/backend/app/routers/websocket.py` → `websocket_endpoint()`

### Subscription
**Frontend sends**:
```json
{
  "action": "subscribe",
  "event_types": [
    "pt_discovery_complete",
    "pt_test_plan_ready", 
    "pt_test_result",
    "pt_complete"
  ],
  "filters": {
    "run_id": 23
  }
}
```

### Backend Flow
1. **Dashboard WS** receives subscription
2. **OMNI2 WebSocket Broadcaster** (`app/services/websocket_broadcaster.py`)
   - Listens to Redis channel `pt_events`
   - Filters events by subscription
   - Forwards matching events to subscribed clients

### Frontend Receives
```json
{
  "type": "pt_discovery_complete",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "run_id": 23,
    "tool_count": 12,
    ...
  }
}
```

---

## 4. GET RUN DETAILS

### Frontend → Dashboard Backend
**Endpoint**: `GET http://localhost:8001/api/v1/mcp-pt/runs/23`
**Component**: `PTRunDetails.tsx` → `loadData()`

### Dashboard Backend → PT Service
**Proxy**: `mcp_pt_proxy.py` → `get_run()`
**Endpoint**: `GET http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/23`
**Handler**: `pt_runs.py` → `get_run()`

**Response**:
```json
{
  "run_id": 23,
  "mcp_name": "docker_controller",
  "status": "completed",
  "test_plan": {...},
  "security_profile": {...},
  "total_tests": 8,
  "passed": 5,
  "failed": 3
}
```

---

## 5. GET DISCOVERY DATA

### Frontend → Dashboard Backend
**Endpoint**: `GET http://localhost:8001/api/v1/mcp-pt/runs/23/discovery`

### Dashboard Backend → PT Service
**Proxy**: `mcp_pt_proxy.py` → `get_discovery()`
**Endpoint**: `GET http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/23/discovery`
**Handler**: `pt_runs.py` → `get_discovery()`

**Source**: Redis key `pt_run:23:discovery`

**Response**:
```json
{
  "tools": [
    {
      "name": "list_containers",
      "description": "List all Docker containers",
      "inputSchema": {...}
    }
  ],
  "prompts": [...],
  "resources": [...],
  "tool_count": 12,
  "prompt_count": 5,
  "resource_count": 1
}
```

---

## 6. GET TEST RESULTS

### Frontend → Dashboard Backend
**Endpoint**: `GET http://localhost:8001/api/v1/mcp-pt/runs/23/results`

### Dashboard Backend → PT Service
**Proxy**: `mcp_pt_proxy.py` → `get_run_results()`
**Endpoint**: `GET http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/23/results`
**Handler**: `pt_runs.py` → `get_run_results()`

**Source**: Database `omni2.pt_test_results`

**Response**:
```json
[
  {
    "result_id": 101,
    "run_id": 23,
    "category": "auth_validation",
    "test_name": "test_unauthorized_access",
    "status": "fail",
    "severity": "high",
    "evidence": "Unauthorized access detected",
    "latency_ms": 150
  }
]
```

---

## 7. GET SECURITY PROFILE

### Frontend → Dashboard Backend
**Endpoint**: `GET http://localhost:8001/api/v1/mcp-pt/runs/23/security-profile`

### Dashboard Backend → PT Service
**Proxy**: `mcp_pt_proxy.py` → `get_security_profile()`
**Endpoint**: `GET http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/23/security-profile`
**Handler**: `pt_runs.py` → `get_security_profile()`

**Source**: Database `omni2.pt_runs.security_profile` (JSONB)

**Response**:
```json
{
  "risk_score": 7,
  "high_risk_tools": [
    "restart_container",
    "stop_container",
    "start_container",
    "remove_container"
  ],
  "attack_vectors": [
    {
      "vector": "Unauthorized Container Control",
      "severity": "critical",
      "description": "Attacker could control containers without auth"
    }
  ],
  "data_sensitivity": {
    "handles_pii": false,
    "handles_credentials": true,
    "handles_system_access": true
  }
}
```

---

## Summary Table

| Action | Frontend Endpoint | Dashboard Proxy | PT Service Endpoint | PT Service Handler |
|--------|------------------|-----------------|---------------------|-------------------|
| Start Run | POST `/api/v1/mcp-pt/run` | `start_run()` | POST `/api/v1/mcp-pt/run` | `run_pt()` |
| Get Run | GET `/api/v1/mcp-pt/runs/{id}` | `get_run()` | GET `/api/v1/mcp-pt/runs/{id}` | `get_run()` |
| Get Discovery | GET `/api/v1/mcp-pt/runs/{id}/discovery` | `get_discovery()` | GET `/api/v1/mcp-pt/runs/{id}/discovery` | `get_discovery()` |
| Get Results | GET `/api/v1/mcp-pt/runs/{id}/results` | `get_run_results()` | GET `/api/v1/mcp-pt/runs/{id}/results` | `get_run_results()` |
| Get Profile | GET `/api/v1/mcp-pt/runs/{id}/security-profile` | `get_security_profile()` | GET `/api/v1/mcp-pt/runs/{id}/security-profile` | `get_security_profile()` |
| WebSocket | WS `/ws?token={token}` | `websocket_endpoint()` | N/A (Redis pub/sub) | `redis_publisher.py` |

## Event Types (WebSocket)

| Event Type | Trigger | Data Includes |
|-----------|---------|---------------|
| `pt_discovery_complete` | MCP discovery done | tools, prompts, resources, counts |
| `pt_test_plan_ready` | LLM analysis done | security_profile, test_plan, categories |
| `pt_test_result` | Each test completes | category, test_name, status, severity |
| `pt_progress` | Every 5 tests | completed, total, progress_pct |
| `pt_complete` | All tests done | status, summary (passed/failed/critical) |
| `pt_error` | Error occurs | error message |
