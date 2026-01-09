-- ============================================================
-- OMNI2 Database Seed Data
-- ============================================================
-- Populates initial users, MCP servers, and sample data
-- ============================================================

-- ============================================================
-- Seed Users
-- ============================================================

-- Seed Roles
INSERT INTO roles (name, display_name, description, color)
VALUES
    ('admin', 'Administrator', 'Full system access', '#7c3aed'),
    ('dba', 'Database Administrator', 'Database management and tuning', '#0ea5e9'),
    ('power_user', 'Power User', 'Advanced access to MCP tools', '#6366f1'),
    ('qa_tester', 'QA Tester', 'Testing and validation access', '#f97316'),
    ('read_only', 'Read Only', 'Limited access to safe tools', '#64748b')
ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    color = EXCLUDED.color,
    updated_at = NOW();

-- Seed Teams
INSERT INTO teams (name, display_name, description, notify_on_errors)
VALUES
    ('analytics', 'Analytics', 'Data analytics and reporting', false),
    ('development', 'Development', 'Core engineering and development', false),
    ('database', 'Database', 'Database operations', false),
    ('qa', 'QA', 'Quality assurance', false)
ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    notify_on_errors = EXCLUDED.notify_on_errors,
    updated_at = NOW();

-- Admin Users
INSERT INTO users (email, name, role, is_super_admin, is_active)
VALUES 
    ('avicoiot@gmail.com', 'Avi Cohen', 'admin', true, true),
    ('avi.cohen@shift4.com', 'Avi Cohen', 'admin', true, true)
ON CONFLICT (email) DO UPDATE SET
    is_super_admin = EXCLUDED.is_super_admin,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- Developer User
INSERT INTO users (email, name, role, is_super_admin, is_active)
VALUES ('alonab@shift4.com', 'Alon AB', 'developer', false, true)
ON CONFLICT (email) DO UPDATE SET
    role = EXCLUDED.role,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- DBA User
INSERT INTO users (email, name, role, is_super_admin, is_active)
VALUES ('dba1@shift4.com', 'DBA User', 'dba', false, true)
ON CONFLICT (email) DO UPDATE SET
    role = EXCLUDED.role,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- Additional Shift4 Users
INSERT INTO users (email, name, role, is_super_admin, is_active)
VALUES
    ('osnat.shilov@shift4.com', 'Osnat Shilov', 'admin', true, true),
    ('addison.baitcher@shift4.com', 'Addison Baitcher', 'power_user', false, true),
    ('alona.babich@shift4.com', 'Alona Babich', 'power_user', false, true),
    ('test.junior.dba@shift4.com', 'Test Junior DBA', 'dba', false, true)
ON CONFLICT (email) DO UPDATE SET
    role = EXCLUDED.role,
    is_super_admin = EXCLUDED.is_super_admin,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();

-- Seed User Teams
INSERT INTO user_teams (user_id, team_name)
SELECT id, 'analytics' FROM users WHERE email = 'osnat.shilov@shift4.com'
ON CONFLICT (user_id, team_name) DO NOTHING;

INSERT INTO user_teams (user_id, team_name)
SELECT id, 'development' FROM users WHERE email = 'addison.baitcher@shift4.com'
ON CONFLICT (user_id, team_name) DO NOTHING;

INSERT INTO user_teams (user_id, team_name)
SELECT id, 'development' FROM users WHERE email = 'alona.babich@shift4.com'
ON CONFLICT (user_id, team_name) DO NOTHING;

INSERT INTO user_teams (user_id, team_name)
SELECT id, 'database' FROM users WHERE email = 'test.junior.dba@shift4.com'
ON CONFLICT (user_id, team_name) DO NOTHING;

-- ============================================================
-- Seed MCP Servers
-- ============================================================

INSERT INTO mcp_servers (name, url, is_enabled, is_healthy)
VALUES 
    ('database_mcp', 'http://database-mcp:8001', true, true),
    ('github_mcp', 'http://github-mcp:8002', true, true),
    ('filesystem_mcp', 'http://filesystem-mcp:8003', false, true),
    ('smoketest_mcp', 'http://smoketest-mcp:8004', false, true),
    ('omni2_analytics_mcp', 'http://analytics_mcp:8302', true, true)
ON CONFLICT (name) DO UPDATE SET
    url = EXCLUDED.url,
    is_enabled = EXCLUDED.is_enabled,
    updated_at = NOW();

-- ============================================================
-- Completion Message
-- ============================================================
DO $$
DECLARE
    user_count INTEGER;
    mcp_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT COUNT(*) INTO mcp_count FROM mcp_servers;
    
    RAISE NOTICE '============================================================';
    RAISE NOTICE '✅ OMNI2 Seed Data Loaded Successfully!';
    RAISE NOTICE '============================================================';
    RAISE NOTICE 'Users Created/Updated: %', user_count;
    RAISE NOTICE '  • Admins: avicoiot@gmail.com, avi.cohen@shift4.com';
    RAISE NOTICE '  • Developer: alonab@shift4.com';
    RAISE NOTICE '  • DBA: dba1@shift4.com';
    RAISE NOTICE '';
    RAISE NOTICE 'MCP Servers Registered: %', mcp_count;
    RAISE NOTICE '  • database_mcp (enabled)';
    RAISE NOTICE '  • github_mcp (enabled)';
    RAISE NOTICE '  • filesystem_mcp (disabled)';
    RAISE NOTICE '  • smoketest_mcp (disabled)';
    RAISE NOTICE '  • omni2_analytics_mcp (enabled - admin only)';
    RAISE NOTICE '';
    RAISE NOTICE '🚀 Database ready for use!';
    RAISE NOTICE '============================================================';
END $$;
