# Endpoint Usage Audit (What is "unused")

Date generated: 2026-02-02

## What the counts mean (plain English)

For each service (Dashboard Backend / Omni2 Core / Auth Service) this report shows three numbers:

- **Discovered endpoints**: endpoints found by scanning FastAPI decorators in that service's code (e.g., `@router.get("/x")`, `@app.post("/y")`, `@router.websocket("/ws")`) and applying the router prefixes from `include_router(...)`.
- **Referenced by someone (runtime)**: at least one other *runtime* file contains a likely reference to that endpoint path (examples: UI `fetch(...)`, backend `httpx.get(...)`, Traefik router rules, docker-compose labels). This is a "string evidence" check, not an execution trace.
- **Unused endpoints (runtime)**: endpoints that have **no** such reference anywhere in runtime files (excluding the file where the endpoint is defined). These are the endpoints that look "not used by anyone".

So: **Unused endpoints (runtime)** is the list you asked for.

## How "referenced" is detected (so you can trust the result)

- Exact string matches are counted (e.g., `"/api/v1/events/metadata"`).
- For templated paths like `/users/{user_id}`, it also detects common concatenations like `"/users/" + userId + "/activity"` by checking that the **static path parts appear in order**.
- Docs/tests are **not** counted as runtime usage; doc/test-only hits are shown in the last column.

## Important limits (avoid false assumptions)

- "Unused" here means: **unused inside this repo's runtime code/config**. It does *not* prove the endpoint is unused by external callers (e.g., curl, Postman, other services not in this repo).
- Some endpoints are invoked indirectly (e.g., a path is built dynamically from variables). That can evade string-based detection.
- `auth_service` has duplicate mounts under `/auth/...` in `auth_service/main.py`; many of those are "unused" because Traefik typically strips `/auth` before forwarding, so the runtime uses `/api/v1/...` on the service side.

## Dashboard Backend

Discovered endpoints: 68
Referenced by someone (runtime): 62
Unused endpoints (runtime): 6

| Method | Path | Defined In | Only docs/tests refs (max 3) |
|---|---|---|---|
| GET | `/api/v1/config/dev_features` | `omni2/dashboard/backend/app/routers/config.py` |  |
| GET | `/api/v1/dashboard/charts/cost` | `omni2/dashboard/backend/app/routers/charts.py` | omni2/docs/IAM_ARCHITECTURE.md:44 |
| GET | `/api/v1/dashboard/charts/errors` | `omni2/dashboard/backend/app/routers/charts.py` | omni2/dashboard/README.md:205<br>omni2/dashboard/progress/PHASE_1.md:188 |
| GET | `/api/v1/dashboard/charts/queries` | `omni2/dashboard/backend/app/routers/charts.py` | omni2/docs/IAM_ARCHITECTURE.md:44 |
| GET | `/api/v1/dashboard/charts/response-times` | `omni2/dashboard/backend/app/routers/charts.py` | omni2/dashboard/README.md:204<br>omni2/dashboard/progress/PHASE_1.md:175 |
| GET | `/api/v1/events/metadata` | `omni2/dashboard/backend/app/routers/events.py` |  |

## Omni2 Core

Discovered endpoints: 66
Referenced by someone (runtime): 49
Unused endpoints (runtime): 17

| Method | Path | Defined In | Only docs/tests refs (max 3) |
|---|---|---|---|
| POST | `/admin/permissions/cache/invalidate` | `omni2/app/routers/admin.py` |  |
| GET | `/api/v1/circuit-breaker/config` | `omni2/app/routers/circuit_breaker.py` | omni2/docs/CIRCUIT_BREAKER_IMPLEMENTATION.md:31<br>omni2/docs/CIRCUIT_BREAKER_IMPLEMENTATION.md:32<br>omni2/docs/CIRCUIT_BREAKER_IMPLEMENTATION.md:58 |
| PUT | `/api/v1/circuit-breaker/config` | `omni2/app/routers/circuit_breaker.py` | omni2/docs/CIRCUIT_BREAKER_IMPLEMENTATION.md:31<br>omni2/docs/CIRCUIT_BREAKER_IMPLEMENTATION.md:32<br>omni2/docs/CIRCUIT_BREAKER_IMPLEMENTATION.md:58 |
| POST | `/api/v1/circuit-breaker/mcp/{server_id}/enable` | `omni2/app/routers/circuit_breaker.py` | omni2/docs/CIRCUIT_BREAKER_IMPLEMENTATION.md:33<br>omni2/docs/CIRCUIT_BREAKER_IMPLEMENTATION.md:116<br>omni2/docs/CIRCUIT_BREAKER_IMPLEMENTATION.md:119 |
| POST | `/api/v1/circuit-breaker/mcp/{server_id}/reset` | `omni2/app/routers/circuit_breaker.py` | omni2/docs/CIRCUIT_BREAKER_IMPLEMENTATION.md:34<br>omni2/docs/CIRCUIT_BREAKER_QUICK_REFERENCE.md:141 |
| GET | `/api/v1/circuit-breaker/mcp/{server_id}/status` | `omni2/app/routers/circuit_breaker.py` | omni2/docs/CIRCUIT_BREAKER_IMPLEMENTATION.md:35<br>omni2/docs/CIRCUIT_BREAKER_IMPLEMENTATION.md:132<br>omni2/docs/CIRCUIT_BREAKER_QUICK_REFERENCE.md:79 |
| GET | `/audit/logs` | `omni2/app/routers/audit.py` |  |
| GET | `/audit/my-logs` | `omni2/app/routers/audit.py` | omni2/docs/archive/TEST_RESULTS.md:12<br>omni2/tests/test_endpoints.py:27<br>omni2/tests/test_endpoints.py:29 |
| GET | `/audit/my-stats` | `omni2/app/routers/audit.py` | omni2/docs/archive/TEST_RESULTS.md:13<br>omni2/tests/test_endpoints.py:36<br>omni2/tests/test_endpoints.py:38 |
| GET | `/audit/stats` | `omni2/app/routers/audit.py` |  |
| POST | `/cache/clear` | `omni2/app/routers/cache.py` | omni2/docs/archive/CACHE_TEST_RESULTS.md:101 |
| POST | `/cache/invalidate/user/{user_id}` | `omni2/app/routers/cache.py` | omni2/docs/archive/CACHE_TEST_RESULTS.md:75<br>omni2/docs/archive/CACHE_TEST_RESULTS.md:83<br>omni2/docs/archive/CACHE_TEST_RESULTS.md:100 |
| GET | `/cache/stats` | `omni2/app/routers/cache.py` | omni2/docs/archive/CACHE_TEST_RESULTS.md:98 |
| GET | `/health/cache` | `omni2/app/routers/health.py` | omni2/docs/archive/DEMO.md:222 |
| POST | `/health/cache/invalidate` | `omni2/app/routers/health.py` |  |
| GET | `/health/live` | `omni2/app/routers/health.py` |  |
| GET | `/health/ready` | `omni2/app/routers/health.py` |  |

## Auth Service

Discovered endpoints: 31
Referenced by someone (runtime): 18
Unused endpoints (runtime): 13

| Method | Path | Defined In | Only docs/tests refs (max 3) |
|---|---|---|---|
| GET | `/auth/api/v1/api-keys` | `auth_service/routes/api_keys.py` |  |
| POST | `/auth/api/v1/api-keys` | `auth_service/routes/api_keys.py` |  |
| POST | `/auth/api/v1/api-keys/validate` | `auth_service/routes/api_keys.py` |  |
| DELETE | `/auth/api/v1/api-keys/{key_id}` | `auth_service/routes/api_keys.py` |  |
| POST | `/auth/api/v1/auth/login` | `auth_service/routes/auth.py` | omni2/docs/architecture/TRAEFIK_ARCHITECTURE.md:86 |
| POST | `/auth/api/v1/auth/logout` | `auth_service/routes/auth.py` | auth_service/test/test_full.py:10 |
| POST | `/auth/api/v1/auth/refresh` | `auth_service/routes/auth.py` | auth_service/test/test_full.py:10 |
| GET | `/auth/api/v1/auth/validate` | `auth_service/routes/auth.py` | omni2/docs/architecture/TRAEFIK_ARCHITECTURE.md:86 |
| GET | `/auth/api/v1/permissions/check/{user_id}/{mcp_name}/{tool_name}` | `auth_service/routes/permissions.py` | omni2/docs/IAM_ARCHITECTURE.md:14 |
| GET | `/auth/api/v1/users/users/{user_id}/activity` | `auth_service/routes/users.py` | omni2/docs/IAM_ARCHITECTURE.md:14 |
| POST | `/auth/api/v1/users/users/{user_id}/reset-password` | `auth_service/routes/users.py` | omni2/docs/USERS_TAB_QUICK_REF.md:35 |
| GET | `/auth/health` | `auth_service/routes/health.py` | omni2/docs/architecture/TRAEFIK_ARCHITECTURE.md:129<br>omni2/docs/deployment/QUICK_START.md:102 |
| GET | `/auth/info` | `auth_service/routes/health.py` |  |

