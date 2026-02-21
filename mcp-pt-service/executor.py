"""Parallel Test Execution Engine."""

import asyncio
import time
from typing import Dict, List, Any, Callable, Optional
from test_registry import get_test_function
from mcp_client import MCPConnectionError
from logger import logger

# If more than this fraction of tests errored, the run is flagged inconclusive.
_INCONCLUSIVE_ERROR_THRESHOLD = 0.6


class PTExecutor:
    """Parallel test executor with semaphore control."""

    def __init__(self, max_parallel: int = 5, timeout_seconds: int = 300,
                 run_id: int = None, redis_client=None):
        self.max_parallel = max_parallel
        self.timeout_seconds = timeout_seconds
        self.semaphore = asyncio.Semaphore(max_parallel)
        self.run_id = run_id
        self.redis_client = redis_client
        self._cancelled = False     # local cache so we only hit Redis once

    async def _is_cancelled(self) -> bool:
        """Check Redis for a cancellation flag set by the cancel endpoint."""
        if self._cancelled:
            return True
        if self.run_id and self.redis_client:
            try:
                flag = await self.redis_client.get(f"pt_run:{self.run_id}:cancel")
                if flag:
                    self._cancelled = True
                    logger.info(f"Cancellation flag detected for run {self.run_id}")
                    return True
            except Exception as e:
                logger.warning(f"Could not check cancel flag: {e}")
        return False

    async def smoke_test(self, mcp_client) -> None:
        """Verify the MCP is reachable before running the full suite.

        Raises MCPConnectionError if the session cannot be established so the
        caller can abort cleanly rather than queuing hundreds of doomed tests.
        """
        await mcp_client._ensure_session()
        logger.info("Smoke test passed — MCP is reachable")

    async def run_tests(self, test_plan: Dict, mcp_client,
                        on_result: Optional[Callable] = None) -> List[Dict]:
        """Execute all tests in parallel with rate limiting.

        on_result: optional async callback called immediately after each test
                   completes, with the result dict as the argument.

        Returns the result list.  Callers should check calculate_summary()
        for the 'inconclusive' flag when the error rate is too high.
        """
        tests = test_plan.get("tests", [])
        logger.info(f"Executing {len(tests)} tests with max_parallel={self.max_parallel}")

        tasks = [self._run_test_with_limit(test, mcp_client, on_result) for test in tests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = {
                    "category": tests[i].get("category", "unknown"),
                    "test_name": tests[i].get("test", "unknown"),
                    "tool_name": tests[i].get("tool"),
                    "status": "error",
                    "severity": "info",
                    "evidence": f"Test error: {str(result)[:200]}",
                    "error_message": str(result),
                    "request": tests[i].get("params", {}),
                    "response": {},
                    "latency_ms": 0
                }
                if on_result:
                    await on_result(error_result)
                final_results.append(error_result)
            else:
                final_results.append(result)

        return final_results

    async def _run_test_with_limit(self, test: Dict, mcp_client,
                                   on_result: Optional[Callable] = None) -> Dict:
        """Run single test with semaphore, then fire on_result callback.

        Checks the cancellation flag BEFORE acquiring the semaphore so that
        pending tests are skipped immediately when a cancel is requested.
        Already-running tests inside the semaphore are allowed to finish.
        """
        if await self._is_cancelled():
            result = {
                "category":           test.get("category", "unknown"),
                "test_name":          test.get("test", "unknown"),
                "tool_name":          test.get("tool"),
                "status":             "error",
                "severity":           "info",
                "evidence":           "TEST ERROR: Run cancelled by user",
                "request":            test.get("params", {}),
                "response":           {},
                "latency_ms":         0,
                "error_message":      "cancelled",
                "presidio_findings":  None,
                "trufflehog_findings": None,
            }
            if on_result:
                await on_result(result)
            return result

        async with self.semaphore:
            result = await self._execute_test(test, mcp_client)
            if on_result:
                await on_result(result)
            return result
    
    async def _execute_test(self, test: Dict, mcp_client) -> Dict:
        """Execute single test with timeout."""
        category = test.get("category")
        test_name = test.get("test")
        tool_name = test.get("tool")
        params = test.get("params", {})
        
        start = time.time()
        
        try:
            # Get test function
            test_func = get_test_function(category, test_name)
            
            # Execute with timeout
            result = await asyncio.wait_for(
                test_func(mcp_client, tool_name, params),
                timeout=self.timeout_seconds
            )
            
            latency_ms = int((time.time() - start) * 1000)
            
            # Build result
            return {
                "category": category,
                "test_name": test_name,
                "tool_name": tool_name,
                "status": result.get("status", "error"),
                "severity": result.get("severity", "info"),
                "evidence": result.get("evidence", ""),
                "request": params,
                "response": result.get("response", {}),
                "latency_ms": latency_ms,
                "presidio_findings": result.get("presidio_findings"),
                "trufflehog_findings": result.get("trufflehog_findings"),
                "error_message": None
            }
            
        except asyncio.TimeoutError:
            latency_ms = int((time.time() - start) * 1000)
            return {
                "category": category,
                "test_name": test_name,
                "tool_name": tool_name,
                "status": "error",
                "severity": "info",
                "evidence": f"Test timeout after {self.timeout_seconds}s",
                "request": params,
                "response": {},
                "latency_ms": latency_ms,
                "error_message": "Timeout"
            }
        
        except Exception as e:
            latency_ms = int((time.time() - start) * 1000)
            logger.error(f"Test execution error: {category}.{test_name}: {e}")
            return {
                "category": category,
                "test_name": test_name,
                "tool_name": tool_name,
                "status": "error",
                "severity": "info",
                "evidence": f"Execution error: {str(e)[:200]}",
                "request": params,
                "response": {},
                "latency_ms": latency_ms,
                "error_message": str(e)
            }
    
    def calculate_summary(self, results: List[Dict]) -> Dict:
        """Calculate run summary from results.

        Sets 'inconclusive': True when the error rate exceeds the threshold
        (_INCONCLUSIVE_ERROR_THRESHOLD).  This prevents a run where most tests
        silently errored from appearing as a clean "0 failures" result.
        """
        total = len(results)
        passed = sum(1 for r in results if r["status"] == "pass")
        failed = sum(1 for r in results if r["status"] == "fail")
        errors = sum(1 for r in results if r["status"] == "error")

        critical = sum(1 for r in results if r["severity"] == "critical" and r["status"] == "fail")
        high     = sum(1 for r in results if r["severity"] == "high"     and r["status"] == "fail")
        medium   = sum(1 for r in results if r["severity"] == "medium"   and r["status"] == "fail")
        low      = sum(1 for r in results if r["severity"] == "low"      and r["status"] == "fail")

        error_rate = errors / total if total else 0
        inconclusive = error_rate >= _INCONCLUSIVE_ERROR_THRESHOLD

        if inconclusive:
            logger.warning(
                f"Run flagged INCONCLUSIVE: {errors}/{total} tests errored "
                f"({error_rate:.0%} >= {_INCONCLUSIVE_ERROR_THRESHOLD:.0%} threshold). "
                "Results are not reliable — check MCP connectivity."
            )

        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "critical": critical,
            "high": high,
            "medium": medium,
            "low": low,
            "inconclusive": inconclusive,
        }
