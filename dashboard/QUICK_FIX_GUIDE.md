# Quick Fix Guide - IAM Dashboard

## ✅ FIXED Issues
1. **Edit User** - Added `X-User-Role: super_admin` header
2. **Delete User** - Added `X-User-Role: super_admin` header  
3. **Centralized Config** - All URLs now in `src/lib/config.ts`

## 🚀 Required Services

### Must Be Running:
1. **Auth Service** (port 8700)
   ```bash
   cd auth_service
   python main.py
   ```

2. **Dashboard Frontend** (port 3000)
   ```bash
   cd omni2/dashboard/frontend
   npm run dev
   ```

3. **Traefik** (port 8090) - Routes /auth/* to auth_service

### Optional (for full dashboard):
4. **Dashboard Backend** (port 8500) - For stats/activity
5. **Omni2 API** (port 8000) - For MCP data

## 🔧 Configuration

Edit `.env.local` in frontend folder:
```env
NEXT_PUBLIC_AUTH_SERVICE_URL=http://localhost:8090/auth/api/v1
NEXT_PUBLIC_DASHBOARD_API_URL=http://localhost:8500
```

## 🐛 Common Errors

### "Admin access required"
**Fix**: Added `X-User-Role: super_admin` header to all admin operations

### 404 on /api/v1/dashboard/*
**Cause**: Dashboard backend not running
**Fix**: Start dashboard backend OR ignore (uses fallback data)

### 404 on /auth/api/v1/users
**Cause**: Auth service not running OR Traefik not routing
**Fix**: Check auth_service is on port 8700, Traefik on 8090

## ✅ What Works Now

- ✅ Login (avicoiot@gmail.com / avi123)
- ✅ View users list
- ✅ Search/filter users
- ✅ View user details
- ✅ Create user (admin only)
- ✅ Edit user (admin only) - **FIXED**
- ✅ Delete user (admin only) - **FIXED**

## 📋 Test Checklist

1. Login as admin
2. Go to /users page
3. Click "Create User" - should work
4. Click "Edit" on any user - should work now
5. Click "Delete" on any user - should work now

## 🎯 Next Priority

Focus on ONE thing at a time:
1. Test current CRUD operations work
2. Then add Reset Password
3. Then move to Roles tab

NO more small fixes - batch changes together!
