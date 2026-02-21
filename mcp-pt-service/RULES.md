# MCP PT Service - Rules & Critical Info

## Database
- **Connection**: `postgresql+asyncpg://omni:omni@omni_pg_db:5432/omni`
- **Schema**: `omni2` (NOT separate mcp_pt schema)
- **Tables**: `pt_runs`, `pt_test_results`, `pt_categories`, `pt_test_functions`, `pt_presets`, `pt_llm_suggestions`
- **FK**: `pt_runs.mcp_server_id` → `omni2.mcp_servers(id)`

## Redis Events
- **Host**: `omni2-redis:6379`
- **Channel**: `pt_events`
- **Events**: `pt_started`, `pt_progress`, `pt_complete`, `pt_error`
- **Publisher**: `redis_publisher.py` → `get_publisher()`
- **Progress**: Published every 5 tests to avoid spam
- **Consumer**: Dashboard backend subscribes to `pt_events` and forwards to UI via existing WebSocket

## LLM Configuration
- **Tokens from**: `DNA/.env` (copied to mcp-pt-service/.env)
- **Anthropic**: `ANTHROPIC_API_KEY`, model: `claude-sonnet-4-5-20250929`
- **Gemini**: `GOOGLE_API_KEY`, model: `gemini-2.5-flash`
- **Pattern**: Follow `DNA/ai-service/llm_client.py` and `gemini_client.py`
- **Rate limit**: 2 concurrent calls (shared semaphore)
- **Provider**: Set via `LLM_PROVIDER` env var (anthropic/gemini)

## Test Categories (6)
1. `protocol_robustness` - 4 tests
2. `tool_schema_abuse` - 4 tests
3. `tool_boundary` - 4 tests
4. `auth_validation` - 3 tests
5. `resource_exhaustion` - 3 tests
6. `data_leakage` - 2 tests

## Presets
- **fast**: 2 categories, 10 parallel, 120s timeout
- **quick**: 3 categories, 8 parallel, 300s timeout
- **deep**: 6 categories, 5 parallel, 900s timeout

## Test Function Registry
- **File**: `test_registry.py`
- **Format**: `TEST_REGISTRY[category][test_name] = async_function`
- **Functions**: `test_invalid_json`, `test_unknown_param`, etc.
- **Return**: `{"status": "pass/fail/error", "severity": "...", "evidence": "..."}`

## LLM Rules
- LLM ONLY generates test plan JSON
- LLM NEVER executes tests
- LLM NEVER decides pass/fail
- Python executor runs all tests deterministically
- **Planner**: `planner.py` → `PTPlanner.generate_test_plan()`

## Execution Flow
1. User calls POST /api/v1/mcp-pt/run
2. Create run record in DB (status=pending)
3. Start background task: `execute_pt_run()`
4. Publish `pt_started` to Redis
5. LLM generates test plan
6. Executor runs tests in parallel (with semaphore)
7. Save each result to `pt_test_results`
8. Publish `pt_progress` every 5 tests
9. Calculate summary, update run (status=completed)
10. Publish `pt_complete` to Redis

## API Endpoints
- **Base**: `/api/v1/mcp-pt/`
- **Auth**: Standard Omni2 JWT via Traefik (TODO)
- **RBAC**: `admin`, `security_analyst` roles (TODO)
- **Port**: 8200

## File Structure
```
mcp-pt-service/
├── config.py              # Settings (DB, LLM, Redis)
├── db.py                  # Database operations
├── llm_client.py          # Dual LLM client (Claude/Gemini)
├── planner.py             # LLM test plan generator
├── test_registry.py       # 20 test functions
├── executor.py            # Parallel execution engine
├── mcp_client.py          # MCP wrapper for testing
├── redis_publisher.py     # Redis event publisher
├── main.py                # FastAPI app
├── routers/
│   ├── pt_runs.py         # Run management API
│   └── pt_config.py       # Config & comparison API
├── schema_v2.sql          # Database schema
├── .env                   # Environment config
└── RULES.md               # This file
```

## Dashboard Integration
- **Location**: `Admin → Security → MCP-PT`
- **Backend**: Subscribe to Redis `pt_events` channel
- **Frontend**: Display runs, results, history, comparison
- **Real-time**: Dashboard backend forwards Redis events to UI via existing WebSocket

## Testing
- **Test file**: `test_all.py` - Single comprehensive test suite
- **Run**: `python test_all.py`
- **Update**: Add new tests to this file as features are added
- **Tests covered**: Health, categories, presets, runs, results, history, comparison, LLM client, DB connection
- **Quick test**: Comment out `test_wait_for_completion()` to skip waiting
- **Full test**: Uncomment wait/results tests to verify complete workflow

## Important Notes
- Background tasks handle PT execution (non-blocking)
- All results persisted to DB before Redis events
- MCP client has auth variants: `call_tool()`, `call_tool_no_auth()`, `call_tool_expired_token()`
- Test functions are deterministic - same input = same output
- Presidio/TruffleHog use regex patterns (not external services)
