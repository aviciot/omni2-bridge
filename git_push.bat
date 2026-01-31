@echo off
echo ============================================
echo OMNI2 - Commit and Push to GitHub
echo ============================================
echo.

REM Add all changes
"C:\Program Files\Git\bin\git.exe" add -A

REM Show status
echo Current changes:
"C:\Program Files\Git\bin\git.exe" status --short

echo.
echo ============================================
echo Committing changes...
echo ============================================

REM Commit with detailed message
"C:\Program Files\Git\bin\git.exe" commit -m "Major Update: Zero-Trust Architecture + WebSocket Support" -m "Security Enhancements:" -m "- OMNI2 complete isolation (no exposed ports)" -m "- Traefik as single authenticated entry point" -m "- ForwardAuth middleware for all requests" -m "- Defense in depth architecture" -m "" -m "WebSocket Features:" -m "- Real-time MCP status updates" -m "- Bidirectional communication" -m "- Token-based authentication" -m "- Debug window in dashboard" -m "" -m "Phase 1 & 2 Complete:" -m "- Circuit breaker with auto-recovery" -m "- MCP coordinator service" -m "- Tool result cache (LRU + TTL)" -m "- WebSocket broadcaster" -m "- Thread-aware logging" -m "" -m "Bug Fixes:" -m "- Database AsyncSessionLocal global variable" -m "- WebSocket library parameter (additional_headers)" -m "- Token storage key (access_token)" -m "- CORS configuration" -m "- Traefik route priority" -m "" -m "Documentation:" -m "- Complete WebSocket guide" -m "- Zero-trust architecture docs" -m "- Updated security overview" -m "- Phase 1 & 2 progress" -m "" -m "See CHANGELOG.md for full details"

echo.
echo ============================================
echo Pushing to GitHub...
echo ============================================

REM Push to main branch
"C:\Program Files\Git\bin\git.exe" push origin main

echo.
echo ============================================
echo Done!
echo ============================================
pause
