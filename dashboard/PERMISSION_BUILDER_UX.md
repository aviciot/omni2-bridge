# Advanced Permission Builder - UI/UX Guide

## 🎨 Design Philosophy

**Goal:** Make complex permission management intuitive and visual, not overwhelming.

### Key Principles
1. **Progressive Disclosure** - Show details only when needed
2. **Visual Hierarchy** - Color-coded modes, clear grouping
3. **Bulk Actions** - Select/Deselect all for efficiency
4. **Instant Feedback** - Visual states show what's enabled/disabled

---

## 🖼️ UI Layout

### Level 1: MCP Server List
```
┌─────────────────────────────────────────┐
│ MCP Permissions          3 of 5 enabled │
├─────────────────────────────────────────┤
│ ☑ filesystem              ▶ Configure   │
│   [ALL] [ALLOW] [DENY] [NONE]          │
├─────────────────────────────────────────┤
│ ☐ database                              │
├─────────────────────────────────────────┤
│ ☑ github                  ▶ Configure   │
│   [ALL] [ALLOW] [DENY] [NONE]          │
└─────────────────────────────────────────┘
```

### Level 2: Expanded MCP Details (when "Configure" clicked)
```
┌─────────────────────────────────────────┐
│ ☑ filesystem              ▼ Hide Details│
│   [ALL] [ALLOW] [DENY] [NONE]          │
├─────────────────────────────────────────┤
│ 🔧 Tools (12)      Select All | Deselect│
│ ┌─────────────┬─────────────┐          │
│ │☑ read_file  │☑ write_file │          │
│ │☐ delete_file│☑ list_dir   │          │
│ └─────────────┴─────────────┘          │
│                                         │
│ 📁 Resources (5)   Select All | Deselect│
│ ┌─────────────┬─────────────┐          │
│ │☑ /home/*    │☐ /etc/*     │          │
│ └─────────────┴─────────────┘          │
│                                         │
│ 💬 Prompts (3)     Select All | Deselect│
│ ┌─────────────┬─────────────┐          │
│ │☑ analyze    │☑ search     │          │
│ └─────────────┴─────────────┘          │
└─────────────────────────────────────────┘
```

---

## 🎯 User Flow

### Creating a Role

**Step 1: Basic Info**
- Enter role name & description
- Set dashboard access, rate limits, cost limits

**Step 2: Enable MCPs**
- Check MCPs to enable
- Each MCP defaults to "ALL" mode (full access)

**Step 3: Configure Permissions (Optional)**
- Click "Configure" on any MCP
- Choose access mode:
  - **ALL** = Full access (default)
  - **ALLOW** = Whitelist mode
  - **DENY** = Blacklist mode
  - **NONE** = Block completely

**Step 4: Select Items (if ALLOW or DENY)**
- See all tools, resources, prompts
- Use checkboxes to select/deselect
- Use "Select All" / "Deselect All" for bulk actions

---

## 🎨 Visual Design Elements

### Color Coding

**Access Modes:**
- 🟢 **ALL** - Green (permissive)
- 🔵 **ALLOW** - Blue (controlled)
- 🟡 **DENY** - Amber (restricted)
- 🔴 **NONE** - Red (blocked)

**Item States:**
- **Selected in ALLOW mode** - Blue background
- **Selected in DENY mode** - Amber background
- **Unselected** - Gray background
- **Enabled MCP** - Purple border
- **Disabled MCP** - Gray border

### Icons
- 🔧 Tools
- 📁 Resources
- 💬 Prompts
- ▶ Expand
- ▼ Collapse

---

## 💡 Smart Features

### 1. Auto-Load Details
When you enable an MCP, it automatically fetches:
- Available tools
- Available resources
- Available prompts

### 2. Mode-Aware Checkboxes
- **ALLOW mode**: Checked = Allowed
- **DENY mode**: Checked = Denied (inverted logic)
- Visual feedback shows the actual effect

### 3. Bulk Actions
- "Select All" - Check all items
- "Deselect All" - Uncheck all items
- Works per category (tools, resources, prompts)

### 4. Progressive Disclosure
- Details hidden by default
- Click "Configure" to expand
- Click "Hide Details" to collapse
- Keeps UI clean and focused

---

## 📊 Data Structure

### Saved Format
```json
{
  "mcp_access": ["filesystem", "github"],
  "tool_restrictions": {
    "filesystem": {
      "mode": "allow",
      "tools": ["read_file", "list_directory"],
      "resources": ["/home/*"],
      "prompts": ["analyze"]
    },
    "github": {
      "mode": "deny",
      "tools": ["delete_repo"],
      "resources": [],
      "prompts": []
    }
  }
}
```

---

## 🎭 Example Scenarios

### Scenario 1: Read-Only Analyst
```
✅ filesystem (ALLOW mode)
   ✅ read_file
   ✅ list_directory
   ❌ write_file
   ❌ delete_file

✅ database (ALLOW mode)
   ✅ query
   ✅ describe_table
   ❌ insert
   ❌ update
```

### Scenario 2: Developer (Almost Full Access)
```
✅ filesystem (ALL mode)
   → All tools allowed

✅ database (DENY mode)
   ❌ drop_database
   ❌ drop_table
   ✅ Everything else allowed

✅ github (ALL mode)
   → All tools allowed
```

### Scenario 3: Restricted QA
```
✅ filesystem (ALLOW mode)
   ✅ read_file
   ✅ list_directory

❌ database (NONE mode)
   → Completely blocked

✅ github (ALLOW mode)
   ✅ list_repos
   ✅ get_file
```

---

## 🚀 Benefits

### For Admins
- **Visual** - See permissions at a glance
- **Fast** - Bulk actions for efficiency
- **Safe** - Clear mode indicators prevent mistakes
- **Flexible** - Granular control when needed

### For Users
- **Clear** - Know exactly what they can access
- **Predictable** - Consistent behavior across MCPs
- **Documented** - Mode legend explains everything

---

## 🔄 Future Enhancements

1. **Search/Filter** - Find specific tools quickly
2. **Templates** - Pre-configured permission sets
3. **Copy Permissions** - Duplicate from another role
4. **Diff View** - Compare roles side-by-side
5. **Usage Stats** - Show which tools are actually used
6. **Recommendations** - Suggest permissions based on role name
