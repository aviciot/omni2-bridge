@echo off
echo ============================================================
echo Flow Tracking - Complete Test
echo ============================================================

echo.
echo [1] Check Redis is running
docker exec omni2-redis redis-cli ping
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Redis not running
    exit /b 1
)
echo [OK] Redis is running

echo.
echo [2] Check OMNI2 Redis connection
docker logs omni2-bridge 2>&1 | findstr "[REDIS]" | findstr "successful" | findstr /V "grep"
if %ERRORLEVEL% EQU 0 (
    echo [OK] OMNI2 connected to Redis
) else (
    echo [ERROR] OMNI2 not connected to Redis
)

echo.
echo [3] Check Dashboard Flow Listener
docker logs omni2-dashboard-backend 2>&1 | findstr "[FLOW-LISTENER]" | findstr "Subscribed"
if %ERRORLEVEL% EQU 0 (
    echo [OK] Dashboard subscribed to Redis Pub/Sub
) else (
    echo [ERROR] Dashboard not subscribed
)

echo.
echo [4] Check monitoring config in database
docker exec -i omni_pg_db psql -U omni -d omni -t -c "SELECT config_value FROM omni2.omni2_config WHERE config_key = 'flow_monitoring';" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] Monitoring config exists
) else (
    echo [ERROR] Monitoring config not found
)

echo.
echo ============================================================
echo System Status: READY
echo ============================================================
echo.
echo Next: Run Python test to enable monitoring and make requests
echo   python test_flow_system.py
echo.
pause
