@echo off
echo Restarting containers to load new WebSocket logging...
docker restart omni2-dashboard-backend
docker restart omni2-bridge
echo.
echo Waiting for containers to start...
timeout /t 5
echo.
echo Done! Now:
echo 1. Open dashboard: http://localhost:3001
echo 2. Click chat bubble
echo 3. Click first icon to enable WebSocket (should have white background)
echo 4. Send a message
echo 5. Check logs: docker logs omni2-bridge --tail 50 | findstr "WS-CHAT"
pause
