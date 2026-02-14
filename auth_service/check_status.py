#!/usr/bin/env python3
"""
Quick Auth Service Status Check
================================
Run this to quickly check if auth service is working properly.
"""

import subprocess
import sys
import re
from datetime import datetime

def run_command(cmd):
    """Run shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout + result.stderr
    except Exception as e:
        return f"Error: {e}"

def check_auth_service():
    """Check auth service status."""
    print("=" * 80)
    print("AUTH SERVICE STATUS CHECK")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. Check if container is running
    print("1. Container Status")
    print("-" * 40)
    output = run_command("docker ps --filter name=mcp-auth-service --format '{{.Status}}'")
    if output.strip():
        print(f"   ✓ Container is running: {output.strip()}")
    else:
        print("   ✗ Container is NOT running!")
        print("   Run: cd auth_service && docker-compose up -d")
        return
    print()
    
    # 2. Check health endpoint
    print("2. Health Check")
    print("-" * 40)
    output = run_command("curl -s http://localhost:8700/health")
    if "healthy" in output.lower() or "ok" in output.lower():
        print("   ✓ Health endpoint responding")
    else:
        print(f"   ⚠ Health endpoint response: {output[:100]}")
    print()
    
    # 3. Check recent logs
    print("3. Recent Activity (last 50 lines)")
    print("-" * 40)
    output = run_command("docker logs --tail 50 mcp-auth-service 2>&1")
    
    # Count validate requests
    validate_lines = [line for line in output.split('\n') if 'auth/validate' in line]
    count_401 = len([line for line in validate_lines if '401' in line])
    count_200 = len([line for line in validate_lines if '200' in line])
    total = count_401 + count_200
    
    if total > 0:
        print(f"   Validate requests: {total}")
        print(f"   - 200 OK: {count_200} ({count_200/total*100:.1f}%)")
        print(f"   - 401 Unauthorized: {count_401} ({count_401/total*100:.1f}%)")
        
        if count_401 / total > 0.7:
            print("   ⚠ High 401 rate - check frontend token handling")
        else:
            print("   ✓ Normal 401 rate")
    else:
        print("   No validate requests in recent logs")
    print()
    
    # 4. Check for errors
    print("4. Error Check")
    print("-" * 40)
    error_lines = [line for line in output.split('\n') if 'ERROR' in line.upper()]
    if error_lines:
        print(f"   ⚠ Found {len(error_lines)} error(s) in recent logs:")
        for line in error_lines[-3:]:  # Show last 3 errors
            print(f"     {line[:100]}")
    else:
        print("   ✓ No errors in recent logs")
    print()
    
    # 5. Check database connection
    print("5. Database Connection")
    print("-" * 40)
    if "database" in output.lower() and "error" in output.lower():
        print("   ✗ Database connection issues detected")
    else:
        print("   ✓ No database errors detected")
    print()
    
    # 6. Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if total > 0 and count_401 / total < 0.7 and not error_lines:
        print("✓ Auth service is working normally")
        print()
        print("The 401 errors you see are EXPECTED - they indicate:")
        print("  - Unauthenticated requests being blocked (correct behavior)")
        print("  - Traefik ForwardAuth doing its job")
        print()
        print("No action needed unless:")
        print("  - 401 rate exceeds 70%")
        print("  - You see ERROR messages")
        print("  - Service is not responding")
    else:
        print("⚠ Issues detected - review the output above")
        print()
        print("Common fixes:")
        print("  1. Restart service: cd auth_service && docker-compose restart")
        print("  2. Check logs: docker logs -f mcp-auth-service")
        print("  3. Run diagnostics: docker logs mcp-auth-service 2>&1 | python diagnose_401.py")
    
    print()
    print("For detailed analysis, run:")
    print("  docker logs mcp-auth-service 2>&1 | python auth_service/diagnose_401.py")
    print("=" * 80)

if __name__ == "__main__":
    try:
        check_auth_service()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError running status check: {e}")
        sys.exit(1)
