@echo off
echo ========================================
echo Clean Rebuild Frontend
echo ========================================

cd omni2\dashboard\frontend

echo.
echo [1/4] Removing .next folder...
if exist .next (
    rmdir /s /q .next
    echo ✓ .next removed
) else (
    echo ✓ .next already clean
)

echo.
echo [2/4] Stopping Docker containers...
cd ..\..
docker-compose down
echo ✓ Containers stopped

echo.
echo [3/4] Rebuilding frontend container...
docker-compose build omni2-dashboard-frontend
echo ✓ Frontend rebuilt

echo.
echo [4/4] Starting all containers...
docker-compose up -d
echo ✓ Containers started

echo.
echo ========================================
echo ✓ Clean rebuild complete!
echo ========================================
echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak

echo.
echo Checking service status...
docker-compose ps

echo.
echo Frontend should be available at: http://localhost:3000
echo Dashboard backend at: http://localhost:8001
echo.
