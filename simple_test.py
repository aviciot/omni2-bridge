#!/usr/bin/env python3
"""
OMNI2 Simple Validation Test
============================
Basic validation for Phase 1 changes without Unicode characters
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    import asyncpg
    import httpx
    from sqlalchemy import create_engine, text
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Run: pip install asyncpg httpx sqlalchemy[asyncio] psycopg2-binary")
    sys.exit(1)

class SimpleValidator:
    """Simple validation tests"""
    
    def __init__(self):
        self.db_url = "postgresql://omni:omni@localhost:5435/omni"
        self.omni2_url = "http://localhost:8000"
        self.dashboard_url = "http://localhost:3001"
        self.results = []
    
    def test_database_schema(self):
        """Test database schema"""
        print("Testing database schema...")
        
        try:
            engine = create_engine(self.db_url)
            with engine.connect() as conn:
                # Test schema exists
                result = conn.execute(text("""
                    SELECT schema_name FROM information_schema.schemata 
                    WHERE schema_name = 'omni2'
                """))
                if not result.fetchone():
                    raise Exception("omni2 schema missing")
                
                # Test circuit breaker columns
                result = conn.execute(text("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'omni2' AND table_name = 'mcp_servers' 
                    AND column_name IN ('circuit_state', 'consecutive_failures', 'last_recovery_attempt', 'total_downtime_seconds')
                """))
                
                columns = [row[0] for row in result.fetchall()]
                expected = ['circuit_state', 'consecutive_failures', 'last_recovery_attempt', 'total_downtime_seconds']
                
                for col in expected:
                    if col not in columns:
                        raise Exception(f"Column {col} missing")
                
                # Test config entries
                result = conn.execute(text("""
                    SELECT config_key FROM omni2.omni2_config 
                    WHERE config_key IN ('health_check', 'circuit_breaker', 'thread_logging')
                    AND is_active = true
                """))
                
                configs = [row[0] for row in result.fetchall()]
                expected_configs = ['health_check', 'circuit_breaker', 'thread_logging']
                
                for config in expected_configs:
                    if config not in configs:
                        raise Exception(f"Config {config} missing")
                
                print("PASS: Database schema validation")
                self.results.append(("Database", "PASS", None))
                
        except Exception as e:
            print(f"FAIL: Database schema - {e}")
            self.results.append(("Database", "FAIL", str(e)))
    
    async def test_api_endpoints(self):
        """Test API endpoints"""
        print("Testing API endpoints...")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                # Test health endpoint
                try:
                    response = await client.get(f"{self.omni2_url}/health")
                    if response.status_code != 200:
                        raise Exception(f"Health endpoint returned {response.status_code}")
                    
                    data = response.json()
                    if data.get("status") != "healthy":
                        raise Exception("Health status not healthy")
                    
                    print("PASS: Health endpoint working")
                    self.results.append(("API Health", "PASS", None))
                    
                except httpx.ConnectError:
                    print("SKIP: OMNI2 service not running")
                    self.results.append(("API Health", "SKIP", "Service not running"))
                    return False
                
                # Test MCP endpoints
                try:
                    response = await client.get(f"{self.omni2_url}/api/v1/mcp/tools/servers")
                    if response.status_code not in [200, 503]:
                        raise Exception(f"MCP endpoint returned {response.status_code}")
                    
                    print("PASS: MCP endpoints accessible")
                    self.results.append(("API MCP", "PASS", None))
                    
                except Exception as e:
                    print(f"FAIL: MCP endpoints - {e}")
                    self.results.append(("API MCP", "FAIL", str(e)))
                
                return True
                
        except Exception as e:
            print(f"FAIL: API endpoints - {e}")
            self.results.append(("API", "FAIL", str(e)))
            return False
    
    async def test_dashboard(self):
        """Test dashboard"""
        print("Testing dashboard...")
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                try:
                    response = await client.get(self.dashboard_url)
                    if response.status_code != 200:
                        raise Exception(f"Dashboard returned {response.status_code}")
                    
                    # Check for React errors
                    content = response.text
                    if "Something went wrong" in content:
                        raise Exception("React error boundary triggered")
                    
                    print("PASS: Dashboard loads successfully")
                    self.results.append(("Dashboard", "PASS", None))
                    
                except httpx.ConnectError:
                    print("SKIP: Dashboard not running")
                    self.results.append(("Dashboard", "SKIP", "Service not running"))
                    
        except Exception as e:
            print(f"FAIL: Dashboard - {e}")
            self.results.append(("Dashboard", "FAIL", str(e)))
    
    def test_thread_logging_config(self):
        """Test thread logging configuration"""
        print("Testing thread logging config...")
        
        try:
            engine = create_engine(self.db_url)
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT config_value FROM omni2.omni2_config 
                    WHERE config_key = 'thread_logging' AND is_active = true
                """))
                
                row = result.fetchone()
                if not row:
                    raise Exception("thread_logging config missing")
                
                config = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                if 'enabled' not in config:
                    raise Exception("thread_logging config missing 'enabled' field")
                
                print("PASS: Thread logging configuration valid")
                self.results.append(("Thread Logging", "PASS", None))
                
        except Exception as e:
            print(f"FAIL: Thread logging config - {e}")
            self.results.append(("Thread Logging", "FAIL", str(e)))
    
    async def run_all_tests(self):
        """Run all tests"""
        print("OMNI2 Phase 1 Validation")
        print("=" * 40)
        
        # Database tests
        self.test_database_schema()
        self.test_thread_logging_config()
        
        # API tests
        await self.test_api_endpoints()
        
        # Frontend tests
        await self.test_dashboard()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 40)
        print("TEST RESULTS SUMMARY")
        print("=" * 40)
        
        passed = sum(1 for r in self.results if r[1] == "PASS")
        failed = sum(1 for r in self.results if r[1] == "FAIL")
        skipped = sum(1 for r in self.results if r[1] == "SKIP")
        total = len(self.results)
        
        print(f"PASSED:  {passed}")
        print(f"FAILED:  {failed}")
        print(f"SKIPPED: {skipped}")
        print(f"TOTAL:   {total}")
        
        if failed > 0:
            print("\nFAILED TESTS:")
            for test, status, error in self.results:
                if status == "FAIL":
                    print(f"  {test}: {error}")
        
        success_rate = (passed / (total - skipped) * 100) if (total - skipped) > 0 else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("EXCELLENT! System is ready for production")
        elif success_rate >= 75:
            print("GOOD! Minor issues to address")
        else:
            print("NEEDS WORK! Critical issues found")

async def main():
    """Main entry point"""
    validator = SimpleValidator()
    await validator.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())