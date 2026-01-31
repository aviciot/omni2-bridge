@echo off
echo ============================================================
echo OMNI2 Phase 2 - Docker Restart and Validation
echo ============================================================
echo.

echo [1/4] Restarting omni2-bridge container...
docker restart omni2-bridge
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to restart container
    exit /b 1
)
echo OK: Container restarted
echo.

echo [2/4] Waiting 5 seconds for startup...
timeout /t 5 /nobreak >nul
echo.

echo [3/4] Checking container status...
docker ps --filter "name=omni2-bridge" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo.

echo [4/4] Checking logs for errors...
echo ============================================================
docker logs omni2-bridge --tail 50
echo ============================================================
echo.

echo Done! Check logs above for any errors.
echo.
echo Key things to look for:
echo   - "MCP Coordinator started"
echo   - "Tool Cache started"
echo   - "WebSocket Broadcaster started"
echo   - No "TypeError: 'NoneType' object is not callable" errors
echo.
pause
