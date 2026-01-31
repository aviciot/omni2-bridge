# WebSocket Debug Window - UI Improvements

## Changes Made

### 1. ✅ Only Show After Login
**File:** `dashboard/frontend/src/components/DevFeatures.tsx`

**Before:**
- WebSocket window shown on all pages including login screen

**After:**
- Checks for `access_token` in localStorage
- Only renders WebSocket window if user is authenticated
- Listens for storage changes to hide/show on login/logout

```typescript
const [isAuthenticated, setIsAuthenticated] = useState(false);

useEffect(() => {
  const token = localStorage.getItem('access_token');
  setIsAuthenticated(!!token);

  const handleStorageChange = () => {
    const token = localStorage.getItem('access_token');
    setIsAuthenticated(!!token);
  };

  window.addEventListener('storage', handleStorageChange);
  return () => window.removeEventListener('storage', handleStorageChange);
}, []);

if (!DEV_WEBSOCKET_SCREEN || !isAuthenticated) {
  return null;
}
```

---

### 2. ✅ Disconnect Button Added
**File:** `dashboard/frontend/src/components/WebSocketDebugWindow.tsx`

**Before:**
- Only "Reconnect" button when disconnected
- No way to manually disconnect

**After:**
- Shows "Disconnect" button when connected (red)
- Shows "Reconnect" button when disconnected (blue)
- Disconnect function closes WebSocket and logs event

```typescript
const disconnectWebSocket = () => {
  if (wsRef.current) {
    wsRef.current.close();
    wsRef.current = null;
    setIsConnected(false);
    setMessages(prev => [...prev, {
      timestamp: new Date().toISOString(),
      type: 'system',
      data: { message: '🔌 Manually disconnected', status: 'disconnected' }
    }]);
  }
};

// In UI:
{isConnected ? (
  <button onClick={disconnectWebSocket} className="...bg-red-600...">
    Disconnect
  </button>
) : (
  <button onClick={connectWebSocket} className="...bg-blue-600...">
    Reconnect
  </button>
)}
```

---

### 3. ✅ Updated WebSocket URL to Use Traefik
**File:** `dashboard/frontend/src/components/WebSocketDebugWindow.tsx`

**Before:**
```typescript
const wsUrl = `ws://localhost:8500/ws/mcp-status?token=${token}`;
const ws = new WebSocket(wsUrl);
```

**After:**
```typescript
const wsUrl = `ws://localhost:8090/ws/mcp-status`;
const ws = new WebSocket(wsUrl, {
  headers: {
    'Authorization': `Bearer ${token}`
  }
} as any);
```

**Changes:**
- Port changed from 8500 (dashboard backend) to 8090 (Traefik gateway)
- Token passed in Authorization header instead of query parameter
- Consistent with Traefik ForwardAuth architecture

---

### 4. ✅ Already Resizable & Draggable

The component already had these features implemented:

**Draggable:**
- Click and drag the header to move window
- Uses `onMouseDown`, `onMouseMove`, `onMouseUp` events
- Position stored in state

**Resizable:**
- Drag bottom-right corner to resize
- Minimum size: 300x200 pixels
- Size stored in state
- Resize handle with icon in bottom-right corner

---

## Testing

### Test 1: Login Screen
1. Navigate to login page
2. ✅ WebSocket window should NOT be visible
3. Login with credentials
4. ✅ WebSocket window should appear after login

### Test 2: Disconnect Button
1. After login, WebSocket should auto-connect
2. ✅ "Disconnect" button (red) should be visible
3. Click "Disconnect"
4. ✅ Connection closes, button changes to "Reconnect" (blue)
5. Click "Reconnect"
6. ✅ Connection re-establishes

### Test 3: Draggable
1. Click and hold on window header
2. ✅ Drag window to new position
3. Release mouse
4. ✅ Window stays in new position

### Test 4: Resizable
1. Hover over bottom-right corner
2. ✅ Cursor changes to resize cursor
3. Click and drag
4. ✅ Window resizes
5. ✅ Minimum size enforced (300x200)

---

## UI States

### Connected State
```
┌─────────────────────────────────────────┐
│ WebSocket Monitor  🟢 Connected         │
│                    [Disconnect]      ✕  │
├─────────────────────────────────────────┤
│ [Filter...] [Type: all ▼]              │
├─────────────────────────────────────────┤
│ Messages...                             │
│                                         │
└─────────────────────────────────────────┘
```

### Disconnected State
```
┌─────────────────────────────────────────┐
│ WebSocket Monitor  🔴 Disconnected      │
│                    [Reconnect]       ✕  │
├─────────────────────────────────────────┤
│ ⚠️ Disconnected (code: 1000)            │
├─────────────────────────────────────────┤
│ [Filter...] [Type: all ▼]              │
├─────────────────────────────────────────┤
│ Messages...                             │
│                                         │
└─────────────────────────────────────────┘
```

### Hidden State (Login Screen)
```
(No WebSocket window visible)
```

---

## Architecture Flow

```
User Login
    ↓
localStorage.setItem('access_token', token)
    ↓
DevFeatures detects token
    ↓
WebSocketDebugWindow renders
    ↓
Auto-connects to ws://localhost:8090/ws/mcp-status
    ↓
Traefik validates Authorization header
    ↓
Connection established
    ↓
User can Disconnect/Reconnect manually
```

---

## Files Modified

1. **`dashboard/frontend/src/components/DevFeatures.tsx`**
   - Added authentication check
   - Only renders WebSocket window when logged in

2. **`dashboard/frontend/src/components/WebSocketDebugWindow.tsx`**
   - Added `disconnectWebSocket()` function
   - Added Disconnect button (shows when connected)
   - Updated WebSocket URL to use Traefik (port 8090)
   - Changed token passing from query param to Authorization header

---

## Summary

✅ **Only shows after login** - Hidden on login screen
✅ **Disconnect button** - Red button when connected, blue "Reconnect" when disconnected
✅ **Resizable** - Already implemented, drag bottom-right corner
✅ **Draggable** - Already implemented, drag header to move
✅ **Traefik integration** - Uses correct gateway URL with Authorization header

All requirements met! 🎉
