# LLM Test Planning - How Tests Are Applied

## Current Behavior

### ✅ TOOLS (Fully Tested)
**LLM receives**: 3 tools with names, descriptions, input schemas
**LLM applies**: Tests from all 6 categories to each tool

**Example for docker_controller with 12 tools**:
```json
{
  "tests": [
    {
      "category": "auth_validation",
      "test": "no_token",
      "tool": "restart_container",  // ← Real tool name
      "params": {"container_id": "test123"}
    },
    {
      "category": "tool_schema_abuse",
      "test": "unknown_param",
      "tool": "list_containers",  // ← Real tool name
      "params": {}
    },
    {
      "category": "data_leakage",
      "test": "presidio_scan",
      "tool": "inspect_container",  // ← Real tool name
      "params": {"container_id": "test123"}
    }
  ]
}
```

**How it works**:
1. LLM sees tool list: `restart_container`, `stop_container`, `list_containers`, etc.
2. LLM categorizes by risk: HIGH (restart/stop), MEDIUM (list), LOW (health)
3. LLM selects tests per tool based on risk
4. Each test specifies **exact tool name** from discovery
5. Executor runs test against that specific tool

**Tests applied per tool**:
- `auth_validation` → no_token, forbidden_tool
- `tool_schema_abuse` → unknown_param, wrong_type, missing_required, oversized_param
- `tool_boundary` → file_traversal (if tool has path params)
- `resource_exhaustion` → parallel_connections, hanging_tool
- `data_leakage` → presidio_scan, trufflehog_scan
- `protocol_robustness` → invalid_json, missing_fields, oversized_frame

---

### ⚠️ PROMPTS (NOT Currently Tested)
**LLM receives**: 2 prompts with names, descriptions, arguments
**LLM does**: Includes in security profile analysis
**LLM does NOT**: Generate tests for prompts

**What SHOULD happen**:
```json
{
  "tests": [
    {
      "category": "prompt_injection",  // ← NEW CATEGORY NEEDED
      "test": "jailbreak_attempt",
      "prompt": "docker_management_prompt",  // ← Prompt name
      "params": {"user_input": "Ignore previous instructions..."}
    },
    {
      "category": "prompt_injection",
      "test": "context_manipulation",
      "prompt": "docker_management_prompt",
      "params": {"user_input": "{{system_prompt}}"}
    }
  ]
}
```

**Missing tests for prompts**:
- Prompt injection attacks
- Context manipulation
- Jailbreak attempts
- Role confusion
- System prompt extraction

---

### ⚠️ RESOURCES (NOT Currently Tested)
**LLM receives**: 2 resources with URIs, MIME types, descriptions
**LLM does**: Includes in security profile analysis
**LLM does NOT**: Generate tests for resources

**What SHOULD happen**:
```json
{
  "tests": [
    {
      "category": "resource_access",  // ← NEW CATEGORY NEEDED
      "test": "unauthorized_read",
      "resource": "file://logs/docker.log",  // ← Resource URI
      "params": {}
    },
    {
      "category": "resource_access",
      "test": "path_traversal",
      "resource": "file://logs/../../../etc/passwd",
      "params": {}
    }
  ]
}
```

**Missing tests for resources**:
- Unauthorized access
- Path traversal
- MIME type validation
- Size limits
- Rate limiting

---

## How LLM Decides Test Coverage

### 1. Risk-Based Selection
```
HIGH RISK TOOLS (restart, stop, remove)
  → Apply ALL categories (15 tests each)
  → Priority: auth_validation, tool_boundary, data_leakage

MEDIUM RISK TOOLS (list, inspect, logs)
  → Apply MOST categories (10 tests each)
  → Priority: tool_schema_abuse, data_leakage

LOW RISK TOOLS (health, version)
  → Apply BASIC categories (5 tests each)
  → Priority: protocol_robustness, resource_exhaustion
```

### 2. Preset-Based Selection
```
FAST preset (30s)
  → Test 3 high-risk tools only
  → 2 categories per tool (auth + data_leakage)
  → ~6 tests total

QUICK preset (2min)
  → Test all high-risk + 2 medium-risk tools
  → 3 categories per tool
  → ~15 tests total

DEEP preset (10min)
  → Test ALL tools
  → ALL categories per tool
  → ~50+ tests total
```

### 3. Category-Based Selection (Advanced Mode)
```
User selects: ["auth_validation", "data_leakage"]
  → LLM applies ONLY these 2 categories
  → To ALL tools (high + medium + low risk)
  → ~24 tests (12 tools × 2 categories)
```

---

## Example: docker_controller with 12 tools, 5 prompts, 1 resource

### Discovery Output
```json
{
  "tools": [
    {"name": "restart_container", "description": "Restart a container"},
    {"name": "stop_container", "description": "Stop a container"},
    {"name": "list_containers", "description": "List all containers"},
    // ... 9 more tools
  ],
  "prompts": [
    {"name": "docker_management", "description": "Manage Docker containers"},
    {"name": "container_health", "description": "Check container health"},
    // ... 3 more prompts
  ],
  "resources": [
    {"uri": "file://logs/docker.log", "mimeType": "text/plain"}
  ]
}
```

### LLM Test Plan (QUICK preset)
```json
{
  "security_profile": {
    "risk_score": 7,
    "high_risk_tools": ["restart_container", "stop_container", "start_container", "remove_container"],
    "attack_vectors": [
      {
        "vector": "Unauthorized Container Control",
        "severity": "critical",
        "affected_tools": ["restart_container", "stop_container"]
      }
    ]
  },
  "selected_categories": ["auth_validation", "tool_boundary", "data_leakage"],
  "tests": [
    // HIGH RISK TOOL #1: restart_container
    {"category": "auth_validation", "test": "no_token", "tool": "restart_container"},
    {"category": "auth_validation", "test": "forbidden_tool", "tool": "restart_container"},
    {"category": "tool_boundary", "test": "file_traversal", "tool": "restart_container"},
    {"category": "data_leakage", "test": "presidio_scan", "tool": "restart_container"},
    
    // HIGH RISK TOOL #2: stop_container
    {"category": "auth_validation", "test": "no_token", "tool": "stop_container"},
    {"category": "tool_boundary", "test": "file_traversal", "tool": "stop_container"},
    {"category": "data_leakage", "test": "trufflehog_scan", "tool": "stop_container"},
    
    // MEDIUM RISK TOOL: list_containers
    {"category": "data_leakage", "test": "presidio_scan", "tool": "list_containers"},
    
    // ... more tests
  ],
  "total_tests": 15
}
```

**Notice**:
- ✅ Tests applied to **tools** (restart_container, stop_container, list_containers)
- ❌ NO tests for **prompts** (docker_management, container_health)
- ❌ NO tests for **resources** (file://logs/docker.log)

---

## What's Missing

### 1. Prompt Testing Category
**Need to add**:
```python
# In test_registry.py
"prompt_injection": {
    "jailbreak_attempt": test_jailbreak,
    "context_manipulation": test_context_manipulation,
    "role_confusion": test_role_confusion,
    "system_prompt_extraction": test_system_prompt_extraction,
}
```

### 2. Resource Testing Category
**Need to add**:
```python
# In test_registry.py
"resource_access": {
    "unauthorized_read": test_unauthorized_read,
    "path_traversal_resource": test_path_traversal_resource,
    "mime_validation": test_mime_validation,
    "size_limit": test_size_limit,
}
```

### 3. Update LLM Prompt
**Need to update** `planner.py` SYSTEM_PROMPT:
```
Available Categories:
- protocol_robustness: Tests for protocol-level vulnerabilities
- tool_schema_abuse: Tests for schema validation and parameter abuse
- tool_boundary: Tests for boundary violations and unsafe operations
- auth_validation: Tests for authentication and authorization weaknesses
- resource_exhaustion: Tests for resource exhaustion and DoS vulnerabilities
- data_leakage: Tests for sensitive data exposure (PII, secrets)
+ prompt_injection: Tests for prompt injection and manipulation attacks  ← ADD
+ resource_access: Tests for resource access control and validation      ← ADD

Test Targets:
- TOOLS: Apply auth, schema, boundary, exhaustion, leakage tests
- PROMPTS: Apply prompt_injection tests                                  ← ADD
- RESOURCES: Apply resource_access tests                                 ← ADD
```

---

## Summary

### Current State
✅ **Tools**: Fully tested (15 tests across 6 categories)  
⚠️ **Prompts**: Analyzed but NOT tested (0 tests)  
⚠️ **Resources**: Analyzed but NOT tested (0 tests)

### Recommended Enhancement
Add 2 new categories:
1. **prompt_injection** (4 tests) → Apply to all prompts
2. **resource_access** (4 tests) → Apply to all resources

**Total tests would be**:
- 15 tests × 12 tools = 180 tool tests
- 4 tests × 5 prompts = 20 prompt tests
- 4 tests × 1 resource = 4 resource tests
- **TOTAL: 204 tests** (vs current 180)

This would provide **complete MCP security coverage** across all three MCP primitives: tools, prompts, and resources.
