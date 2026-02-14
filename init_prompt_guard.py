#!/usr/bin/env python3
"""
Initialize Prompt Guard Configuration
"""

import asyncio
import asyncpg
import json

async def init_prompt_guard_config():
    """Initialize prompt guard configuration in database."""
    
    # Default configuration
    config = {
        "enabled": True,
        "threshold": 0.5,
        "cache_ttl_seconds": 3600,
        "bypass_roles": ["admin"],  # Admin role bypasses guard
        "behavioral_tracking": {
            "enabled": True,
            "warning_threshold": 3,
            "block_threshold": 5,
            "window_hours": 24
        },
        "actions": {
            "warn": True,
            "filter": False,
            "block": False
        },
        "messages": {
            "warning": "Suspicious content detected. Please review your message.",
            "blocked_message": "Message blocked due to security policy violation.",
            "blocked_user": "Account suspended due to security violations."
        }
    }
    
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            database="omni",
            user="omni",
            password="omni123"  # Update with actual password
        )
        
        # Insert or update configuration
        await conn.execute("""
            INSERT INTO omni2.omni2_config (config_key, config_value, is_active, created_at, updated_at)
            VALUES ('prompt_guard', $1, true, NOW(), NOW())
            ON CONFLICT (config_key) DO UPDATE SET
                config_value = $1,
                updated_at = NOW(),
                is_active = true
        """, json.dumps(config))
        
        print("✅ Prompt guard configuration initialized successfully")
        print(f"   Enabled: {config['enabled']}")
        print(f"   Threshold: {config['threshold']}")
        print(f"   Bypass roles: {config['bypass_roles']}")
        print(f"   Actions: {config['actions']}")
        
        await conn.close()
        
    except Exception as e:
        print(f"❌ Failed to initialize configuration: {e}")

if __name__ == "__main__":
    asyncio.run(init_prompt_guard_config())