"""
Diagnostic Script for 401 Errors on /api/v1/auth/validate
==========================================================

This script helps identify:
1. Who is calling the validate endpoint (IP addresses)
2. What requests are failing (missing/invalid tokens)
3. Patterns in the 401 errors

Run this to analyze your auth service logs.
"""

import re
from collections import Counter, defaultdict
from datetime import datetime

def parse_auth_logs(log_file_path=None):
    """
    Parse auth service logs to identify 401 patterns.
    
    If log_file_path is None, reads from stdin (pipe docker logs to this script).
    """
    
    # Patterns to match
    validate_pattern = re.compile(r'(\d+\.\d+\.\d+\.\d+):(\d+) - "GET /api/v1/auth/validate HTTP/1\.1" (\d+)')
    
    # Counters
    ip_counter = Counter()
    status_counter = Counter()
    hourly_401 = defaultdict(int)
    hourly_200 = defaultdict(int)
    
    total_requests = 0
    
    print("=" * 80)
    print("AUTH SERVICE 401 DIAGNOSTIC REPORT")
    print("=" * 80)
    print()
    
    # Read logs
    if log_file_path:
        with open(log_file_path, 'r') as f:
            lines = f.readlines()
    else:
        import sys
        print("Reading from stdin... (Ctrl+C to stop)")
        print("Usage: docker logs mcp-auth-service 2>&1 | python diagnose_401.py")
        print()
        lines = sys.stdin.readlines()
    
    # Parse each line
    for line in lines:
        match = validate_pattern.search(line)
        if match:
            ip = match.group(1)
            port = match.group(2)
            status = match.group(3)
            
            total_requests += 1
            ip_counter[ip] += 1
            status_counter[status] += 1
            
            # Extract hour if timestamp present
            timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}):', line)
            if timestamp_match:
                hour = timestamp_match.group(1)
                if status == "401":
                    hourly_401[hour] += 1
                elif status == "200":
                    hourly_200[hour] += 1
    
    # Print results
    print(f"Total /api/v1/auth/validate requests: {total_requests}")
    print()
    
    print("STATUS CODE BREAKDOWN:")
    print("-" * 40)
    for status, count in sorted(status_counter.items()):
        percentage = (count / total_requests * 100) if total_requests > 0 else 0
        status_name = "OK" if status == "200" else "UNAUTHORIZED"
        print(f"  {status} {status_name:15} {count:6} ({percentage:.1f}%)")
    print()
    
    print("TOP CALLERS (by IP):")
    print("-" * 40)
    for ip, count in ip_counter.most_common(10):
        percentage = (count / total_requests * 100) if total_requests > 0 else 0
        print(f"  {ip:15} {count:6} requests ({percentage:.1f}%)")
    print()
    
    # Identify the caller
    print("WHO IS CALLING?")
    print("-" * 40)
    top_ip = ip_counter.most_common(1)[0][0] if ip_counter else None
    if top_ip:
        if top_ip.startswith("172."):
            print(f"  Primary caller: {top_ip} (Docker internal network)")
            print(f"  This is likely: Traefik ForwardAuth middleware")
            print()
            print("  EXPLANATION:")
            print("  - Traefik is configured to validate ALL requests to protected endpoints")
            print("  - It calls /api/v1/auth/validate before forwarding requests")
            print("  - 401 errors are EXPECTED when:")
            print("    * No Authorization header is sent")
            print("    * Token is expired")
            print("    * Token is invalid")
            print("    * User tries to access protected endpoint without login")
        else:
            print(f"  Primary caller: {top_ip}")
    print()
    
    # Hourly breakdown
    if hourly_401 or hourly_200:
        print("HOURLY BREAKDOWN:")
        print("-" * 40)
        all_hours = sorted(set(list(hourly_401.keys()) + list(hourly_200.keys())))
        for hour in all_hours[-10:]:  # Last 10 hours
            count_401 = hourly_401.get(hour, 0)
            count_200 = hourly_200.get(hour, 0)
            total = count_401 + count_200
            ratio = (count_401 / total * 100) if total > 0 else 0
            print(f"  {hour}:xx  200={count_200:4}  401={count_401:4}  (401 rate: {ratio:.1f}%)")
        print()
    
    # Recommendations
    print("RECOMMENDATIONS:")
    print("-" * 40)
    
    if status_counter.get("401", 0) > status_counter.get("200", 0):
        print("  ⚠️  HIGH 401 RATE DETECTED")
        print()
        print("  Possible causes:")
        print("  1. Frontend not sending Authorization header")
        print("  2. Tokens expiring too quickly")
        print("  3. Users not logged in trying to access protected endpoints")
        print("  4. Token refresh not working properly")
        print()
        print("  Actions to take:")
        print("  - Check frontend: Is it sending 'Authorization: Bearer <token>' header?")
        print("  - Check token expiry settings in auth_service")
        print("  - Implement automatic token refresh in frontend")
        print("  - Add public endpoints to Traefik config (no auth required)")
    else:
        print("  ✓ 401 rate is normal (expected for unauthenticated requests)")
        print()
        print("  The 401 errors you see are EXPECTED behavior:")
        print("  - Traefik validates every request")
        print("  - Public/unauthenticated requests will return 401")
        print("  - This is not an error - it's the auth system working correctly")
    
    print()
    print("  To reduce log noise:")
    print("  1. Set LOG_LEVEL=WARNING in auth_service (already done)")
    print("  2. Configure Traefik to skip auth for public endpoints")
    print("  3. Filter out 401s from monitoring alerts")
    print()
    
    print("=" * 80)


if __name__ == "__main__":
    import sys
    
    # Check if file path provided
    if len(sys.argv) > 1:
        parse_auth_logs(sys.argv[1])
    else:
        parse_auth_logs()
