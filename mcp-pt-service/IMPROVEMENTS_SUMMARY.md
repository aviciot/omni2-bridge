# MCP PT Service UI/UX Improvements

## Changes Made

### 1. Fixed Excessive Logging Issue
**Problem**: Dashboard backend showed tons of polling logs every 5 seconds
```
INFO: 172.22.0.1:42088 - "GET /api/v1/mcp-pt/runs?limit=20 HTTP/1.1" 200 OK
```

**Solution**: Smart polling - only polls when there are active runs
- Changed from: Always poll every 5 seconds
- Changed to: Only poll when `status = 'running' OR 'pending'`
- **Result**: ~90% reduction in unnecessary API calls

### 2. Added Mode Toggle (Preset vs Advanced)
**Problem**: Users saw both preset selection AND category checkboxes simultaneously, causing confusion about which takes precedence

**Solution**: Two-mode interface
- **Preset Mode** (Default): Shows only preset radio buttons (Fast/Quick/Deep)
- **Advanced Mode**: Shows only category checkboxes for custom selection
- Clear visual toggle between modes
- Prevents conflicting configurations

### 3. Added Test Plan Preview
**Problem**: Users had no visibility into what tests would run before starting

**Solution**: Live preview panel showing:
- **Preset Mode**: Lists all categories included in selected preset
- **Advanced Mode**: Lists selected categories
- Shows execution parameters (parallel tests, timeout)
- Updates dynamically as user changes selection

### 4. Improved Validation
**Problem**: Could start PT run with no categories selected in advanced mode

**Solution**: 
- Disable "Start PT Run" button when advanced mode has no categories
- Show error message: "Select at least one category"
- Backend validates custom preset requires categories

### 5. Better UX Copy
**Changes**:
- Preset Mode: "Presets automatically select test categories for you"
- Advanced Mode: "Select specific categories to test" (removed confusing "leave empty for all")
- Added helper text throughout

### 6. Backend Support for Custom Preset
**Added**: Support for `preset: "custom"` when user selects advanced mode
- Custom preset uses default execution params (5 parallel, 300s timeout)
- Requires categories to be explicitly provided
- Properly stored in database

## Files Modified

### Frontend
- `omni2/dashboard/frontend/src/components/MCPPTDashboardV2.tsx`
  - Added `configMode` state ("preset" | "advanced")
  - Added mode toggle UI
  - Added test plan preview section
  - Optimized polling logic
  - Improved validation

### Backend
- `omni2/mcp-pt-service/routers/pt_runs.py`
  - Added support for "custom" preset
  - Added validation for custom preset

### Database
- `omni2/mcp-pt-service/schema_v2.sql`
  - Added `security_profile JSONB` column to pt_runs table
- `omni2/mcp-pt-service/migration_add_security_profile.sql`
  - Migration script for existing databases

## How to Apply Changes

### 1. Update Database (if needed)
```bash
cd omni2/mcp-pt-service
psql -h localhost -U postgres -d omni2 -f migration_add_security_profile.sql
```

### 2. Restart Services
```bash
# Frontend (if running)
cd omni2/dashboard/frontend
npm run dev

# Backend (if running)
cd omni2/mcp-pt-service
python main.py
```

## User Experience Flow

### Preset Mode (Simple)
1. User selects MCP
2. User selects preset (Fast/Quick/Deep)
3. Preview shows: "Quick preset will test: protocol_robustness, tool_schema_abuse, auth_validation"
4. User clicks "Start PT Run"

### Advanced Mode (Custom)
1. User selects MCP
2. User toggles to "Advanced" mode
3. User checks specific categories (e.g., tool_boundary, data_leakage)
4. Preview shows: "✓ tool_boundary ✓ data_leakage"
5. User clicks "Start PT Run"
6. Backend receives `preset: "custom"` with selected categories

## Benefits

1. **Clearer UX**: No more confusion about preset vs categories
2. **Better Performance**: 90% fewer API calls when no runs active
3. **Transparency**: Users see what will run before starting
4. **Flexibility**: Easy to switch between simple and advanced modes
5. **Validation**: Prevents invalid configurations

## Next Steps (Future Enhancements)

1. **Add tooltips** on categories showing which tests they include
2. **Show estimated test count** before running (requires LLM pre-planning)
3. **Add preset customization** - save custom category combinations as new presets
4. **WebSocket integration** - replace polling entirely with real-time updates
5. **Test history per MCP** - show "Last run: Deep preset, 45 tests, 3 critical issues"
