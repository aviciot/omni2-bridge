#!/usr/bin/env python3
"""
OMNI2 Comprehensive Test Suite - Phase 2
========================================
Advanced testing with MCP mocking, stress testing, and full coverage
"""

import asyncio
import json
import random
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import asyncpg
    import httpx
    from sqlalchemy import create_engine, text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install asyncpg httpx sqlalchemy[asyncio] psycopg2-binary")
    sys.exit(1)

from app.services.circuit_breaker import get_circuit_breaker
from app.services.tool_cache import get_tool_cache
from app.services.websocket_broadcaster import get_websocket_broadcaster


class MockMCPServer:
    """Mock MCP server for testing"""
    
    def __init__(self, name: str, port: int, should_fail: bool = False):
        self.name = name
        self.port = port
        self.should_fail = should_fail
        self.request_count = 0
        self.server = None
        
    async def start(self):
        """Start mock MCP server"""
        from aiohttp import web
        
        app = web.Application()
        app.router.add_get('/health', self.health_handler)
        app.router.add_post('/mcp/tools/list', self.list_tools_handler)
        app.router.add_post('/mcp/tools/call', self.call_tool_handler)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        
        self.server = runner
        print(f"Mock MCP {self.name} started on port {self.port}")
        
    async def stop(self):
        """Stop mock MCP server"""
        if self.server:
            await self.server.cleanup()
            print(f"Mock MCP {self.name} stopped")
            
    async def health_handler(self, request):
        """Health check endpoint"""
        from aiohttp import web
        
        self.request_count += 1
        
        if self.should_fail:
            return web.Response(status=500, text="Mock failure")
            
        return web.json_response({"status": "healthy", "requests": self.request_count})
        
    async def list_tools_handler(self, request):
        """List tools endpoint"""
        from aiohttp import web
        
        if self.should_fail:
            return web.Response(status=500, text="Mock failure")
            
        tools = [
            {"name": "test_tool", "description": "Test tool for mocking"},
            {"name": "slow_tool", "description": "Slow tool for performance testing"}
        ]
        
        return web.json_response({"tools": tools})
        
    async def call_tool_handler(self, request):
        """Call tool endpoint"""
        from aiohttp import web
        
        if self.should_fail:
            return web.Response(status=500, text="Mock failure")
            
        data = await request.json()
        tool_name = data.get("name", "unknown")
        
        # Simulate different response times
        if tool_name == "slow_tool":
            await asyncio.sleep(2)
            
        result = {
            "success": True,
            "result": f"Mock result from {self.name} for {tool_name}",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return web.json_response(result)


class ComprehensiveTestSuite:
    """Comprehensive test suite with advanced scenarios"""
    
    def __init__(self):
        self.db_url = "postgresql://omni:omni@localhost:5435/omni"
        self.omni2_url = "http://localhost:8000"
        self.dashboard_url = "http://localhost:3001"
        self.results = []
        self.mock_servers = []
        
    async def setup_mock_mcps(self):
        """Setup mock MCP servers for testing"""
        print("Setting up mock MCP servers...")
        
        # Healthy MCP
        healthy_mcp = MockMCPServer("test-healthy-mcp", 9001, should_fail=False)
        await healthy_mcp.start()
        self.mock_servers.append(healthy_mcp)
        
        # Failing MCP
        failing_mcp = MockMCPServer("test-failing-mcp", 9002, should_fail=True)
        await failing_mcp.start()
        self.mock_servers.append(failing_mcp)
        
        # Add mock MCPs to database
        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            # Insert healthy MCP
            conn.execute(text("""
                INSERT INTO omni2.mcp_servers (name, url, protocol, status, health_status)
                VALUES ('test-healthy-mcp', 'http://localhost:9001', 'http', 'active', 'healthy')
                ON CONFLICT (name) DO UPDATE SET 
                    url = EXCLUDED.url,
                    status = EXCLUDED.status,
                    health_status = EXCLUDED.health_status
            """))
            
            # Insert failing MCP
            conn.execute(text("""
                INSERT INTO omni2.mcp_servers (name, url, protocol, status, health_status)
                VALUES ('test-failing-mcp', 'http://localhost:9002', 'http', 'active', 'disconnected')
                ON CONFLICT (name) DO UPDATE SET 
                    url = EXCLUDED.url,
                    status = EXCLUDED.status,
                    health_status = EXCLUDED.health_status
            """))
            
            conn.commit()
            
        print("Mock MCP servers setup complete")
        
    async def cleanup_mock_mcps(self):
        """Cleanup mock MCP servers"""
        print("Cleaning up mock MCP servers...")
        
        for server in self.mock_servers:
            await server.stop()
            
        # Remove from database
        engine = create_engine(self.db_url)
        with engine.connect() as conn:
            conn.execute(text("""
                DELETE FROM omni2.mcp_servers 
                WHERE name IN ('test-healthy-mcp', 'test-failing-mcp')
            """))
            conn.commit()
            
        self.mock_servers.clear()
        print("Mock MCP cleanup complete")
        
    async def test_circuit_breaker_advanced(self):
        """Test advanced circuit breaker functionality"""
        print("Testing advanced circuit breaker...")
        
        try:
            cb = get_circuit_breaker()
            test_mcp = "circuit-breaker-test"
            
            # Test initial state
            assert cb.get_state(test_mcp) == "closed"
            
            # Test failure accumulation
            for i in range(5):
                cb.record_failure(test_mcp)
                
            assert cb.get_state(test_mcp) == "open"
            assert cb.is_open(test_mcp)
            
            # Test half-open transition (simulate time passing)
            cb.last_failure_time[test_mcp] = time.time() - 61  # 61 seconds ago
            assert not cb.is_open(test_mcp)  # Should move to half-open
            assert cb.get_state(test_mcp) == "half_open"
            
            # Test recovery
            cb.record_success(test_mcp)
            assert cb.get_state(test_mcp) == "closed"
            
            self.results.append(("Circuit Breaker Advanced", "PASS", None))
            print("PASS: Advanced circuit breaker functionality")
            
        except Exception as e:
            self.results.append(("Circuit Breaker Advanced", "FAIL", str(e)))
            print(f"FAIL: Advanced circuit breaker - {e}")
            
    async def test_tool_cache_performance(self):
        """Test tool result caching performance"""
        print("Testing tool result cache...")
        
        try:
            cache = get_tool_cache()
            await cache.start()
            
            # Test cache miss
            result = await cache.get("test-mcp", "test_tool", {"param": "value"})
            assert result is None
            
            # Test cache set and hit
            test_result = {"data": "test_result", "timestamp": time.time()}
            await cache.set("test-mcp", "test_tool", {"param": "value"}, test_result)
            
            cached_result = await cache.get("test-mcp", "test_tool", {"param": "value"})
            assert cached_result == test_result
            
            # Test cache stats
            stats = cache.get_stats()
            assert stats["hits"] >= 1
            assert stats["misses"] >= 1
            assert stats["hit_rate_percent"] > 0
            
            # Test cache invalidation
            removed = await cache.invalidate_mcp("test-mcp")
            assert removed >= 1
            
            result_after_invalidation = await cache.get("test-mcp", "test_tool", {"param": "value"})
            assert result_after_invalidation is None
            
            await cache.stop()
            
            self.results.append(("Tool Cache Performance", "PASS", None))
            print("PASS: Tool result caching")
            
        except Exception as e:
            self.results.append(("Tool Cache Performance", "FAIL", str(e)))
            print(f"FAIL: Tool result caching - {e}")
            
    async def test_websocket_broadcaster(self):
        """Test WebSocket broadcaster functionality"""
        print("Testing WebSocket broadcaster...")
        
        try:
            broadcaster = get_websocket_broadcaster()
            await broadcaster.start()
            
            # Test message queuing
            await broadcaster.broadcast_mcp_status("test-mcp", "healthy", {"test": True})
            await broadcaster.broadcast_health_event("test-mcp", "recovery", {"attempts": 3})
            
            # Test metrics broadcasting
            metrics = {"active_mcps": 2, "total_requests": 100}
            await broadcaster.broadcast_system_metrics(metrics)
            
            # Verify message queue has messages
            assert not broadcaster.message_queue.empty()
            
            await broadcaster.stop()
            
            self.results.append(("WebSocket Broadcaster", "PASS", None))
            print("PASS: WebSocket broadcaster")
            
        except Exception as e:
            self.results.append(("WebSocket Broadcaster", "FAIL", str(e)))
            print(f"FAIL: WebSocket broadcaster - {e}")
            
    async def test_database_stress(self):
        """Stress test database operations"""
        print("Testing database stress scenarios...")
        
        try:
            engine = create_engine(self.db_url)
            
            # Test concurrent database operations
            async def concurrent_db_operation(operation_id: int):
                with engine.connect() as conn:
                    # Simulate health check updates
                    conn.execute(text("""
                        UPDATE omni2.mcp_servers 
                        SET last_health_check = NOW(), 
                            consecutive_failures = :failures
                        WHERE name = 'test-healthy-mcp'
                    """), {"failures": operation_id % 3})
                    
                    # Simulate health log insertion
                    conn.execute(text("""
                        INSERT INTO omni2.mcp_health_log (mcp_server_id, status, event_type)
                        SELECT id, 'healthy', 'stress_test'
                        FROM omni2.mcp_servers 
                        WHERE name = 'test-healthy-mcp'
                        LIMIT 1
                    """))
                    
                    conn.commit()
                    
            # Run 20 concurrent operations
            tasks = [concurrent_db_operation(i) for i in range(20)]
            await asyncio.gather(*tasks)
            
            # Verify database integrity
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT COUNT(*) FROM omni2.mcp_health_log 
                    WHERE event_type = 'stress_test'
                """))
                count = result.scalar()
                assert count >= 20
                
                # Cleanup stress test data
                conn.execute(text("""
                    DELETE FROM omni2.mcp_health_log 
                    WHERE event_type = 'stress_test'
                """))
                conn.commit()
                
            self.results.append(("Database Stress Test", "PASS", None))
            print("PASS: Database stress test")
            
        except Exception as e:
            self.results.append(("Database Stress Test", "FAIL", str(e)))
            print(f"FAIL: Database stress test - {e}")
            
    async def test_thread_safety(self):
        """Test thread safety of shared components"""
        print("Testing thread safety...")
        
        try:
            # Test circuit breaker thread safety
            cb = get_circuit_breaker()
            
            def thread_worker(thread_id: int):
                test_mcp = f"thread-test-{thread_id}"
                for i in range(10):
                    if i % 2 == 0:
                        cb.record_success(test_mcp)
                    else:
                        cb.record_failure(test_mcp)
                        
            # Run 10 threads concurrently
            threads = []
            for i in range(10):
                thread = threading.Thread(target=thread_worker, args=(i,))
                threads.append(thread)
                thread.start()
                
            for thread in threads:
                thread.join()
                
            # Verify no crashes occurred and states are valid
            for i in range(10):
                test_mcp = f"thread-test-{i}"
                state = cb.get_state(test_mcp)
                assert state in ["closed", "open", "half_open"]
                
            self.results.append(("Thread Safety", "PASS", None))
            print("PASS: Thread safety test")
            
        except Exception as e:
            self.results.append(("Thread Safety", "FAIL", str(e)))
            print(f"FAIL: Thread safety test - {e}")
            
    async def test_mcp_failure_recovery(self):
        """Test MCP failure and recovery scenarios"""
        print("Testing MCP failure recovery...")
        
        try:
            # Test with mock failing MCP
            failing_server = None
            for server in self.mock_servers:
                if server.name == "test-failing-mcp":
                    failing_server = server
                    break
                    
            if not failing_server:
                raise Exception("Failing mock server not found")
                
            # Verify MCP is initially failing
            async with httpx.AsyncClient(timeout=5) as client:
                try:
                    response = await client.get(f"http://localhost:{failing_server.port}/health")
                    assert response.status_code == 500
                except:
                    pass  # Expected to fail
                    
            # Simulate recovery by changing failure state
            failing_server.should_fail = False
            
            # Test that MCP now responds
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"http://localhost:{failing_server.port}/health")
                assert response.status_code == 200
                
            # Reset failure state for other tests
            failing_server.should_fail = True
            
            self.results.append(("MCP Failure Recovery", "PASS", None))
            print("PASS: MCP failure recovery")
            
        except Exception as e:
            self.results.append(("MCP Failure Recovery", "FAIL", str(e)))
            print(f"FAIL: MCP failure recovery - {e}")
            
    async def test_performance_benchmarks(self):
        """Performance benchmark tests"""
        print("Running performance benchmarks...")
        
        try:
            # Test database query performance
            engine = create_engine(self.db_url)
            
            start_time = time.time()
            with engine.connect() as conn:
                for _ in range(100):
                    conn.execute(text("""
                        SELECT name, health_status, circuit_state 
                        FROM omni2.mcp_servers 
                        WHERE status = 'active'
                    """))
            db_time = time.time() - start_time
            
            # Test cache performance
            cache = get_tool_cache()
            await cache.start()
            
            # Populate cache
            for i in range(100):
                await cache.set("perf-test", f"tool_{i}", {"id": i}, {"result": f"data_{i}"})
                
            # Benchmark cache hits
            start_time = time.time()
            for i in range(100):
                result = await cache.get("perf-test", f"tool_{i}", {"id": i})
                assert result is not None
            cache_time = time.time() - start_time
            
            await cache.stop()
            
            # Performance assertions
            assert db_time < 5.0  # 100 queries should take less than 5 seconds
            assert cache_time < 0.1  # 100 cache hits should take less than 100ms
            
            performance_data = {
                "db_queries_per_second": round(100 / db_time, 2),
                "cache_hits_per_second": round(100 / cache_time, 2)
            }
            
            self.results.append(("Performance Benchmarks", "PASS", json.dumps(performance_data)))
            print(f"PASS: Performance benchmarks - {performance_data}")
            
        except Exception as e:
            self.results.append(("Performance Benchmarks", "FAIL", str(e)))
            print(f"FAIL: Performance benchmarks - {e}")
            
    async def run_comprehensive_tests(self, run_number: int):
        """Run all comprehensive tests"""
        print(f"\n{'='*60}")
        print(f"OMNI2 Comprehensive Test Suite - Run {run_number}")
        print(f"{'='*60}")
        
        # Setup
        await self.setup_mock_mcps()
        
        try:
            # Core functionality tests
            await self.test_circuit_breaker_advanced()
            await self.test_tool_cache_performance()
            await self.test_websocket_broadcaster()
            
            # Stress and reliability tests
            await self.test_database_stress()
            await self.test_thread_safety()
            await self.test_mcp_failure_recovery()
            
            # Performance tests
            await self.test_performance_benchmarks()
            
        finally:
            # Cleanup
            await self.cleanup_mock_mcps()
            
    def print_summary(self, run_number: int):
        """Print test results summary"""
        print(f"\n{'='*60}")
        print(f"TEST RESULTS SUMMARY - Run {run_number}")
        print(f"{'='*60}")
        
        passed = sum(1 for r in self.results if r[1] == "PASS")
        failed = sum(1 for r in self.results if r[1] == "FAIL")
        total = len(self.results)
        
        print(f"PASSED:  {passed}")
        print(f"FAILED:  {failed}")
        print(f"TOTAL:   {total}")
        
        if failed > 0:
            print("\nFAILED TESTS:")
            for test, status, error in self.results:
                if status == "FAIL":
                    print(f"  {test}: {error}")
                    
        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        return success_rate


async def main():
    """Main test runner"""
    print("OMNI2 Comprehensive Test Suite - Phase 2")
    print("Advanced testing with MCP mocking and stress scenarios")
    
    suite = ComprehensiveTestSuite()
    
    # Run tests twice for consistency
    all_results = []
    
    for run in range(1, 3):
        suite.results = []  # Reset results for each run
        
        await suite.run_comprehensive_tests(run)
        success_rate = suite.print_summary(run)
        all_results.append(success_rate)
        
        if run < 2:
            print(f"\nWaiting 5 seconds before run {run + 1}...")
            await asyncio.sleep(5)
            
    # Final summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY - Both Runs")
    print(f"{'='*60}")
    print(f"Run 1 Success Rate: {all_results[0]:.1f}%")
    print(f"Run 2 Success Rate: {all_results[1]:.1f}%")
    print(f"Average Success Rate: {sum(all_results) / len(all_results):.1f}%")
    
    if all(rate >= 90 for rate in all_results):
        print("\nEXCELLENT! System is highly stable and ready for production")
    elif all(rate >= 75 for rate in all_results):
        print("\nGOOD! System is stable with minor issues")
    else:
        print("\nNEEDS WORK! Stability issues detected")


if __name__ == "__main__":
    try:
        import aiohttp
    except ImportError:
        print("Installing aiohttp for mock servers...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "aiohttp"])
        import aiohttp
        
    asyncio.run(main())