from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from typing import Optional

router = APIRouter()


@router.get("/mcp-analytics/overview")
async def get_overview(days: int = Query(30), db: AsyncSession = Depends(get_db)):
    """Total sessions, tool calls, users — split by source"""
    result = await db.execute(text("""
        SELECT
            source,
            COUNT(*) AS sessions,
            SUM(jsonb_array_length(flow_data->'events')) AS total_events,
            COUNT(DISTINCT user_id) AS unique_users
        FROM omni2.interaction_flows
        WHERE created_at >= NOW() - INTERVAL '1 day' * :days
        GROUP BY source
    """), {"days": days})
    rows = result.fetchall()
    return {"data": [{"source": r[0], "sessions": r[1], "total_events": r[2], "unique_users": r[3]} for r in rows]}


@router.get("/mcp-analytics/top-tools")
async def get_top_tools(days: int = Query(30), source: Optional[str] = None, limit: int = Query(10), db: AsyncSession = Depends(get_db)):
    """Most called tools extracted from flow_data JSONB events"""
    source_filter = "AND source = :source" if source else ""
    result = await db.execute(text(f"""
        SELECT
            e->>'mcp'  AS mcp_name,
            e->>'tool' AS tool_name,
            COUNT(*)   AS call_count
        FROM omni2.interaction_flows f,
             jsonb_array_elements(f.flow_data->'events') e
        WHERE e->>'event_type' = 'tool_call'
          AND f.created_at >= NOW() - INTERVAL '1 day' * :days
          {source_filter}
        GROUP BY mcp_name, tool_name
        ORDER BY call_count DESC
        LIMIT :limit
    """), {"days": days, "source": source, "limit": limit})
    rows = result.fetchall()
    return {"data": [{"mcp": r[0], "tool": r[1], "count": r[2]} for r in rows]}


@router.get("/mcp-analytics/top-mcps")
async def get_top_mcps(days: int = Query(30), source: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Most used MCP servers"""
    source_filter = "AND source = :source" if source else ""
    result = await db.execute(text(f"""
        SELECT
            e->>'mcp' AS mcp_name,
            COUNT(*)  AS call_count,
            COUNT(DISTINCT f.user_id) AS unique_users
        FROM omni2.interaction_flows f,
             jsonb_array_elements(f.flow_data->'events') e
        WHERE e->>'event_type' = 'tool_call'
          AND f.created_at >= NOW() - INTERVAL '1 day' * :days
          {source_filter}
        GROUP BY mcp_name
        ORDER BY call_count DESC
    """), {"days": days, "source": source})
    rows = result.fetchall()
    return {"data": [{"mcp": r[0], "count": r[1], "unique_users": r[2]} for r in rows]}


@router.get("/mcp-analytics/user-stats")
async def get_user_stats(days: int = Query(30), source: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Per-user activity: sessions, tool calls, MCPs used"""
    source_filter = "AND f.source = :source" if source else ""
    result = await db.execute(text(f"""
        SELECT
            u.username,
            u.email,
            COUNT(DISTINCT f.session_id) AS sessions,
            SUM(jsonb_array_length(f.flow_data->'events')) AS total_events,
            COUNT(e.*) FILTER (WHERE e->>'event_type' = 'tool_call') AS tool_calls
        FROM omni2.interaction_flows f
        JOIN auth_service.users u ON u.id = f.user_id
        LEFT JOIN LATERAL jsonb_array_elements(f.flow_data->'events') e ON true
        WHERE f.created_at >= NOW() - INTERVAL '1 day' * :days
          {source_filter}
        GROUP BY u.id, u.username, u.email
        ORDER BY tool_calls DESC
        LIMIT 20
    """), {"days": days, "source": source})
    rows = result.fetchall()
    return {"data": [{"username": r[0], "email": r[1], "sessions": r[2], "total_events": r[3], "tool_calls": r[4]} for r in rows]}


@router.get("/mcp-analytics/team-stats")
async def get_team_stats(days: int = Query(30), source: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Per-team MCP usage"""
    source_filter = "AND f.source = :source" if source else ""
    result = await db.execute(text(f"""
        SELECT
            t.name AS team_name,
            COUNT(DISTINCT f.session_id) AS sessions,
            COUNT(e.*) FILTER (WHERE e->>'event_type' = 'tool_call') AS tool_calls,
            COUNT(DISTINCT f.user_id) AS members_active
        FROM auth_service.teams t
        JOIN auth_service.team_members tm ON tm.team_id = t.id
        JOIN omni2.interaction_flows f ON f.user_id = tm.user_id
        LEFT JOIN LATERAL jsonb_array_elements(f.flow_data->'events') e ON true
        WHERE f.created_at >= NOW() - INTERVAL '1 day' * :days
          {source_filter}
        GROUP BY t.id, t.name
        ORDER BY tool_calls DESC
    """), {"days": days, "source": source})
    rows = result.fetchall()
    return {"data": [{"team": r[0], "sessions": r[1], "tool_calls": r[2], "members_active": r[3]} for r in rows]}


@router.get("/mcp-analytics/activity-over-time")
async def get_activity_over_time(days: int = Query(14), db: AsyncSession = Depends(get_db)):
    """Daily sessions split by source for trend chart"""
    result = await db.execute(text("""
        SELECT
            DATE(created_at) AS day,
            source,
            COUNT(*) AS sessions
        FROM omni2.interaction_flows
        WHERE created_at >= NOW() - INTERVAL '1 day' * :days
        GROUP BY day, source
        ORDER BY day ASC
    """), {"days": days})
    rows = result.fetchall()
    return {"data": [{"day": str(r[0]), "source": r[1], "sessions": r[2]} for r in rows]}


@router.get("/mcp-analytics/chat-vs-gateway")
async def get_chat_vs_gateway(days: int = Query(30), db: AsyncSession = Depends(get_db)):
    """Breakdown: avg events per session, tool call rate per source"""
    result = await db.execute(text("""
        SELECT
            source,
            COUNT(*) AS sessions,
            ROUND(AVG(jsonb_array_length(flow_data->'events')), 1) AS avg_steps,
            SUM((
                SELECT COUNT(*) FROM jsonb_array_elements(flow_data->'events') e
                WHERE e->>'event_type' = 'tool_call'
            )) AS total_tool_calls
        FROM omni2.interaction_flows
        WHERE created_at >= NOW() - INTERVAL '1 day' * :days
        GROUP BY source
    """), {"days": days})
    rows = result.fetchall()
    return {"data": [{"source": r[0], "sessions": r[1], "avg_steps": float(r[2] or 0), "total_tool_calls": r[3]} for r in rows]}
