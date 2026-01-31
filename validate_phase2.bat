@echo off
echo.
echo ============================================================
echo OMNI2 Phase 2 - Complete Restart and Validation
echo ============================================================
echo.

echo Step 1: Stopping omni2-bridge container...
docker stop omni2-bridge
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Container may not be running
)
echo.

echo Step 2: Starting omni2-bridge container...
docker start omni2-bridge
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to start container
    exit /b 1
)
echo OK: Container started
echo.

echo Step 3: Waiting 10 seconds for full startup...
timeout /t 10 /nobreak >nul
echo.

echo Step 4: Checking container health...
docker ps --filter "name=omni2-bridge" --format "table {{.Names}}\t{{.Status}}"
echo.

echo Step 5: Checking for startup errors...
echo ============================================================
docker logs omni2-bridge --tail 100 | findstr /C:"error" /C:"Error" /C:"ERROR" /C:"FAIL" /C:"Exception" /C:"Traceback"
if %ERRORLEVEL% EQU 0 (
    echo.
    echo WARNING: Errors found in logs above!
    echo.
) else (
    echo No errors found - looking good!
    echo.
)

echo Step 6: Checking Phase 2 services started...
echo ============================================================
docker logs omni2-bridge --tail 100 | findstr /C:"MCP Coordinator started" /C:"Tool Cache started" /C:"WebSocket Broadcaster started"
echo ============================================================
echo.

echo Step 7: Checking service logging...
echo ============================================================
docker logs omni2-bridge --tail 50 | findstr /C:"service="
echo ============================================================
echo.

echo ============================================================
echo VALIDATION COMPLETE
echo ============================================================
echo.
echo What to look for:
echo   [OK] "MCP Coordinator started" with service=Coordinator
echo   [OK] "Tool Cache started" with service=Cache
echo   [OK] "WebSocket Broadcaster started" with service=WebSocket
echo   [OK] No "TypeError: 'NoneType' object is not callable"
echo   [OK] Service names visible in logs (service=...)
echo.
echo If all checks pass, Phase 2 is stable and ready!
echo.
pause
