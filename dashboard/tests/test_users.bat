@echo off
REM Users API Test Runner
REM Tests all user management endpoints

echo ========================================
echo Users API Test Suite
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found
    exit /b 1
)

REM Check if requests library is installed
python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo Installing requests library...
    pip install requests
)

REM Run tests
echo Running tests...
echo.
python test_users_api.py

REM Capture exit code
set TEST_EXIT_CODE=%ERRORLEVEL%

echo.
echo ========================================
if %TEST_EXIT_CODE% EQU 0 (
    echo RESULT: ALL TESTS PASSED
) else (
    echo RESULT: SOME TESTS FAILED
)
echo ========================================

exit /b %TEST_EXIT_CODE%
