@echo off
echo Clearing Next.js cache...
docker exec omni2-dashboard-frontend rm -rf /app/.next/dev/* 2>nul
docker exec omni2-dashboard-frontend rm -rf /app/.next/cache/* 2>nul
echo Restarting frontend...
docker restart omni2-dashboard-frontend
echo Done! Wait 30 seconds then refresh browser.
