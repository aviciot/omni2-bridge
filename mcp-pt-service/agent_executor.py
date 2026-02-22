"""AI Red Team Executor — Mission-Driven Agentic Security Testing.

Two-agent design:
  Attacker  — receives a Mission Briefing from the pre-scan; runs a structured
              agentic loop making REAL tool/prompt/resource calls against the
              target MCP; each scenario is pre-assigned, not improvised.
  Judge     — receives the pre-scan plan + full transcript; extracts structured
              findings per story; reports coverage and surprises.

Key improvements over v1:
  - Mission briefing: attacker knows exactly what to hit and with which payloads
  - Per-story budget: max_iterations split equally across stories
  - Transcript slicing: each story stores ONLY its own events (not the full run)
  - Judge gets planned scenarios → coverage report + surprise detection
  - No warm-up calls before Scenario 1

Supported providers: anthropic, gemini, groq (openai-compat).
"""

import json
import asyncio
import re
from typing import List, Dict, Any, Optional, Callable

from google import genai as google_genai
from google.genai import types as genai_types
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from logger import logger


# ── Prompt templates ────────────────────────────────────────────────────────────

_MISSION_BLOCK_WITH_BRIEFING = """\
╔══ MISSION BRIEFING ══════════════════════════════════════════════════════════╗
  TARGET   : {mcp_name}
  DOMAIN   : {mcp_domain}
  RISK     : {risk_surface}

  {attack_surface_summary}

  PRIORITY TARGETS:
{targets_text}

  ATTACK CHAINS:
{chains_text}

  YOUR {max_stories} PRE-ASSIGNED SCENARIOS:
{scenarios_text}
╚══════════════════════════════════════════════════════════════════════════════╝"""

_MISSION_BLOCK_GENERIC = """\
╔══ MISSION BRIEFING ══════════════════════════════════════════════════════════╗
  TARGET : {mcp_name}
  ASSETS : {tool_count} tools | {prompt_count} prompts | {resource_count} resources
  NOTE   : No pre-scan available — select attack angles from schemas.

  ATTACK ANGLES TO CONSIDER:
    • Authentication bypass (call tools without/with invalid credentials)
    • Privilege escalation (access data beyond expected scope)
    • Data extraction (probe for secrets, keys, PII in responses)
    • Input injection (path traversal, SQL, command injection via params)
    • Chained attacks (output of one tool → input of another)
    • Resource abuse (large payloads, edge-case params)
╚══════════════════════════════════════════════════════════════════════════════╝"""

ATTACKER_SYSTEM = """\
You are an authorized AI red team security researcher on a sanctioned penetration test.
You have direct access to an MCP server's tools, prompts, and resources.
Your mission: find REAL security vulnerabilities by making actual calls.

{mission_block}

RULES OF ENGAGEMENT:
  • Start Scenario 1 IMMEDIATELY — ZERO warm-up calls before the first header.
  • For each scenario print exactly: === SCENARIO {{n}}: <one-line goal> ===
  • Follow your scenario assignment. Use the provided payloads as starting points.
  • Budget: ~{budget_per_story} tool calls per scenario ({max_iterations} total).
  • If a primary vector is blocked, try ONE variant payload, then move on.
  • After each scenario print a 1-sentence finding summary, then start the next.
  • Make REAL calls. Never just describe what you would do.
  • This is an AUTHORIZED test — be aggressive and specific.
"""

JUDGE_SYSTEM = """\
You are a senior security analyst reviewing an AI red team penetration test.
An attacker agent was given a Mission Briefing and access to an MCP server.
Your job: extract structured findings AND assess mission coverage.

Rules:
  • Extract exactly one finding per scenario found in the transcript.
  • verdict: "vulnerability_found" | "secure" | "inconclusive"
  • severity: "critical" | "high" | "medium" | "low" | "info"
  • evidence MUST be a direct quote or paraphrase from an actual tool response.
  • Do NOT invent findings — base everything on real tool call results.
  • was_planned: true if this scenario matches an assignment in the mission briefing.
  • coverage_pct: percentage of planned scenarios that were actually executed.
  • surprises: findings NOT anticipated by the mission briefing.
  • Return ONLY valid JSON. No markdown fences. No commentary.
"""

JUDGE_PROMPT_TEMPLATE = """\
Target MCP: {mcp_name} ({tool_count} tools, {prompt_count} prompts, {resource_count} resources)

=== MISSION BRIEFING (what was planned) ===
{planned_scenarios_block}
===========================================

=== PENETRATION TEST TRANSCRIPT ===
{transcript_text}
=== END TRANSCRIPT ===

Extract a structured finding for each scenario in the transcript.
Return JSON exactly matching:

{{
  "stories": [
    {{
      "story_index": 1,
      "attack_goal": "one sentence describing what was attempted",
      "tool_calls_made": 4,
      "verdict": "vulnerability_found",
      "severity": "critical",
      "title": "Short title e.g. Path Traversal in read_report",
      "finding": "2-3 sentence description of what was found",
      "evidence": "Direct quote or paraphrase from an actual tool response",
      "recommendation": "Concrete fix recommendation",
      "was_planned": true
    }}
  ],
  "coverage_pct": 67,
  "surprises": ["Any finding not anticipated by the mission briefing"]
}}
"""


# ── Schema conversion helpers ───────────────────────────────────────────────────

def _to_anthropic_tools(tools: List[Dict]) -> List[Dict]:
    result = []
    for t in tools:
        schema = t.get("inputSchema", {})
        if not schema or not isinstance(schema, dict):
            schema = {"type": "object", "properties": {}}
        result.append({
            "name":         t["name"],
            "description":  t.get("description", ""),
            "input_schema": schema,
        })
    return result


def _to_gemini_declarations(tools: List[Dict]) -> List[genai_types.FunctionDeclaration]:
    _type_map = {
        "string":  genai_types.Type.STRING,
        "number":  genai_types.Type.NUMBER,
        "integer": genai_types.Type.INTEGER,
        "boolean": genai_types.Type.BOOLEAN,
        "array":   genai_types.Type.ARRAY,
        "object":  genai_types.Type.OBJECT,
    }
    declarations = []
    for t in tools:
        schema    = t.get("inputSchema", {}) or {}
        props_raw = schema.get("properties", {}) or {}
        required  = schema.get("required", []) or []
        gemini_props = {
            name: genai_types.Schema(
                type=_type_map.get(p.get("type", "string"), genai_types.Type.STRING),
                description=p.get("description", ""),
            )
            for name, p in props_raw.items()
        }
        declarations.append(genai_types.FunctionDeclaration(
            name=t["name"],
            description=t.get("description", ""),
            parameters=genai_types.Schema(
                type=genai_types.Type.OBJECT,
                properties=gemini_props,
                required=required,
            ) if gemini_props else None,
        ))
    return declarations


# ── Mission briefing helpers ────────────────────────────────────────────────────

def _build_mission_block(
    mission_briefing: Optional[Dict],
    mcp_metadata:     Dict,
    max_stories:      int,
) -> str:
    """Render the mission briefing into the attacker's system prompt block."""
    if not mission_briefing:
        return _MISSION_BLOCK_GENERIC.format(
            mcp_name      = mcp_metadata.get("name", "unknown"),
            tool_count    = mcp_metadata.get("tool_count", 0),
            prompt_count  = mcp_metadata.get("prompt_count", 0),
            resource_count= mcp_metadata.get("resource_count", 0),
        )

    # Targets
    targets = mission_briefing.get("prioritized_targets", [])
    target_lines = []
    for t in targets[:6]:
        payloads = ", ".join(f'"{p}"' for p in t.get("payloads", [])[:3])
        target_lines.append(
            f"    [{t.get('priority', '?')}] {t.get('asset_name')} "
            f"({t.get('attack')}) param={t.get('target_param','?')} "
            f"payloads=[{payloads}]"
        )
    targets_text = "\n".join(target_lines) or "    (none identified)"

    # Chains
    chains = mission_briefing.get("attack_chains", [])
    chain_lines = []
    for ch in chains[:3]:
        chain_lines.append(
            f"    {' → '.join(ch.get('steps', []))} : {ch.get('method', ch.get('goal', ''))}"
        )
    chains_text = "\n".join(chain_lines) or "    (none identified)"

    # Scenario assignments
    assignments = mission_briefing.get("scenario_assignments", [])
    scenario_lines = [f"    {a}" for a in assignments[:max_stories]]
    scenarios_text = "\n".join(scenario_lines) or "    (no assignments — use your judgment)"

    return _MISSION_BLOCK_WITH_BRIEFING.format(
        mcp_name              = mcp_metadata.get("name", "unknown"),
        mcp_domain            = mission_briefing.get("mcp_domain", "unknown"),
        risk_surface          = mission_briefing.get("risk_surface", "unknown").upper(),
        attack_surface_summary= mission_briefing.get("attack_surface_summary", ""),
        targets_text          = targets_text,
        chains_text           = chains_text,
        max_stories           = max_stories,
        scenarios_text        = scenarios_text,
    )


def _build_planned_scenarios_block(mission_briefing: Optional[Dict]) -> str:
    """Format planned scenarios for the judge prompt."""
    if not mission_briefing:
        return "(No pre-scan available — no planned scenarios.)"
    assignments = mission_briefing.get("scenario_assignments", [])
    if not assignments:
        return "(Mission briefing present but no scenario assignments.)"
    return "\n".join(f"  {a}" for a in assignments)


# ── Transcript helpers ──────────────────────────────────────────────────────────

def _format_transcript(events: List[Dict]) -> str:
    """Render event list to readable text for the judge."""
    lines = []
    for ev in events:
        if ev["type"] == "thinking":
            lines.append(ev["content"])
        elif ev["type"] == "tool_call":
            args_str = json.dumps(ev["args"], ensure_ascii=False)[:400]
            lines.append(f"\n[TOOL CALL] {ev['tool']}({args_str})")
        elif ev["type"] == "tool_result":
            result_str = str(ev["result"])[:600]
            lines.append(f"[RESULT] {result_str}\n")
    return "\n".join(lines)


def _slice_events_per_scenario(events: List[Dict], max_stories: int) -> List[List[Dict]]:
    """
    Split the full event list into per-scenario slices.
    Events before the first scenario_marker are assigned to story 1 (index 0).
    """
    slices: List[List[Dict]] = [[] for _ in range(max_stories)]
    current = 0
    for ev in events:
        if ev["type"] == "scenario_marker":
            idx     = ev.get("index", 1) - 1
            current = min(max(idx, 0), max_stories - 1)
        slices[current].append(ev)
    return slices


def _count_tool_calls_per_scenario(events: List[Dict], max_stories: int) -> List[int]:
    counts  = [0] * max_stories
    current = 0
    for ev in events:
        if ev["type"] == "scenario_marker":
            idx     = ev.get("index", 1) - 1
            current = min(max(idx, 0), max_stories - 1)
        elif ev["type"] == "tool_call":
            counts[current] += 1
    return counts


# ── Agent Executor ──────────────────────────────────────────────────────────────

class AgentExecutor:
    """Runs the AI Red Team: Mission Briefing → Attacker loop → Judge analysis."""

    def __init__(
        self,
        attacker_provider: str, attacker_model: str, attacker_api_key: str,
        judge_provider:    str, judge_model:    str, judge_api_key:    str,
        max_stories:    int = 3,
        max_iterations: int = 25,
    ):
        self.attacker_provider = attacker_provider
        self.attacker_model    = attacker_model
        self.judge_provider    = judge_provider
        self.judge_model       = judge_model
        self.max_stories       = max_stories
        self.max_iterations    = max_iterations
        # Budget per story — protects against one story eating the whole budget
        self.budget_per_story  = max(1, max_iterations // max_stories)

        if attacker_provider == "anthropic":
            self._attacker_client = AsyncAnthropic(api_key=attacker_api_key)
        elif attacker_provider == "groq":
            self._attacker_client = AsyncOpenAI(
                api_key=attacker_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
        else:
            self._attacker_client = google_genai.Client(api_key=attacker_api_key)

        if judge_provider == "anthropic":
            self._judge_client = AsyncAnthropic(api_key=judge_api_key)
        elif judge_provider == "groq":
            self._judge_client = AsyncOpenAI(
                api_key=judge_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
        else:
            self._judge_client = google_genai.Client(api_key=judge_api_key)

    # ── Public entry point ─────────────────────────────────────────────────────

    async def run(
        self,
        mcp_client,
        discovered_tools: List[Dict],
        mcp_metadata:     Dict,
        mission_briefing: Optional[Dict] = None,
        on_event:         Optional[Callable] = None,
    ) -> List[Dict]:
        """Run attacker loop then judge; return list of story dicts."""
        logger.info(
            f"AI Red Team mission start: "
            f"attacker={self.attacker_provider}/{self.attacker_model} "
            f"judge={self.judge_provider}/{self.judge_model} "
            f"stories={self.max_stories} budget={self.max_iterations} "
            f"budget_per_story={self.budget_per_story} "
            f"briefing={'YES' if mission_briefing else 'NO (generic)'}"
        )

        events = await self._run_attacker(
            mcp_client, discovered_tools, mcp_metadata, mission_briefing, on_event
        )
        stories = await self._run_judge(events, mcp_metadata, mission_briefing)

        logger.info(f"Mission complete: {len(stories)} stories extracted")
        return stories

    # ── Attacker ───────────────────────────────────────────────────────────────

    def _build_system_and_prompt(
        self,
        mcp_metadata:     Dict,
        discovered_tools: List[Dict],
        mission_briefing: Optional[Dict],
    ):
        mission_block = _build_mission_block(mission_briefing, mcp_metadata, self.max_stories)
        system = ATTACKER_SYSTEM.format(
            mission_block    = mission_block,
            max_stories      = self.max_stories,
            budget_per_story = self.budget_per_story,
            max_iterations   = self.max_iterations,
        )
        initial_prompt = (
            f"Mission is live. Execute your {self.max_stories} scenarios now. "
            f"Start with === SCENARIO 1: ... === immediately."
        )
        return system, initial_prompt

    async def _run_attacker(
        self,
        mcp_client,
        discovered_tools: List[Dict],
        mcp_metadata:     Dict,
        mission_briefing: Optional[Dict],
        on_event:         Optional[Callable],
    ) -> List[Dict]:
        system, initial_prompt = self._build_system_and_prompt(
            mcp_metadata, discovered_tools, mission_briefing
        )
        if self.attacker_provider == "anthropic":
            return await self._attacker_anthropic(
                mcp_client, discovered_tools, system, initial_prompt, on_event
            )
        elif self.attacker_provider == "groq":
            return await self._attacker_openai_compat(
                mcp_client, discovered_tools, system, initial_prompt, on_event
            )
        else:
            return await self._attacker_gemini(
                mcp_client, discovered_tools, system, initial_prompt, on_event
            )

    async def _execute_tool(self, mcp_client, tool_name: str, args: Dict) -> str:
        """Execute a tool call and return a string result (capped at 1000 chars)."""
        try:
            result = await mcp_client.call_tool(tool_name, args)
            return (
                json.dumps(result)[:1000]
                if isinstance(result, (dict, list))
                else str(result)[:1000]
            )
        except Exception as e:
            return f"ERROR: {str(e)[:200]}"

    # ── Anthropic attacker ─────────────────────────────────────────────────────

    async def _attacker_anthropic(
        self, mcp_client, tools, system, initial_prompt, on_event
    ) -> List[Dict]:
        anthropic_tools = _to_anthropic_tools(tools)
        messages = [{"role": "user", "content": initial_prompt}]
        events: List[Dict] = []
        total_calls = 0

        for _ in range(self.max_iterations + self.max_stories):
            response = await self._attacker_client.messages.create(
                model=self.attacker_model,
                max_tokens=4096,
                system=system,
                tools=anthropic_tools,
                messages=messages,
            )

            tool_uses = []
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    ev = {"type": "thinking", "content": block.text}
                    events.append(ev)
                    for m in re.finditer(r"=== SCENARIO (\d+):", block.text):
                        events.append({"type": "scenario_marker", "index": int(m.group(1))})
                    if on_event:
                        await on_event(ev)
                if block.type == "tool_use":
                    tool_uses.append(block)

            if response.stop_reason == "end_turn" or not tool_uses:
                break

            tool_results = []
            for tu in tool_uses:
                if total_calls >= self.max_iterations:
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": tu.id,
                        "content": "BUDGET EXHAUSTED — mission ended.",
                    })
                    continue

                ev_call = {"type": "tool_call", "tool": tu.name, "args": tu.input}
                events.append(ev_call)
                if on_event:
                    await on_event(ev_call)

                result_str = await self._execute_tool(mcp_client, tu.name, tu.input)

                ev_result = {"type": "tool_result", "tool": tu.name, "result": result_str}
                events.append(ev_result)
                if on_event:
                    await on_event(ev_result)

                tool_results.append({
                    "type": "tool_result", "tool_use_id": tu.id, "content": result_str,
                })
                total_calls += 1

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            if total_calls >= self.max_iterations:
                break

        logger.info(f"Attacker (anthropic): {total_calls} tool calls, {len(events)} events")
        return events

    # ── OpenAI-compat attacker (Groq) ──────────────────────────────────────────

    async def _attacker_openai_compat(
        self, mcp_client, tools, system, initial_prompt, on_event
    ) -> List[Dict]:
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name":        t["name"],
                    "description": t.get("description", ""),
                    "parameters":  t.get("inputSchema") or {"type": "object", "properties": {}},
                },
            }
            for t in tools
        ]
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": initial_prompt},
        ]
        events: List[Dict] = []
        total_calls = 0

        for _ in range(self.max_iterations + self.max_stories):
            try:
                response = await self._attacker_client.chat.completions.create(
                    model=self.attacker_model,
                    max_tokens=4096,
                    messages=messages,
                    tools=openai_tools,
                    tool_choice="auto",
                )
            except Exception as api_err:
                ev = {"type": "thinking",
                      "content": f"[ATTACKER ERROR] {str(api_err)[:300]}"}
                events.append(ev)
                if on_event:
                    await on_event(ev)
                logger.warning(f"Attacker API error (openai-compat): {api_err}")
                break

            msg = response.choices[0].message
            if msg.content:
                ev = {"type": "thinking", "content": msg.content}
                events.append(ev)
                for m in re.finditer(r"=== SCENARIO (\d+):", msg.content):
                    events.append({"type": "scenario_marker", "index": int(m.group(1))})
                if on_event:
                    await on_event(ev)

            tool_calls = msg.tool_calls or []
            if not tool_calls:
                break

            messages.append({
                "role": "assistant", "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id, "type": "function",
                        "function": {
                            "name":      tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            })

            for tc in tool_calls:
                if total_calls >= self.max_iterations:
                    messages.append({
                        "role": "tool", "tool_call_id": tc.id,
                        "content": "BUDGET EXHAUSTED — mission ended.",
                    })
                    continue

                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                ev_call = {"type": "tool_call", "tool": tc.function.name, "args": args}
                events.append(ev_call)
                if on_event:
                    await on_event(ev_call)

                result_str = await self._execute_tool(mcp_client, tc.function.name, args)

                ev_result = {"type": "tool_result", "tool": tc.function.name,
                             "result": result_str}
                events.append(ev_result)
                if on_event:
                    await on_event(ev_result)

                messages.append({
                    "role": "tool", "tool_call_id": tc.id, "content": result_str,
                })
                total_calls += 1

            if total_calls >= self.max_iterations:
                break

        logger.info(f"Attacker (groq): {total_calls} tool calls, {len(events)} events")
        return events

    # ── Gemini attacker ────────────────────────────────────────────────────────

    async def _attacker_gemini(
        self, mcp_client, tools, system, initial_prompt, on_event
    ) -> List[Dict]:
        declarations  = _to_gemini_declarations(tools)
        gemini_tools  = [genai_types.Tool(function_declarations=declarations)]
        config = genai_types.GenerateContentConfig(
            system_instruction=system,
            tools=gemini_tools,
        )
        contents = [genai_types.Content(
            role="user",
            parts=[genai_types.Part.from_text(initial_prompt)],
        )]
        events: List[Dict] = []
        total_calls = 0

        for _ in range(self.max_iterations + self.max_stories):
            response = await self._attacker_client.aio.models.generate_content(
                model=self.attacker_model,
                contents=contents,
                config=config,
            )
            candidate = response.candidates[0]
            contents.append(candidate.content)

            function_call_parts = []
            for part in candidate.content.parts:
                if getattr(part, "text", None):
                    ev = {"type": "thinking", "content": part.text}
                    events.append(ev)
                    for m in re.finditer(r"=== SCENARIO (\d+):", part.text):
                        events.append({"type": "scenario_marker", "index": int(m.group(1))})
                    if on_event:
                        await on_event(ev)
                if getattr(part, "function_call", None) and part.function_call.name:
                    function_call_parts.append(part)

            if not function_call_parts:
                break

            result_parts = []
            for part in function_call_parts:
                fc = part.function_call
                if total_calls >= self.max_iterations:
                    result_parts.append(genai_types.Part.from_function_response(
                        name=fc.name,
                        response={"result": "BUDGET EXHAUSTED — mission ended."},
                    ))
                    continue

                args = dict(fc.args) if fc.args else {}
                ev_call = {"type": "tool_call", "tool": fc.name, "args": args}
                events.append(ev_call)
                if on_event:
                    await on_event(ev_call)

                result_str = await self._execute_tool(mcp_client, fc.name, args)

                ev_result = {"type": "tool_result", "tool": fc.name, "result": result_str}
                events.append(ev_result)
                if on_event:
                    await on_event(ev_result)

                result_parts.append(genai_types.Part.from_function_response(
                    name=fc.name,
                    response={"result": result_str},
                ))
                total_calls += 1

            contents.append(genai_types.Content(role="user", parts=result_parts))
            if total_calls >= self.max_iterations:
                break

        logger.info(f"Attacker (gemini): {total_calls} tool calls, {len(events)} events")
        return events

    # ── Judge ──────────────────────────────────────────────────────────────────

    async def _run_judge(
        self,
        events:           List[Dict],
        mcp_metadata:     Dict,
        mission_briefing: Optional[Dict],
    ) -> List[Dict]:
        transcript_text        = _format_transcript(events)
        tool_call_counts       = _count_tool_calls_per_scenario(events, self.max_stories)
        event_slices           = _slice_events_per_scenario(events, self.max_stories)
        planned_scenarios_block = _build_planned_scenarios_block(mission_briefing)

        prompt = JUDGE_PROMPT_TEMPLATE.format(
            mcp_name               = mcp_metadata.get("name", "unknown"),
            tool_count             = mcp_metadata.get("tool_count", 0),
            prompt_count           = mcp_metadata.get("prompt_count", 0),
            resource_count         = mcp_metadata.get("resource_count", 0),
            planned_scenarios_block= planned_scenarios_block,
            transcript_text        = transcript_text,
        )

        try:
            if self.judge_provider == "anthropic":
                response = await self._judge_client.messages.create(
                    model=self.judge_model,
                    max_tokens=4096,
                    system=JUDGE_SYSTEM,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = response.content[0].text
            elif self.judge_provider == "groq":
                response = await self._judge_client.chat.completions.create(
                    model=self.judge_model,
                    max_tokens=4096,
                    messages=[
                        {"role": "system", "content": JUDGE_SYSTEM},
                        {"role": "user",   "content": prompt},
                    ],
                )
                raw = response.choices[0].message.content
            else:
                full_prompt = f"{JUDGE_SYSTEM}\n\n{prompt}"
                response = await self._judge_client.aio.models.generate_content(
                    model=self.judge_model,
                    contents=full_prompt,
                )
                raw = response.text

            # Parse judge JSON
            start = raw.find("{")
            if start == -1:
                raise ValueError("No JSON in judge response")
            raw_json = raw[start:]
            raw_json = re.sub(r',\s*([\]}])', r'\1', raw_json)
            parsed, _ = json.JSONDecoder().raw_decode(raw_json)

            stories      = parsed.get("stories", [])
            coverage_pct = parsed.get("coverage_pct", 0)
            surprises    = parsed.get("surprises", [])

            # Enrich each story with metadata + its own transcript slice
            for i, s in enumerate(stories):
                s["story_index"]   = s.get("story_index", i + 1)
                s["tool_calls_made"] = tool_call_counts[i] if i < len(tool_call_counts) else 0
                s["attacker_model"]  = f"{self.attacker_provider}/{self.attacker_model}"
                s["judge_model"]     = f"{self.judge_provider}/{self.judge_model}"
                # ✅ Each story gets ONLY its own events (not the full run)
                s["transcript"]      = event_slices[i] if i < len(event_slices) else []
                s["coverage_pct"]    = coverage_pct
                s["surprises"]       = surprises

            return stories

        except Exception as e:
            logger.error(f"Judge analysis failed: {e}", exc_info=True)
            return [{
                "story_index":     1,
                "attack_goal":     "Agent ran but judge analysis failed",
                "tool_calls_made": sum(1 for ev in events if ev["type"] == "tool_call"),
                "verdict":         "inconclusive",
                "severity":        "info",
                "title":           "Judge Analysis Failed",
                "finding":         f"Attacker ran but judge could not parse results: {str(e)[:200]}",
                "evidence":        "",
                "recommendation":  "Review raw transcript manually.",
                "attacker_model":  f"{self.attacker_provider}/{self.attacker_model}",
                "judge_model":     f"{self.judge_provider}/{self.judge_model}",
                "transcript":      events,
                "coverage_pct":    0,
                "surprises":       [],
                "was_planned":     False,
            }]
