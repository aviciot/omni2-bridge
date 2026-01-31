# IAM Dashboard - Design & Implementation Plan

## 🔌 Auth Service API Endpoints

### **Users Management** (7 endpoints)
| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/users` | List users with pagination & filters | `{users: [], total, page, per_page}` |
| GET | `/users/{id}` | Get user details | User object with role info |
| POST | `/users` | Create new user | Created user object |
| PUT | `/users/{id}` | Update user | `{message: "User updated"}` |
| DELETE | `/users/{id}` | Delete user | 204 No Content |
| POST | `/users/{id}/reset-password` | Reset password (admin) | `{temporary_password}` |
| GET | `/users/{id}/activity` | Get user audit log | `{activity: []}` |

**User Object Fields:**
- `id`, `username`, `email`, `name`
- `role_id`, `role_name`, `mcp_access`
- `active`, `rate_limit_override`
- `last_login_at`, `created_at`, `updated_at`

**Filters:** `search`, `role_id`, `active`, `page`, `per_page`

---

### **Roles Management** (5 endpoints)
| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/roles` | List all roles | `{roles: []}` |
| GET | `/roles/{id}` | Get role details | Role object |
| POST | `/roles` | Create role (admin) | `{role_id, name}` |
| PUT | `/roles/{id}` | Update role (admin) | `{message}` |
| DELETE | `/roles/{id}` | Delete role (admin) | `{message}` |

**Role Object Fields:**
- `id`, `name`, `description`
- `mcp_access` (TEXT[]) - List of allowed MCPs
- `tool_restrictions` (JSONB) - Per-MCP tool restrictions
- `dashboard_access` (VARCHAR) - Dashboard permission level
- `rate_limit` (INT) - Requests per minute
- `cost_limit_daily` (DECIMAL) - Daily cost limit
- `token_expiry` (INT) - Token expiry in seconds
- `created_at`, `updated_at`

**Default Roles:**
1. `super_admin` - Full access
2. `developer` - All MCPs, full tools
3. `analyst` - Read-only MCPs
4. `viewer` - Limited read access

---

### **Teams Management** (7 endpoints)
| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/teams` | List all teams | `{teams: []}` with member_count |
| GET | `/teams/{id}` | Get team with members | Team object + members array |
| POST | `/teams` | Create team (admin) | `{team_id, name}` |
| PUT | `/teams/{id}` | Update team (admin) | `{message}` |
| DELETE | `/teams/{id}` | Delete team (admin) | `{message}` |
| POST | `/teams/{id}/members/{user_id}` | Add member (admin) | `{message}` |
| DELETE | `/teams/{id}/members/{user_id}` | Remove member (admin) | `{message}` |

**Team Object Fields:**
- `id`, `name`, `description`
- `mcp_access` (TEXT[]) - Team MCP restrictions
- `resource_access` (JSONB) - Resource-level permissions
- `team_rate_limit`, `team_cost_limit`
- `member_count`, `members` (array)
- `created_at`, `updated_at`

---

### **Permissions** (2 endpoints)
| Method | Endpoint | Description | Response |
|--------|----------|-------------|----------|
| GET | `/permissions/{user_id}` | Calculate effective permissions | Full permission object |
| GET | `/permissions/check/{user_id}/{mcp}/{tool}` | Quick permission check | `{allowed, reason}` |

**Permission Calculation Logic:**
1. Start with role permissions
2. Intersect with team permissions (if user in teams)
3. Apply user overrides (restrictions only)
4. Apply rate_limit_override if set

---

## 🎨 Design Philosophy

### Visual Design
- **Glass Morphism**: Backdrop blur on all cards
- **Gradient Backgrounds**: Purple → Indigo → Blue
- **Smooth Animations**: Fade-in, slide-up, hover effects
- **Color Coding**: 
  - Purple/Indigo: Primary actions
  - Green: Active/Success
  - Red: Inactive/Danger
  - Blue: Info
  - Amber: Warnings
- **Icons**: Mix of emojis + SVG icons
- **Spacing**: Generous padding, rounded corners (xl, 2xl)

### Layout Structure
```
IAM Page
├── Navbar (sticky, glass effect)
├── Hero Section (title + icon)
├── Sub-tabs (Users | Roles | Teams)
└── Tab Content
    ├── Search/Filter Bar
    ├── Action Buttons (Create, Export)
    ├── Data Table/Cards
    └── Modals (View, Edit, Create)
```

### Component Architecture
```
/app/iam/page.tsx          → Main IAM page with sub-tabs
/components/iam/
  ├── UsersTab.tsx          → Users management
  ├── RolesTab.tsx          → Roles management
  ├── TeamsTab.tsx          → Teams management
  ├── UserDetailsModal.tsx  → View user details
  ├── UserEditModal.tsx     → Edit user
  ├── RoleDetailsModal.tsx  → View role details
  ├── TeamDetailsModal.tsx  → View team + members
  └── ConfirmDialog.tsx     → Delete confirmation
```

---

## 📋 Phase 1 Implementation Plan

### **1. Users Tab** 
**Status: 🟢 80% COMPLETE**

#### 1.1 Users List (Read-Only) ✅ DONE
- [x] Display users table with pagination
- [x] Search by name, email, username
- [x] Filter by role (dropdown)
- [x] Filter by status (Active/Inactive)
- [x] Click row to view details
- [x] User details modal with all fields
- [x] Loading states & animations

#### 1.2 Users CRUD ✅ DONE
- [x] Create User button + modal
  - [x] Form: username, email, name, password, role, active
  - [x] Validation (email format, required fields)
  - [x] Success/error messages
- [x] Edit User modal
  - [x] Update name, email, role, active status
  - [x] Change rate_limit_override
- [x] Delete User
  - [x] Confirmation dialog
  - [x] Admin-only access
- [ ] Reset Password
  - [ ] Generate temp password
  - [ ] Copy to clipboard
  - [ ] Show in modal

#### 1.3 User Activity Log 🔴 TODO
- [ ] Activity tab in user details modal
- [ ] Show last 50 actions
- [ ] Filter by action type
- [ ] Date range picker

---

### **2. Roles Tab**
**Status: 🔴 NOT STARTED**

#### 2.1 Roles List 🔴 TODO
- [ ] Display roles as cards (not table)
- [ ] Show: name, description, user count
- [ ] Color-coded by permission level
- [ ] Click to view details

#### 2.2 Role Details Modal 🔴 TODO
- [ ] Display all role fields
- [ ] MCP Access list (badges)
- [ ] Tool Restrictions (expandable JSON)
- [ ] Dashboard Access level
- [ ] Rate & Cost limits
- [ ] List of users with this role

#### 2.3 Role CRUD 🔴 TODO
- [ ] Create Role (admin only)
  - [ ] Form with all fields
  - [ ] MCP selector (multi-select)
  - [ ] Tool restrictions builder
- [ ] Edit Role
  - [ ] Update all fields
  - [ ] Warning if users assigned
- [ ] Delete Role
  - [ ] Block if users assigned
  - [ ] Suggest reassignment

---

### **3. Teams Tab**
**Status: 🔴 NOT STARTED**

#### 3.1 Teams List 🔴 TODO
- [ ] Display teams as cards
- [ ] Show: name, description, member count
- [ ] MCP access badges
- [ ] Click to view details

#### 3.2 Team Details Modal 🔴 TODO
- [ ] Team info section
- [ ] Members table
  - [ ] User avatar, name, role
  - [ ] Remove member button
- [ ] Add member section
  - [ ] User search/select
  - [ ] Add button

#### 3.3 Team CRUD 🔴 TODO
- [ ] Create Team
  - [ ] Form: name, description, mcp_access
  - [ ] Resource access builder
  - [ ] Rate/cost limits
- [ ] Edit Team
  - [ ] Update all fields
- [ ] Delete Team
  - [ ] Confirmation
  - [ ] Remove all members first

---

## 🚀 Implementation Priority

### Sprint 1 (Current)
1. ✅ Fix API connection (use Traefik URL)
2. ✅ Create IAM page structure with sub-tabs
3. 🟡 Complete Users Tab CRUD operations
4. 🔴 Add toast notifications

### Sprint 2
1. Implement Roles Tab (read-only)
2. Role details modal
3. Role CRUD operations

### Sprint 3
1. Implement Teams Tab (read-only)
2. Team details with members
3. Team CRUD + member management

### Sprint 4
1. User activity log
2. Advanced filters
3. Export functionality
4. Bulk operations

---

## 🔧 Technical Notes

### API Client Setup
```typescript
// Use Traefik proxy
const AUTH_API = 'http://localhost:8090/auth/api/v1';

// Add Bearer token to all requests
authApi.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### Admin-Only Operations
All CREATE, UPDATE, DELETE operations require `X-User-Role: super_admin` header.
Check user role before showing action buttons.

### Error Handling
- 401: Redirect to login
- 403: Show "Admin access required" toast
- 404: Show "Not found" message
- 500: Show generic error + log to console

---

## 📊 Progress Tracking

**Overall Progress: 65%**

- Users Tab: 80% (List ✅, CRUD ✅, Activity ❌)
- Roles Tab: 0%
- Teams Tab: 0%
- Permissions: 0%

**Next Task:** Implement Reset Password functionality
