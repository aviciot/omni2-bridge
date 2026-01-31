#!/usr/bin/env python3
"""
Quick Phase 2 Validation Script
Tests Phase 2 services without requiring full Docker setup
"""

import asyncio
import sys
from pathlib import Path

# Fix Windows console encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from app.services.circuit_breaker import get_circuit_breaker
from app.services.tool_cache import get_tool_cache
from app.services.websocket_broadcaster import get_websocket_broadcaster


async def test_circuit_breaker():
    """Test circuit breaker basic functionality"""
    print("\n" + "="*60)
    print("Testing Circuit Breaker...")
    print("="*60)
    
    try:
        cb = get_circuit_breaker()
        test_mcp = "test-mcp"
        
        # Test initial state
        assert cb.get_state(test_mcp) == "closed", "Initial state should be closed"
        print("✅ Initial state: closed")
        
        # Test failure accumulation
        for i in range(5):
            cb.record_failure(test_mcp)
        
        assert cb.get_state(test_mcp) == "open", "Should be open after 5 failures"
        print("✅ Circuit opens after 5 failures")
        
        # Test success recovery
        cb.record_success(test_mcp)
        assert cb.get_state(test_mcp) == "closed", "Should close after success"
        print("✅ Circuit closes after success")
        
        print("✅ Circuit Breaker: PASS")
        return True
        
    except Exception as e:
        print(f"❌ Circuit Breaker: FAIL - {e}")
        return False


async def test_tool_cache():
    """Test tool cache functionality"""
    print("\n" + "="*60)
    print("Testing Tool Cache...")
    print("="*60)
    
    try:
        cache = get_tool_cache()
        await cache.start()
        
        # Test cache miss
        result = await cache.get("test-mcp", "test_tool", {"param": "value"})
        assert result is None, "Should be cache miss"
        print("✅ Cache miss works")
        
        # Test cache set and hit
        test_data = {"result": "test_data"}
        await cache.set("test-mcp", "test_tool", {"param": "value"}, test_data)
        
        cached = await cache.get("test-mcp", "test_tool", {"param": "value"})
        assert cached == test_data, "Should retrieve cached data"
        print("✅ Cache hit works")
        
        # Test statistics
        stats = cache.get_stats()
        assert stats["hits"] >= 1, "Should have at least 1 hit"
        assert stats["misses"] >= 1, "Should have at least 1 miss"
        print(f"✅ Cache stats: {stats['hits']} hits, {stats['misses']} misses, {stats['hit_rate_percent']}% hit rate")
        
        # Test invalidation
        removed = await cache.invalidate_mcp("test-mcp")
        assert removed >= 1, "Should remove at least 1 entry"
        print(f"✅ Invalidation removed {removed} entries")
        
        await cache.stop()
        print("✅ Tool Cache: PASS")
        return True
        
    except Exception as e:
        print(f"❌ Tool Cache: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_websocket_broadcaster():
    """Test WebSocket broadcaster functionality"""
    print("\n" + "="*60)
    print("Testing WebSocket Broadcaster...")
    print("="*60)
    
    try:
        broadcaster = get_websocket_broadcaster()
        await broadcaster.start()
        
        # Test message queuing (without actual WebSocket connections)
        await broadcaster.broadcast_mcp_status("test-mcp", "healthy", {"test": True})
        await broadcaster.broadcast_health_event("test-mcp", "recovery", {"attempts": 3})
        await broadcaster.broadcast_system_metrics({"active_mcps": 2})
        
        # Verify messages are queued
        assert not broadcaster.message_queue.empty(), "Should have queued messages"
        print("✅ Message queuing works")
        
        # Test connection tracking (empty initially)
        assert len(broadcaster.connections) == 0, "Should have no connections"
        print("✅ Connection tracking initialized")
        
        await broadcaster.stop()
        print("✅ WebSocket Broadcaster: PASS")
        return True
        
    except Exception as e:
        print(f"❌ WebSocket Broadcaster: FAIL - {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all validation tests"""
    print("\n" + "="*60)
    print("OMNI2 Phase 2 - Quick Validation")
    print("="*60)
    
    results = []
    
    # Run tests
    results.append(await test_circuit_breaker())
    results.append(await test_tool_cache())
    results.append(await test_websocket_broadcaster())
    
    # Summary
    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - Phase 2 services are working!")
        print("Next step: Restart Docker and test with database")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
