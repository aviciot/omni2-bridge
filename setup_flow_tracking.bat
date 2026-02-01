@echo off
REM Flow Tracking System - Setup Script
REM Prepares the system for testing

echo ============================================================
echo Flow Tracking System - Setup
echo ============================================================

echo.
echo Step 1: Run Database Migration
echo ============================================================
echo Running phase2_flow_tracking.sql...
psql -h localhost -p 5435 -U omni -d omni -f migrations\phase2_flow_tracking.sql
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Migration failed
    pause
    exit /b 1
)
echo [OK] Migration completed

echo.
echo Step 2: Enable Redis in OMNI2
echo ============================================================
echo Checking .env file...
findstr /C:"REDIS_ENABLED=true" .env >nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] REDIS_ENABLED not set to true in .env
    echo Please add or update: REDIS_ENABLED=true
    echo.
    echo Current Redis settings:
    findstr /C:"REDIS_" .env
    echo.
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i not "%CONTINUE%"=="y" exit /b 1
) else (
    echo [OK] REDIS_ENABLED=true
)

echo.
echo Step 3: Start Redis
echo ============================================================
docker-compose up -d redis
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to start Redis
    pause
    exit /b 1
)
echo [OK] Redis started

echo.
echo Step 4: Restart OMNI2 (to load Redis)
echo ============================================================
docker-compose restart omni2
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to restart OMNI2
    pause
    exit /b 1
)
echo [OK] OMNI2 restarted

echo.
echo Step 5: Check Services
echo ============================================================
timeout /t 5 /nobreak >nul
docker ps --filter "name=omni2" --format "table {{.Names}}\t{{.Status}}"

echo.
echo Step 6: Verify Logs
echo ============================================================
echo Checking OMNI2 logs for Redis connection...
docker logs omni2-bridge 2>&1 | findstr /C:"[REDIS]" | findstr /C:"successful"
if %ERRORLEVEL% EQU 0 (
    echo [OK] Redis connected in OMNI2
) else (
    echo [WARNING] Redis connection not confirmed in logs
)

echo.
echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo Next Steps:
echo 1. Run test script: python test_flow_tracking.py
echo 2. Monitor logs: docker logs -f omni2-bridge ^| findstr FLOW
echo 3. Start Dashboard: cd dashboard ^&^& docker-compose up -d
echo.
echo Useful Commands:
echo - View OMNI2 logs:     docker logs -f omni2-bridge ^| findstr FLOW
echo - View Dashboard logs: docker logs -f omni2-dashboard-backend ^| findstr FLOW
echo - Check Redis:         docker exec -it omni2-redis redis-cli ping
echo.
pause
