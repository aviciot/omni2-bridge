# MCP PT - LLM Analysis & UI Implementation Plan

## Current State

### ✅ What We Have

**Database Schema:**
- `pt_runs.security_profile` (JSONB) - Stores LLM security analysis
- `pt_runs.test_plan` (JSONB) - Stores LLM test plan
- `pt_llm_suggestions` table - Stores LLM recommendations
- 6 test categories with 20 predefined tests
- PII/Secrets scanning support (Presidio + TruffleHog)

**Backend:**
- `planner.py` - LLM generates security profile + test plan
- `scanner.py` - PII/Secrets detection
- `mcp_discovery.py` - MCP metadata collection (NOW WORKING!)
- Redis publisher/handler ready

**Test Categories (All in DB):**
1. `auth_validation` - Auth/authz tests
2. `data_leakage` - **PII & Secrets** (presidio_scan, trufflehog_scan)
3. `protocol_robustness` - Protocol vulnerabilities
4. `resource_exhaustion` - DoS tests
5. `tool_boundary` - SQL injection, path traversal, SSRF
6. `tool_schema_abuse` - Schema validation

### ❌ What's Missing

**Flow:**
1. Discovery → Redis → Dashboard (not wired)
2. LLM Analysis → Redis → Dashboard (not wired)
3. Test execution doesn't use all categories

**UI:**
1. No security profile display
2. No test plan breakdown
3. No LLM recommendations display
4. No live discovery updates

---

## Implementation Steps

### Step 1: Wire Discovery → LLM → Redis Flow

**File: `pt_runs.py`**

```python
# After MCP discovery
discovery_data = {
    "mcp_server": {
        "name": mcp.name,
        "url": mcp.url,
        "protocol": mcp.protocol,
        "server_info": server_info,
        "capabilities": capabilities
    },
    "tools": tools,
    "prompts": prompts,
    "resources": resources
}

# Store in Redis
await redis_client.setex(
    f"pt_run:{run_id}:discovery",
    3600,
    json.dumps(discovery_data)
)

# Publish event
await redis_client.publish(
    f"pt_run:{run_id}",
    json.dumps({
        "event": "discovery_complete",
        "stage": "health_check",
        "tool_count": len(tools),
        "prompt_count": len(prompts),
        "resource_count": len(resources)
    })
)

# Call LLM planner
planner = PTPlanner()
plan_result = await planner.generate_test_plan(
    mcp_metadata=discovery_data,
    preset=security_profile,
    categories=None
)

# Store test plan in DB
await update_pt_run(run_id, {
    "test_plan": plan_result["test_plan"],
    "security_profile": plan_result["test_plan"]["security_profile"],
    "llm_cost_usd": plan_result["llm_cost"]
})

# Store in Redis
await redis_client.setex(
    f"pt_run:{run_id}:test_plan",
    3600,
    json.dumps(plan_result["test_plan"])
)

# Publish event
await redis_client.publish(
    f"pt_run:{run_id}",
    json.dumps({
        "event": "test_plan_ready",
        "stage": "llm_analysis",
        "test_count": len(plan_result["test_plan"]["tests"]),
        "categories": plan_result["test_plan"]["selected_categories"]
    })
)
```

### Step 2: Dashboard Backend - Subscribe to Redis

**File: `dashboard/backend/app/routers/mcp_pt_proxy.py`**

```python
@router.get("/runs/{run_id}/discovery")
async def get_discovery(run_id: int):
    """Get discovery data from Redis."""
    data = await redis_client.get(f"pt_run:{run_id}:discovery")
    if not data:
        raise HTTPException(404, "Discovery data not found")
    return json.loads(data)

@router.get("/runs/{run_id}/test-plan")
async def get_test_plan(run_id: int):
    """Get test plan from Redis."""
    data = await redis_client.get(f"pt_run:{run_id}:test_plan")
    if not data:
        raise HTTPException(404, "Test plan not found")
    return json.loads(data)

@router.websocket("/ws/pt-run/{run_id}")
async def websocket_pt_run(websocket: WebSocket, run_id: int):
    """WebSocket for live PT run updates."""
    await websocket.accept()
    
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(f"pt_run:{run_id}")
    
    try:
        async for message in pubsub.listen():
            if message['type'] == 'message':
                await websocket.send_json(json.loads(message['data']))
    except:
        pass
    finally:
        await pubsub.unsubscribe(f"pt_run:{run_id}")
```

### Step 3: Update UI Components

**Add to `MCPPTDashboardV2.tsx`:**

```typescript
interface SecurityProfile {
  overview: string;
  tool_summary: {
    total: number;
    high_risk: number;
    medium_risk: number;
    low_risk: number;
    high_risk_tools: string[];
  };
  risk_surface: string[];
  data_sensitivity: {
    handles_pii: boolean;
    handles_credentials: boolean;
    handles_financial: boolean;
    evidence: string[];
  };
  attack_vectors: Array<{
    vector: string;
    severity: string;
    affected_tools: string[];
    description: string;
  }>;
  recommended_focus: string[];
  risk_score: number;
}

interface TestPlan {
  selected_categories: string[];
  tests: Array<{
    category: string;
    test: string;
    tool: string;
    params: any;
  }>;
  recommendations: Array<{
    category: string;
    reason: string;
    priority: string;
    estimated_tests: number;
  }>;
}

// Add state
const [securityProfile, setSecurityProfile] = useState<SecurityProfile | null>(null);
const [testPlan, setTestPlan] = useState<TestPlan | null>(null);
const [discovery, setDiscovery] = useState<any>(null);

// WebSocket connection
useEffect(() => {
  if (selectedRun) {
    const ws = new WebSocket(`ws://localhost:8000/api/v1/mcp-pt/ws/pt-run/${selectedRun.run_id}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.event === 'discovery_complete') {
        fetchDiscovery(selectedRun.run_id);
      }
      
      if (data.event === 'test_plan_ready') {
        fetchTestPlan(selectedRun.run_id);
      }
    };
    
    return () => ws.close();
  }
}, [selectedRun]);

// Add UI sections
<Card>
  <CardHeader>
    <CardTitle>Security Profile</CardTitle>
  </CardHeader>
  <CardContent>
    {securityProfile && (
      <>
        <p>{securityProfile.overview}</p>
        <div className="mt-4">
          <h4>Risk Score: {securityProfile.risk_score}/10</h4>
          <h4>High Risk Tools: {securityProfile.tool_summary.high_risk}</h4>
        </div>
      </>
    )}
  </CardContent>
</Card>

<Card>
  <CardHeader>
    <CardTitle>Test Plan</CardTitle>
  </CardHeader>
  <CardContent>
    {testPlan && (
      <>
        <p>Categories: {testPlan.selected_categories.join(', ')}</p>
        <p>Total Tests: {testPlan.tests.length}</p>
      </>
    )}
  </CardContent>
</Card>
```

### Step 4: Enable All Test Categories in Executor

**File: `executor.py`**

Ensure all 6 categories are executed, including:
- `data_leakage` (PII/Secrets)
- `tool_boundary` (SQL injection, path traversal)

---

## Summary

**What LLM Does:**
1. Analyzes MCP metadata (tools, prompts, resources, capabilities)
2. Generates security profile (risk assessment, attack vectors)
3. Selects appropriate tests from 20 predefined tests
4. Provides recommendations for additional testing

**What UI Shows:**
1. Discovery results (tool/prompt/resource counts)
2. Security profile (risk score, high-risk tools, attack vectors)
3. Test plan (selected categories, test count)
4. LLM recommendations (future improvements)
5. Live updates via WebSocket

**Data Flow:**
```
MCP Discovery → Redis → Dashboard (WebSocket)
     ↓
LLM Analysis → Redis → Dashboard (WebSocket)
     ↓
Test Execution → Redis → Dashboard (WebSocket)
```
