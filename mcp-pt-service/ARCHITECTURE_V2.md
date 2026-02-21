# MCP Penetration Testing Service - Architecture V2

## Overview

Automated MCP penetration testing system with:
- **LLM-driven test planning** (Claude/Gemini)
- **Deterministic Python execution**
- **Database persistence** (Omni2 PostgreSQL)
- **UI management** (Dashboard integration)
- **Advanced reporting & comparison**
- **Parallel execution support**

---

## Architecture Flow

```
User (Dashboard UI)
    ↓
PT Management API
    ↓
LLM Planner (Claude/Gemini) → Test Plan JSON
    ↓
Python Executor (Parallel)
    ↓
Results → Omni2 Database
    ↓
Reporting & Comparison UI
```

---

## Database Configuration

### Connection Details
- **Database**: `omni`
- **User**: `omni`
- **Password**: `omni`
- **Host**: `omni_pg_db`
- **Port**: `5432`
- **Connection String**: `postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni`
- **Schema**: `mcp_pt`

### Environment Variables
```env
DATABASE_URL=postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni
ANTHROPIC_API_KEY=<from DNA/.env>
GOOGLE_API_KEY=<from DNA/.env>
LLM_PROVIDER=anthropic  # or gemini
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
GEMINI_MODEL=gemini-2.5-flash
```

---

## Database Schema

### Table: `mcp_pt.pt_runs`
```sql
CREATE TABLE mcp_pt.pt_runs (
    run_id SERIAL PRIMARY KEY,
    mcp_id VARCHAR(255) NOT NULL,
    mcp_name VARCHAR(255),
    preset VARCHAR(50),  -- 'fast', 'quick', 'deep'
    status VARCHAR(50),  -- 'pending', 'running', 'completed', 'failed'
    llm_provider VARCHAR(50),  -- 'anthropic', 'gemini'
    llm_model VARCHAR(100),
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    total_tests INT DEFAULT 0,
    passed INT DEFAULT 0,
    failed INT DEFAULT 0,
    critical INT DEFAULT 0,
    high INT DEFAULT 0,
    medium INT DEFAULT 0,
    low INT DEFAULT 0,
    duration_ms INT,
    test_plan JSONB,  -- LLM-generated plan
    created_by INT REFERENCES auth_service.users(id),
    FOREIGN KEY (mcp_id) REFERENCES omni2.mcp_registry(mcp_id)
);
```

### Table: `mcp_pt.pt_test_results`
```sql
CREATE TABLE mcp_pt.pt_test_results (
    result_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES mcp_pt.pt_runs(run_id) ON DELETE CASCADE,
    category VARCHAR(100),
    test_name VARCHAR(100),
    tool_name VARCHAR(255),
    status VARCHAR(50),  -- 'pass', 'fail', 'error'
    severity VARCHAR(50),  -- 'critical', 'high', 'medium', 'low', 'info'
    request JSONB,
    response JSONB,
    evidence TEXT,
    latency_ms INT,
    presidio_findings JSONB,
    trufflehog_findings JSONB,
    executed_at TIMESTAMP DEFAULT NOW()
);
```

### Table: `mcp_pt.pt_categories`
```sql
CREATE TABLE mcp_pt.pt_categories (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    severity_default VARCHAR(50),
    enabled BOOLEAN DEFAULT TRUE
);
```

### Table: `mcp_pt.pt_test_functions`
```sql
CREATE TABLE mcp_pt.pt_test_functions (
    function_id SERIAL PRIMARY KEY,
    category_id INT REFERENCES mcp_pt.pt_categories(category_id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    python_function VARCHAR(255),
    enabled BOOLEAN DEFAULT TRUE,
    UNIQUE(category_id, name)
);
```

### Table: `mcp_pt.pt_presets`
```sql
CREATE TABLE mcp_pt.pt_presets (
    preset_id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,  -- 'fast', 'quick', 'deep'
    description TEXT,
    categories TEXT[],  -- Array of category names
    max_parallel INT DEFAULT 5,
    timeout_seconds INT DEFAULT 300
);
```

### Table: `mcp_pt.pt_llm_suggestions`
```sql
CREATE TABLE mcp_pt.pt_llm_suggestions (
    suggestion_id SERIAL PRIMARY KEY,
    run_id INT REFERENCES mcp_pt.pt_runs(run_id) ON DELETE CASCADE,
    suggestion TEXT,
    category VARCHAR(100),
    priority VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Test Categories & Functions

### Categories (Hardcoded Enums)

1. **protocol_robustness**
   - `invalid_json` - Malformed JSON payloads
   - `missing_fields` - Required fields omitted
   - `oversized_frame` - Payload size limits
   - `partial_stream` - Incomplete message streams

2. **tool_schema_abuse**
   - `unknown_param` - Extra parameters not in schema
   - `wrong_type` - Type mismatches (string vs int)
   - `missing_required` - Required params omitted
   - `oversized_param` - Parameter size limits

3. **tool_boundary**
   - `db_select_star` - SELECT * queries
   - `db_no_limit` - Queries without LIMIT
   - `file_traversal` - Path traversal attempts (../)
   - `internal_http` - Internal network access

4. **auth_validation**
   - `no_token` - Missing authentication
   - `expired_token` - Expired credentials
   - `forbidden_tool` - Unauthorized tool access

5. **resource_exhaustion**
   - `parallel_connections` - Connection flooding
   - `slow_client` - Slow read attacks
   - `hanging_tool` - Long-running operations

6. **data_leakage**
   - `presidio_scan` - PII detection (emails, SSN, etc.)
   - `trufflehog_scan` - Secret detection (API keys, tokens)

---

## PT Presets

### Fast (5-10 tests, ~2 min)
```json
{
  "name": "fast",
  "categories": ["protocol_robustness", "auth_validation"],
  "max_parallel": 10,
  "timeout_seconds": 120
}
```

### Quick (15-25 tests, ~5 min)
```json
{
  "name": "quick",
  "categories": ["protocol_robustness", "tool_schema_abuse", "auth_validation"],
  "max_parallel": 8,
  "timeout_seconds": 300
}
```

### Deep (40+ tests, ~15 min)
```json
{
  "name": "deep",
  "categories": ["protocol_robustness", "tool_schema_abuse", "tool_boundary", 
                 "auth_validation", "resource_exhaustion", "data_leakage"],
  "max_parallel": 5,
  "timeout_seconds": 900
}
```

---

## LLM Integration

### Dual Model Support

Following DNA ai-service pattern:

```python
# llm_client.py
from anthropic import AsyncAnthropic
import google.generativeai as genai

class LLMClient:
    def __init__(self, provider: str, api_key: str, model: str):
        self.provider = provider
        if provider == "anthropic":
            self.client = AsyncAnthropic(api_key=api_key)
            self.model = model
        elif provider == "gemini":
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(model)
            self.model = model
    
    async def generate_test_plan(self, mcp_metadata: dict, preset: str) -> dict:
        prompt = self._build_prompt(mcp_metadata, preset)
        
        if self.provider == "anthropic":
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}]
            )
            return self._parse_response(response.content[0].text)
        
        elif self.provider == "gemini":
            response = await self.client.generate_content_async(prompt)
            return self._parse_response(response.text)
```

### System Prompt

```
You are an MCP penetration testing planner.

Analyze MCP metadata and generate a test plan JSON.

Available categories: {categories}
Available tests per category: {test_functions}

Rules:
1. Select only from provided categories/tests
2. Do not invent new tests
3. Output strict JSON only
4. Maximize security coverage
5. Parametrize tests per tool

Output format:
{
  "mcp_id": "string",
  "selected_categories": ["category1", "category2"],
  "tests": [
    {
      "category": "tool_schema_abuse",
      "test": "unknown_param",
      "tool": "sql_query",
      "params": {"query": "SELECT 1", "evil": "hack"}
    }
  ],
  "suggestions": ["Future improvement ideas"]
}
```

---

## API Endpoints

### PT Management

```python
# POST /api/v1/mcp-pt/run
{
  "mcp_id": "informatica_mcp",
  "preset": "quick",  # or custom categories
  "categories": ["protocol_robustness", "tool_schema_abuse"]  # optional override
}

# GET /api/v1/mcp-pt/runs
# List all PT runs with filters

# GET /api/v1/mcp-pt/runs/{run_id}
# Get specific run details

# GET /api/v1/mcp-pt/runs/{run_id}/results
# Get test results for a run

# POST /api/v1/mcp-pt/compare
{
  "run_id_1": 123,
  "run_id_2": 456
}
# Compare two runs (regression/improvement)

# GET /api/v1/mcp-pt/mcps/{mcp_id}/history
# Get PT history for specific MCP

# GET /api/v1/mcp-pt/categories
# List available categories

# GET /api/v1/mcp-pt/presets
# List available presets
```

---

## Dashboard UI Integration

### Location
`Dashboard → Admin → Security → MCP-PT`

### Features

#### 1. Run PT Tests
- Select MCP from dropdown
- Choose preset (Fast/Quick/Deep) or custom categories
- Start test button
- Real-time progress via WebSocket

#### 2. View Results
- Table of all PT runs
- Filters: MCP, Status, Date range
- Columns: MCP, Preset, Status, Tests, Failed, Critical, Duration, Date
- Click row → detailed results

#### 3. PT History
- Timeline view per MCP
- Chart: Pass/Fail trends over time
- Filter by category

#### 4. Compare Runs
- Select two runs
- Side-by-side comparison
- Highlight: New failures, Fixed issues, Regressions
- Diff view for test results

#### 5. Test Details
- Expandable rows showing:
  - Request/Response
  - Evidence
  - Presidio/TruffleHog findings
  - Latency
  - Severity

---

## Execution Engine

### Parallel Execution

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class PTExecutor:
    def __init__(self, max_parallel: int = 5):
        self.max_parallel = max_parallel
        self.executor = ThreadPoolExecutor(max_workers=max_parallel)
    
    async def run_tests(self, test_plan: dict) -> list:
        tasks = []
        semaphore = asyncio.Semaphore(self.max_parallel)
        
        for test in test_plan["tests"]:
            task = self._run_test_with_limit(test, semaphore)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    async def _run_test_with_limit(self, test: dict, semaphore):
        async with semaphore:
            return await self._execute_test(test)
    
    async def _execute_test(self, test: dict) -> dict:
        # Call test function
        # Capture request/response
        # Run Presidio/TruffleHog
        # Determine pass/fail
        # Return result
        pass
```

### Test Function Registry

```python
# test_functions.py
from typing import Callable, Dict

TEST_REGISTRY: Dict[str, Dict[str, Callable]] = {
    "protocol_robustness": {
        "invalid_json": test_invalid_json,
        "missing_fields": test_missing_fields,
        "oversized_frame": test_oversized_frame,
        "partial_stream": test_partial_stream,
    },
    "tool_schema_abuse": {
        "unknown_param": test_unknown_param,
        "wrong_type": test_wrong_type,
        "missing_required": test_missing_required,
        "oversized_param": test_oversized_param,
    },
    # ... other categories
}

async def test_unknown_param(mcp_client, tool: str, params: dict) -> dict:
    """Test tool with unknown parameter."""
    params["_evil_param"] = "hack"
    
    try:
        response = await mcp_client.call_tool(tool, params)
        # Should reject unknown param
        return {
            "status": "fail",
            "severity": "medium",
            "evidence": "MCP accepted unknown parameter"
        }
    except Exception as e:
        # Expected behavior
        return {
            "status": "pass",
            "severity": "info",
            "evidence": f"Correctly rejected: {e}"
        }
```

---

## Reporting System

### Run Summary
```json
{
  "run_id": 123,
  "mcp_id": "informatica_mcp",
  "status": "completed",
  "summary": {
    "total_tests": 25,
    "passed": 20,
    "failed": 5,
    "by_severity": {
      "critical": 1,
      "high": 2,
      "medium": 2,
      "low": 0
    },
    "by_category": {
      "protocol_robustness": {"passed": 4, "failed": 0},
      "tool_schema_abuse": {"passed": 6, "failed": 2},
      "tool_boundary": {"passed": 5, "failed": 3}
    }
  },
  "duration_ms": 45000,
  "llm_cost_usd": 0.023
}
```

### Comparison Report
```json
{
  "run_1": 123,
  "run_2": 456,
  "comparison": {
    "new_failures": [
      {
        "category": "tool_boundary",
        "test": "db_select_star",
        "tool": "sql_query",
        "severity": "high"
      }
    ],
    "fixed_issues": [
      {
        "category": "auth_validation",
        "test": "expired_token",
        "tool": "get_user"
      }
    ],
    "regressions": 1,
    "improvements": 1,
    "unchanged": 23
  }
}
```

---

## WebSocket Events

Real-time PT progress:

```json
{
  "event": "pt_progress",
  "run_id": 123,
  "status": "running",
  "progress": {
    "completed": 15,
    "total": 25,
    "current_test": "tool_schema_abuse.unknown_param"
  }
}

{
  "event": "pt_complete",
  "run_id": 123,
  "status": "completed",
  "summary": { ... }
}
```

---

## Security & Performance

### Rate Limiting
- LLM calls: 2 concurrent max (shared semaphore)
- Test execution: Configurable per preset
- API endpoints: Standard Omni2 rate limits

### Caching
- MCP metadata cached (5 min TTL)
- Test function registry loaded at startup
- Category/preset definitions cached

### Permissions
- Role-based access: `admin`, `security_analyst`
- Per-MCP PT permissions
- Audit logging for all PT runs

---

## Implementation Priority

1. **Database schema** - Create tables
2. **LLM client** - Dual provider support
3. **Test registry** - Core test functions
4. **Executor** - Parallel execution engine
5. **API endpoints** - CRUD operations
6. **Dashboard UI** - Management interface
7. **Reporting** - Comparison & history
8. **WebSocket** - Real-time updates

---

## File Structure

```
mcp-pt-service/
├── config.py              # DB, LLM config
├── db.py                  # Database client
├── llm_client.py          # Claude/Gemini client
├── test_registry.py       # Test function definitions
├── executor.py            # Parallel execution engine
├── scanner.py             # Presidio/TruffleHog integration
├── main.py                # FastAPI app
├── routers/
│   ├── pt_runs.py         # Run management
│   ├── pt_results.py      # Results API
│   └── pt_compare.py      # Comparison API
├── schema.sql             # Database schema
└── requirements.txt
```

---

## Next Steps

1. Review and approve architecture
2. Create database schema
3. Implement LLM client with dual provider
4. Build test registry with core functions
5. Develop parallel executor
6. Create API endpoints
7. Build Dashboard UI components
8. Add comparison & reporting features
