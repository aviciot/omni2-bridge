@echo off
REM OMNI2 Validation Test Runner for Windows
REM Run this script to validate all Phase 1 changes

echo 🚀 OMNI2 Phase 1 Validation Suite
echo ==================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.8+
    pause
    exit /b 1
)

REM Check if required packages are installed
echo 📦 Checking dependencies...
python -c "import asyncpg, httpx, sqlalchemy" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Installing required packages...
    pip install asyncpg httpx sqlalchemy[asyncio] pytest
)

REM Run the validation tests
echo 🧪 Running validation tests...
python test_validation.py

echo.
echo ✅ Validation complete!
echo Check the results above for any issues that need attention.
pause