# IAM Dashboard - Implementation Plan

## Overview
Build IAM (Identity & Access Management) tab in dashboard to manage users, roles, and teams.

**Backend:** auth_service (already complete with 23 API endpoints)  
**Frontend:** Dashboard React app (needs IAM tab)

---

## Phase 1: Users Management (Read-Only)

**Goal:** Display users list with search/filter

### Backend (Already Done ✅)
```
GET /auth/api/v1/users              - List users (pagination, search, filters)
GET /auth/api/v1/users/{id}         - Get user details
GET /auth/api/v1/roles              - List roles (for dropdown)
```

### Frontend (To Build)
**File:** `dashboard/frontend/src/app/iam/users/page.tsx`

**Components:**
1. **UsersTable** - Display users with columns:
   - Username
   - Email
   - Role (badge with color)
   - Status (active/inactive badge)
   - Last Login
   - Actions (view details)

2. **SearchBar** - Search by username/email

3. **FilterBar** - Filter by:
   - Role (dropdown)
   - Status (active/inactive)

4. **UserDetailsModal** - Show user details:
   - Basic info (username, email, name)
   - Role info (role name, mcp_access, rate_limit)
   - Last login
   - Created date

**API Calls:**
```typescript
// Fetch users
const response = await fetch('http://localhost:8090/auth/api/v1/users', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// Fetch roles for filter
const roles = await fetch('http://localhost:8090/auth/api/v1/roles', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

**Test:**
```bash
# After implementation
# 1. Login to dashboard (localhost:3001)
# 2. Navigate to IAM > Users
# 3. Verify users list displays
# 4. Test search (type "avi")
# 5. Test filter (select "super_admin" role)
# 6. Click user row → verify details modal opens
```

---

## Phase 2: Users Management (CRUD)

**Goal:** Create, edit, delete users + reset password

### Backend (Already Done ✅)
```
POST   /auth/api/v1/users                    - Create user
PUT    /auth/api/v1/users/{id}               - Update user
DELETE /auth/api/v1/users/{id}               - Delete user
POST   /auth/api/v1/users/{id}/reset-password - Reset password
```

### Frontend (To Build)

**1. Create User Modal**
- Form fields:
  - Username (required)
  - Email (required)
  - Name (required)
  - Role (dropdown, required)
  - Password (required, min 8 chars)
- Validation
- Success/error toast

**2. Edit User Modal**
- Same fields as create (except password)
- Pre-fill with current values
- Update button

**3. Delete Confirmation Modal**
- Show user details
- Confirm button (red, dangerous)
- Cancel button

**4. Reset Password Modal**
- Generates temporary password
- Display temp password (copy button)
- User must change on first login

**API Calls:**
```typescript
// Create user
await fetch('http://localhost:8090/auth/api/v1/users', {
  method: 'POST',
  headers: { 
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    username: 'newuser',
    email: 'new@example.com',
    name: 'New User',
    role_id: 2,
    password: 'password123'
  })
});

// Update user
await fetch(`http://localhost:8090/auth/api/v1/users/${userId}`, {
  method: 'PUT',
  headers: { 
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'Updated Name',
    role_id: 3
  })
});

// Delete user
await fetch(`http://localhost:8090/auth/api/v1/users/${userId}`, {
  method: 'DELETE',
  headers: { 'Authorization': `Bearer ${token}` }
});

// Reset password
await fetch(`http://localhost:8090/auth/api/v1/users/${userId}/reset-password`, {
  method: 'POST',
  headers: { 'Authorization': `Bearer ${token}` }
});
```

**Test:**
```bash
# After implementation
# 1. Click "Create User" button
# 2. Fill form, submit → verify user appears in list
# 3. Click edit icon → modify name → verify update
# 4. Click reset password → verify temp password shown
# 5. Click delete icon → confirm → verify user removed
```

---

## File Structure

```
dashboard/frontend/src/app/iam/
├── layout.tsx                    - IAM layout (tabs: Users, Roles, Teams)
├── users/
│   ├── page.tsx                  - Users list page
│   ├── components/
│   │   ├── UsersTable.tsx        - Table component
│   │   ├── UserDetailsModal.tsx  - View details
│   │   ├── CreateUserModal.tsx   - Create form
│   │   ├── EditUserModal.tsx     - Edit form
│   │   ├── DeleteUserModal.tsx   - Delete confirmation
│   │   └── ResetPasswordModal.tsx - Reset password
│   └── hooks/
│       └── useUsers.ts           - API calls hook
```

---

## Auth Service Endpoints Reference

### Users (7 endpoints)
```
GET    /auth/api/v1/users                    - List (pagination, search, filters)
GET    /auth/api/v1/users/{id}               - Get one
POST   /auth/api/v1/users                    - Create
PUT    /auth/api/v1/users/{id}               - Update
DELETE /auth/api/v1/users/{id}               - Delete
POST   /auth/api/v1/users/{id}/reset-password - Reset password
GET    /auth/api/v1/users/{id}/activity      - Activity log
```

### Roles (5 endpoints)
```
GET    /auth/api/v1/roles                    - List all
GET    /auth/api/v1/roles/{id}               - Get one
POST   /auth/api/v1/roles                    - Create
PUT    /auth/api/v1/roles/{id}               - Update
DELETE /auth/api/v1/roles/{id}               - Delete
```

### Teams (7 endpoints)
```
GET    /auth/api/v1/teams                    - List all
GET    /auth/api/v1/teams/{id}               - Get one (with members)
POST   /auth/api/v1/teams                    - Create
PUT    /auth/api/v1/teams/{id}               - Update
DELETE /auth/api/v1/teams/{id}               - Delete
POST   /auth/api/v1/teams/{id}/members/{user_id} - Add member
DELETE /auth/api/v1/teams/{id}/members/{user_id} - Remove member
```

### Permissions (2 endpoints)
```
GET    /auth/api/v1/permissions/{user_id}    - Get effective permissions
GET    /auth/api/v1/permissions/check/{user_id}/{mcp}/{tool} - Check specific
```

---

## Default Roles (From auth_service)

| Role | MCP Access | Dashboard | Rate Limit | Cost Limit |
|------|-----------|-----------|------------|------------|
| super_admin | All (*) | admin | 10000/hr | $1000/day |
| developer | database_mcp, macgyver_mcp, informatica_mcp | view | 5000/hr | $100/day |
| analyst | database_mcp | view | 1000/hr | $50/day |
| viewer | None | view | 100/hr | $10/day |

---

## Success Criteria

**Phase 1 Complete:**
- ✅ Users list displays with all columns
- ✅ Search works (username/email)
- ✅ Filter works (role, status)
- ✅ User details modal shows complete info
- ✅ No errors in console

**Phase 2 Complete:**
- ✅ Can create new user
- ✅ Can edit existing user
- ✅ Can delete user (with confirmation)
- ✅ Can reset password (shows temp password)
- ✅ All operations show success/error feedback
- ✅ Table refreshes after operations

---

## Next Phases (After Phase 1 & 2)

**Phase 3:** Roles Management (list, create, edit, delete roles)  
**Phase 4:** Teams Management (list, create, edit, delete teams, manage members)  
**Phase 5:** Permissions View (show effective permissions per user)

---

## Notes

- All backend APIs already exist and tested (12/12 pass)
- Dashboard login already works (5/5 pass)
- Focus on frontend React components only
- Use existing auth token from login
- Follow existing dashboard patterns (same styling, components)
