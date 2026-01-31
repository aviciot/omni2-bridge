# Users Tab - Quick Reference

**URL**: http://localhost:3001/users  
**Status**: 🚧 Planning → Implementation

---

## 🎯 What We Want

A user management interface where admins can:
- View all users in a table
- Create new users
- Edit existing users
- Delete users
- View user activity logs
- Reset passwords

---

## 🔐 Access Control

| Role | Can Access? |
|------|-------------|
| **admin** | ✅ Full access |
| **developer** | ✅ View only |
| **viewer** | ❌ No access |

---

## 🛠️ API Endpoints Needed

### Already Implemented ✅
```bash
# Create user
POST /auth/api/v1/users
Body: {username, name, email, password, role, active}

# Delete user
DELETE /auth/api/v1/users/{id}
```

### To Implement 🚧
```bash
# List users (with pagination, search, filter)
GET /auth/api/v1/users?page=1&per_page=20&search=john&role=admin

# Update user
PUT /auth/api/v1/users/{id}
Body: {name, email, role, active}

# Get user activity
GET /auth/api/v1/users/{id}/activity

# Reset password
POST /auth/api/v1/users/{id}/reset-password
```

---

## 🧪 Testing

### Run Tests
```bash
cd omni2/dashboard/tests
python test_users_api.py
# OR
test_users.bat
```

### Expected Output
```
TEST 1: List Users - SKIP (not implemented)
TEST 2: Create User - PASS
TEST 3: Update User - SKIP (not implemented)
TEST 4: User Activity - SKIP (not implemented)
TEST 5: Delete User - PASS
TEST 6: Unauthorized - PASS
TEST 7: Non-Admin - SKIP (not implemented)

Passed: 2/7
Skipped: 5/7
```

---

## 📊 Database Tables (Already Exist)

```sql
-- Users table
auth_service.users
  - id, username, name, email
  - password_hash, api_key_hash
  - role, active, rate_limit
  - last_login_at, created_at, updated_at

-- Activity log
auth_service.auth_audit
  - id, user_id, username
  - action, resource, result
  - ip_address, user_agent, details
  - created_at

-- Active sessions
auth_service.user_sessions
  - id, user_id
  - token_hash, refresh_token_hash
  - expires_at, created_at
```

---

## 🎨 UI Components to Build

### 1. UserTable
```tsx
<UserTable 
  users={users}
  onEdit={handleEdit}
  onDelete={handleDelete}
  onResetPassword={handleResetPassword}
/>
```

### 2. CreateUserModal
```tsx
<CreateUserModal
  isOpen={showModal}
  onClose={() => setShowModal(false)}
  onSubmit={handleCreate}
/>
```

### 3. EditUserModal
```tsx
<EditUserModal
  user={selectedUser}
  isOpen={showEditModal}
  onClose={() => setShowEditModal(false)}
  onSubmit={handleUpdate}
/>
```

---

## 🚀 Implementation Steps

### Step 1: Backend (auth_service)
```python
# File: auth_service/routes/users.py

@router.get("/users")
async def list_users(
    page: int = 1,
    per_page: int = 20,
    search: str = None,
    role: str = None,
    x_user_role: str = Header(None, alias="X-User-Role")
):
    # Check admin permission
    if x_user_role != "admin":
        raise HTTPException(403, "Admin access required")
    
    # Query users with filters
    # Return paginated results

@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdate,
    x_user_role: str = Header(None, alias="X-User-Role")
):
    # Check admin permission
    # Update user
    # Return updated user

@router.get("/users/{user_id}/activity")
async def get_user_activity(
    user_id: int,
    x_user_role: str = Header(None, alias="X-User-Role")
):
    # Check admin permission
    # Query auth_audit table
    # Return activity log
```

### Step 2: Frontend (dashboard)
```typescript
// File: omni2/dashboard/frontend/src/services/userService.ts

export async function listUsers(params: {
  page?: number;
  per_page?: number;
  search?: string;
  role?: string;
}) {
  const token = localStorage.getItem('access_token');
  const response = await fetch(
    `http://localhost:8090/auth/api/v1/users?${new URLSearchParams(params)}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  return response.json();
}

export async function createUser(userData: UserCreate) {
  const token = localStorage.getItem('access_token');
  const response = await fetch(
    'http://localhost:8090/auth/api/v1/users',
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(userData)
    }
  );
  return response.json();
}
```

### Step 3: Update Users Page
```typescript
// File: omni2/dashboard/frontend/src/app/users/page.tsx

export default function UsersPage() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    loadUsers();
  }, []);
  
  async function loadUsers() {
    const data = await listUsers({ page: 1, per_page: 20 });
    setUsers(data.users);
    setLoading(false);
  }
  
  return (
    <div>
      <UserTable 
        users={users}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />
    </div>
  );
}
```

---

## 📝 Checklist

### Backend
- [ ] GET /users endpoint with pagination
- [ ] PUT /users/{id} endpoint
- [ ] GET /users/{id}/activity endpoint
- [ ] POST /users/{id}/reset-password endpoint
- [ ] Admin-only permission checks
- [ ] Input validation
- [ ] Error handling

### Frontend
- [ ] UserTable component
- [ ] CreateUserModal component
- [ ] EditUserModal component
- [ ] UserActivityLog component
- [ ] API service functions
- [ ] Error handling
- [ ] Loading states
- [ ] Success/error toasts

### Testing
- [ ] Backend unit tests
- [ ] Frontend component tests
- [ ] Integration tests (API)
- [ ] E2E tests (full flow)
- [ ] Manual QA

---

## 🔗 Documentation

- **Full Spec**: `omni2/docs/USERS_TAB_SPEC.md`
- **Test Suite**: `omni2/dashboard/tests/test_users_api.py`
- **Traefik Config**: `omni2/docs/architecture/TRAEFIK_ARCHITECTURE.md`
- **Auth Service**: `auth_service/routes/users.py`

---

**Ready to implement!** Start with backend endpoints, then build frontend components.
