#!/usr/bin/env python3
"""
WebSocket Conversation Verification Script
Checks logs and database to confirm WebSocket chat is working
"""

import asyncio
import asyncpg
import os
from datetime import datetime, timedelta

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "mcp_performance",
    "user": "postgres",
    "password": "postgres"
}

async def check_database():
    """Check database for WebSocket conversation records"""
    print("\n" + "="*80)
    print("DATABASE VERIFICATION")
    print("="*80)
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        
        # 1. Check if conversation_id column exists
        print("\n1. Checking schema...")
        columns = await conn.fetch("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'omni2' 
                AND table_name = 'interaction_flows'
            ORDER BY ordinal_position
        """)
        
        print(f"   Table: omni2.interaction_flows")
        has_conversation_id = False
        for col in columns:
            print(f"   - {col['column_name']}: {col['data_type']} {'NULL' if col['is_nullable'] == 'YES' else 'NOT NULL'}")
            if col['column_name'] == 'conversation_id':
                has_conversation_id = True
        
        if not has_conversation_id:
            print("\n   ❌ conversation_id column MISSING!")
            print("   Run migration: ALTER TABLE omni2.interaction_flows ADD COLUMN conversation_id UUID;")
            return False
        else:
            print("\n   ✅ conversation_id column EXISTS")
        
        # 2. Check recent WebSocket conversations
        print("\n2. Checking recent WebSocket conversations...")
        conversations = await conn.fetch("""
            SELECT 
                session_id,
                conversation_id,
                user_id,
                created_at,
                completed_at,
                EXTRACT(EPOCH FROM (completed_at - created_at)) as duration_seconds,
                jsonb_array_length(flow_data->'events') as event_count
            FROM omni2.interaction_flows
            WHERE conversation_id IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        if not conversations:
            print("   ⚠️  No WebSocket conversations found in database")
            print("   This is normal if you haven't used WebSocket chat yet")
        else:
            print(f"   ✅ Found {len(conversations)} WebSocket conversation(s)")
            for conv in conversations:
                print(f"\n   Conversation: {conv['conversation_id']}")
                print(f"   - Session: {conv['session_id']}")
                print(f"   - User ID: {conv['user_id']}")
                print(f"   - Started: {conv['created_at']}")
                print(f"   - Duration: {conv['duration_seconds']:.2f}s")
                print(f"   - Events: {conv['event_count']}")
        
        # 3. Check conversation statistics
        print("\n3. Conversation statistics...")
        stats = await conn.fetch("""
            SELECT 
                COUNT(DISTINCT conversation_id) as total_conversations,
                COUNT(DISTINCT session_id) as total_sessions,
                COUNT(DISTINCT user_id) as unique_users,
                MIN(created_at) as first_conversation,
                MAX(created_at) as last_conversation
            FROM omni2.interaction_flows
            WHERE conversation_id IS NOT NULL
        """)
        
        if stats and stats[0]['total_conversations'] > 0:
            s = stats[0]
            print(f"   - Total conversations: {s['total_conversations']}")
            print(f"   - Total sessions: {s['total_sessions']}")
            print(f"   - Unique users: {s['unique_users']}")
            print(f"   - First: {s['first_conversation']}")
            print(f"   - Last: {s['last_conversation']}")
        else:
            print("   No statistics available yet")
        
        # 4. Check event types
        print("\n4. Event types in WebSocket conversations...")
        events = await conn.fetch("""
            SELECT 
                event->>'event_type' as event_type,
                COUNT(*) as count
            FROM omni2.interaction_flows if_
            CROSS JOIN jsonb_array_elements(if_.flow_data->'events') as event
            WHERE if_.conversation_id IS NOT NULL
            GROUP BY event->>'event_type'
            ORDER BY count DESC
            LIMIT 10
        """)
        
        if events:
            for evt in events:
                print(f"   - {evt['event_type']}: {evt['count']} times")
        else:
            print("   No events found")
        
        # 5. Show latest conversation details
        print("\n5. Latest conversation details...")
        latest = await conn.fetchrow("""
            SELECT 
                session_id,
                conversation_id,
                user_id,
                created_at,
                completed_at,
                flow_data
            FROM omni2.interaction_flows
            WHERE conversation_id IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        if latest:
            print(f"   Conversation ID: {latest['conversation_id']}")
            print(f"   Session ID: {latest['session_id']}")
            print(f"   User ID: {latest['user_id']}")
            print(f"   Created: {latest['created_at']}")
            print(f"   Completed: {latest['completed_at']}")
            
            # Show events
            events = latest['flow_data'].get('events', [])
            print(f"\n   Events ({len(events)}):")
            for i, evt in enumerate(events[:5], 1):  # Show first 5
                print(f"   {i}. {evt.get('event_type')} @ {evt.get('timestamp')}")
            if len(events) > 5:
                print(f"   ... and {len(events) - 5} more events")
        
        await conn.close()
        return True
        
    except Exception as e:
        print(f"\n   ❌ Database error: {e}")
        return False


def check_logs():
    """Check Docker logs for WebSocket activity"""
    print("\n" + "="*80)
    print("LOG VERIFICATION")
    print("="*80)
    
    # Check OMNI2 backend logs
    print("\n1. Checking OMNI2 backend logs...")
    print("   Looking for WebSocket chat connections...\n")
    
    os.system('docker logs omni2 --tail 100 2>&1 | findstr /i "WS-CHAT conversation"')
    
    print("\n2. Checking Dashboard backend logs...")
    print("   Looking for WebSocket proxy activity...\n")
    
    os.system('docker logs omni2-dashboard-backend --tail 100 2>&1 | findstr /i "websocket chat"')
    
    print("\n3. Recent OMNI2 logs (last 20 lines)...")
    os.system('docker logs omni2 --tail 20')
    
    print("\n4. Recent Dashboard backend logs (last 20 lines)...")
    os.system('docker logs omni2-dashboard-backend --tail 20')


async def main():
    """Main verification function"""
    print("\n" + "="*80)
    print("WEBSOCKET CONVERSATION VERIFICATION")
    print("="*80)
    print(f"Time: {datetime.now()}")
    
    # Check database
    db_ok = await check_database()
    
    # Check logs
    check_logs()
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    if db_ok:
        print("✅ Database schema is correct")
        print("✅ Check the output above for conversation records")
    else:
        print("❌ Database schema needs migration")
    
    print("\n📝 To test WebSocket chat:")
    print("   1. Login to dashboard: http://localhost:3001")
    print("   2. Click chat bubble (bottom-right)")
    print("   3. Click first icon in header to enable WebSocket mode")
    print("   4. Send a message")
    print("   5. Run this script again to verify")
    
    print("\n📊 To view in database:")
    print("   psql -U postgres -d mcp_performance")
    print("   SELECT * FROM omni2.interaction_flows WHERE conversation_id IS NOT NULL ORDER BY created_at DESC LIMIT 5;")


if __name__ == "__main__":
    asyncio.run(main())
