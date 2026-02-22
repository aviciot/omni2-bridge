"""Database operations for MCP PT Service."""

import asyncpg
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from config import settings
from logger import logger

pool: asyncpg.Pool = None


async def _init_connection(conn):
    """Register JSON/JSONB codecs so asyncpg returns dicts instead of raw strings."""
    await conn.set_type_codec('jsonb', encoder=json.dumps, decoder=json.loads, schema='pg_catalog')
    await conn.set_type_codec('json',  encoder=json.dumps, decoder=json.loads, schema='pg_catalog')


async def init_db():
    """Initialize database connection pool and ensure prescan cache table exists."""
    global pool
    pool = await asyncpg.create_pool(
        host=settings.DATABASE_HOST,
        port=settings.DATABASE_PORT,
        database=settings.DATABASE_NAME,
        user=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD,
        min_size=2,
        max_size=10,
        init=_init_connection,
    )
    logger.info("Database pool created")

    # Ensure prescan cache table + mission_briefing column exist (idempotent)
    async with pool.acquire() as conn:
        await conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {settings.DATABASE_SCHEMA}.pt_prescan_cache (
                id            SERIAL PRIMARY KEY,
                mcp_server_id INTEGER NOT NULL REFERENCES omni2.mcp_servers(id) ON DELETE CASCADE,
                tools_hash    TEXT    NOT NULL,
                briefing      JSONB   NOT NULL,
                is_stale      BOOLEAN NOT NULL DEFAULT FALSE,
                created_at    TIMESTAMPTZ DEFAULT now(),
                updated_at    TIMESTAMPTZ DEFAULT now(),
                UNIQUE (mcp_server_id)
            )
        """)
        await conn.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_pt_prescan_mcp
            ON {settings.DATABASE_SCHEMA}.pt_prescan_cache (mcp_server_id)
        """)
        # Add mission_briefing column to pt_runs if it doesn't exist yet
        await conn.execute(f"""
            ALTER TABLE {settings.DATABASE_SCHEMA}.pt_runs
            ADD COLUMN IF NOT EXISTS mission_briefing JSONB
        """)
        # Add judge-enriched columns to pt_agent_stories
        for col_ddl in [
            f"ALTER TABLE {settings.DATABASE_SCHEMA}.pt_agent_stories ADD COLUMN IF NOT EXISTS was_planned BOOLEAN",
            f"ALTER TABLE {settings.DATABASE_SCHEMA}.pt_agent_stories ADD COLUMN IF NOT EXISTS coverage_pct INTEGER",
            f"ALTER TABLE {settings.DATABASE_SCHEMA}.pt_agent_stories ADD COLUMN IF NOT EXISTS surprises TEXT[]",
        ]:
            await conn.execute(col_ddl)
    logger.info("Prescan cache schema ensured")


async def close_db():
    """Close database connection pool."""
    global pool
    if pool:
        await pool.close()
        logger.info("Database pool closed")


async def create_pt_run(mcp_server_id: int, mcp_name: str, preset: str,
                        llm_provider: str, llm_model: str, created_by: int,
                        plan_source: str = 'llm') -> int:
    """Create new PT run."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""
            INSERT INTO {settings.DATABASE_SCHEMA}.pt_runs
            (mcp_server_id, mcp_name, preset, status, llm_provider, llm_model, created_by, plan_source)
            VALUES ($1, $2, $3, 'pending', $4, $5, $6, $7)
            RETURNING run_id
            """,
            mcp_server_id, mcp_name, preset, llm_provider, llm_model, created_by, plan_source
        )
        return row['run_id']


async def get_cached_plan(cache_key: str) -> Optional[Dict]:
    """Return unexpired cached test plan dict, or None on miss."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""SELECT test_plan, llm_cost_usd
                FROM {settings.DATABASE_SCHEMA}.pt_plan_cache
                WHERE cache_key = $1 AND expires_at > now()""",
            cache_key
        )
        return dict(row) if row else None


async def save_plan_cache(cache_key: str, mcp_name: str, preset: str,
                          tools_hash: str, test_plan: Dict, llm_cost_usd: float):
    """Upsert a test plan into cache with 7-day TTL."""
    async with pool.acquire() as conn:
        await conn.execute(
            f"""
            INSERT INTO {settings.DATABASE_SCHEMA}.pt_plan_cache
                (cache_key, mcp_name, preset, tools_hash, test_plan, llm_cost_usd)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6)
            ON CONFLICT (cache_key) DO UPDATE SET
                test_plan    = EXCLUDED.test_plan,
                llm_cost_usd = EXCLUDED.llm_cost_usd,
                created_at   = now(),
                expires_at   = now() + INTERVAL '7 days'
            """,
            cache_key, mcp_name, preset, tools_hash,
            json.dumps(test_plan), float(llm_cost_usd or 0)
        )


async def update_pt_run(run_id: int, **kwargs):
    """Update PT run fields."""
    fields = []
    values = []
    idx = 1
    
    for key, value in kwargs.items():
        # Convert dicts to JSON strings for JSONB columns
        if key in ('stage_details', 'security_profile', 'test_plan', 'mission_briefing') and isinstance(value, dict):
            value = json.dumps(value)
        fields.append(f"{key} = ${idx}")
        values.append(value)
        idx += 1
    
    values.append(run_id)
    query = f"UPDATE {settings.DATABASE_SCHEMA}.pt_runs SET {', '.join(fields)} WHERE run_id = ${idx}"
    
    async with pool.acquire() as conn:
        await conn.execute(query, *values)


async def save_test_result(run_id: int, category: str, test_name: str, 
                          tool_name: Optional[str], status: str, severity: str,
                          request: Dict, response: Dict, evidence: str, 
                          latency_ms: int, presidio_findings: Optional[Dict] = None,
                          trufflehog_findings: Optional[Dict] = None,
                          error_message: Optional[str] = None):
    """Save individual test result."""
    async with pool.acquire() as conn:
        await conn.execute(
            f"""
            INSERT INTO {settings.DATABASE_SCHEMA}.pt_test_results
            (run_id, category, test_name, tool_name, status, severity, request, response, 
             evidence, latency_ms, presidio_findings, trufflehog_findings, error_message)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9, $10, $11::jsonb, $12::jsonb, $13)
            """,
            run_id, category, test_name, tool_name, status, severity,
            json.dumps(request), json.dumps(response), evidence, latency_ms,
            json.dumps(presidio_findings) if presidio_findings else None,
            json.dumps(trufflehog_findings) if trufflehog_findings else None,
            error_message
        )


async def update_mcp_pt_summary(mcp_name: str, summary: dict):
    """Write PT run outcome back to omni2.mcp_servers for at-a-glance visibility.

    pt_score  — 0-100 based only on pass/fail tests (errors excluded from calc)
    pt_status — 'pass' | 'fail' | 'inconclusive'
    pt_last_run — set to now()

    Score semantics:
      inconclusive or no pass/fail tests  → score=NULL,  status='inconclusive'
      failed == 0 and tested > 0          → score=100,   status='pass'
      failed > 0                          → score=round(passed/tested*100), status='fail'
    """
    passed = summary.get('passed', 0)
    failed = summary.get('failed', 0)
    inconclusive = summary.get('inconclusive', False)
    tested = passed + failed   # errors are intentionally excluded from the score

    if inconclusive or tested == 0:
        pt_status = 'inconclusive'
        pt_score  = None
    elif failed == 0:
        pt_status = 'pass'
        pt_score  = 100
    else:
        pt_status = 'fail'
        pt_score  = round(passed / tested * 100)

    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE omni2.mcp_servers
               SET pt_score    = $1,
                   pt_last_run = now(),
                   pt_status   = $2
               WHERE name = $3""",
            pt_score, pt_status, mcp_name
        )
    logger.info(
        f"PT summary updated for '{mcp_name}': "
        f"score={pt_score} status={pt_status} "
        f"(passed={passed} failed={failed} inconclusive={inconclusive})"
    )


async def save_agent_story(run_id: int, story: dict):
    """Persist one AI Red Team story to pt_agent_stories."""
    async with pool.acquire() as conn:
        await conn.execute(
            f"""
            INSERT INTO {settings.DATABASE_SCHEMA}.pt_agent_stories
            (run_id, story_index, attack_goal, tool_calls_made, verdict, severity,
             title, finding, evidence, recommendation, attacker_model, judge_model, transcript,
             was_planned, coverage_pct, surprises)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13::jsonb,$14,$15,$16)
            """,
            run_id,
            story.get("story_index", 1),
            story.get("attack_goal", ""),
            story.get("tool_calls_made", 0),
            story.get("verdict", "inconclusive"),
            story.get("severity", "info"),
            story.get("title", ""),
            story.get("finding", ""),
            story.get("evidence", ""),
            story.get("recommendation", ""),
            story.get("attacker_model", ""),
            story.get("judge_model", ""),
            story.get("transcript", []),
            story.get("was_planned"),                    # Optional[bool]
            story.get("coverage_pct"),                   # Optional[int]
            story.get("surprises") or None,              # Optional[List[str]] → TEXT[]
        )


async def get_agent_stories(run_id: int) -> list:
    """Return all AI Red Team stories for a run."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""SELECT id, run_id, story_index, attack_goal, tool_calls_made,
                       verdict, severity, title, finding, evidence,
                       recommendation, attacker_model, judge_model, transcript,
                       was_planned, coverage_pct, surprises, created_at
                FROM {settings.DATABASE_SCHEMA}.pt_agent_stories
                WHERE run_id = $1
                ORDER BY story_index""",
            run_id,
        )
        return [dict(r) for r in rows]


# ── Prescan cache ──────────────────────────────────────────────────────────────

async def get_prescan(mcp_server_id: int, tools_hash: str) -> Optional[Dict]:
    """Return cached mission briefing if hash matches and not stale, else None."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""SELECT briefing, tools_hash, is_stale, created_at, updated_at
                FROM {settings.DATABASE_SCHEMA}.pt_prescan_cache
                WHERE mcp_server_id = $1 AND tools_hash = $2 AND NOT is_stale""",
            mcp_server_id, tools_hash,
        )
        if not row:
            return None
        raw = row["briefing"]
        if isinstance(raw, str):
            raw = json.loads(raw)
        result = dict(raw)
        result["_cached_at"]   = row["created_at"].isoformat() if row["created_at"] else None
        result["_updated_at"]  = row["updated_at"].isoformat()  if row["updated_at"]  else None
        result["_is_stale"]    = row["is_stale"]
        return result


async def save_prescan(mcp_server_id: int, tools_hash: str, briefing: dict):
    """Upsert mission briefing into prescan cache (one row per MCP)."""
    async with pool.acquire() as conn:
        await conn.execute(
            f"""
            INSERT INTO {settings.DATABASE_SCHEMA}.pt_prescan_cache
                (mcp_server_id, tools_hash, briefing, is_stale, updated_at)
            VALUES ($1, $2, $3::jsonb, FALSE, now())
            ON CONFLICT (mcp_server_id) DO UPDATE SET
                tools_hash = EXCLUDED.tools_hash,
                briefing   = EXCLUDED.briefing,
                is_stale   = FALSE,
                updated_at = now()
            """,
            mcp_server_id, tools_hash, briefing,  # asyncpg codec (encoder=json.dumps) handles serialisation
        )
    logger.info(f"Prescan saved: mcp_server_id={mcp_server_id} hash={tools_hash}")


async def invalidate_prescan(mcp_server_id: int):
    """Mark prescan as stale — triggers re-scan on next red team run."""
    async with pool.acquire() as conn:
        await conn.execute(
            f"""UPDATE {settings.DATABASE_SCHEMA}.pt_prescan_cache
                SET is_stale = TRUE, updated_at = now()
                WHERE mcp_server_id = $1""",
            mcp_server_id,
        )
    logger.info(f"Prescan invalidated: mcp_server_id={mcp_server_id}")


async def get_prescan_by_mcp(mcp_server_id: int) -> Optional[Dict]:
    """Return the latest prescan for an MCP regardless of staleness (for UI display)."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"""SELECT briefing, tools_hash, is_stale, created_at, updated_at
                FROM {settings.DATABASE_SCHEMA}.pt_prescan_cache
                WHERE mcp_server_id = $1""",
            mcp_server_id,
        )
        if not row:
            return None
        raw = row["briefing"]
        if isinstance(raw, str):
            raw = json.loads(raw)
        result = dict(raw)
        result["_cached_at"]  = row["created_at"].isoformat() if row["created_at"] else None
        result["_updated_at"] = row["updated_at"].isoformat()  if row["updated_at"]  else None
        result["_is_stale"]   = row["is_stale"]
        return result


async def get_preset(name: str) -> Optional[Dict]:
    """Get preset configuration."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT * FROM {settings.DATABASE_SCHEMA}.pt_presets WHERE name = $1 AND enabled = true",
            name
        )
        return dict(row) if row else None


async def get_categories() -> List[Dict]:
    """Get all enabled categories."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"SELECT * FROM {settings.DATABASE_SCHEMA}.pt_categories WHERE enabled = true ORDER BY category_id"
        )
        return [dict(row) for row in rows]


async def get_test_functions(category_ids: List[int]) -> List[Dict]:
    """Get test functions for categories."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT f.*, c.name as category_name 
            FROM {settings.DATABASE_SCHEMA}.pt_test_functions f
            JOIN {settings.DATABASE_SCHEMA}.pt_categories c ON f.category_id = c.category_id
            WHERE f.category_id = ANY($1) AND f.enabled = true
            ORDER BY f.category_id, f.function_id
            """,
            category_ids
        )
        return [dict(row) for row in rows]
