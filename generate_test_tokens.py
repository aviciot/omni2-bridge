"""
Generate JWT tokens for testing WebSocket authentication
"""

import jwt
from datetime import datetime, timedelta
import sys

# Secret key from .env (default value)
SECRET_KEY = "change-this-in-production"

def generate_token(email: str, role: str, hours: int = 1):
    """Generate a JWT token"""
    payload = {
        "sub": email,
        "email": email,
        "role": role,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=hours)
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def main():
    print("\n" + "="*80)
    print("JWT TOKEN GENERATOR FOR WEBSOCKET TESTING")
    print("="*80)
    
    # Generate admin token
    admin_token = generate_token("admin@company.com", "admin", hours=24)
    print("\n[OK] ADMIN TOKEN (valid for 24 hours):")
    print(f"   Email: admin@company.com")
    print(f"   Role: admin")
    print(f"   Token: {admin_token}")
    
    # Generate developer token
    dev_token = generate_token("developer@company.com", "developer", hours=24)
    print("\n[OK] DEVELOPER TOKEN (valid for 24 hours):")
    print(f"   Email: developer@company.com")
    print(f"   Role: developer")
    print(f"   Token: {dev_token}")
    
    # Generate DBA token
    dba_token = generate_token("dba@company.com", "dba", hours=24)
    print("\n[OK] DBA TOKEN (valid for 24 hours):")
    print(f"   Email: dba@company.com")
    print(f"   Role: dba")
    print(f"   Token: {dba_token}")
    
    # Generate read_only token (should be rejected)
    readonly_token = generate_token("readonly@company.com", "read_only", hours=24)
    print("\n[REJECT] READ_ONLY TOKEN (should be REJECTED - insufficient permissions):")
    print(f"   Email: readonly@company.com")
    print(f"   Role: read_only")
    print(f"   Token: {readonly_token}")
    
    # Generate expired token
    expired_payload = {
        "sub": "expired@company.com",
        "email": "expired@company.com",
        "role": "admin",
        "iat": datetime.utcnow() - timedelta(hours=2),
        "exp": datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
    }
    expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm="HS256")
    print("\n[REJECT] EXPIRED TOKEN (should be REJECTED):")
    print(f"   Email: expired@company.com")
    print(f"   Role: admin")
    print(f"   Token: {expired_token}")
    
    print("\n" + "="*80)
    print("USAGE INSTRUCTIONS")
    print("="*80)
    print("\n1. Copy one of the tokens above")
    print("\n2. Test in browser console:")
    print("   const token = 'PASTE_TOKEN_HERE';")
    print("   const ws = new WebSocket(`ws://localhost:8000/ws/mcp-status?token=${token}`);")
    print("   ws.onopen = () => console.log('Connected!');")
    print("   ws.onmessage = (e) => console.log('Message:', JSON.parse(e.data));")
    print("   ws.onclose = (e) => console.log('Closed:', e.code, e.reason);")
    
    print("\n3. Or update test_websocket_auth.py:")
    print("   VALID_TOKEN = 'PASTE_ADMIN_TOKEN_HERE'")
    print("   python test_websocket_auth.py")
    
    print("\n" + "="*80)
    print("EXPECTED RESULTS")
    print("="*80)
    print("[OK] Admin token: Connection accepted")
    print("[OK] Developer token: Connection accepted")
    print("[OK] DBA token: Connection accepted")
    print("[REJECT] Read_only token: Connection rejected (insufficient permissions)")
    print("[REJECT] Expired token: Connection rejected (expired)")
    print("[REJECT] Invalid token: Connection rejected (invalid)")
    print("[REJECT] No token: Connection rejected (authentication required)")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        print("\nMake sure PyJWT is installed:")
        print("  pip install pyjwt")
        sys.exit(1)
