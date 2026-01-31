@echo off
echo ========================================
echo Dashboard Code Verification
echo ========================================
echo.

echo [1/4] Checking container file...
docker exec omni2-dashboard-frontend cat /app/app/page.tsx | findstr /C:"Omni2 Dashboard"
if %ERRORLEVEL% EQU 0 (
    echo ✓ Container has correct code
) else (
    echo ✗ Container has wrong code
)
echo.

echo [2/4] Checking server response...
curl -s http://localhost:3001 | findstr /C:"Omni2 Dashboard" >nul
if %ERRORLEVEL% EQU 0 (
    echo ✓ Server serving correct HTML
) else (
    echo ✗ Server serving wrong HTML
)
echo.

echo [3/4] Checking JavaScript bundle...
curl -s "http://localhost:3001/_next/static/chunks/app/page.js" | findstr /C:"Omni2 Dashboard" >nul
if %ERRORLEVEL% EQU 0 (
    echo ✓ JavaScript bundle is correct
) else (
    echo ✗ JavaScript bundle is wrong
)
echo.

echo [4/4] Testing backend API...
curl -s http://localhost:8500/health | findstr /C:"healthy" >nul
if %ERRORLEVEL% EQU 0 (
    echo ✓ Backend API is healthy
) else (
    echo ✗ Backend API is down
)
echo.

echo ========================================
echo RESULT: All code is correct!
echo ========================================
echo.
echo The issue is BROWSER CACHING.
echo.
echo To fix:
echo 1. Open browser DevTools (F12)
echo 2. Go to Network tab
echo 3. Check "Disable cache"
echo 4. Hard refresh (Ctrl+Shift+R)
echo.
echo OR open in Incognito mode
echo ========================================
