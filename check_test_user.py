import asyncio
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from app.database import get_db

async def check_test_user():
    async for db in get_db():
        # Get TEST user
        result = await db.execute(
            text("SELECT user_id, email, role_id FROM omni2.users WHERE email = 'test@example.com'")
        )
        user = result.fetchone()
        if not user:
            print("TEST user not found")
            return
        
        print(f"User: {user.email}, role_id: {user.role_id}")
        
        # Get role
        result = await db.execute(
            text("SELECT role_name, tool_restrictions FROM omni2.roles WHERE role_id = :role_id"),
            {"role_id": user.role_id}
        )
        role = result.fetchone()
        if not role:
            print("Role not found")
            return
        
        print(f"Role: {role.role_name}")
        print(f"tool_restrictions type: {type(role.tool_restrictions)}")
        print(f"tool_restrictions: {role.tool_restrictions}")
        
        break

asyncio.run(check_test_user())
