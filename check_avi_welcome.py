"""Check welcome message for user avi"""
import asyncio
import asyncpg

async def check_welcome():
    conn = await asyncpg.connect(
        host="localhost",
        port=5435,
        user="omni",
        password="omni",
        database="omni"
    )
    
    # Get user info
    user = await conn.fetchrow("""
        SELECT id, username, email, role_id, active
        FROM auth_service.users
        WHERE username = 'avi' OR email LIKE '%avi%'
    """)
    
    if not user:
        print("User 'avi' not found")
        await conn.close()
        return
    
    print(f"User found: {user['username']} (ID: {user['id']}, Role ID: {user['role_id']}, Active: {user['active']})")
    
    # Get role info
    role = await conn.fetchrow("""
        SELECT id, name FROM auth_service.roles WHERE id = $1
    """, user['role_id'])
    
    if role:
        print(f"   Role: {role['name']}")
    
    # Check welcome message config
    welcome = await conn.fetchrow("""
        SELECT config_type, target_id, welcome_message, show_usage_info
        FROM omni2.chat_welcome_config
        WHERE 
            (config_type = 'user' AND target_id = $1)
            OR (config_type = 'role' AND target_id = $2)
            OR (config_type = 'default' AND target_id IS NULL)
        ORDER BY 
            CASE config_type
                WHEN 'user' THEN 1
                WHEN 'role' THEN 2
                WHEN 'default' THEN 3
            END
        LIMIT 1
    """, user['id'], user['role_id'])
    
    print("\nWelcome Message Configuration:")
    if welcome:
        print(f"   Type: {welcome['config_type']}")
        print(f"   Target ID: {welcome['target_id']}")
        print(f"   Show Usage Info: {welcome['show_usage_info']}")
        print(f"\n   Message:\n   {welcome['welcome_message']}")
    else:
        print("   No welcome message configured - will use default")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_welcome())
