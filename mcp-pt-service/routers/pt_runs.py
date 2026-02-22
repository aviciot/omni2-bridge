"""PT Runs API Router."""

import json
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

import db
from planner import PTPlanner, VALID_TESTS
from executor import PTExecutor
from mcp_client import MCPClient
from mcp_discovery import MCPDiscovery
from config_service import get_config_service
from logger import logger

router = APIRouter(prefix="/api/v1/mcp-pt", tags=["pt"])


class RunPTRequest(BaseModel):
    mcp_id: str
    preset: Optional[str] = "quick"
    categories: Optional[List[str]] = None
    created_by: int
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    template_mode: Optional[bool] = False       # deterministic run, no LLM
    force_regenerate: Optional[bool] = False    # bypass cache, always call LLM


class RunPTResponse(BaseModel):
    run_id: int
    status: str
    message: str


@router.post("/run", response_model=RunPTResponse)
async def run_pt(request: RunPTRequest, background_tasks: BackgroundTasks):
    """Start PT run for MCP."""

    async with db.pool.acquire() as conn:
        mcp = await conn.fetchrow(
            """SELECT id, name, url, protocol, timeout_seconds, auth_type, auth_config
               FROM omni2.mcp_servers
               WHERE name = $1 AND status = 'active'""",
            request.mcp_id
        )
        if not mcp:
            raise HTTPException(404, f"MCP server not found or inactive: {request.mcp_id}")

    if request.preset == "custom":
        if not request.categories or len(request.categories) == 0:
            raise HTTPException(400, "Categories required for custom preset")
        preset_config = {"max_parallel": 5, "timeout_seconds": 300, "categories": request.categories}
    else:
        preset_config = await db.get_preset(request.preset)
        if not preset_config:
            raise HTTPException(404, f"Preset not found: {request.preset}")

    # Resolve categories: explicit (custom/advanced) → preset → all
    run_categories = (
        request.categories
        or preset_config.get("categories")
        or None   # LLM path uses preset name; template path uses ALL
    )

    from config_service import get_config_service
    config_service = get_config_service()

    template_mode = bool(request.template_mode)

    if template_mode:
        llm_provider = "template"
        llm_model = ""
        plan_source = "template"
    else:
        llm_provider = request.llm_provider or config_service.get_execution_settings().get('default_llm_provider', 'gemini')
        llm_model = request.llm_model or config_service.get_llm_config(llm_provider).get('default_model')
        plan_source = "llm"   # will be updated to 'cached' if cache hits

    run_id = await db.create_pt_run(
        mcp_server_id=mcp["id"],
        mcp_name=mcp["name"],
        preset=request.preset,
        llm_provider=llm_provider,
        llm_model=llm_model,
        created_by=request.created_by,
        plan_source=plan_source,
    )

    # Extract bearer token from auth_config (supports auth_type = 'bearer')
    auth_config = mcp["auth_config"] or {}
    auth_token = auth_config.get("token") if mcp["auth_type"] == "bearer" else None

    background_tasks.add_task(
        execute_pt_run,
        run_id=run_id,
        mcp_name=mcp["name"],
        mcp_url=mcp["url"],
        mcp_protocol=mcp["protocol"],
        auth_token=auth_token,
        preset=request.preset,
        categories=run_categories,
        max_parallel=preset_config["max_parallel"],
        timeout_seconds=preset_config["timeout_seconds"],
        llm_provider=llm_provider,
        llm_model=llm_model,
        template_mode=template_mode,
        force_regenerate=bool(request.force_regenerate),
    )

    return RunPTResponse(run_id=run_id, status="pending", message=f"PT run started for {mcp['name']}")


async def execute_pt_run(run_id: int, mcp_name: str, mcp_url: str, mcp_protocol: str,
                        auth_token: Optional[str],
                        preset: str, categories: Optional[List[str]],
                        max_parallel: int, timeout_seconds: int,
                        llm_provider: str, llm_model: str,
                        template_mode: bool = False, force_regenerate: bool = False):
    """Execute PT run — supports LLM, cached-plan, and template (deterministic) modes."""

    from redis_publisher import get_publisher
    publisher = await get_publisher()
    start_time = datetime.now()

    try:
        # ── Stage 1: Initialization ──────────────────────────────────────────
        await db.update_pt_run(run_id, current_stage="initialization",
                               stage_details={"message": "Starting PT run"})
        await publisher.publish_started(run_id, mcp_name, preset)

        # ── Stage 2: MCP Discovery (always runs) ─────────────────────────────
        await db.update_pt_run(run_id, current_stage="health_check",
                               stage_details={"message": "Discovering MCP capabilities"})

        discovery = MCPDiscovery(mcp_url, mcp_protocol, auth_token=auth_token)
        discovered = await discovery.discover_all()
        await discovery.close()

        mcp_metadata = {
            "id": mcp_name,
            "name": mcp_name,
            "url": mcp_url,
            "protocol": mcp_protocol,
            "tools": discovered["tools"],
            "prompts": discovered["prompts"],
            "resources": discovered["resources"],
            "tool_count": discovered["tool_count"],
            "prompt_count": discovered["prompt_count"],
            "resource_count": discovered["resource_count"],
        }
        logger.info(f"Discovered: {mcp_metadata['tool_count']} tools, "
                    f"{mcp_metadata['prompt_count']} prompts, "
                    f"{mcp_metadata['resource_count']} resources")

        import json
        from redis_handler import get_redis
        redis_client = await get_redis()
        await redis_client.setex(f"pt_run:{run_id}:discovery", 3600, json.dumps(mcp_metadata))
        await publisher.publish_event(run_id, "discovery_complete", mcp_metadata)

        # Separate ai_red_team (handled in Stage 5) from regular test categories
        run_ai_red_team = bool(categories and 'ai_red_team' in categories)
        regular_categories = [c for c in categories if c != 'ai_red_team'] if categories else None
        # If ONLY ai_red_team was selected, skip the LLM plan + test execution entirely
        skip_regular_tests = run_ai_red_team and not regular_categories

        # Create MCP client + executor early — needed for both smoke test and AI Red Team
        mcp_client = MCPClient(mcp_url, mcp_protocol, auth_token=auth_token)
        executor = PTExecutor(max_parallel, timeout_seconds,
                              run_id=run_id, redis_client=redis_client)

        # Smoke test — abort early if MCP is unreachable
        from mcp_client import MCPConnectionError as _ConnErr
        try:
            await executor.smoke_test(mcp_client)
        except _ConnErr as e:
            logger.error(f"PT run {run_id} aborted — MCP unreachable: {e}")
            await db.update_pt_run(
                run_id, status="failed", completed_at=datetime.now(),
                stage_details={"error": f"MCP unreachable: {e}"}
            )
            await publisher.publish_error(run_id, f"MCP unreachable: {e}")
            return

        results = []
        summary = executor.calculate_summary([])

        if not skip_regular_tests:
            # ── Stage 3: Test Plan (Template / Cache / LLM) ─────────────────
            if template_mode:
                # — Deterministic path: skip LLM entirely ————————————————————
                run_cats = categories or list(VALID_TESTS.keys())
                total_combos = sum(
                    len(VALID_TESTS.get(c, {})) for c in run_cats
                ) * max(mcp_metadata["tool_count"], 1)
                await db.update_pt_run(
                    run_id,
                    current_stage="test_execution", status="running", started_at=start_time,
                    stage_details={"message": f"⚙️ Deterministic: {mcp_metadata['tool_count']} tools × all tests ≈ {total_combos} runs"},
                    plan_source="template",
                )
                from planner import generate_template_plan
                test_plan = generate_template_plan(mcp_metadata, run_cats)
                llm_cost = 0.0
                plan_source = "template"

            else:
                # — LLM path (with optional cache) ———————————————————————————
                from planner import compute_cache_key, PTPlanner
                cache_key, tools_hash = compute_cache_key(mcp_name, preset, discovered["tools"])

                cached = None
                if not force_regenerate:
                    cached = await db.get_cached_plan(cache_key)

                if cached:
                    # ✅ Cache hit — skip LLM
                    test_plan = cached["test_plan"]
                    llm_cost = 0.0
                    plan_source = "cached"
                    logger.info(f"Cache HIT for {mcp_name} preset={preset} key={cache_key[:8]}…")

                    await db.update_pt_run(
                        run_id,
                        current_stage="llm_analysis", status="running", started_at=start_time,
                        stage_details={"message": "📋 Using cached test plan (LLM skipped)"},
                        plan_source="cached",
                    )
                    await publisher.publish_event(run_id, "cache_hit", {
                        "cache_key": cache_key[:8] + "…",
                        "mcp_name": mcp_name,
                        "preset": preset,
                    })
                else:
                    # 🧠 LLM call
                    await db.update_pt_run(
                        run_id,
                        current_stage="llm_analysis", status="running", started_at=start_time,
                        stage_details={"message": f"🧠 LLM analyzing {mcp_metadata['tool_count']} tools"},
                    )
                    planner = PTPlanner(llm_provider=llm_provider, llm_model=llm_model)
                    plan_result = await planner.generate_test_plan(mcp_metadata, preset, regular_categories)
                    test_plan = plan_result["test_plan"]
                    llm_cost = plan_result["llm_cost"]
                    plan_source = "llm"

                    # Store in cache for future runs
                    await db.save_plan_cache(
                        cache_key, mcp_name, preset, tools_hash, test_plan, llm_cost
                    )
                    logger.info(f"Cache STORED for {mcp_name} preset={preset} key={cache_key[:8]}… "
                                f"cost=${llm_cost:.4f}")

            # Ensure test_plan is always a dict (cache may return a JSON string)
            if isinstance(test_plan, str):
                test_plan = json.loads(test_plan)

            # Persist plan + security profile
            await db.update_pt_run(
                run_id,
                test_plan=json.dumps(test_plan),
                security_profile=json.dumps(test_plan.get("security_profile", {})),
                llm_cost_usd=llm_cost,
                plan_source=plan_source,
            )
            await redis_client.setex(f"pt_run:{run_id}:test_plan", 3600, json.dumps(test_plan))
            await publisher.publish_event(run_id, "test_plan_ready", test_plan)

            # ── Stage 4: Test Execution ──────────────────────────────────────
            if not template_mode:
                await db.update_pt_run(run_id, current_stage="test_execution",
                                       stage_details={"message": "Running tests"})

            tests = test_plan.get("tests", [])
            total_tests = len(tests)
            completed_count = 0
            await publisher.publish_progress(run_id, 0, total_tests)

            async def on_result(result: dict):
                """Save each test result to DB immediately as it completes."""
                nonlocal completed_count
                await db.save_test_result(
                    run_id=run_id,
                    category=result["category"],
                    test_name=result["test_name"],
                    tool_name=result.get("tool_name"),
                    status=result["status"],
                    severity=result["severity"],
                    request=result["request"],
                    response=result["response"],
                    evidence=result["evidence"],
                    latency_ms=result["latency_ms"],
                    presidio_findings=result.get("presidio_findings"),
                    trufflehog_findings=result.get("trufflehog_findings"),
                    error_message=result.get("error_message")
                )
                completed_count += 1
                await publisher.publish_event(run_id, "test_result", {
                    "result": {
                        "category": result["category"],
                        "test_name": result["test_name"],
                        "tool_name": result.get("tool_name"),
                        "status": result["status"],
                        "severity": result["severity"],
                        "evidence": result["evidence"],
                        "latency_ms": result["latency_ms"],
                    },
                    "completed": completed_count,
                    "total": total_tests,
                })

            results = await executor.run_tests(test_plan, mcp_client, on_result=on_result)
            summary = executor.calculate_summary(results)

            # Did the user cancel during test execution?
            if executor._cancelled:
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                await db.update_pt_run(
                    run_id,
                    status="cancelled",
                    current_stage="cancelled",
                    completed_at=datetime.now(),
                    duration_ms=duration_ms,
                    stage_details={"message": "Cancelled by user"},
                    **summary
                )
                await publisher.publish_event(run_id, "cancelled", {"message": "Run cancelled by user"})
                await mcp_client.close()
                await redis_client.delete(f"pt_run:{run_id}:cancel")
                logger.info(f"PT run {run_id} cancelled by user during test execution")
                return

        else:
            # AI Red Team only — skip LLM planning + test execution entirely
            logger.info(f"PT run {run_id}: AI Red Team only — skipping stages 3 & 4")
            await db.update_pt_run(
                run_id,
                current_stage="ai_red_team", status="running", started_at=start_time,
                stage_details={"message": "🤖 AI Red Team only — skipping regular tests"},
                plan_source="ai_red_team",
            )

        # Cancel check before Stage 5 — catches cancel during LLM/plan phase
        # or an immediate cancel when the user aborts an AI-Red-Team-only run.
        if await executor._is_cancelled():
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            await db.update_pt_run(
                run_id,
                status="cancelled",
                current_stage="cancelled",
                completed_at=datetime.now(),
                duration_ms=duration_ms,
                stage_details={"message": "Cancelled by user"},
                **summary
            )
            await publisher.publish_event(run_id, "cancelled", {"message": "Run cancelled by user"})
            await mcp_client.close()
            await redis_client.delete(f"pt_run:{run_id}:cancel")
            logger.info(f"PT run {run_id} cancelled before AI Red Team")
            return

        # ── Stage 5: Mission Briefing (pre-scan) + AI Red Team ───────────────
        agent_stories_count = 0
        if run_ai_red_team:
            # ── 5a: Mission Briefing (pre-scan — cached or fresh) ─────────────
            mission_briefing = None
            try:
                await db.update_pt_run(
                    run_id, current_stage="mission_briefing",
                    stage_details={"message": "🔍 Scanning attack surface…"}
                )
                await publisher.publish_event(run_id, "stage_update", {
                    "stage": "mission_briefing",
                    "message": "Attack surface analysis starting",
                })

                # Fetch mcp_server_id from DB
                async with db.pool.acquire() as _conn:
                    _row = await _conn.fetchrow(
                        "SELECT id FROM omni2.mcp_servers WHERE name = $1", mcp_name
                    )
                mcp_server_id = _row["id"] if _row else None

                if mcp_server_id:
                    from recon import run_prescan
                    from config_service import get_config_service as _gcs
                    _cfg = _gcs().get_ai_red_team_config()
                    _prov = _cfg.get("attacker_provider", "gemini")
                    _llm_cfg = _gcs().get_llm_config(_prov) or {}
                    _api_key = _llm_cfg.get("api_key", "")
                    _model   = _cfg.get("attacker_model",
                                        _llm_cfg.get("default_model", "gemini-2.0-flash"))
                    _max_stories = int(_cfg.get("max_stories", 3))

                    mission_briefing = await run_prescan(
                        mcp_name      = mcp_name,
                        mcp_server_id = mcp_server_id,
                        tools         = mcp_metadata.get("tools", []),
                        prompts       = mcp_metadata.get("prompts", []),
                        resources     = mcp_metadata.get("resources", []),
                        max_stories   = _max_stories,
                        llm_provider  = _prov,
                        llm_model     = _model,
                        api_key       = _api_key,
                    )

                    cache_hit = mission_briefing.get("cache_hit", False)
                    await db.update_pt_run(
                        run_id,
                        mission_briefing=mission_briefing,
                        stage_details={
                            "message": (
                                f"✅ Mission briefing ready "
                                f"({'cached' if cache_hit else 'fresh'}) — "
                                f"risk={mission_briefing.get('risk_surface','?')} "
                                f"domain={mission_briefing.get('mcp_domain','?')}"
                            ),
                            "cache_hit": cache_hit,
                        },
                    )
                    await publisher.publish_event(run_id, "mission_briefing_ready", {
                        "mcp_domain":            mission_briefing.get("mcp_domain"),
                        "risk_surface":           mission_briefing.get("risk_surface"),
                        "attack_surface_summary": mission_briefing.get("attack_surface_summary"),
                        "scenario_count":         len(mission_briefing.get("scenario_assignments", [])),
                        "target_count":           len(mission_briefing.get("prioritized_targets", [])),
                        "chain_count":            len(mission_briefing.get("attack_chains", [])),
                        "cache_hit":              cache_hit,
                    })
                    logger.info(
                        f"Mission briefing for run {run_id}: "
                        f"domain={mission_briefing.get('mcp_domain')} "
                        f"risk={mission_briefing.get('risk_surface')} "
                        f"cache_hit={cache_hit}"
                    )
                else:
                    logger.warning(f"mcp_server_id not found for '{mcp_name}' — skipping prescan")

            except Exception as e:
                logger.error(f"Mission briefing failed for run {run_id}: {e}", exc_info=True)
                await publisher.publish_event(run_id, "mission_briefing_error",
                                              {"error": str(e)[:200]})
                # Non-fatal: attacker continues with generic briefing

            # ── 5b: AI Red Team attack ────────────────────────────────────────
            await db.update_pt_run(run_id, current_stage="ai_red_team",
                                   stage_details={"message": "🤖 AI Red Team agent executing mission…"})
            await publisher.publish_event(run_id, "stage_update",
                                          {"stage": "ai_red_team", "message": "AI Red Team executing"})
            try:
                agent_stories_count = await _run_ai_red_team(
                    run_id, mcp_client, mcp_metadata, mission_briefing, redis_client, publisher
                )
            except Exception as e:
                logger.error(f"AI Red Team failed for run {run_id}: {e}", exc_info=True)
                await publisher.publish_event(run_id, "agent_error", {"error": str(e)[:200]})

        # Persist run result
        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        await db.update_pt_run(
            run_id,
            status="completed",
            current_stage="completed",
            completed_at=datetime.now(),
            duration_ms=duration_ms,
            stage_details={"message": "Completed", "agent_stories": agent_stories_count},
            **summary
        )

        # Update mcp_servers with latest PT score/status for at-a-glance visibility
        await db.update_mcp_pt_summary(mcp_name, summary)

        await publisher.publish_complete(run_id, "completed", {**summary, "agent_stories": agent_stories_count})
        await mcp_client.close()
        
    except Exception as e:
        logger.error(f"PT run {run_id} failed: {e}", exc_info=True)
        await db.update_pt_run(run_id, status="failed", completed_at=datetime.now())
        await publisher.publish_error(run_id, str(e))


@router.get("/runs")
async def list_runs(mcp_id: Optional[str] = None, limit: int = 50):
    async with db.pool.acquire() as conn:
        cols = "run_id, mcp_name, preset, status, total_tests, passed, failed, critical, high, medium, low, duration_ms, created_at, completed_at, plan_source, llm_provider"
        if mcp_id:
            rows = await conn.fetch(
                f"SELECT {cols} FROM omni2.pt_runs WHERE mcp_name = $1 ORDER BY created_at DESC LIMIT $2",
                mcp_id, limit
            )
        else:
            rows = await conn.fetch(
                f"SELECT {cols} FROM omni2.pt_runs ORDER BY created_at DESC LIMIT $1",
                limit
            )
        return [dict(row) for row in rows]


@router.get("/runs/{run_id}")
async def get_run(run_id: int):
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM omni2.pt_runs WHERE run_id = $1", run_id)
        if not row:
            raise HTTPException(404, "Run not found")
        return dict(row)


@router.get("/runs/{run_id}/results")
async def get_run_results(run_id: int):
    async with db.pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT result_id, run_id, category, test_name, tool_name, status, severity, request as prompt, response, evidence, latency_ms, presidio_findings, trufflehog_findings, error_message, executed_at FROM omni2.pt_test_results WHERE run_id = $1 ORDER BY executed_at",
            run_id
        )
        return [dict(row) for row in rows]


@router.get("/runs/{run_id}/security-profile")
async def get_security_profile(run_id: int):
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow("SELECT security_profile, test_plan FROM omni2.pt_runs WHERE run_id = $1", run_id)
        if not row:
            raise HTTPException(404, "Run not found")
        
        if row['security_profile']:
            return row['security_profile']
        elif row['test_plan'] and isinstance(row['test_plan'], dict):
            return row['test_plan'].get('security_profile', {})
        return {}


@router.get("/runs/{run_id}/recommendations")
async def get_recommendations(run_id: int):
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow("SELECT test_plan FROM omni2.pt_runs WHERE run_id = $1", run_id)
        if not row:
            raise HTTPException(404, "Run not found")
        
        test_plan = row['test_plan']
        if test_plan and isinstance(test_plan, dict):
            return test_plan.get('recommendations', [])
        return []


@router.delete("/runs/{run_id}")
async def delete_run(run_id: int):
    """Delete a PT run and all its results."""
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow("SELECT run_id, status FROM omni2.pt_runs WHERE run_id = $1", run_id)
        if not row:
            raise HTTPException(404, "Run not found")
        if row["status"] in ("running", "pending"):
            raise HTTPException(400, "Cannot delete a run that is still in progress")
        await conn.execute("DELETE FROM omni2.pt_runs WHERE run_id = $1", run_id)
    logger.info(f"Deleted PT run {run_id}")
    return {"message": f"Run {run_id} deleted"}


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: int):
    """Request cancellation of an in-progress PT run.

    Sets a Redis flag that the executor checks before each test.
    Pending tests are skipped immediately; already-running tests finish.
    The run status transitions: running → cancelling → cancelled.
    """
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT run_id, status FROM omni2.pt_runs WHERE run_id = $1", run_id
        )
        if not row:
            raise HTTPException(404, "Run not found")
        if row["status"] not in ("running", "pending", "cancelling"):
            raise HTTPException(400, f"Run cannot be cancelled (status: {row['status']})")

    from redis_handler import get_redis
    redis_client = await get_redis()
    await redis_client.setex(f"pt_run:{run_id}:cancel", 300, "1")   # TTL 5 min

    await db.update_pt_run(
        run_id,
        status="cancelling",
        stage_details={"message": "Cancellation requested — stopping after current tests…"},
    )
    logger.info(f"Cancel requested for PT run {run_id}")
    return {"message": f"Cancellation requested for run {run_id}"}


async def _run_ai_red_team(
    run_id:           int,
    mcp_client,
    mcp_metadata:     dict,
    mission_briefing: Optional[dict],
    redis_client,
    publisher,
) -> int:
    """Run the AI Red Team attack phase and persist stories. Returns story count."""
    from agent_executor import AgentExecutor
    from config_service import get_config_service

    cfg = get_config_service().get_ai_red_team_config()

    def _api_key(provider: str) -> str:
        llm_cfg = get_config_service().get_llm_config(provider) or {}
        key = llm_cfg.get('api_key', '')
        if not key:
            raise ValueError(f"No API key configured for provider: {provider}")
        return key

    attacker_provider = cfg.get('attacker_provider', 'gemini')
    judge_provider    = cfg.get('judge_provider', 'gemini')

    executor = AgentExecutor(
        attacker_provider = attacker_provider,
        attacker_model    = cfg.get('attacker_model', 'gemini-2.0-flash'),
        attacker_api_key  = _api_key(attacker_provider),
        judge_provider    = judge_provider,
        judge_model       = cfg.get('judge_model', 'gemini-2.0-flash'),
        judge_api_key     = _api_key(judge_provider),
        max_stories       = int(cfg.get('max_stories', 3)),
        max_iterations    = int(cfg.get('max_iterations', 25)),
    )

    discovered_tools = mcp_metadata.get('tools', [])

    async def on_event(event: dict):
        await publisher.publish_event(run_id, "agent_event", event)

    stories = await executor.run(
        mcp_client,
        discovered_tools,
        mcp_metadata,
        mission_briefing = mission_briefing,
        on_event         = on_event,
    )

    for story in stories:
        await db.save_agent_story(run_id, story)
        await publisher.publish_event(run_id, "agent_story", {
            "story_index":  story["story_index"],
            "verdict":      story["verdict"],
            "severity":     story["severity"],
            "title":        story["title"],
            "finding":      story["finding"],
            "was_planned":  story.get("was_planned", False),
            "coverage_pct": story.get("coverage_pct", 0),
        })

    logger.info(f"AI Red Team saved {len(stories)} stories for run {run_id}")
    return len(stories)


@router.get("/runs/{run_id}/agent-stories")
async def get_agent_stories(run_id: int):
    """Return AI Red Team stories for a run."""
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow("SELECT run_id FROM omni2.pt_runs WHERE run_id = $1", run_id)
        if not row:
            raise HTTPException(404, "Run not found")
    stories = await db.get_agent_stories(run_id)
    for s in stories:
        if s.get("created_at"):
            s["created_at"] = s["created_at"].isoformat()
        # surprises is a Postgres TEXT[] — convert to list if asyncpg returns it as something else
        if s.get("surprises") is None:
            s["surprises"] = []
    return stories


@router.get("/runs/{run_id}/agent-stories/{story_id}/transcript")
async def get_story_transcript(run_id: int, story_id: int):
    """Return the full transcript for a single story."""
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT transcript FROM omni2.pt_agent_stories WHERE id = $1 AND run_id = $2",
            story_id, run_id
        )
        if not row:
            raise HTTPException(404, "Story not found")
        transcript = row["transcript"] or []
        # asyncpg returns jsonb strings as Python str — double-decode if needed
        if isinstance(transcript, str):
            import json as _json
            transcript = _json.loads(transcript)
        return transcript


def _normalize_briefing(raw) -> dict:
    """Normalize raw prescan dict to the UI-facing contract.
    Handles both fresh JSONB dicts and legacy double-encoded strings."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return {}
    if not isinstance(raw, dict):
        return {}

    def _target(t):
        name = t.get("asset_name") or t.get("tool", "")
        attack = t.get("attack") or t.get("risk", "")
        reason = t.get("reason", "")
        return {
            "tool": name,
            "risk": f"{attack} — {reason}".strip(" —"),
            "payloads": t.get("payloads", []),
        }

    def _chain(c):
        return {"steps": c.get("steps", []), "goal": c.get("goal", "")}

    def _scenario(s, idx):
        if isinstance(s, str):
            return {"index": idx + 1, "attack_goal": s, "target_tools": [], "technique": ""}
        return {
            "index": s.get("index", idx + 1),
            "attack_goal": s.get("attack_goal", ""),
            "target_tools": s.get("target_tools", []),
            "technique": s.get("technique", ""),
            "payload_hints": s.get("payload_hints", []),
        }

    return {
        "domain":           raw.get("mcp_domain") or raw.get("domain", ""),
        "risk_rating":      raw.get("risk_surface") or raw.get("risk_rating", "medium"),
        "risk_surface":     raw.get("attack_surface_summary") or raw.get("risk_surface", ""),
        "priority_targets": [_target(t) for t in (raw.get("prioritized_targets") or raw.get("priority_targets", []))],
        "chains":           [_chain(c) for c in (raw.get("attack_chains") or raw.get("chains", []))],
        "scenarios":        [_scenario(s, i) for i, s in enumerate(raw.get("scenario_assignments") or raw.get("scenarios", []))],
        "cache_hit":        raw.get("cache_hit", False),
        "_cached_at":       raw.get("_cached_at"),
        "_is_stale":        raw.get("_is_stale", False),
    }


@router.get("/runs/{run_id}/mission-briefing")
async def get_run_mission_briefing(run_id: int):
    """Return the mission briefing used for a specific PT run."""
    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT mission_briefing FROM omni2.pt_runs WHERE run_id = $1", run_id
        )
        if not row:
            raise HTTPException(404, "Run not found")
        briefing = row["mission_briefing"]
        if not briefing:
            raise HTTPException(404, "No mission briefing for this run (not a red team run or pre-scan failed)")
        return _normalize_briefing(briefing)


@router.get("/mcp-servers/{mcp_server_id}/mission-briefing")
async def get_mcp_mission_briefing(mcp_server_id: int):
    """Return the latest cached mission briefing for an MCP server."""
    briefing = await db.get_prescan_by_mcp(mcp_server_id)
    if not briefing:
        raise HTTPException(404, "No mission briefing cached for this MCP — run a red team test first")
    return _normalize_briefing(briefing)


@router.delete("/mcp-servers/{mcp_server_id}/mission-briefing")
async def invalidate_mcp_mission_briefing(mcp_server_id: int):
    """Force-invalidate the prescan cache for an MCP (triggers fresh scan on next run)."""
    await db.invalidate_prescan(mcp_server_id)
    return {"ok": True, "message": f"Prescan cache invalidated for mcp_server_id={mcp_server_id}"}


@router.get("/ai-red-team-config")
async def get_ai_red_team_config():
    """Return current AI Red Team configuration."""
    cfg = get_config_service().get_ai_red_team_config()
    # Also return available providers/models so the UI can build dropdowns
    llm_providers = get_config_service()._cache.get("llm_providers", {})
    providers = {
        p: {"models": v.get("models", []), "default_model": v.get("default_model", "")}
        for p, v in llm_providers.items()
        if v.get("enabled", True)
    }
    return {"config": cfg, "providers": providers}


@router.put("/ai-red-team-config")
async def update_ai_red_team_config(body: dict):
    """Persist AI Red Team configuration to DB."""
    allowed = {"enabled", "max_stories", "max_iterations",
               "attacker_provider", "attacker_model", "judge_provider", "judge_model"}
    current = dict(get_config_service().get_ai_red_team_config())
    current.update({k: v for k, v in body.items() if k in allowed})
    ok = await get_config_service().update("ai_red_team", current)
    if not ok:
        raise HTTPException(500, "Failed to save config")
    return {"ok": True, "config": current}


@router.get("/runs/{run_id}/discovery")
async def get_discovery(run_id: int):
    """Get MCP discovery data from Redis."""
    from redis_handler import get_redis
    import json
    
    redis_client = await get_redis()
    data = await redis_client.get(f"pt_run:{run_id}:discovery")
    
    if not data:
        raise HTTPException(404, "Discovery data not found or expired")
    
    return json.loads(data)
