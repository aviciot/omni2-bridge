# Dev Features Implementation

## Features Added

### 1. WebSocket Debug Window ✅
- **Draggable window** showing real-time WebSocket messages
- **Auto-capture** all WebSocket traffic
- **JSON formatting** with syntax highlighting
- **Message history** (last 50 messages)
- **Clear button** to reset messages
- **Minimize/Show** toggle button

### 2. Dev Login Button ✅
- **One-click login** with avi@omnit.com/avi123
- **Green button** on login page
- **Only shows when enabled** in config

## Configuration

Database: `omni2_dashboard.dashboard_config`

```json
{
  "key": "dev_features",
  "value": {
    "websocket_debug": true,
    "quick_login": true,
    "quick_login_email": "avi@omnit.com",
    "quick_login_password": "avi123"
  }
}
```

## How to Enable/Disable

### Enable Both Features:
```sql
UPDATE omni2_dashboard.dashboard_config 
SET value = '{"websocket_debug": true, "quick_login": true, "quick_login_email": "avi@omnit.com", "quick_login_password": "avi123"}'
WHERE key = 'dev_features';
```

### Disable WebSocket Debug Only:
```sql
UPDATE omni2_dashboard.dashboard_config 
SET value = jsonb_set(value, '{websocket_debug}', 'false')
WHERE key = 'dev_features';
```

### Disable Quick Login Only:
```sql
UPDATE omni2_dashboard.dashboard_config 
SET value = jsonb_set(value, '{quick_login}', 'false')
WHERE key = 'dev_features';
```

### Disable All Dev Features:
```sql
UPDATE omni2_dashboard.dashboard_config 
SET value = '{"websocket_debug": false, "quick_login": false}'
WHERE key = 'dev_features';
```

## Files Created/Modified

### Frontend:
- `src/components/WebSocketDebugWindow.tsx` - Draggable debug window
- `src/components/DevFeatures.tsx` - Wrapper component
- `src/app/layout.tsx` - Added DevFeatures component
- `src/app/login/page.tsx` - Added dev login button
- `src/app/api/config/dev_features/route.ts` - API endpoint

### Backend:
- `app/routers/config.py` - Added `/config/dev_features` endpoint

### Database:
- Added `dev_features` config entry

## Usage

### WebSocket Debug Window:
1. Enable in config (already enabled)
2. Refresh dashboard
3. Draggable window appears in bottom-right
4. Shows all WebSocket messages in real-time
5. Click "✕" to minimize, "Show WS Debug" to restore

### Dev Login:
1. Enable in config (already enabled)
2. Go to login page
3. Green "🚀 Dev Login" button appears
4. Click to auto-login as avi@omnit.com

## Production Safety

Both features are **disabled by default** and only activate when:
- `dev_features.websocket_debug = true` (for WebSocket window)
- `dev_features.quick_login = true` (for dev login button)

Set both to `false` in production!

## Testing

1. Restart dashboard frontend: `docker restart omni2-dashboard-frontend`
2. Go to http://localhost:3001/login
3. See green "Dev Login" button
4. Click it to auto-login
5. See draggable WebSocket debug window in bottom-right
6. Watch real-time WebSocket messages

## Status: READY TO TEST ✅
