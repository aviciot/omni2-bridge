from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.config import settings
import httpx

router = APIRouter(prefix="/api/v1/mcp-pt")

@router.get("/config")
async def get_config(request: Request, db: AsyncSession = Depends(get_db)):
    headers = {"Authorization": request.headers.get("Authorization", "")}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.TRAEFIK_BASE_URL}/api/v1/mcp-pt/config", headers=headers)
        return response.json()

@router.put("/config")
async def update_config(config: dict, request: Request, db: AsyncSession = Depends(get_db)):
    headers = {"Authorization": request.headers.get("Authorization", "")}
    async with httpx.AsyncClient() as client:
        response = await client.put(f"{settings.TRAEFIK_BASE_URL}/api/v1/mcp-pt/config", json=config, headers=headers)
        return response.json()

@router.post("/scan")
async def start_scan(scan_request: dict, request: Request, db: AsyncSession = Depends(get_db)):
    headers = {"Authorization": request.headers.get("Authorization", "")}
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{settings.TRAEFIK_BASE_URL}/api/v1/mcp-pt/scan", json=scan_request, headers=headers)
        return response.json()

@router.get("/scans")
async def get_scans(request: Request, limit: int = 50, mcp_name: str = None, db: AsyncSession = Depends(get_db)):
    headers = {"Authorization": request.headers.get("Authorization", "")}
    params = {"limit": limit}
    if mcp_name:
        params["mcp_name"] = mcp_name
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.TRAEFIK_BASE_URL}/api/v1/mcp-pt/scans", params=params, headers=headers)
        return response.json()

@router.get("/scans/{scan_id}")
async def get_scan_detail(scan_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    headers = {"Authorization": request.headers.get("Authorization", "")}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{settings.TRAEFIK_BASE_URL}/api/v1/mcp-pt/scans/{scan_id}", headers=headers)
        return response.json()

@router.delete("/scans/{scan_id}")
async def delete_scan(scan_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    headers = {"Authorization": request.headers.get("Authorization", "")}
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"{settings.TRAEFIK_BASE_URL}/api/v1/mcp-pt/scans/{scan_id}", headers=headers)
        return response.json()

# V2 Routes
@router.get("/llm-options")
async def get_llm_options(request: Request):
    """Get available LLM providers and models for PT runs (no API keys exposed)."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://omni2-mcp-pt:8200/api/v1/mcp-pt/config")
            if response.status_code == 200:
                data = response.json()
                llm_providers = data.get("llm_providers") or {}
                execution_settings = data.get("execution_settings") or {}
                options = {
                    provider: {
                        "models": cfg.get("models", []),
                        "default_model": cfg.get("default_model", ""),
                    }
                    for provider, cfg in llm_providers.items()
                    if cfg.get("enabled", True)
                }
                return {
                    "providers": options,
                    "default_provider": execution_settings.get("default_llm_provider", "gemini"),
                }
            return {"providers": {}, "default_provider": "gemini"}
        except Exception:
            return {"providers": {}, "default_provider": "gemini"}


@router.get("/mcps")
async def get_mcps(request: Request, db: AsyncSession = Depends(get_db)):
    """Get active MCPs for PT testing — queried directly from omni2.mcp_servers (no auth chain needed)."""
    try:
        result = await db.execute(text("""
            SELECT id, name, url, protocol, status, health_status
            FROM omni2.mcp_servers
            WHERE status = 'active'
            ORDER BY name
        """))
        rows = result.fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception:
        return []

@router.get("/categories")
async def get_categories(request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get("http://omni2-mcp-pt:8200/api/v1/mcp-pt/categories")
        return response.json()

@router.get("/categories/{category_name}/tests")
async def get_category_tests(category_name: str, request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/categories/{category_name}/tests")
        return response.json()

@router.get("/presets")
async def get_presets(request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get("http://omni2-mcp-pt:8200/api/v1/mcp-pt/presets")
        return response.json()

@router.get("/runs")
async def get_runs(request: Request, limit: int = 20):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs?limit={limit}")
        return response.json()

@router.get("/runs/{run_id}")
async def get_run(run_id: int, request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/{run_id}")
        return response.json()

@router.get("/runs/{run_id}/results")
async def get_run_results(run_id: int, request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/{run_id}/results")
        return response.json()

@router.get("/runs/{run_id}/security-profile")
async def get_security_profile(run_id: int, request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/{run_id}/security-profile")
        return response.json()

@router.get("/runs/{run_id}/recommendations")
async def get_recommendations(run_id: int, request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/{run_id}/recommendations")
        return response.json()

@router.get("/runs/{run_id}/discovery")
async def get_discovery(run_id: int, request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/{run_id}/discovery")
        return response.json()

@router.get("/runs/{run_id}/agent-stories")
async def get_agent_stories(run_id: int, request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/{run_id}/agent-stories")
        return response.json()

@router.get("/runs/{run_id}/agent-stories/{story_id}/transcript")
async def get_story_transcript(run_id: int, story_id: int, request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/{run_id}/agent-stories/{story_id}/transcript")
        return response.json()

@router.get("/runs/{run_id}/mission-briefing")
async def get_run_mission_briefing(run_id: int, request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/{run_id}/mission-briefing")
        return response.json()

@router.get("/mcp-servers/{mcp_server_id}/mission-briefing")
async def get_mcp_mission_briefing(mcp_server_id: int, request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/mcp-servers/{mcp_server_id}/mission-briefing")
        return response.json()

@router.delete("/mcp-servers/{mcp_server_id}/mission-briefing")
async def invalidate_mcp_mission_briefing(mcp_server_id: int, request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/mcp-servers/{mcp_server_id}/mission-briefing")
        return response.json()

@router.post("/run")
async def start_run(run_request: dict, request: Request):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post("http://omni2-mcp-pt:8200/api/v1/mcp-pt/run", json=run_request)
        return response.json()

@router.post("/compare")
async def compare_runs(compare_request: dict, request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.post("http://omni2-mcp-pt:8200/api/v1/mcp-pt/compare", json=compare_request)
        return response.json()

@router.get("/mcps/{mcp_id}/history")
async def get_mcp_history(mcp_id: str, request: Request, limit: int = 20):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/mcps/{mcp_id}/history?limit={limit}")
        return response.json()

@router.get("/tests")
async def get_all_tests(request: Request):
    """Get full test catalog (all categories + their tests) from DB."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://omni2-mcp-pt:8200/api/v1/mcp-pt/tests")
        return response.json()


@router.get("/ai-red-team-config")
async def get_ai_red_team_config(request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.get("http://omni2-mcp-pt:8200/api/v1/mcp-pt/ai-red-team-config")
        return Response(content=response.content, status_code=response.status_code, media_type="application/json")

@router.put("/ai-red-team-config")
async def update_ai_red_team_config(body: dict, request: Request):
    async with httpx.AsyncClient() as client:
        response = await client.put("http://omni2-mcp-pt:8200/api/v1/mcp-pt/ai-red-team-config", json=body)
        return Response(content=response.content, status_code=response.status_code, media_type="application/json")

@router.get("/runs/{run_id}/agent-stories")
async def get_agent_stories(run_id: int, request: Request):
    """Get AI Red Team stories for a run."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/{run_id}/agent-stories")
        return Response(content=response.content, status_code=response.status_code, media_type="application/json")


@router.get("/runs/{run_id}/agent-stories/{story_id}/transcript")
async def get_story_transcript(run_id: int, story_id: int, request: Request):
    """Get full transcript for a single AI Red Team story."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/{run_id}/agent-stories/{story_id}/transcript")
        return Response(content=response.content, status_code=response.status_code, media_type="application/json")

@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: int, request: Request):
    """Request cancellation of an in-progress PT run."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/{run_id}/cancel")
        return Response(content=response.content, status_code=response.status_code, media_type="application/json")

@router.delete("/runs/{run_id}")
async def delete_run(run_id: int, request: Request):
    """Delete a PT run and all its results."""
    async with httpx.AsyncClient() as client:
        response = await client.delete(f"http://omni2-mcp-pt:8200/api/v1/mcp-pt/runs/{run_id}")
        return response.json()
