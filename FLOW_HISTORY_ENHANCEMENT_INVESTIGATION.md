# Flow History Analytics Enhancement - Investigation Report

**Date:** February 12, 2026
**Task:** Add detailed checkpoint results/data to Flow History Analytics graph
**Status:** ✅ Investigation Complete

---

## Current State

### What Data is Already Captured?

The system **DOES** capture detailed data for each checkpoint! Here's what's currently stored:

#### Database Schema
```sql
CREATE TABLE omni2.interaction_flows (
    session_id UUID PRIMARY KEY,
    user_id INTEGER NOT NULL,
    flow_data JSONB NOT NULL,  -- Contains all events with metadata
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

#### Data Flow
1. **Checkpoints logged** via `flow_tracker.log_event()` in `app/services/flow_tracker.py`
2. **Stored in Redis** temporarily: `flow:{session_id}` stream
3. **Saved to PostgreSQL**: `omni2.interaction_flows.flow_data` (JSONB)

#### Current Data Captured Per Checkpoint

Based on `app/routers/chat.py` lines 385-393:

1. **auth_check**
   - `status`: "passed" or "failed"
   - `node_id`, `event_type`, `parent_id`, `timestamp`

2. **block_check**
   - `status`: "passed" or "failed"
   - `node_id`, `event_type`, `parent_id`, `timestamp`

3. **usage_check**
   - `remaining`: Number of remaining credits/tokens
   - `node_id`, `event_type`, `parent_id`, `timestamp`

4. **mcp_permission_check**
   - `mcp_access`: List of MCPs user has access to
   - `available_mcps`: List of available MCP names
   - `node_id`, `event_type`, `parent_id`, `timestamp`

5. **tool_filter**
   - `tool_restrictions`: Tool restriction rules applied
   - `node_id`, `event_type`, `parent_id`, `timestamp`

6. **llm_thinking**
   - `node_id`, `event_type`, `parent_id`, `timestamp`

7. **tool_call**
   - `mcp`: MCP server name
   - `tool`: Tool name called
   - `node_id`, `event_type`, `parent_id`, `timestamp`

8. **llm_complete**
   - `tokens`: Number of tokens used
   - `node_id`, `event_type`, `parent_id`, `timestamp`

9. **error** (if occurs)
   - `error`: Error message
   - `node_id`, `event_type`, `parent_id`, `timestamp`

---

## Current UI Display

**Location:** `omni2/dashboard/frontend/src/app/analytics/flow-history/page.tsx`

### What's Currently Shown (lines 244-261):
```tsx
{event.status && (
  <div className="text-xs mb-1">
    <span className="font-medium">Status:</span>{' '}
    <span className={event.status === 'passed' ? 'text-green-600' : 'text-red-600'}>
      {event.status}
    </span>
  </div>
)}
{event.remaining && (
  <div className="text-xs text-gray-600">
    <span className="font-medium">Remaining:</span> {event.remaining}
  </div>
)}
{event.tokens && (
  <div className="text-xs text-gray-600">
    <span className="font-medium">Tokens:</span> {event.tokens}
  </div>
)}
```

### What's MISSING:
- ❌ `mcp_access` (what MCPs the user has permission for)
- ❌ `available_mcps` (what MCPs are available)
- ❌ `tool_restrictions` (what tool rules were applied)
- ❌ `mcp` (which MCP was called)
- ❌ `tool` (which tool was executed)
- ❌ `error` (error details if checkpoint failed)

---

## ✅ Feasibility Assessment

### Is This Data Already in the Database?
**YES! 100% Feasible**

The data is **ALREADY CAPTURED** and stored in `flow_data` JSONB column. It's just not being displayed in the UI.

### Proof of Concept Query
```sql
SELECT
    session_id,
    user_id,
    flow_data->'events' as events,
    created_at
FROM omni2.interaction_flows
WHERE user_id = 1
ORDER BY created_at DESC
LIMIT 1;
```

**Sample Output** (what's actually in DB):
```json
{
  "session_id": "uuid-here",
  "user_id": 1,
  "events": [
    {
      "node_id": "abc123",
      "event_type": "auth_check",
      "parent_id": "",
      "timestamp": "1707747123.456",
      "status": "passed"
    },
    {
      "node_id": "def456",
      "event_type": "mcp_permission_check",
      "parent_id": "abc123",
      "timestamp": "1707747123.789",
      "mcp_access": "['Oracle MCP', 'Postgres MCP']",
      "available_mcps": "['Oracle MCP', 'Postgres MCP', 'GitHub MCP']"
    },
    {
      "node_id": "ghi789",
      "event_type": "tool_call",
      "parent_id": "xyz999",
      "timestamp": "1707747125.123",
      "mcp": "Oracle MCP",
      "tool": "execute_query"
    }
  ]
}
```

---

## 🎯 Implementation Plan

### What Needs to Be Done?

**TL;DR:** Just update the UI - the data is already there!

### High-Level Steps:

1. ✅ **Data is Already Captured** - No backend changes needed
2. ✅ **Data is Already in DB** - No schema changes needed
3. ✅ **Data is Already Flowing to UI** - API already returns it
4. ⚠️ **UI Just Needs to Display It** - Simple frontend update

---

## 📋 Implementation Checklist

### Frontend Changes (Only Required Work)

**File:** `omni2/dashboard/frontend/src/app/analytics/flow-history/page.tsx`

**Lines to Update:** 244-261 (the event display section)

#### 1. Add MCP Access Display (for mcp_permission_check)
```tsx
{event.mcp_access && (
  <div className="text-xs text-gray-600 mb-1">
    <span className="font-medium">✅ MCP Access:</span> {event.mcp_access}
  </div>
)}
{event.available_mcps && (
  <div className="text-xs text-gray-500">
    <span className="font-medium">📋 Available MCPs:</span> {event.available_mcps}
  </div>
)}
```

#### 2. Add Tool Restrictions Display (for tool_filter)
```tsx
{event.tool_restrictions && (
  <div className="text-xs text-gray-600">
    <span className="font-medium">🔒 Tool Restrictions:</span> {event.tool_restrictions}
  </div>
)}
```

#### 3. Add Tool Call Details (for tool_call)
```tsx
{event.mcp && event.tool && (
  <div className="text-xs text-gray-600">
    <span className="font-medium">🔧 Called:</span>{' '}
    <span className="font-mono bg-blue-50 px-2 py-1 rounded">{event.mcp}</span>
    {' → '}
    <span className="font-mono bg-green-50 px-2 py-1 rounded">{event.tool}</span>
  </div>
)}
```

#### 4. Add Error Display (for error checkpoints)
```tsx
{event.error && (
  <div className="text-xs text-red-600 bg-red-50 p-2 rounded mt-1">
    <span className="font-medium">❌ Error:</span> {event.error}
  </div>
)}
```

#### 5. Optional: Add Expandable Details
For cleaner UI, add a "Show Details" button that expands full JSON:

```tsx
{Object.keys(event).length > 4 && (
  <button
    onClick={() => setExpandedNode(event.node_id)}
    className="text-xs text-purple-600 hover:underline mt-1"
  >
    {expandedNode === event.node_id ? '▼ Hide Details' : '▶ Show All Details'}
  </button>
)}
{expandedNode === event.node_id && (
  <pre className="text-xs bg-gray-100 p-2 rounded mt-2 overflow-x-auto">
    {JSON.stringify(event, null, 2)}
  </pre>
)}
```

---

## 🎨 Enhanced UI Mockup

### Before (Current):
```
┌─────────────────────────────────┐
│ 1  AUTH_CHECK                   │
│    ⏱️ 10:30:45                  │
│    Status: passed               │
└─────────────────────────────────┘
```

### After (Enhanced):
```
┌─────────────────────────────────────────────────────┐
│ 1  AUTH_CHECK                                       │
│    ⏱️ 10:30:45                                      │
│    Status: ✅ passed                                │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 3  USAGE_CHECK                                      │
│    ⏱️ 10:30:46                                      │
│    Status: ✅ passed                                │
│    Remaining: 950 credits                           │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 4  MCP_PERMISSION_CHECK                             │
│    ⏱️ 10:30:46                                      │
│    ✅ MCP Access: ['Oracle MCP', 'Postgres MCP']    │
│    📋 Available MCPs: ['Oracle', 'Postgres', 'Git'] │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 5  TOOL_FILTER                                      │
│    ⏱️ 10:30:46                                      │
│    🔒 Tool Restrictions: {"oracle": ["query"]}      │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ 7  TOOL_CALL                                        │
│    ⏱️ 10:30:47                                      │
│    🔧 Called: [Oracle MCP] → [execute_query]        │
└─────────────────────────────────────────────────────┘
```

---

## 📊 Benefits of Enhancement

1. **Better Debugging**
   - See exactly which MCPs user had access to
   - Understand why certain tools were filtered
   - Identify which specific tool was called

2. **Compliance & Audit**
   - Track MCP permission decisions
   - Show tool restriction enforcement
   - Document authorization flow

3. **Performance Analysis**
   - Understand which MCPs/tools are most used
   - Identify bottlenecks in permission checks
   - Optimize based on actual usage patterns

4. **User Support**
   - Quickly diagnose "why can't I use X?" questions
   - Show users what permissions they had
   - Explain tool filtering decisions

---

## ⚡ Quick Implementation Guide

### Step 1: Update the Event Display Component
```tsx
// Current location: lines 237-263 in flow-history/page.tsx

<div className="flex-1 bg-gray-50 rounded-lg p-3 border border-gray-200">
  <div className="font-semibold text-sm mb-1" style={{ color: getCheckpointColor(event.event_type) }}>
    {event.event_type.replace(/_/g, ' ').toUpperCase()}
  </div>

  <div className="text-xs text-gray-600 mb-2">
    ⏱️ {formatTimestamp(event.timestamp)}
  </div>

  {/* Existing fields */}
  {event.status && (
    <div className="text-xs mb-1">
      <span className="font-medium">Status:</span>{' '}
      <span className={event.status === 'passed' ? 'text-green-600' : 'text-red-600'}>
        {event.status}
      </span>
    </div>
  )}

  {/* ADD NEW FIELDS HERE */}
  {event.mcp_access && (
    <div className="text-xs text-blue-700 bg-blue-50 px-2 py-1 rounded mb-1">
      <span className="font-medium">✅ Has Access:</span> {event.mcp_access}
    </div>
  )}

  {event.available_mcps && (
    <div className="text-xs text-gray-600 mb-1">
      <span className="font-medium">📋 Available:</span> {event.available_mcps}
    </div>
  )}

  {event.tool_restrictions && (
    <div className="text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded mb-1">
      <span className="font-medium">🔒 Restrictions:</span> {event.tool_restrictions}
    </div>
  )}

  {event.mcp && event.tool && (
    <div className="text-xs text-purple-700 bg-purple-50 px-2 py-1 rounded mb-1">
      <span className="font-medium">🔧 Tool Called:</span>{' '}
      <span className="font-mono">{event.mcp} → {event.tool}</span>
    </div>
  )}

  {event.error && (
    <div className="text-xs text-red-700 bg-red-50 px-2 py-1 rounded mt-1">
      <span className="font-medium">❌ Error:</span> {event.error}
    </div>
  )}

  {/* Keep existing fields */}
  {event.remaining && (
    <div className="text-xs text-gray-600">
      <span className="font-medium">Remaining:</span> {event.remaining}
    </div>
  )}

  {event.tokens && (
    <div className="text-xs text-gray-600">
      <span className="font-medium">Tokens:</span> {event.tokens}
    </div>
  )}
</div>
```

### Step 2: Test with Real Data
1. Enable flow monitoring for a test user
2. Make a request through the system
3. Go to Analytics → Flow History
4. Select the user and session
5. Verify all new fields appear

---

## 🚀 Estimated Implementation Time

- **UI Changes:** 15 minutes
- **Testing:** 10 minutes
- **Total:** 25 minutes

**No backend changes needed!** The data is already there.

---

## 📝 Summary

### ✅ Current State
- ✅ Data is captured at each checkpoint
- ✅ Data is stored in PostgreSQL
- ✅ Data is returned by API
- ✅ Data reaches the frontend

### ⚠️ What's Missing
- ⚠️ UI only displays 3 fields: `status`, `remaining`, `tokens`
- ⚠️ Other fields like `mcp_access`, `tool_restrictions`, `mcp`, `tool` are ignored

### 🎯 Solution
- 🎯 Add 5-10 lines of JSX to display additional fields
- 🎯 No backend changes
- 🎯 No database changes
- 🎯 No API changes

### 💡 The data you want is already there - it just needs to be shown!

---

**Ready to implement?** This is a quick frontend-only change. All the hard work (data capture, storage, API) is already done!
