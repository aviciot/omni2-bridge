# MCP PT Service - Test Categories & Tests

## Test Registry Location
**File**: `omni2/mcp-pt-service/test_registry.py`

---

## 📋 TEST CATEGORIES (6 Total)

### 1. 🔴 PROTOCOL_ROBUSTNESS (4 tests)
**Description**: Tests for protocol-level vulnerabilities and malformed requests  
**Default Severity**: HIGH  
**Database ID**: 1

#### Tests:
1. **invalid_json** - Send malformed JSON payload
   - Cuts off JSON to create syntax error
   - PASS: Rejects with 400 Bad Request
   - FAIL: Accepts malformed JSON

2. **missing_fields** - Omit required protocol fields
   - Sends empty parameters {}
   - PASS: Rejects with 400/422
   - FAIL: Accepts empty params

3. **oversized_frame** - Send oversized message frame
   - Sends 10MB payload
   - PASS: Rejects with 413 Payload Too Large
   - FAIL: Accepts 10MB payload

4. **partial_stream** - Send incomplete message stream
   - Sends partial/incomplete stream
   - PASS: Times out or handles gracefully
   - FAIL: Doesn't handle partial stream

---

### 2. 🟡 TOOL_SCHEMA_ABUSE (4 tests)
**Description**: Tests for schema validation and parameter abuse  
**Default Severity**: MEDIUM  
**Database ID**: 2

#### Tests:
1. **unknown_param** - Add unknown parameters to tool call
   - Adds `_evil`, `__proto__` params
   - PASS: Rejects with 400/422
   - FAIL: Accepts unknown params

2. **wrong_type** - Send wrong parameter types
   - Converts int→string, string→int
   - PASS: Rejects with 400/422
   - FAIL: Accepts wrong types

3. **missing_required** - Omit required parameters
   - Removes first required param
   - PASS: Rejects with 400/422
   - FAIL: Accepts missing required

4. **oversized_param** - Send oversized parameter values
   - Sends 1MB string parameter
   - PASS: Rejects with 400/413/422
   - FAIL: Accepts 1MB param

---

### 3. 🟠 TOOL_BOUNDARY (1 test)
**Description**: Tests for boundary violations and unsafe operations  
**Default Severity**: HIGH  
**Database ID**: 3

#### Tests:
1. **file_traversal** - Test path traversal attempts
   - Tests: `../../../etc/passwd`, `..\\..\\..\\windows\\system32\\config\\sam`
   - PASS: Blocks path traversal
   - FAIL: Path traversal succeeds (CRITICAL)

---

### 4. 🔴 AUTH_VALIDATION (2 tests)
**Description**: Tests for authentication and authorization weaknesses  
**Default Severity**: CRITICAL  
**Database ID**: 4

#### Tests:
1. **no_token** - Test access without authentication
   - Calls tool without auth token
   - PASS: Blocks with 401/403
   - FAIL: Allows unauthenticated access (CRITICAL)

2. **forbidden_tool** - Test unauthorized tool access
   - Attempts unauthorized tool access
   - PASS: Blocks with 401/403
   - FAIL: Unauthorized access succeeds (HIGH)

---

### 5. 🟠 RESOURCE_EXHAUSTION (2 tests)
**Description**: Tests for resource exhaustion and DoS vulnerabilities  
**Default Severity**: HIGH  
**Database ID**: 5

#### Tests:
1. **parallel_connections** - Test connection flooding
   - Sends 100 parallel requests
   - PASS: Rate limits to <50 connections
   - FAIL: Accepts >50 parallel connections (HIGH)

2. **hanging_tool** - Test long-running operations
   - Waits 60s for timeout
   - PASS: Times out correctly
   - FAIL: Execution exceeds 60s (MEDIUM)

---

### 6. 🔴 DATA_LEAKAGE (2 tests)
**Description**: Tests for sensitive data exposure (PII, secrets)  
**Default Severity**: CRITICAL  
**Database ID**: 6

#### Tests:
1. **presidio_scan** - Scan response for PII
   - Detects: email, SSN, phone, credit card
   - PASS: No PII detected
   - FAIL: PII DETECTED (CRITICAL)

2. **trufflehog_scan** - Scan response for secrets
   - Detects: AWS keys, API keys, JWT tokens
   - PASS: No secrets detected
   - FAIL: SECRETS DETECTED (CRITICAL)

---

## 📊 SUMMARY

| Category | Tests | Severity | Status |
|----------|-------|----------|--------|
| protocol_robustness | 4 | HIGH | ✅ Implemented |
| tool_schema_abuse | 4 | MEDIUM | ✅ Implemented |
| tool_boundary | 1 | HIGH | ✅ Implemented |
| auth_validation | 2 | CRITICAL | ✅ Implemented |
| resource_exhaustion | 2 | HIGH | ✅ Implemented |
| data_leakage | 2 | CRITICAL | ✅ Implemented |
| **TOTAL** | **15** | - | **✅ All Implemented** |

---

## 🎨 UI COMPLETION STATUS

### ✅ COMPLETED UI Components

1. **MCPPTDashboardV2.tsx** - Main Dashboard
   - ✅ Start PT Run panel
   - ✅ Preset selection (fast/quick/deep)
   - ✅ Advanced mode with category selection
   - ✅ Recent runs display
   - ✅ History timeline view
   - ✅ Run comparison

2. **PTRunDetails.tsx** - Run Details Modal
   - ✅ Discovery Tab
     - Shows tools count, prompts count, resources count
     - Lists all discovered tools with descriptions
     - Lists all prompts
     - Lists all resources
   - ✅ Security Profile Tab
     - Risk score (0-10)
     - High-risk tools list
     - Attack vectors with severity
     - Data sensitivity indicators (PII/Credentials/System Access)
   - ✅ Test Plan Tab
     - Total tests count
     - Selected categories
     - Estimated duration
     - Detailed test list with rationale
   - ✅ Results Tab
     - Live test results
     - Pass/Fail status
     - Severity badges
     - Evidence details

3. **WebSocket Integration**
   - ✅ Real-time updates via existing WS infrastructure
   - ✅ Subscription-based filtering
   - ✅ Event types: discovery_complete, test_plan_ready, test_result, pt_complete

4. **API Endpoints**
   - ✅ POST /api/v1/mcp-pt/run - Start PT run
   - ✅ GET /api/v1/mcp-pt/runs - List runs
   - ✅ GET /api/v1/mcp-pt/runs/{id} - Get run details
   - ✅ GET /api/v1/mcp-pt/runs/{id}/discovery - Get discovery data
   - ✅ GET /api/v1/mcp-pt/runs/{id}/results - Get test results
   - ✅ GET /api/v1/mcp-pt/runs/{id}/security-profile - Get security profile
   - ✅ GET /api/v1/mcp-pt/categories - List categories
   - ✅ GET /api/v1/mcp-pt/categories/{name}/tests - Get category tests
   - ✅ GET /api/v1/mcp-pt/presets - List presets
   - ✅ POST /api/v1/mcp-pt/compare - Compare runs

---

## 🔄 DATA FLOW

### 1. User Starts PT Run
```
Frontend → Dashboard Backend → PT Service
POST /api/v1/mcp-pt/run
{
  "mcp_id": "docker_controller",
  "preset": "quick",
  "categories": ["auth_validation", "data_leakage"]
}
```

### 2. PT Service Executes
```
Stage 1: Discovery (MCP metadata)
  → Redis: pt_run:{id}:discovery
  → Event: pt_discovery_complete

Stage 2: LLM Analysis (Security profile + Test plan)
  → Redis: pt_run:{id}:test_plan
  → Event: pt_test_plan_ready

Stage 3: Test Execution (Run 15 tests)
  → Database: omni2.pt_test_results
  → Event: pt_test_result (per test)

Stage 4: Completion
  → Event: pt_complete
```

### 3. Frontend Receives Updates
```
WebSocket → Dashboard receives events
  → PTRunDetails component updates UI
  → Discovery tab populates
  → Security Profile tab shows risk score
  → Test Plan tab shows selected tests
  → Results tab shows live results
```

---

## ✅ ALL FEATURES COMPLETE

**Backend**: ✅ All 15 tests implemented in test_registry.py  
**Database**: ✅ 6 categories, 20 test functions (includes extras)  
**API**: ✅ All endpoints implemented and proxied  
**Frontend**: ✅ Full UI with 4 tabs (Discovery, Profile, Plan, Results)  
**WebSocket**: ✅ Real-time updates via existing infrastructure  
**LLM Integration**: ✅ Generates security profile and test plan  

**Status**: 🎉 **FULLY OPERATIONAL**
