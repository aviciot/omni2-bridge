#!/usr/bin/env python3
"""
OMNI2 Schema Initialization - Complete E2E Script

Usage:
    python scripts/init_schema.py          # Create tables only (safe)
    python scripts/init_schema.py --drop   # Drop schema, backup, recreate, restore
"""

import sys
import asyncio
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.database import Base
from app.config import settings
from app import models  # Import to register models


async def main():
    parser = argparse.ArgumentParser(description='Initialize OMNI2 schema')
    parser.add_argument('--drop', action='store_true', help='Drop existing schema before creating')
    args = parser.parse_args()
    
    print("="*60)
    print("OMNI2 SCHEMA INITIALIZATION")
    print("="*60)
    
    if args.drop:
        print("\n⚠️  WARNING: This will DROP ONLY the omni2 schema!")
        print("   Other schemas (auth_service, etc.) will NOT be affected.")
        print("   MCP servers and role permissions will be backed up and restored.")
        response = input("\nContinue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return
    
    engine = create_async_engine(settings.database.url, echo=False)
    
    # Step 1: Backup (if dropping)
    backup = {'mcp_servers': [], 'role_permissions': []}
    if args.drop:
        print("\n📦 Backing up data...")
        async with engine.connect() as conn:
            # Check if schema exists
            result = await conn.execute(text(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'omni2'"
            ))
            if result.fetchone():
                # Backup mcp_servers
                try:
                    result = await conn.execute(text("SELECT * FROM omni2.mcp_servers"))
                    backup['mcp_servers'] = result.fetchall()
                    print(f"  ✅ Backed up {len(backup['mcp_servers'])} MCP servers")
                except:
                    print("  ℹ️  mcp_servers table not found")
                
                # Backup role_permissions
                try:
                    result = await conn.execute(text("SELECT * FROM omni2.role_permissions"))
                    backup['role_permissions'] = result.fetchall()
                    print(f"  ✅ Backed up {len(backup['role_permissions'])} role permissions")
                except:
                    print("  ℹ️  role_permissions table not found")
            else:
                print("  ℹ️  Schema doesn't exist yet")
    
    # Step 2: Drop schema (if requested)
    if args.drop:
        print("\n🗑️  Dropping omni2 schema...")
        async with engine.begin() as conn:
            await conn.execute(text("DROP SCHEMA IF EXISTS omni2 CASCADE"))
        print("  ✅ Schema dropped")
    
    # Step 3: Create schema
    print("\n🏗️  Creating omni2 schema...")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS omni2"))
    print("  ✅ Schema created")
    
    # Step 4: Create all tables from models
    print("\n📋 Creating tables from SQLAlchemy models...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("  ✅ All tables created")
    
    # Step 5: Restore data (if we had backup)
    if args.drop and (backup['mcp_servers'] or backup['role_permissions']):
        print("\n📥 Restoring data...")
        async with engine.begin() as conn:
            # Restore mcp_servers
            if backup['mcp_servers']:
                for row in backup['mcp_servers']:
                    await conn.execute(text("""
                        INSERT INTO omni2.mcp_servers 
                        (name, url, description, status, protocol, timeout_seconds, max_retries, 
                         retry_delay_seconds, auth_type, auth_config, health_status, error_count, meta_data)
                        VALUES (:name, :url, :description, :status, :protocol, :timeout_seconds, 
                                :max_retries, :retry_delay_seconds, :auth_type, :auth_config::jsonb, 
                                :health_status, :error_count, :meta_data::jsonb)
                    """), {
                        'name': row.name,
                        'url': row.url,
                        'description': row.description,
                        'status': row.status,
                        'protocol': row.protocol,
                        'timeout_seconds': row.timeout_seconds,
                        'max_retries': row.max_retries,
                        'retry_delay_seconds': float(row.retry_delay_seconds) if row.retry_delay_seconds else None,
                        'auth_type': row.auth_type,
                        'auth_config': row.auth_config,
                        'health_status': row.health_status,
                        'error_count': row.error_count,
                        'meta_data': row.meta_data
                    })
                print(f"  ✅ Restored {len(backup['mcp_servers'])} MCP servers")
            
            # Restore role_permissions
            if backup['role_permissions']:
                for row in backup['role_permissions']:
                    await conn.execute(text("""
                        INSERT INTO omni2.role_permissions 
                        (role_name, mcp_name, mode, allowed_tools, denied_tools, description, is_active)
                        VALUES (:role_name, :mcp_name, :mode, :allowed_tools, :denied_tools, :description, :is_active)
                    """), {
                        'role_name': row.role_name,
                        'mcp_name': row.mcp_name,
                        'mode': row.mode,
                        'allowed_tools': row.allowed_tools,
                        'denied_tools': row.denied_tools,
                        'description': row.description,
                        'is_active': row.is_active
                    })
                print(f"  ✅ Restored {len(backup['role_permissions'])} role permissions")
    
    await engine.dispose()
    
    print("\n" + "="*60)
    print("✅ OMNI2 SCHEMA INITIALIZED SUCCESSFULLY")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
