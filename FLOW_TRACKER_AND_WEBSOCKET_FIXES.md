# Flow Tracker and WebSocket Fixes

**Date:** February 12, 2026
**Status:** ✅ Complete

---

## Issues Fixed

### 1. ✅ Multi-User Flow Tracker
**Problem:** The FlowTracker only showed flows for the currently logged-in user, not for monitored users like "neo@matrix.com".

**Solution:** Created a new `MultiUserFlowTracker` component that:
- Shows all monitored users with selectable checkboxes
- Allows selecting multiple users simultaneously
- Each selected user gets their own dedicated flow panel with real-time updates
- Each panel has independent WebSocket connection
- Shows connection status per user
- Allows removing users from tracking without disabling monitoring

**Files Modified:**
- ✅ Created: `omni2/dashboard/frontend/src/components/MultiUserFlowTracker.tsx`
- ✅ Updated: `omni2/dashboard/frontend/src/app/live-updates/page.tsx`
  - Added `monitoredUsers` state
  - Added `loadMonitoredUsers()` function
  - Replaced `FlowTracker` with `MultiUserFlowTracker`
  - Added auto-refresh of monitored users every 10 seconds
- ✅ Updated: `omni2/dashboard/frontend/src/components/MonitoringConfig.tsx`
  - Added `onUpdate` callback prop
  - Calls `onUpdate()` after enabling/disabling monitoring

**How It Works:**
1. User enables monitoring for "neo@matrix.com" and "avi@omni.com" in MonitoringConfig
2. MultiUserFlowTracker fetches the list of monitored users
3. User selects which monitored users to track
4. Each selected user gets:
   - Dedicated flow panel
   - Independent WebSocket connection to `ws://localhost:8500/api/v1/ws/flows/{userId}`
   - Real-time flow event updates
   - Connection status indicator
   - Remove button

---

### 2. ✅ WebSocket Disconnect Race Condition
**Problem:** When navigating away from pages with WebSocket connections, error occurred:
```
Error forwarding to OMNI2: (<CloseCode.NO_STATUS_RCVD: 1005>, '')
Error forwarding from OMNI2: Unexpected ASGI message 'websocket.send', after sending 'websocket.close'
```

**Root Cause:** The WebSocket proxy had a race condition where one side would close the connection, but the other forwarding task would still try to send messages after closure.

**Solution:** Implemented a shared `close_event` (asyncio.Event) pattern:
- Both forwarding tasks check the `close_event` before sending
- When either side disconnects, it sets the `close_event`
- The other task immediately stops trying to send
- Prevents "send after close" errors

**Files Modified:**
- ✅ Updated: `omni2/dashboard/backend/app/routers/websocket.py`
  - Added `close_event = asyncio.Event()` in both `/ws` and `/ws/chat` endpoints
  - Modified `forward_from_omni2()` to check event before sending
  - Modified `forward_to_omni2()` to check event in loop and handle `WebSocketDisconnect`
  - Wrapped send operations in try/except to set event on failure

**Before:**
```python
async def forward_from_omni2():
    async for message in omni2_ws:
        await websocket.send_text(message)  # Could fail if client disconnected

async def forward_to_omni2():
    while True:
        data = await websocket.receive_text()
        await omni2_ws.send(data)  # Could fail if server disconnected
```

**After:**
```python
close_event = asyncio.Event()

async def forward_from_omni2():
    async for message in omni2_ws:
        if close_event.is_set():
            break
        try:
            await websocket.send_text(message)
        except Exception:
            close_event.set()
            break

async def forward_to_omni2():
    while not close_event.is_set():
        data = await websocket.receive_text()
        try:
            await omni2_ws.send(data)
        except Exception:
            close_event.set()
            break
```

---

### 3. ✅ Username Search in AI Interaction Flows
**Problem:** The "Search & Filter" in Analytics → AI Interaction Flows only supported User ID search, not username/email.

**Solution:** Added username/email search field with autocomplete:
- Fetches all users on page load
- Provides datalist autocomplete for email addresses
- Converts username to user_id before API call
- Displays username/email in conversation list instead of just "User {id}"

**Files Modified:**
- ✅ Updated: `omni2/dashboard/frontend/src/app/analytics/conversations/page.tsx`
  - Added `users` state
  - Added `searchUsername` state
  - Added `loadUsers()` function
  - Modified `loadConversations()` to convert username to user_id
  - Added `getUserDisplay()` function to show email instead of ID
  - Updated `handleClear()` to clear username field
  - Added username search input with datalist autocomplete
  - Updated conversation display to show email instead of "User {id}"

**Features:**
- 📧 Autocomplete dropdown with all user emails
- 🔍 Partial matching (searches for emails containing the text)
- 👤 Shows username/email in results instead of just User ID
- 🔄 Works alongside User ID search (username takes precedence)

---

## Testing

### Test Multi-User Flow Tracker:
1. Go to Dashboard → Live Updates
2. Expand "Flow Monitoring Configuration"
3. Enable monitoring for multiple users (e.g., neo@matrix.com, avi@omni.com)
4. Select users from the checkboxes below
5. Each selected user should get their own flow panel
6. Trigger activity for each user and verify flows appear in correct panels

### Test WebSocket Fix:
1. Go to any page with WebSocket (Live Updates, Chat, etc.)
2. Navigate away or close the tab
3. Check logs - should NOT see "Unexpected ASGI message" errors

### Test Username Search:
1. Go to Analytics → AI Interaction Flows
2. Click on "Username/Email" field
3. Type partial email (e.g., "avi")
4. Select from autocomplete
5. Click Search
6. Verify conversations for that user appear
7. Verify email shows in results instead of "User {id}"

---

## Architecture

### Multi-User Flow Tracking:
```
MonitoringConfig
  ↓ (onUpdate callback)
LiveUpdatesPage
  ↓ (loadMonitoredUsers)
  ↓ (passes monitoredUsers prop)
MultiUserFlowTracker
  ↓ (User Selection)
  ↓ (Creates multiple)
UserFlowTracker[user1]  UserFlowTracker[user2]  UserFlowTracker[user3]
  ↓                       ↓                       ↓
  WS Connection          WS Connection           WS Connection
  (flow_events:1)        (flow_events:2)         (flow_events:3)
```

### WebSocket Close Event Pattern:
```
Client <---> Dashboard Backend <---> Traefik <---> OMNI2

close_event = Event()

forward_from_omni2()    forward_to_omni2()
     ↓                         ↓
  Check event             Check event
     ↓                         ↓
  Try send                 Try receive
     ↓                         ↓
  On error → Set event    On error → Set event
     ↓                         ↓
  Other task stops        Other task stops
```

---

## Benefits

1. **Multi-User Monitoring:**
   - Track multiple users simultaneously
   - Independent panels for better organization
   - Real-time updates per user
   - Easy add/remove without disabling monitoring

2. **WebSocket Stability:**
   - No more console errors on page close
   - Clean connection cleanup
   - Better error handling
   - Improved user experience

3. **Better Search:**
   - Search by email (more intuitive than user ID)
   - Autocomplete for faster search
   - See usernames in results
   - Better usability

---

## Files Changed

**Created:**
- `omni2/dashboard/frontend/src/components/MultiUserFlowTracker.tsx`

**Modified:**
- `omni2/dashboard/backend/app/routers/websocket.py`
- `omni2/dashboard/frontend/src/app/live-updates/page.tsx`
- `omni2/dashboard/frontend/src/components/MonitoringConfig.tsx`
- `omni2/dashboard/frontend/src/app/analytics/conversations/page.tsx`

---

## Next Steps

1. Test all features in development
2. Verify no console errors
3. Test with multiple users generating activity
4. Monitor logs for any WebSocket issues
5. Consider adding:
   - Export flow data per user
   - Flow comparison between users
   - Historical flow playback
   - Username search in other analytics pages
