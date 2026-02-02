# Auth Service Errors Fixed

## Summary
Fixed schema mismatches between code and SCHEMA.sql

## Errors Fixed

### 1. audit_service.py - Wrong Column Names
**Problem:** Function used `result` and `resource` columns that don't exist in `auth_service.auth_audit` table

**Schema (SCHEMA.sql):**
```sql
CREATE TABLE auth_service.auth_audit (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    username VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- NOT 'result'
    ip_address VARCHAR(45),
    user_agent TEXT,
    details TEXT,  -- NOT JSONB, just TEXT
    created_at TIMESTAMP
);
```

**Fixed:**
- Changed `result` → `status`
- Removed `resource` parameter
- Changed `details` from `Dict` → `str`
- Added missing `user_agent` parameter
- Fixed table name to include schema: `auth_service.auth_audit`

### 2. routes/users.py - Wrong Column in Query
**Problem:** `get_user_activity()` queried non-existent columns

**Fixed:**
```python
# BEFORE (WRONG)
SELECT id, user_id, username, action, resource, result, ...

# AFTER (CORRECT)
SELECT id, user_id, username, action, status, ...
```

### 3. routes/api_keys.py - Wrong audit_log Calls
**Problem:** Passed `details` as dict instead of string

**Fixed:**
```python
# BEFORE (WRONG)
await audit_log(..., details={"name": request.name, ...})

# AFTER (CORRECT)
await audit_log(..., details=f"name={request.name}, ...")
```

### 4. routes/auth.py - Wrong audit_log Calls
**Problem:** Same issue - passed dict instead of string

**Fixed:**
```python
# BEFORE (WRONG)
await audit_log(..., details={"reason": "invalid_api_key"})

# AFTER (CORRECT)
await audit_log(..., details="invalid_api_key")
```

## Root Cause
Code was not aligned with SCHEMA.sql which is the single source of truth.

## Verification Needed
Run these to verify fixes:
```bash
cd auth_service
python -m pytest test/test_full.py -v
```

## Files Modified
1. `services/audit_service.py` - Fixed function signature and SQL
2. `routes/users.py` - Fixed query columns
3. `routes/api_keys.py` - Fixed audit_log calls (2 places)
4. `routes/auth.py` - Fixed audit_log calls (2 places)
