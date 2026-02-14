# Auth Service 401 Errors - Complete Guide

## TL;DR (Too Long; Didn't Read)

**The 401 errors are NORMAL** - your auth system is working correctly. We've reduced log noise and added diagnostic tools.

**Quick Fix:**
```bash
cd omni2/auth_service
docker-compose restart
python check_status.py
```

---

## What's Happening?

You're seeing logs like this:
```
INFO: 172.26.0.3:37290 - "GET /api/v1/auth/validate HTTP/1.1" 401 Unauthorized
```

### The Answer

**Traefik** (your reverse proxy) is calling `/api/v1/auth/validate` on **every request** to check if the user is authenticated. The 401 errors mean "user not authenticated" - which is **expected and correct**.

Think of it like a bouncer at a club checking IDs - they turn away people without valid IDs (401), and let in people with valid IDs (200). Both are normal operations.

---

## Files in This Directory

### 📖 Documentation
- **`401_ERRORS_EXPLAINED.md`** - Detailed explanation of the issue
- **`CHANGES_SUMMARY.md`** - Summary of changes made
- **`README_401.md`** - This file (quick reference)

### 🔧 Tools
- **`diagnose_401.py`** - Analyze auth logs and identify patterns
- **`check_status.py`** - Quick health check for auth service

### ⚙️ Configuration
- **`docker-compose.yml`** - Updated with LOG_LEVEL=WARNING

### 📝 Code Changes
- **`routes/auth.py`** - Better error handling in validate endpoint
- **`services/token_service.py`** - Debug-level logging for expected failures

---

## Quick Commands

### Check Status
```bash
# Quick status check
python auth_service/check_status.py

# View live logs (reduced noise now)
docker logs -f mcp-auth-service

# Check health
curl http://localhost:8700/health
```

### Run Diagnostics
```bash
# Full diagnostic report
docker logs mcp-auth-service 2>&1 | python auth_service/diagnose_401.py

# Count 401 vs 200
docker logs mcp-auth-service 2>&1 | grep "auth/validate" | grep -c "401"
docker logs mcp-auth-service 2>&1 | grep "auth/validate" | grep -c "200"
```

### Apply Changes
```bash
# Restart with new settings
cd omni2/auth_service
docker-compose restart

# Or rebuild if needed
docker-compose down
docker-compose build
docker-compose up -d
```

---

## Understanding the Numbers

### ✅ Normal (Healthy)
- **401 rate: 30-50%** - Mix of authenticated and unauthenticated requests
- **200 rate: 50-70%** - Most requests are authenticated
- **No ERROR logs** - System working correctly

### ⚠️ Investigate
- **401 rate: 70-90%** - Possible frontend issue (not sending tokens)
- **Occasional ERRORs** - Check database connection, token validation

### 🚨 Critical
- **401 rate: >90%** - Frontend not sending tokens at all
- **All requests failing** - Auth service or database down
- **Frequent ERRORs** - System malfunction

---

## Common Scenarios

### Scenario 1: "Too many 401 errors!"

**Diagnosis:**
```bash
python auth_service/diagnose_401.py
```

**If 401 rate < 50%:** This is normal, no action needed.

**If 401 rate > 70%:** Check your frontend:
- Is it sending `Authorization: Bearer <token>` header?
- Are tokens expiring too quickly?
- Is token refresh working?

### Scenario 2: "All requests return 401"

**Diagnosis:**
```bash
python auth_service/check_status.py
```

**Possible causes:**
1. Frontend not sending tokens → Fix frontend code
2. Tokens expiring immediately → Check token expiry settings
3. Database issues → Check database connection
4. JWT secret mismatch → Verify JWT_SECRET in config

### Scenario 3: "Service is slow"

**Diagnosis:**
```bash
docker logs mcp-auth-service 2>&1 | grep -i "slow\|timeout\|latency"
```

**Possible causes:**
1. Database connection pool exhausted
2. Too many validation requests
3. Network issues between services

---

## The Flow (Visual)

```
┌──────────────────────────────────────────────────────────────┐
│                         USER REQUEST                          │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ↓
                    ┌───────────────┐
                    │    Traefik    │ (Reverse Proxy)
                    │  172.26.0.3   │
                    └───────┬───────┘
                            │
                            │ ForwardAuth: Check authentication
                            ↓
                ┌───────────────────────┐
                │   Auth Service        │
                │   /api/v1/auth/       │
                │   validate            │
                └───────┬───────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ↓                               ↓
   ┌─────────┐                    ┌─────────┐
   │ 200 OK  │                    │ 401 ✗   │
   │ Valid   │                    │ Invalid │
   │ Token   │                    │ Token   │
   └────┬────┘                    └────┬────┘
        │                               │
        ↓                               ↓
   Forward to                      Block request
   Backend                         Return 401
```

---

## What We Fixed

### 1. Reduced Log Noise ✅
- Changed `LOG_LEVEL=INFO` → `LOG_LEVEL=WARNING`
- Expected auth failures now logged as DEBUG
- Only real errors logged as ERROR

### 2. Added Diagnostics ✅
- `diagnose_401.py` - Analyze patterns in auth logs
- `check_status.py` - Quick health check
- Better error messages in code

### 3. Documentation ✅
- Complete explanation of the issue
- Quick reference guides
- Troubleshooting steps

---

## When to Worry

### Don't Worry About:
- ✅ Individual 401 errors (expected)
- ✅ 401 rate < 50% (normal)
- ✅ Mix of 200 and 401 responses (healthy)
- ✅ Requests from 172.26.0.x (Traefik)

### Do Investigate:
- ⚠️ 401 rate > 70% consistently
- ⚠️ All requests returning 401
- ⚠️ ERROR messages in logs
- ⚠️ Slow response times

### Immediate Action Required:
- 🚨 Auth service down
- 🚨 Database connection errors
- 🚨 All tokens being rejected
- 🚨 Security-related errors

---

## Monitoring Setup

### Recommended Alerts

**High 401 Rate:**
```
Alert if: 401_rate > 70% for 5 minutes
Action: Check frontend token handling
```

**Service Down:**
```
Alert if: No responses for 1 minute
Action: Restart auth service
```

**High Latency:**
```
Alert if: Response time > 1 second
Action: Check database connection
```

### What NOT to Alert On
- ❌ Individual 401 errors
- ❌ 401 rate < 50%
- ❌ Expected authentication failures

---

## Troubleshooting Guide

### Problem: High 401 Rate

**Step 1:** Run diagnostics
```bash
docker logs mcp-auth-service 2>&1 | python auth_service/diagnose_401.py
```

**Step 2:** Check frontend
- Open browser DevTools → Network tab
- Look for requests to your API
- Check if `Authorization: Bearer <token>` header is present

**Step 3:** Test manually
```bash
# Get a token
curl -X POST http://localhost:8700/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin@example.com","password":"admin"}'

# Test validation
curl http://localhost:8700/api/v1/auth/validate \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Problem: All Requests Fail

**Step 1:** Check service status
```bash
python auth_service/check_status.py
```

**Step 2:** Check database
```bash
docker exec -it omni_pg_db psql -U omni -d omni -c "SELECT COUNT(*) FROM auth_service.users;"
```

**Step 3:** Check logs for errors
```bash
docker logs mcp-auth-service 2>&1 | grep -i error
```

### Problem: Slow Performance

**Step 1:** Check database connection pool
```bash
docker logs mcp-auth-service 2>&1 | grep -i "pool\|connection"
```

**Step 2:** Check request volume
```bash
docker logs mcp-auth-service 2>&1 | grep "auth/validate" | wc -l
```

**Step 3:** Increase pool size if needed
```yaml
# In docker-compose.yml
environment:
  - DB_POOL_MAX_SIZE=50  # Increase from 20
```

---

## Next Steps

1. **Apply the changes:**
   ```bash
   cd omni2/auth_service
   docker-compose restart
   ```

2. **Verify it's working:**
   ```bash
   python check_status.py
   ```

3. **Run diagnostics:**
   ```bash
   docker logs mcp-auth-service 2>&1 | python diagnose_401.py
   ```

4. **Monitor for issues:**
   - Watch for 401 rate > 70%
   - Check for ERROR messages
   - Monitor response times

5. **Read detailed docs if needed:**
   - `401_ERRORS_EXPLAINED.md` - Full explanation
   - `CHANGES_SUMMARY.md` - What we changed

---

## Support

If you still have issues:

1. ✅ Run `check_status.py` - Quick health check
2. ✅ Run `diagnose_401.py` - Detailed analysis
3. ✅ Read `401_ERRORS_EXPLAINED.md` - Full documentation
4. ✅ Check frontend token handling
5. ✅ Verify Traefik configuration

---

## Summary

**The 401 errors are NOT a problem** - they're your auth system working correctly.

**What we did:**
- ✅ Reduced log noise (WARNING level)
- ✅ Added diagnostic tools
- ✅ Improved error handling
- ✅ Created documentation

**What you should do:**
- ✅ Restart auth service
- ✅ Run diagnostics
- ✅ Monitor for abnormal patterns
- ✅ Focus on real errors (500s, latency)

**Bottom line:** Your auth system is working. We just made it quieter and easier to diagnose.

---

**Questions?** Check `401_ERRORS_EXPLAINED.md` for detailed answers.
