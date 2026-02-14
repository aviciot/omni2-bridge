# TRAEFIK ENFORCEMENT IMPLEMENTATION PLAN
## Baby Steps with Verification

### 🎯 **OBJECTIVE**
Ensure ALL communication with OMNI2 goes through Traefik, establish single source of truth for URLs, and verify each step works before proceeding.

---

## 📋 **PHASE 1: Configuration Cleanup**

### Step 1.1: Remove Dangerous Direct URL Config
**Files to modify:**
- `dashboard/backend/app/config.py` ✅ DONE

**Changes:**
- Remove `OMNI2_DIRECT_URL` 
- Add `TRAEFIK_BASE_URL` as single source of truth
- Add helper properties for URL generation

**Verification:**
```bash
# Check logs for any errors
docker-compose logs dashboard-backend | grep -i error
docker-compose logs omni2 | grep -i error
docker-compose logs traefik-external | grep -i error
```

### Step 1.2: Update Environment Files
**Files to modify:**
- `dashboard/backend/.env` ✅ DONE

**Changes:**
- Add `TRAEFIK_BASE_URL=http://host.docker.internal:8090`

**Verification:**
```bash
# Restart dashboard backend and check it starts properly
docker-compose restart dashboard-backend
docker-compose logs dashboard-backend --tail=20

# MANDATORY: Run integration test
python test_system_integration.py
```

---

## 📋 **PHASE 2: Router Updates (One by One)**

### Step 2.1: Update IAM Router
**Files to modify:**
- `dashboard/backend/app/routers/iam.py` ✅ DONE

**Changes:**
- Replace hardcoded URLs with `settings.omni2_api_url`
- Replace hardcoded auth URLs with `settings.auth_service_url`

**Verification:**
```bash
# Test IAM endpoints
curl -H "Authorization: Bearer <token>" http://localhost:8500/api/v1/roles
# Check logs
docker-compose logs dashboard-backend | grep -i iam
docker-compose logs traefik-external | grep -i "api/v1"

# MANDATORY: Run integration test
python test_system_integration.py
```

### Step 2.2: Update MCP Router
**Files to modify:**
- `dashboard/backend/app/routers/mcp.py` ✅ DONE

**Changes:**
- Replace all hardcoded URLs with `settings.omni2_api_url`

**Verification:**
```bash
# Test MCP endpoints
curl -H "Authorization: Bearer <token>" http://localhost:8500/api/v1/mcp/tools/servers
# Check logs
docker-compose logs dashboard-backend | grep -i mcp
docker-compose logs omni2 | grep -i mcp
```

### Step 2.3: Update Events Router
**Files to modify:**
- `dashboard/backend/app/routers/events.py` ✅ DONE

**Changes:**
- Replace hardcoded URL with `settings.omni2_api_url`

**Verification:**
```bash
# Test events endpoints
curl -H "Authorization: Bearer <token>" http://localhost:8500/api/v1/events/metadata
# Check logs
docker-compose logs dashboard-backend | grep -i events
```

### Step 2.4: Update Chat Router
**Files to modify:**
- `dashboard/backend/app/routers/chat.py` ✅ DONE

**Changes:**
- Replace hardcoded URL with `settings.omni2_api_url`

**Verification:**
```bash
# Test chat streaming
curl -H "Authorization: Bearer <token>" http://localhost:8500/api/v1/chat/stream
# Check logs
docker-compose logs dashboard-backend | grep -i chat
```

### Step 2.5: Update WebSocket Router
**Files to modify:**
- `dashboard/backend/app/routers/websocket.py` ✅ DONE

**Changes:**
- Replace hardcoded URLs with `settings.omni2_ws_url`

**Verification:**
```bash
# Test WebSocket connection
# Use browser dev tools or WebSocket test client
# Check logs
docker-compose logs dashboard-backend | grep -i websocket
docker-compose logs omni2 | grep -i websocket
```

---

## 📋 **PHASE 3: Comprehensive Testing**

### Step 3.1: Run Security Validation
**Command:**
```bash
python validate_security_config.py
```

**Expected Result:**
- No HIGH severity issues
- Minimal MEDIUM severity issues

### Step 3.2: Run Traefik Enforcement Test
**Command:**
```bash
python test_traefik_enforcement.py
```

**Expected Result:**
- All tests pass
- Direct OMNI2 access blocked
- Traefik routing works
- Auth headers forwarded correctly

### Step 3.3: Manual Log Verification
**Check all service logs:**
```bash
# Traefik logs - should show requests coming through
docker-compose -f traefik-external/docker-compose.yml logs traefik-external --tail=50

# Auth service logs - should show token validation
docker-compose -f auth_service/docker-compose.yml logs auth-service --tail=50

# OMNI2 logs - should show requests with auth headers
docker-compose logs omni2 --tail=50

# Dashboard backend logs - should show successful proxying
docker-compose logs dashboard-backend --tail=50
```

---

## 📋 **PHASE 4: OMNI2 Trust Policy (Future)**

### Step 4.1: Configure OMNI2 to Only Trust Traefik
**Files to modify:**
- `app/main.py` (add middleware to validate requests come from Traefik)

### Step 4.2: Network Isolation
**Files to modify:**
- `docker-compose.yml` (ensure OMNI2 port 8000 is not exposed)

---

## 🔧 **VERIFICATION COMMANDS**

### Quick Health Check
```bash
# Check all services are running
docker-compose ps

# Check Traefik dashboard
curl http://localhost:8091/dashboard/

# Check auth service health
curl http://localhost:8090/auth/health

# Check OMNI2 health via Traefik
curl http://localhost:8090/health
```

### Log Monitoring During Tests
```bash
# Terminal 1: Traefik logs
docker-compose -f traefik-external/docker-compose.yml logs -f traefik-external

# Terminal 2: Auth service logs  
docker-compose -f auth_service/docker-compose.yml logs -f auth-service

# Terminal 3: OMNI2 logs
docker-compose logs -f omni2

# Terminal 4: Dashboard backend logs
docker-compose logs -f dashboard-backend
```

### Test Request Flow
```bash
# 1. Get auth token
TOKEN=$(curl -s -X POST http://localhost:8090/auth/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"avicoiot@gmail.com","password":"admin123"}' | \
  jq -r '.access_token')

# 2. Test protected endpoint via dashboard backend
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8500/api/v1/mcp/tools/servers

# 3. Test direct via Traefik
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8090/api/v1/mcp/tools/servers
```

---

## 🚨 **ROLLBACK PLAN**

If any step breaks the system:

1. **Immediate rollback:**
   ```bash
   git checkout HEAD~1 -- <modified-file>
   docker-compose restart <affected-service>
   ```

2. **Check logs for errors:**
   ```bash
   docker-compose logs <service> --tail=100
   ```

3. **Verify basic functionality:**
   ```bash
   curl http://localhost:8090/health
   ```

---

## 📝 **SUCCESS CRITERIA**

### Phase 1 Complete When:
- [ ] No `OMNI2_DIRECT_URL` in codebase
- [ ] `TRAEFIK_BASE_URL` configured in all env files
- [ ] All services start without errors

### Phase 2 Complete When:
- [ ] All routers use centralized configuration
- [ ] No hardcoded URLs in router files
- [ ] All endpoints respond correctly via dashboard backend

### Phase 3 Complete When:
- [ ] Security validation passes
- [ ] Traefik enforcement test passes
- [ ] Manual testing confirms proper request flow
- [ ] All logs show requests going through Traefik → Auth → OMNI2

### Overall Success When:
- [ ] Direct OMNI2 access (port 8000) is blocked
- [ ] All requests go through Traefik (port 8090)
- [ ] Auth headers are properly forwarded
- [ ] No security bypasses detected
- [ ] System is stable and performant