"""PT Config & Comparison API Router."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import db
from config_service import get_config_service

router = APIRouter(prefix="/api/v1/mcp-pt", tags=["pt"])


@router.get("/tests")
async def get_all_tests():
    """Get all categories with their tests - the full test catalog."""
    async with db.pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT c.name AS category, c.description AS category_description,
                   c.severity_default, c.enabled AS category_enabled,
                   f.name AS test_name, f.description AS test_description,
                   f.python_function, f.enabled AS test_enabled
            FROM omni2.pt_test_functions f
            JOIN omni2.pt_categories c ON c.category_id = f.category_id
            ORDER BY c.name, f.name
        """)
        catalog: Dict[str, Any] = {}
        for r in rows:
            cat = r["category"]
            if cat not in catalog:
                catalog[cat] = {
                    "description": r["category_description"],
                    "severity_default": r["severity_default"],
                    "enabled": r["category_enabled"],
                    "tests": []
                }
            catalog[cat]["tests"].append({
                "name": r["test_name"],
                "description": r["test_description"],
                "python_function": r["python_function"],
                "enabled": r["test_enabled"]
            })
        return catalog


@router.get("/config")
async def get_all_config():
    """Get all PT service configuration."""
    config_service = get_config_service()
    return {
        "llm_providers": await config_service.get('llm_providers'),
        "execution_settings": await config_service.get('execution_settings'),
        "progress_stages": await config_service.get('progress_stages'),
        "redis_config": await config_service.get('redis_config')
    }


class UpdateConfigRequest(BaseModel):
    config_key: str
    config_value: Dict[str, Any]
    updated_by: Optional[int] = None


@router.put("/config")
async def update_config(request: UpdateConfigRequest):
    """Update PT service configuration."""
    config_service = get_config_service()
    success = await config_service.update(
        request.config_key, 
        request.config_value,
        request.updated_by
    )
    
    if not success:
        raise HTTPException(404, f"Configuration key not found: {request.config_key}")
    
    return {"message": "Configuration updated", "key": request.config_key}


@router.get("/mcps")
async def get_mcps():
    """Get all active MCP servers from omni2.mcp_servers (same as MCP tab)."""
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, name, url, protocol, description, health_status, 
                      last_health_check, timeout_seconds, status
               FROM omni2.mcp_servers 
               WHERE status = 'active'
               ORDER BY name"""
        )
        return [dict(row) for row in rows]


@router.get("/categories")
async def get_categories():
    """Get all PT categories."""
    categories = await db.get_categories()
    return categories


@router.get("/categories/{category_name}/tests")
async def get_category_tests(category_name: str):
    """Get all tests for a specific category."""
    async with db.pool.acquire() as conn:
        # Get category
        category = await conn.fetchrow(
            "SELECT * FROM omni2.pt_categories WHERE name = $1",
            category_name
        )
        
        if not category:
            raise HTTPException(404, f"Category not found: {category_name}")
        
        # Get tests
        tests = await conn.fetch(
            """
            SELECT name, description, python_function, enabled
            FROM omni2.pt_test_functions
            WHERE category_id = $1
            ORDER BY name
            """,
            category["category_id"]
        )
        
        return {
            "category": dict(category),
            "tests": [dict(t) for t in tests],
            "test_count": len(tests)
        }


@router.get("/presets")
async def get_presets():
    """Get all PT presets."""
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM omni2.pt_presets WHERE enabled = true ORDER BY preset_id"
        )
        return [dict(row) for row in rows]


@router.get("/mcps/{mcp_id}/history")
async def get_mcp_history(mcp_id: str, limit: int = 20):
    """Get PT history for MCP."""
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT run_id, preset, status, total_tests, passed, failed, 
                   critical, high, medium, low, duration_ms, created_at
            FROM omni2.pt_runs
            WHERE mcp_name = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            mcp_id, limit
        )
        return [dict(row) for row in rows]


class CompareRequest(BaseModel):
    run_id_1: int
    run_id_2: int


@router.post("/compare")
async def compare_runs(request: CompareRequest):
    """Compare two PT runs."""
    
    async with db.pool.acquire() as conn:
        # Get both runs
        run1 = await conn.fetchrow(
            "SELECT * FROM omni2.pt_runs WHERE run_id = $1",
            request.run_id_1
        )
        run2 = await conn.fetchrow(
            "SELECT * FROM omni2.pt_runs WHERE run_id = $1",
            request.run_id_2
        )
        
        if not run1 or not run2:
            raise HTTPException(404, "One or both runs not found")
        
        # Get results for both
        results1 = await conn.fetch(
            "SELECT * FROM omni2.pt_test_results WHERE run_id = $1",
            request.run_id_1
        )
        results2 = await conn.fetch(
            "SELECT * FROM omni2.pt_test_results WHERE run_id = $1",
            request.run_id_2
        )
        
        # Build test key maps
        def make_key(r):
            return f"{r['category']}.{r['test_name']}.{r['tool_name']}"
        
        map1 = {make_key(dict(r)): dict(r) for r in results1}
        map2 = {make_key(dict(r)): dict(r) for r in results2}
        
        # Find differences
        new_failures = []
        fixed_issues = []
        regressions = []
        improvements = []
        unchanged = 0
        
        all_keys = set(map1.keys()) | set(map2.keys())
        
        for key in all_keys:
            r1 = map1.get(key)
            r2 = map2.get(key)
            
            if not r1:
                # New test in run2
                if r2["status"] == "fail":
                    new_failures.append({
                        "category": r2["category"],
                        "test": r2["test_name"],
                        "tool": r2["tool_name"],
                        "severity": r2["severity"]
                    })
            elif not r2:
                # Test removed in run2
                continue
            else:
                # Both exist - compare
                if r1["status"] == "fail" and r2["status"] == "pass":
                    fixed_issues.append({
                        "category": r1["category"],
                        "test": r1["test_name"],
                        "tool": r1["tool_name"]
                    })
                    improvements.append(key)
                elif r1["status"] == "pass" and r2["status"] == "fail":
                    regressions.append({
                        "category": r2["category"],
                        "test": r2["test_name"],
                        "tool": r2["tool_name"],
                        "severity": r2["severity"]
                    })
                else:
                    unchanged += 1
        
        return {
            "run_1": {
                "run_id": run1["run_id"],
                "mcp_name": run1["mcp_name"],
                "created_at": run1["created_at"],
                "total_tests": run1["total_tests"],
                "failed": run1["failed"]
            },
            "run_2": {
                "run_id": run2["run_id"],
                "mcp_name": run2["mcp_name"],
                "created_at": run2["created_at"],
                "total_tests": run2["total_tests"],
                "failed": run2["failed"]
            },
            "comparison": {
                "new_failures": new_failures,
                "fixed_issues": fixed_issues,
                "regressions": len(regressions),
                "improvements": len(improvements),
                "unchanged": unchanged
            },
            "details": {
                "regressions": regressions,
                "improvements_list": fixed_issues
            }
        }
