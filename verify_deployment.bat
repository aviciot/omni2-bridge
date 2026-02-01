@echo off
echo ============================================================
echo Flow Tracking System - Deployment Verification
echo ============================================================

echo.
echo Step 1: Check OMNI2 Status
echo ============================================================
docker logs --tail 5 omni2-bridge 2>&1 | findstr "Ready"
if %ERRORLEVEL% EQU 0 (
    echo [OK] OMNI2 is running
) else (
    echo [WARN] OMNI2 may not be ready
)

echo.
echo Step 2: Check Redis Connection in OMNI2
echo ============================================================
docker logs omni2-bridge 2>&1 | findstr "[REDIS]" | findstr "successful"
if %ERRORLEVEL% EQU 0 (
    echo [OK] OMNI2 connected to Redis
) else (
    echo [ERROR] OMNI2 not connected to Redis
)

echo.
echo Step 3: Check Dashboard Status
echo ============================================================
docker logs --tail 5 omni2-dashboard-backend 2>&1 | findstr "startup complete"
if %ERRORLEVEL% EQU 0 (
    echo [OK] Dashboard is running
) else (
    echo [WARN] Dashboard may not be ready
)

echo.
echo Step 4: Check Flow Listener
echo ============================================================
docker logs omni2-dashboard-backend 2>&1 | findstr "[FLOW-LISTENER]" | findstr "Subscribed"
if %ERRORLEVEL% EQU 0 (
    echo [OK] Flow Listener subscribed to Redis
) else (
    echo [ERROR] Flow Listener not subscribed
)

echo.
echo Step 5: Check Database Migration
echo ============================================================
docker exec -i omni_pg_db psql -U omni -d omni -c "SELECT COUNT(*) FROM omni2.interaction_flows;" 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [OK] interaction_flows table exists
) else (
    echo [ERROR] interaction_flows table not found
)

echo.
echo Step 6: Check Monitoring Config
echo ============================================================
docker exec -i omni_pg_db psql -U omni -d omni -c "SELECT config_key FROM omni2.omni2_config WHERE config_key = 'flow_monitoring';" 2>nul | findstr "flow_monitoring"
if %ERRORLEVEL% EQU 0 (
    echo [OK] flow_monitoring config exists
) else (
    echo [ERROR] flow_monitoring config not found
)

echo.
echo ============================================================
echo Deployment Status Summary
echo ============================================================
echo.
echo Services Running:
docker ps --filter "name=omni2" --format "  - {{.Names}}: {{.Status}}"
echo.
echo Next Steps:
echo 1. Enable monitoring: curl -X POST "http://localhost:8090/api/v1/monitoring/enable/123?ttl_hours=1"
echo 2. Make test request with user 123
echo 3. Watch logs: docker logs -f omni2-bridge ^| findstr FLOW
echo.
pause
