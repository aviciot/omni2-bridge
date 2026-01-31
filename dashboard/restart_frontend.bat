@echo off
echo Restarting Dashboard Frontend...
echo.

cd /d "C:\Users\acohen.SHIFT4CORP\Desktop\PythonProjects\MCP Performance\omni2\dashboard\frontend"

echo Killing existing process on port 3001...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3001') do taskkill /F /PID %%a 2>nul

echo.
echo Starting dev server...
echo Press Ctrl+C to stop
echo.

npm run dev
