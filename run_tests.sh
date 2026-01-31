#!/bin/bash
# OMNI2 Validation Test Runner
# Run this script to validate all Phase 1 changes

echo "🚀 OMNI2 Phase 1 Validation Suite"
echo "=================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.8+"
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python3 -c "import asyncpg, httpx, sqlalchemy" 2>/dev/null || {
    echo "⚠️  Installing required packages..."
    pip install asyncpg httpx sqlalchemy[asyncio] pytest
}

# Run the validation tests
echo "🧪 Running validation tests..."
python3 test_validation.py

echo ""
echo "✅ Validation complete!"
echo "Check the results above for any issues that need attention."