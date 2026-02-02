# User Activity Tracking - Implementation Guide

## ✅ Completed Steps

### Step 1: Database Migration ✅ DONE
- **File**: `migrations/add_user_activities_table.sql`
- **Status**: Executed successfully
- **Table**: `omni2.user_activities` created with 6 indexes
- **Test**: Inserted 4-activity conversation flow
- **Conversation ID**: d9a7cfcb-a863-4808-b172-425d6919ebfb

### Step 2: Activity Tracker Service ✅ DONE
- **File**: `app/services/activity_tracker.py`
- **Status**: Created
- **Methods**: 4 tracking methods implemented

### Step 3: Test Data ✅ DONE
```sql
SELECT sequence_num, activity_type, activity_data 
FROM omni2.user_activities 
WHERE conversation_id = 'd9a7cfcb-a863-4808-b172-425d6919ebfb'
ORDER BY sequence_num;

Result:
1 | user_message       | {"message": "What is the status of job XYZ?"}
2 | mcp_tool_call      | {"mcp_server": "informatica_mcp", "tool_name": "get_job_status"}
3 | mcp_tool_response  | {"status": "success"}
4 | assistant_response | {"message": "Job XYZ is running at 75%", "tokens_used": 150}
```

---

## 🚀 Next Steps

### Step 4: Integrate Activity Tracking in WebSocket Chat

```bash
# Connect to database
docker exec omni_pg_db psql -U omni -d omni

# Run migration
\i /path/to/migrations/add_user_activities_table.sql

# Or directly:
docker exec omni_pg_db psql -U omni -d omni -f migrations/add_user_activities_table.sql
```

**Verify**:
```sql
-- Check table exists
\dt omni2.user_activities

-- Check indexes
\di omni2.idx_activities_*

-- Check structure
\d omni2.user_activities
```

---

### Step 4: Add Configuration

**File**: `omni2/app/config.py`

Add to settings:
```python
class Settings:
    # ... existing settings ...
    
    # Activity Tracking
    ACTIVITY_TRACKING_ENABLED: bool = True
```

---

### Step 5: Integrate in LLM Service

**File**: `omni2/app/services/llm_service.py`

Add imports:
```python
from app.services.activity_tracker import get_activity_tracker
```

Add tracking in `ask()` method (around line 850):
```python
# After tool execution
activity_tracker = get_activity_tracker()

# Track tool call
await activity_tracker.record_tool_call(
    db=db,
    conversation_id=conversation_id,
    session_id=session_id,
    user_id=user_id,
    sequence_num=sequence_counter,
    mcp_server=mcp_name,
    tool_name=tool_name,
    parameters=tool_use.input
)
```

---

### Step 6: Test

**Test Script**:
```python
# test_activity_tracker.py
import asyncio
import uuid
from app.services.activity_tracker import get_activity_tracker
from app.database import AsyncSessionLocal

async def test_tracking():
    tracker = get_activity_tracker()
    
    conversation_id = uuid.uuid4()
    session_id = uuid.uuid4()
    user_id = 1
    
    async with AsyncSessionLocal() as db:
        # Record user message
        await tracker.record_user_message(
            db=db,
            conversation_id=conversation_id,
            session_id=session_id,
            user_id=user_id,
            sequence_num=1,
            message="What's the status of job XYZ?"
        )
        
        # Record tool call
        await tracker.record_tool_call(
            db=db,
            conversation_id=conversation_id,
            session_id=session_id,
            user_id=user_id,
            sequence_num=2,
            mcp_server="informatica_mcp",
            tool_name="get_job_status",
            parameters={"job_id": "XYZ"}
        )
        
        # Record tool response
        await tracker.record_tool_response(
            db=db,
            conversation_id=conversation_id,
            session_id=session_id,
            user_id=user_id,
            sequence_num=3,
            mcp_server="informatica_mcp",
            tool_name="get_job_status",
            status="success",
            duration_ms=1200
        )
        
        # Record assistant response
        await tracker.record_assistant_response(
            db=db,
            conversation_id=conversation_id,
            session_id=session_id,
            user_id=user_id,
            sequence_num=4,
            message="Job XYZ is running at 75%",
            tokens_used=150
        )
    
    print(f"✅ Test completed! Conversation ID: {conversation_id}")
    print(f"Query: SELECT * FROM omni2.user_activities WHERE conversation_id = '{conversation_id}';")

if __name__ == "__main__":
    asyncio.run(test_tracking())
```

**Run test**:
```bash
cd omni2
python test_activity_tracker.py
```

**Verify in database**:
```sql
SELECT 
    sequence_num,
    activity_type,
    activity_data,
    created_at
FROM omni2.user_activities
WHERE conversation_id = '<conversation_id_from_test>'
ORDER BY sequence_num;
```

---

## 📊 Expected Result

```
 sequence_num | activity_type        | activity_data                                    | created_at
--------------+----------------------+--------------------------------------------------+-------------------
 1            | user_message         | {"message": "What's the status of job XYZ?"}    | 2026-02-01 14:25:10
 2            | mcp_tool_call        | {"mcp_server": "informatica_mcp", ...}          | 2026-02-01 14:25:11
 3            | mcp_tool_response    | {"status": "success", "duration_ms": 1200}      | 2026-02-01 14:25:12
 4            | assistant_response   | {"message": "Job XYZ is running...", ...}       | 2026-02-01 14:25:13
```

---

## 🎯 Integration Points

### Where to Add Tracking

1. **WebSocket Chat** (`app/routers/websocket_chat.py`)
   - Track user messages
   - Track assistant responses

2. **LLM Service** (`app/services/llm_service.py`)
   - Track tool calls
   - Track tool responses

3. **MCP Registry** (`app/services/mcp_registry.py`)
   - Track tool execution timing

---

## 🔧 Configuration Options

```python
# Enable/disable tracking
ACTIVITY_TRACKING_ENABLED = True

# Validate IDs before insert (optional)
ACTIVITY_TRACKING_VALIDATE_IDS = False

# Data retention (days)
ACTIVITY_TRACKING_RETENTION_DAYS = 365
```

---

## 📝 Next: API Endpoints

After backend tracking works, create API endpoints:

**File**: `app/routers/activities.py`
```python
GET /api/v1/activities/conversation/{conversation_id}
GET /api/v1/activities/user/{user_id}
GET /api/v1/activities/{activity_id}/details
```

---

## 🎨 Next: Frontend Visualization

After API works, build React flow graph:

**File**: `dashboard/frontend/src/components/ConversationFlow.tsx`

---

## ✅ Success Criteria

- [ ] Migration runs successfully
- [ ] Test script inserts 4 activities
- [ ] Database query shows correct data
- [ ] No errors in logs
- [ ] Performance <5ms per insert

---

**Status**: Backend foundation complete! Ready for integration and testing.
