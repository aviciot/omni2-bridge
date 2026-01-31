#!/usr/bin/env python3
"""
Dashboard Schema Initialization
================================
Dashboard-specific tables only. Gets user data from auth_service via API.

Usage:
    python init_dashboard.py          # Create/update tables
    python init_dashboard.py --drop   # Drop and recreate everything
"""

import asyncio
import asyncpg
import sys

DROP_SCHEMA = "--drop" in sys.argv

async def main():
    print("=" * 60)
    print("DASHBOARD SCHEMA INITIALIZATION")
    print("=" * 60)
    
    if DROP_SCHEMA:
        print("\n⚠️  DROP MODE: Will delete existing schema!")
    
    conn = None
    try:
        print("\n[1/5] Connecting to database...")
        conn = await asyncpg.connect("postgresql://omni:omni@omni_pg_db:5432/omni")
        print("✓ Connected")
        
        # Drop schema if requested
        if DROP_SCHEMA:
            print("\n[2/5] Dropping omni2_dashboard schema...")
            await conn.execute("DROP SCHEMA IF EXISTS omni2_dashboard CASCADE")
            print("✓ Schema dropped")
        else:
            print("\n[2/5] Skipping drop (use --drop to drop schema)")
        
        # Create schema
        print("\n[3/5] Creating omni2_dashboard schema...")
        await conn.execute("CREATE SCHEMA IF NOT EXISTS omni2_dashboard")
        print("✓ Schema created")
        
        # Create tables
        print("\n[4/5] Creating tables...")
        
        # 1. Dashboard config
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS omni2_dashboard.dashboard_config (
                id SERIAL PRIMARY KEY,
                key VARCHAR(100) UNIQUE NOT NULL,
                value TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. User preferences (user_id references auth_service.users.id via comment only)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS omni2_dashboard.user_preferences (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                theme VARCHAR(20) DEFAULT 'dark',
                layout JSONB DEFAULT '{}',
                favorite_mcps TEXT[],
                hidden_widgets TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        """)
        await conn.execute("COMMENT ON COLUMN omni2_dashboard.user_preferences.user_id IS 'References auth_service.users.id (no FK - microservice pattern)'")
        
        # 3. Dashboard cache
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS omni2_dashboard.dashboard_cache (
                id SERIAL PRIMARY KEY,
                cache_key VARCHAR(255) UNIQUE NOT NULL,
                cache_value JSONB NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 4. Activity feed (stores user_id + username for display)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS omni2_dashboard.activity_feed (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                username VARCHAR(100) NOT NULL,
                action VARCHAR(50) NOT NULL,
                resource VARCHAR(200),
                details JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("COMMENT ON COLUMN omni2_dashboard.activity_feed.user_id IS 'References auth_service.users.id (no FK)'")
        
        # 5. MCP usage stats (dashboard-specific analytics)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS omni2_dashboard.mcp_usage_stats (
                id SERIAL PRIMARY KEY,
                mcp_name VARCHAR(100) NOT NULL,
                tool_name VARCHAR(100),
                user_id INTEGER,
                success BOOLEAN NOT NULL,
                duration_ms INTEGER,
                cost DECIMAL(10,4),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        print("✓ Tables created: dashboard_config, user_preferences, dashboard_cache, activity_feed, mcp_usage_stats")
        
        # Create indexes
        print("\n[5/5] Creating indexes...")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_config_key ON omni2_dashboard.dashboard_config(key)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON omni2_dashboard.user_preferences(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_cache_key ON omni2_dashboard.dashboard_cache(cache_key)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_cache_expires ON omni2_dashboard.dashboard_cache(expires_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_feed_user_id ON omni2_dashboard.activity_feed(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_feed_created_at ON omni2_dashboard.activity_feed(created_at)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_mcp_usage_stats_mcp_name ON omni2_dashboard.mcp_usage_stats(mcp_name)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_mcp_usage_stats_user_id ON omni2_dashboard.mcp_usage_stats(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_mcp_usage_stats_timestamp ON omni2_dashboard.mcp_usage_stats(timestamp)")
        print("✓ Indexes created")
        
        # Insert default config
        await conn.execute("""
            INSERT INTO omni2_dashboard.dashboard_config (key, value, description) VALUES
            ('refresh_interval', '5', 'Activity feed refresh interval (seconds)'),
            ('chart_data_points', '24', 'Number of data points in charts'),
            ('default_theme', 'dark', 'Default theme (light/dark)'),
            ('stats_cache_ttl', '30', 'Stats cache TTL (seconds)')
            ON CONFLICT (key) DO NOTHING
        """)
        print("✓ Default config inserted")
        
        await conn.close()
        
        print("\n" + "=" * 60)
        print("✓ DASHBOARD SCHEMA INITIALIZATION COMPLETE")
        print("=" * 60)
        print("\nSchema: omni2_dashboard")
        print("Tables: 5")
        print("  - dashboard_config (app settings)")
        print("  - user_preferences (per-user settings)")
        print("  - dashboard_cache (temporary cache)")
        print("  - activity_feed (recent actions)")
        print("  - mcp_usage_stats (analytics)")
        print("\nNote: User data fetched from auth_service via API")
        print()
        
        return 0
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            await conn.close()
        return 1

if __name__ == "__main__":
    exit(asyncio.run(main()))
