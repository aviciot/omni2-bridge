# Corrections / Updates to Prior Dashboard Endpoint Trace

Date generated: 2026-02-02

This file supersedes/corrects specific findings from:
- `omni2/dashboard/ENDPOINT_TRACE_UI_TO_BACKEND_TO_AUTH.md`

No application code was changed; these are documentation updates after re-scanning the current repo state.

---

## Key corrections

### 1) FlowTracker WebSocket path is **not** a backend mismatch

Previous report claimed a mismatch between:
- UI: `ws://localhost:8500/api/v1/ws/flows/${userId}` (`omni2/dashboard/frontend/src/components/FlowTracker.tsx`)
- Backend: `WS /ws/flows/{user_id}` (`omni2/dashboard/backend/app/routers/flows.py`)

After re-checking router prefixes:
- `flows.router` is included with prefix `/api/v1` in `omni2/dashboard/backend/app/main.py`.
- Therefore the effective backend route is:
  - `WS /api/v1/ws/flows/{user_id}`

So the FlowTracker UI path **matches** the dashboard backend route.

---

## Updated “unused endpoints” inventory

If you want “endpoints that no one uses” (no references in runtime code outside their defining module), see:
- `omni2/ENDPOINT_UNUSED_AUDIT.md`

Notes on interpretation:
- For `auth_service`, the “unused” list will heavily include `/auth/...` **duplicate mounts** that are typically bypassed because Traefik strips the `/auth` prefix before forwarding.
- For dashboard backend and omni2, “unused” means: not referenced by dashboard UI / dashboard backend / omni2 core / auth_service / Traefik configs (runtime code), excluding docs/tests.

