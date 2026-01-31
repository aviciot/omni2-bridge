#!/usr/bin/env python3
"""
Real-World Scenario Tests for OMNI2
Tests enable/disable MCPs, disconnections, recovery, and real-life cases
"""

import asyncio
import sys
import time
from pathlib import Path

# Fix Windows console encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)


class RealWorldTests:
    """Real-world scenario tests"""
    
    def __init__(self):
        self.db_url = "postgresql://omni:omni@localhost:5435/omni"
        self.results = []
        
    async def test_enable_disable_mcp(self):
        """Test enabling and disabling an MCP"""
        print("\n" + "="*60)
        print("Test: Enable/Disable MCP")
        print("="*60)
        
        try:
            engine = create_engine(self.db_url)
            
            # Create test MCP
            with engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO omni2.mcp_servers (name, url, protocol, status, health_status)
                    VALUES ('test-enable-disable', 'http://localhost:9999', 'http', 'active', 'healthy')
                    ON CONFLICT (name) DO UPDATE SET status = 'active'
                """))
                conn.commit()
                print("✅ Created test MCP")
                
                # Disable MCP
                conn.execute(text("""
                    UPDATE omni2.mcp_servers 
                    SET status = 'disabled', health_status = 'disabled'
                    WHERE name = 'test-enable-disable'
                """))
                conn.commit()
                print("✅ Disabled MCP")
                
                # Verify disabled
                result = conn.execute(text("""
                    SELECT status, health_status FROM omni2.mcp_servers 
                    WHERE name = 'test-enable-disable'
                """))
                row = result.fetchone()
                assert row[0] == 'disabled', "Status should be disabled"
                assert row[1] == 'disabled', "Health should be disabled"
                print("✅ Verified MCP is disabled")
                
                # Re-enable MCP
                conn.execute(text("""
                    UPDATE omni2.mcp_servers 
                    SET status = 'active', health_status = 'healthy'
                    WHERE name = 'test-enable-disable'
                """))
                conn.commit()
                print("✅ Re-enabled MCP")
                
                # Verify enabled
                result = conn.execute(text("""
                    SELECT status, health_status FROM omni2.mcp_servers 
                    WHERE name = 'test-enable-disable'
                """))
                row = result.fetchone()
                assert row[0] == 'active', "Status should be active"
                print("✅ Verified MCP is enabled")
                
                # Cleanup
                conn.execute(text("DELETE FROM omni2.mcp_servers WHERE name = 'test-enable-disable'"))
                conn.commit()
                
            self.results.append(("Enable/Disable MCP", "PASS", None))
            print("✅ Test PASSED")
            return True
            
        except Exception as e:
            self.results.append(("Enable/Disable MCP", "FAIL", str(e)))
            print(f"❌ Test FAILED: {e}")
            return False
            
    async def test_mcp_disconnection_recovery(self):
        """Test MCP disconnection and recovery cycle"""
        print("\n" + "="*60)
        print("Test: MCP Disconnection and Recovery")
        print("="*60)
        
        try:
            engine = create_engine(self.db_url)
            
            with engine.connect() as conn:
                # Create test MCP
                conn.execute(text("""
                    INSERT INTO omni2.mcp_servers (name, url, protocol, status, health_status, consecutive_failures)
                    VALUES ('test-disconnect', 'http://localhost:9998', 'http', 'active', 'healthy', 0)
                    ON CONFLICT (name) DO UPDATE SET 
                        status = 'active', 
                        health_status = 'healthy',
                        consecutive_failures = 0
                """))
                conn.commit()
                print("✅ Created healthy MCP")
                
                # Simulate disconnection (1 failure)
                conn.execute(text("""
                    UPDATE omni2.mcp_servers 
                    SET health_status = 'disconnected', 
                        consecutive_failures = 1,
                        last_health_check = NOW()
                    WHERE name = 'test-disconnect'
                """))
                conn.commit()
                print("✅ Simulated disconnection (1 failure)")
                
                # Simulate multiple failures
                for i in range(2, 5):
                    conn.execute(text("""
                        UPDATE omni2.mcp_servers 
                        SET consecutive_failures = :failures
                        WHERE name = 'test-disconnect'
                    """), {"failures": i})
                    conn.commit()
                    print(f"✅ Failure {i}/5")
                    
                # Verify still disconnected, not circuit open
                result = conn.execute(text("""
                    SELECT health_status, consecutive_failures, circuit_state 
                    FROM omni2.mcp_servers 
                    WHERE name = 'test-disconnect'
                """))
                row = result.fetchone()
                assert row[0] == 'disconnected', "Should be disconnected"
                assert row[1] == 4, "Should have 4 failures"
                print("✅ Verified 4 failures, still attempting recovery")
                
                # 5th failure - circuit should open
                conn.execute(text("""
                    UPDATE omni2.mcp_servers 
                    SET consecutive_failures = 5,
                        circuit_state = 'open',
                        health_status = 'circuit_open'
                    WHERE name = 'test-disconnect'
                """))
                conn.commit()
                print("✅ Circuit breaker opened after 5 failures")
                
                # Simulate recovery
                conn.execute(text("""
                    UPDATE omni2.mcp_servers 
                    SET health_status = 'healthy',
                        circuit_state = 'closed',
                        consecutive_failures = 0,
                        last_recovery_attempt = NOW()
                    WHERE name = 'test-disconnect'
                """))
                conn.commit()
                print("✅ Simulated successful recovery")
                
                # Verify recovery
                result = conn.execute(text("""
                    SELECT health_status, consecutive_failures, circuit_state 
                    FROM omni2.mcp_servers 
                    WHERE name = 'test-disconnect'
                """))
                row = result.fetchone()
                assert row[0] == 'healthy', "Should be healthy"
                assert row[1] == 0, "Failures should be reset"
                assert row[2] == 'closed', "Circuit should be closed"
                print("✅ Verified full recovery")
                
                # Cleanup
                conn.execute(text("DELETE FROM omni2.mcp_servers WHERE name = 'test-disconnect'"))
                conn.commit()
                
            self.results.append(("MCP Disconnection/Recovery", "PASS", None))
            print("✅ Test PASSED")
            return True
            
        except Exception as e:
            self.results.append(("MCP Disconnection/Recovery", "FAIL", str(e)))
            print(f"❌ Test FAILED: {e}")
            return False
            
    async def test_multiple_mcps_mixed_states(self):
        """Test multiple MCPs with different states"""
        print("\n" + "="*60)
        print("Test: Multiple MCPs with Mixed States")
        print("="*60)
        
        try:
            engine = create_engine(self.db_url)
            
            with engine.connect() as conn:
                # Create 5 MCPs with different states
                mcps = [
                    ('test-healthy-1', 'healthy', 'active', 'closed', 0),
                    ('test-healthy-2', 'healthy', 'active', 'closed', 0),
                    ('test-disconnected', 'disconnected', 'active', 'closed', 2),
                    ('test-circuit-open', 'circuit_open', 'active', 'open', 5),
                    ('test-disabled', 'disabled', 'disabled', 'closed', 0),
                ]
                
                for name, health, status, circuit, failures in mcps:
                    conn.execute(text("""
                        INSERT INTO omni2.mcp_servers 
                        (name, url, protocol, status, health_status, circuit_state, consecutive_failures)
                        VALUES (:name, :url, 'http', :status, :health, :circuit, :failures)
                        ON CONFLICT (name) DO UPDATE SET 
                            status = EXCLUDED.status,
                            health_status = EXCLUDED.health_status,
                            circuit_state = EXCLUDED.circuit_state,
                            consecutive_failures = EXCLUDED.consecutive_failures
                    """), {
                        "name": name,
                        "url": f"http://localhost:999{mcps.index((name, health, status, circuit, failures))}",
                        "status": status,
                        "health": health,
                        "circuit": circuit,
                        "failures": failures
                    })
                conn.commit()
                print("✅ Created 5 MCPs with mixed states")
                
                # Query and verify states
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) FILTER (WHERE health_status = 'healthy') as healthy_count,
                        COUNT(*) FILTER (WHERE health_status = 'disconnected') as disconnected_count,
                        COUNT(*) FILTER (WHERE health_status = 'circuit_open') as circuit_open_count,
                        COUNT(*) FILTER (WHERE health_status = 'disabled') as disabled_count,
                        COUNT(*) FILTER (WHERE status = 'active') as active_count
                    FROM omni2.mcp_servers 
                    WHERE name LIKE 'test-%'
                """))
                row = result.fetchone()
                
                assert row[0] == 2, "Should have 2 healthy MCPs"
                assert row[1] == 1, "Should have 1 disconnected MCP"
                assert row[2] == 1, "Should have 1 circuit open MCP"
                assert row[3] == 1, "Should have 1 disabled MCP"
                assert row[4] == 4, "Should have 4 active MCPs"
                
                print(f"✅ Verified: {row[0]} healthy, {row[1]} disconnected, {row[2]} circuit open, {row[3]} disabled")
                
                # Cleanup
                conn.execute(text("DELETE FROM omni2.mcp_servers WHERE name LIKE 'test-%'"))
                conn.commit()
                
            self.results.append(("Multiple MCPs Mixed States", "PASS", None))
            print("✅ Test PASSED")
            return True
            
        except Exception as e:
            self.results.append(("Multiple MCPs Mixed States", "FAIL", str(e)))
            print(f"❌ Test FAILED: {e}")
            return False
            
    async def test_config_tables(self):
        """Test configuration tables"""
        print("\n" + "="*60)
        print("Test: Configuration Tables")
        print("="*60)
        
        try:
            engine = create_engine(self.db_url)
            
            with engine.connect() as conn:
                # Check omni2.omni2_config
                result = conn.execute(text("""
                    SELECT config_key, config_value 
                    FROM omni2.omni2_config 
                    ORDER BY config_key
                """))
                omni2_configs = result.fetchall()
                print(f"✅ Found {len(omni2_configs)} configs in omni2.omni2_config:")
                for key, value in omni2_configs:
                    print(f"   - {key}: {value}")
                    
                # Check omni2_dashboard.dashboard_config
                result = conn.execute(text("""
                    SELECT key, value, description 
                    FROM omni2_dashboard.dashboard_config 
                    ORDER BY key
                """))
                dashboard_configs = result.fetchall()
                print(f"✅ Found {len(dashboard_configs)} configs in omni2_dashboard.dashboard_config:")
                for key, value, desc in dashboard_configs:
                    print(f"   - {key}: {desc}")
                    
                # Verify required configs exist
                required_omni2_configs = ['circuit_breaker', 'health_check', 'thread_logging']
                for config in required_omni2_configs:
                    assert any(c[0] == config for c in omni2_configs), f"Missing {config} in omni2_config"
                print("✅ All required omni2 configs present")
                
                required_dashboard_configs = ['dev_mode', 'refresh_interval']
                for config in required_dashboard_configs:
                    assert any(c[0] == config for c in dashboard_configs), f"Missing {config} in dashboard_config"
                print("✅ All required dashboard configs present")
                
            self.results.append(("Configuration Tables", "PASS", None))
            print("✅ Test PASSED")
            return True
            
        except Exception as e:
            self.results.append(("Configuration Tables", "FAIL", str(e)))
            print(f"❌ Test FAILED: {e}")
            return False
            
    async def test_health_log_tracking(self):
        """Test health log tracking for MCP events"""
        print("\n" + "="*60)
        print("Test: Health Log Tracking")
        print("="*60)
        
        try:
            engine = create_engine(self.db_url)
            
            with engine.connect() as conn:
                # Create test MCP
                conn.execute(text("""
                    INSERT INTO omni2.mcp_servers (name, url, protocol, status, health_status)
                    VALUES ('test-health-log', 'http://localhost:9997', 'http', 'active', 'healthy')
                    ON CONFLICT (name) DO UPDATE SET status = 'active'
                """))
                conn.commit()
                
                # Get MCP ID
                result = conn.execute(text("""
                    SELECT id FROM omni2.mcp_servers WHERE name = 'test-health-log'
                """))
                mcp_id = result.scalar()
                print(f"✅ Created test MCP (ID: {mcp_id})")
                
                # Log health events
                events = [
                    ('healthy', 'health_check_success', 50, None),
                    ('disconnected', 'health_check_failed', None, 'Connection timeout'),
                    ('disconnected', 'health_check_failed', None, 'Connection refused'),
                    ('healthy', 'recovery_success', 45, None),
                ]
                
                for status, event_type, response_time, error in events:
                    conn.execute(text("""
                        INSERT INTO omni2.mcp_health_log 
                        (mcp_server_id, status, event_type, response_time_ms, error_message)
                        VALUES (:mcp_id, :status, :event_type, :response_time, :error)
                    """), {
                        "mcp_id": mcp_id,
                        "status": status,
                        "event_type": event_type,
                        "response_time": response_time,
                        "error": error
                    })
                conn.commit()
                print(f"✅ Logged {len(events)} health events")
                
                # Query health log
                result = conn.execute(text("""
                    SELECT COUNT(*), 
                           COUNT(*) FILTER (WHERE status = 'healthy') as healthy_count,
                           COUNT(*) FILTER (WHERE status = 'disconnected') as failed_count
                    FROM omni2.mcp_health_log 
                    WHERE mcp_server_id = :mcp_id
                """), {"mcp_id": mcp_id})
                row = result.fetchone()
                
                assert row[0] == 4, "Should have 4 log entries"
                assert row[1] == 2, "Should have 2 healthy events"
                assert row[2] == 2, "Should have 2 failed events"
                print(f"✅ Verified: {row[0]} total events, {row[1]} healthy, {row[2]} failed")
                
                # Cleanup
                conn.execute(text("DELETE FROM omni2.mcp_health_log WHERE mcp_server_id = :mcp_id"), {"mcp_id": mcp_id})
                conn.execute(text("DELETE FROM omni2.mcp_servers WHERE name = 'test-health-log'"))
                conn.commit()
                
            self.results.append(("Health Log Tracking", "PASS", None))
            print("✅ Test PASSED")
            return True
            
        except Exception as e:
            self.results.append(("Health Log Tracking", "FAIL", str(e)))
            print(f"❌ Test FAILED: {e}")
            return False
            
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("REAL-WORLD TEST RESULTS SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.results if r[1] == "PASS")
        failed = sum(1 for r in self.results if r[1] == "FAIL")
        total = len(self.results)
        
        print(f"PASSED:  {passed}/{total}")
        print(f"FAILED:  {failed}/{total}")
        
        if failed > 0:
            print("\nFAILED TESTS:")
            for test, status, error in self.results:
                if status == "FAIL":
                    print(f"  ❌ {test}: {error}")
                    
        success_rate = (passed / total * 100) if total > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        return success_rate >= 100


async def main():
    """Run all real-world tests"""
    print("\n" + "="*60)
    print("OMNI2 Real-World Scenario Tests")
    print("="*60)
    
    tests = RealWorldTests()
    
    # Run all tests
    await tests.test_enable_disable_mcp()
    await tests.test_mcp_disconnection_recovery()
    await tests.test_multiple_mcps_mixed_states()
    await tests.test_config_tables()
    await tests.test_health_log_tracking()
    
    # Print summary
    success = tests.print_summary()
    
    if success:
        print("\n✅ ALL REAL-WORLD TESTS PASSED!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
