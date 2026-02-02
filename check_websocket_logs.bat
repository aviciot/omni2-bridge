@echo off
REM WebSocket Conversation Log Checker
echo ================================================================================
echo WEBSOCKET CONVERSATION LOG VERIFICATION
echo ================================================================================
echo.

echo [1] Checking OMNI2 Backend Logs for WebSocket Chat...
echo ================================================================================
docker logs omni2 --tail 50 2>&1 | findstr /i "WS-CHAT conversation connected disconnected"
echo.

echo [2] Checking Dashboard Backend Logs for WebSocket Proxy...
echo ================================================================================
docker logs omni2-dashboard-backend --tail 50 2>&1 | findstr /i "websocket chat Connected"
echo.

echo [3] Recent OMNI2 Logs (Last 30 lines)...
echo ================================================================================
docker logs omni2 --tail 30
echo.

echo [4] Recent Dashboard Backend Logs (Last 30 lines)...
echo ================================================================================
docker logs omni2-dashboard-backend --tail 30
echo.

echo [5] Checking for conversation_id in database...
echo ================================================================================
docker exec -it omni2-postgres psql -U postgres -d mcp_performance -c "SELECT session_id, conversation_id, user_id, created_at, jsonb_array_length(flow_data->'events') as events FROM omni2.interaction_flows WHERE conversation_id IS NOT NULL ORDER BY created_at DESC LIMIT 5;"
echo.

echo ================================================================================
echo VERIFICATION COMPLETE
echo ================================================================================
echo.
echo To test WebSocket:
echo 1. Login to dashboard: http://localhost:3001
echo 2. Click chat bubble (bottom-right)
echo 3. Click first icon to enable WebSocket mode (should be highlighted)
echo 4. Send a message
echo 5. Run this script again
echo.
pause
