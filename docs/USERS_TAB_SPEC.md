# Users Tab Specification

**URL**: http://localhost:3001/users  
**Purpose**: User management interface for admins  
**Status**: 🚧 Planning Phase

---

## 🎯 Features

### Phase 1: User List (MVP)
- **View all users** - Table with columns: ID, Name, Email, Role, Status, Last Login, Created
- **Search/Filter** - By name, email, role, status
- **Sort** - By any column
- **Pagination** - 20 users per page

### Phase 2: User CRUD
- **Create User** - Modal form (name, email, role, password)
- **Edit User** - Update name, email, role, status
- **Delete User** - Soft delete (set active=false)
- **Reset Password** - Generate temporary password

### Phase 3: Advanced Features
- **Role Management** - Assign/change roles with permission preview
- **Activity Log** - View user's recent actions (from auth_audit)
- **Session Management** - View active sessions, force logout
- **Bulk Actions** - Activate/deactivate multiple users

---

## 🔐 Permissions

| Role | View Users | Create User | Edit User | Delete User | Manage Roles |
|------|-----------|-------------|-----------|-------------|--------------|
| **admin** | ✅ | ✅ | ✅ | ✅ | ✅ |
| **developer** | ✅ | ❌ | ❌ | ❌ | ❌ |
| **viewer** | ❌ | ❌ | ❌ | ❌ | ❌ |

**Implementation**: Check `X-User-Role` header from Traefik ForwardAuth

---

## 🛠️ API Endpoints

### GET /auth/api/v1/users
**Purpose**: List all users  
**Auth**: Required (admin only)  
**Query Params**:
- `page` (default: 1)
- `per_page` (default: 20)
- `search` (optional: search by name/email)
- `role` (optional: filter by role)
- `active` (optional: filter by status)

**Response**:
```json
{
  "users": [
    {
      "id": 1,
      "username": "avicoiot",
      "name": "Avi Cohen",
      "email": "avicoiot@gmail.com",
      "role": "admin",
      "active": true,
      "last_login_at": "2026-01-26T10:30:00Z",
      "created_at": "2026-01-20T08:00:00Z"
    }
  ],
  "total": 3,
  "page": 1,
  "per_page": 20
}
```

### POST /auth/api/v1/users
**Purpose**: Create new user  
**Auth**: Required (admin only)  
**Request**:
```json
{
  "username": "newuser",
  "name": "New User",
  "email": "newuser@company.com",
  "password": "temp123",
  "role": "developer",
  "active": true
}
```
**Response**: User object with ID
**Status**: ✅ Already implemented in `auth_service/routes/users.py`

### PUT /auth/api/v1/users/{user_id}
**Purpose**: Update user  
**Auth**: Required (admin only)  
**Request**:
```json
{
  "name": "Updated Name",
  "email": "updated@company.com",
  "role": "viewer",
  "active": false
}
```

### DELETE /auth/api/v1/users/{user_id}
**Purpose**: Delete user (soft delete)  
**Auth**: Required (admin only)  
**Response**: 204 No Content
**Status**: ✅ Already implemented in `auth_service/routes/users.py`

### GET /auth/api/v1/users/{user_id}/activity
**Purpose**: Get user activity log  
**Auth**: Required (admin only)  
**Response**:
```json
{
  "activity": [
    {
      "id": 123,
      "action": "login",
      "resource": "auth",
      "result": "success",
      "ip_address": "192.168.1.100",
      "created_at": "2026-01-26T10:30:00Z"
    }
  ]
}
```

### POST /auth/api/v1/users/{user_id}/reset-password
**Purpose**: Reset user password  
**Auth**: Required (admin only)  
**Response**:
```json
{
  "temporary_password": "Temp123!@#"
}
```

---

## 🎨 UI Components

### UserTable Component
```tsx
interface User {
  id: number;
  username: string;
  name: string;
  email: string;
  role: string;
  active: boolean;
  last_login_at: string;
  created_at: string;
}

<UserTable 
  users={users}
  onEdit={(user) => openEditModal(user)}
  onDelete={(user) => confirmDelete(user)}
  onResetPassword={(user) => resetPassword(user)}
/>
```

### CreateUserModal Component
```tsx
<CreateUserModal
  isOpen={showModal}
  onClose={() => setShowModal(false)}
  onSubmit={(userData) => createUser(userData)}
/>
```

### UserActivityLog Component
```tsx
<UserActivityLog
  userId={selectedUser.id}
  limit={50}
/>
```

---

## 📊 Data Flow

```
Frontend (localhost:3001)
    ↓ GET /auth/api/v1/users
Traefik (localhost:8090)
    ↓ ForwardAuth validation
    ↓ Check X-User-Role = admin
auth_service (internal:8700)
    ↓ Query database
PostgreSQL (auth_service.users)
    ↓ Return user list
Frontend
    ↓ Render UserTable
```

---

## 🚀 Implementation Plan

### Step 1: Backend API (auth_service)
- [ ] Add GET /users endpoint (list with pagination)
- [x] POST /users endpoint (already exists)
- [ ] Add PUT /users/{id} endpoint (update)
- [x] DELETE /users/{id} endpoint (already exists)
- [ ] Add GET /users/{id}/activity endpoint
- [ ] Add POST /users/{id}/reset-password endpoint
- [ ] Add permission checks (admin only)

### Step 2: Frontend Components
- [ ] Create UserTable component
- [ ] Create CreateUserModal component
- [ ] Create EditUserModal component
- [ ] Create UserActivityLog component
- [ ] Add API service functions

### Step 3: Integration
- [ ] Connect components to API
- [ ] Add error handling
- [ ] Add loading states
- [ ] Add success/error toasts

### Step 4: Testing
- [ ] Write backend tests
- [ ] Write frontend tests
- [ ] Write E2E tests
- [ ] Manual QA

---

## 📝 Database Schema

**Existing Tables** (already in auth_service schema):

```sql
-- users table (source of truth)
CREATE TABLE auth_service.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    api_key_hash VARCHAR(255),
    role VARCHAR(50) DEFAULT 'viewer',
    active BOOLEAN DEFAULT true,
    rate_limit INTEGER,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- auth_audit table (activity log)
CREATE TABLE auth_service.auth_audit (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    username VARCHAR(100),
    action VARCHAR(50),
    resource VARCHAR(100),
    result VARCHAR(20),
    ip_address VARCHAR(50),
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- user_sessions table (active sessions)
CREATE TABLE auth_service.user_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token_hash VARCHAR(255) NOT NULL,
    refresh_token_hash VARCHAR(255),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**No new tables needed** - all data already exists!

---

## 🔒 Security Considerations

1. **Admin-Only Access**: All user management endpoints require admin role
2. **Password Hashing**: Always use bcrypt for password storage
3. **Audit Logging**: Log all user management actions to auth_audit
4. **Rate Limiting**: Prevent brute force on password reset
5. **Input Validation**: Sanitize all user inputs
6. **CSRF Protection**: Use CSRF tokens for state-changing operations

---

## 📚 Related Files

- **Backend**: `auth_service/routes/users.py` (already has POST /users, DELETE /users)
- **Frontend**: `omni2/dashboard/frontend/src/app/users/page.tsx` (placeholder)
- **Tests**: `omni2/dashboard/tests/test_users.py` (to be created)
- **API Service**: `omni2/dashboard/frontend/src/services/userService.ts` (to be created)

---

**Next Steps**: 
1. Implement GET /users endpoint in auth_service
2. Create UserTable component in frontend
3. Write integration tests
