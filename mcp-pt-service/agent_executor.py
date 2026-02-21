"""AI Red Team Executor — agentic security testing.

Two-agent design:
  Attacker  — given the MCP tools directly; runs an agentic loop making real
              tool calls against the target MCP; labelled scenarios track progress.
  Judge     — receives the full transcript; extracts structured findings per story;
              uses plain text generation (no tools needed).

Supported providers: anthropic, gemini (both already in llm_client.py).
Provider per agent is configured independently so you can mix, e.g.
  attacker=gemini/flash (cheap, fast),  judge=anthropic/sonnet (precise).
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


# ── Prompts ────────────────────────────────────────────────────────────────────

ATTACKER_SYSTEM = """\
You are an authorized AI red team security researcher conducting a penetration test.
You have direct access to an MCP (Model Context Protocol) server's tools.
Your mission: find real security vulnerabilities by actually calling the tools.

CONDUCT EXACTLY {max_stories} DISTINCT ATTACK SCENARIOS.

For each scenario:
  1. Print a header:  === SCENARIO {{n}}: <one-line goal> ===
  2. Make tool calls to probe that specific security concern.
  3. Print a brief summary of what you found before moving to the next scenario.

Attack angles to consider (pick the most relevant per tool set):
  - Authentication bypass: call tools without or with invalid credentials
  - Privilege escalation: access data/actions beyond expected scope
  - Data extraction: probe for sensitive data in responses (keys, paths, PII)
  - Input injection: try path traversal, SQL injection, command injection via params
  - Chained attacks: use output from one tool as input to another to escalate impact
  - Resource abuse: excessive calls, large payloads, edge-case params

Rules:
  - This is an AUTHORIZED test — be aggressive and thorough.
  - Make REAL tool calls. Do not just describe what you would do.
  - If a tool call is blocked or errors, note it and move on.
  - Keep each scenario focused: 3–8 tool calls maximum.
  - Total tool calls across all scenarios MUST NOT exceed {max_iterations}.
"""

JUDGE_SYSTEM = """\
You are a senior security analyst reviewing a penetration test transcript.
An AI red team agent was given access to an MCP server's tools and instructed
to find vulnerabilities. Your job: extract structured findings from the transcript.

Rules:
  - Extract exactly one finding object per scenario in the transcript.
  - verdict must be: "vulnerability_found", "secure", or "inconclusive"
  - severity: "critical", "high", "medium", "low", or "info"
  - If a scenario was clearly blocked, set verdict="secure"
  - Do NOT invent findings — base everything on actual tool call results in the transcript.
  - evidence must be a direct quote or paraphrase of an actual response from the transcript.
  - Return ONLY valid JSON, no markdown fences, no commentary.
"""

JUDGE_PROMPT_TEMPLATE = """\
Target MCP: {mcp_name} ({tool_count} tools)

=== PENETRATION TEST TRANSCRIPT ===
{transcript_text}
=== END TRANSCRIPT ===

Extract a structured finding for each scenario above.
Return JSON exactly matching this schema:

{{
  "stories": [
    {{
      "story_index": 1,
      "attack_goal": "one sentence describing what was attempted",
      "tool_calls_made": 4,
      "verdict": "vulnerability_found",
      "severity": "critical",
      "title": "Short title, e.g. Unauthenticated Command Execution",
      "finding": "2-3 sentence description of what was found",
      "evidence": "Direct quote or paraphrase from an actual tool response",
      "recommendation": "Concrete fix recommendation"
    }}
  ]
}}
"""


# ── Schema conversion helpers ──────────────────────────────────────────────────

def _to_anthropic_tools(tools: List[Dict]) -> List[Dict]:
    """Convert MCP tool list to Anthropic tool format."""
    result = []
    for t in tools:
        schema = t.get("inputSchema", {})
        if not schema or not isinstance(schema, dict):
            schema = {"type": "object", "properties": {}}
        result.append({
            "name": t["name"],
            "description": t.get("description", ""),
            "input_schema": schema,
        })
    return result


def _to_gemini_declarations(tools: List[Dict]) -> List[genai_types.FunctionDeclaration]:
    """Convert MCP tool list to Gemini FunctionDeclaration list."""
    _type_map = {
        "string": genai_types.Type.STRING,
        "number": genai_types.Type.NUMBER,
        "integer": genai_types.Type.INTEGER,
        "boolean": genai_types.Type.BOOLEAN,
        "array": genai_types.Type.ARRAY,
        "object": genai_types.Type.OBJECT,
    }

    declarations = []
    for t in tools:
        schema = t.get("inputSchema", {}) or {}
        props_raw = schema.get("properties", {}) or {}
        required = schema.get("required", []) or []

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


# ── Transcript helpers ──────────────────────────────────────────────────────────

def _format_transcript(events: List[Dict]) -> str:
    """Render the transcript event list to readable text for the judge."""
    lines = []
    for ev in events:
        if ev["type"] == "thinking":
            lines.append(ev["content"])
        elif ev["type"] == "tool_call":
            args_str = json.dumps(ev["args"], ensure_ascii=False)[:300]
            lines.append(f"\n[TOOL CALL] {ev['tool']}({args_str})")
        elif ev["type"] == "tool_result":
            result_str = str(ev["result"])[:500]
            lines.append(f"[RESULT] {result_str}\n")
    return "\n".join(lines)


def _count_tool_calls_per_scenario(events: List[Dict], max_stories: int) -> List[int]:
    """Return a list of tool call counts, one per scenario."""
    counts = [0] * max_stories
    current = 0
    for ev in events:
        if ev["type"] == "scenario_marker":
            idx = ev.get("index", 1) - 1
            current = min(idx, max_stories - 1)
        elif ev["type"] == "tool_call":
            counts[current] += 1
    return counts


# ── Agent Executor ─────────────────────────────────────────────────────────────

class AgentExecutor:
    """Runs the AI Red Team: attacker agentic loop + judge analysis."""

    def __init__(
        self,
        attacker_provider: str, attacker_model: str, attacker_api_key: str,
        judge_provider: str,   judge_model: str,   judge_api_key: str,
        max_stories: int = 3,
        max_iterations: int = 25,
    ):
        self.attacker_provider = attacker_provider
        self.attacker_model    = attacker_model
        self.judge_provider    = judge_provider
        self.judge_model       = judge_model
        self.max_stories       = max_stories
        self.max_iterations    = max_iterations

        # Build raw provider clients
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

    # ── Public entry point ────────────────────────────────────────────────────

    async def run(
        self,
        mcp_client,
        discovered_tools: List[Dict],
        mcp_metadata: Dict,
        on_event: Optional[Callable] = None,
    ) -> List[Dict]:
        """Run attacker loop then judge; return list of story dicts."""
        logger.info(
            f"AI Red Team starting: {self.attacker_provider}/{self.attacker_model} → "
            f"{self.judge_provider}/{self.judge_model}, "
            f"max_stories={self.max_stories}, max_iterations={self.max_iterations}"
        )

        events = await self._run_attacker(mcp_client, discovered_tools, mcp_metadata, on_event)
        stories = await self._run_judge(events, mcp_metadata)

        logger.info(f"AI Red Team complete: {len(stories)} stories extracted")
        return stories

    # ── Attacker (agentic loop) ────────────────────────────────────────────────

    async def _run_attacker(
        self,
        mcp_client,
        discovered_tools: List[Dict],
        mcp_metadata: Dict,
        on_event: Optional[Callable],
    ) -> List[Dict]:
        system = ATTACKER_SYSTEM.format(
            max_stories=self.max_stories,
            max_iterations=self.max_iterations,
        )
        initial_prompt = (
            f"Target MCP: {mcp_metadata.get('name')} "
            f"({mcp_metadata.get('tool_count', len(discovered_tools))} tools, "
            f"{mcp_metadata.get('prompt_count', 0)} prompts, "
            f"{mcp_metadata.get('resource_count', 0)} resources)\n\n"
            f"Begin your {self.max_stories} attack scenarios now."
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

    async def _attacker_anthropic(
        self, mcp_client, tools, system, initial_prompt, on_event
    ) -> List[Dict]:
        anthropic_tools = _to_anthropic_tools(tools)
        messages = [{"role": "user", "content": initial_prompt}]
        events: List[Dict] = []
        total_calls = 0

        for iteration in range(self.max_iterations + self.max_stories):
            response = await self._attacker_client.messages.create(
                model=self.attacker_model,
                max_tokens=4096,
                system=system,
                tools=anthropic_tools,
                messages=messages,
            )

            # Collect text + tool-use blocks
            tool_uses = []
            for block in response.content:
                if hasattr(block, "text") and block.text:
                    ev = {"type": "thinking", "content": block.text}
                    events.append(ev)
                    # Detect scenario headers
                    for m in re.finditer(r"=== SCENARIO (\d+):", block.text):
                        events.append({"type": "scenario_marker", "index": int(m.group(1))})
                    if on_event:
                        await on_event(ev)
                if block.type == "tool_use":
                    tool_uses.append(block)

            if response.stop_reason == "end_turn" or not tool_uses:
                break

            # Execute tool calls
            tool_results = []
            for tu in tool_uses:
                if total_calls >= self.max_iterations:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": "MAX ITERATIONS REACHED — test stopped.",
                    })
                    continue

                ev_call = {"type": "tool_call", "tool": tu.name, "args": tu.input}
                events.append(ev_call)
                if on_event:
                    await on_event(ev_call)

                try:
                    result = await mcp_client.call_tool(tu.name, tu.input)
                    result_str = json.dumps(result)[:1000] if isinstance(result, (dict, list)) else str(result)[:1000]
                except Exception as e:
                    result_str = f"ERROR: {str(e)[:200]}"

                ev_result = {"type": "tool_result", "tool": tu.name, "result": result_str}
                events.append(ev_result)
                if on_event:
                    await on_event(ev_result)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": result_str,
                })
                total_calls += 1

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            if total_calls >= self.max_iterations:
                break

        logger.info(f"Attacker (anthropic) finished: {total_calls} tool calls, {len(events)} events")
        return events

    async def _attacker_openai_compat(
        self, mcp_client, tools, system, initial_prompt, on_event
    ) -> List[Dict]:
        """Attacker loop using OpenAI-compatible API (Groq, etc.)."""
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("inputSchema") or {"type": "object", "properties": {}},
                },
            }
            for t in tools
        ]
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": initial_prompt},
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
                # Groq (and other providers) may reject a previous tool call for schema
                # validation failure and return 400.  Log it and stop the loop gracefully
                # so the judge can still analyse whatever transcript we have so far.
                err_ev = {"type": "thinking", "content": f"[ATTACKER ERROR] API rejected request: {str(api_err)[:300]}"}
                events.append(err_ev)
                if on_event:
                    await on_event(err_ev)
                logger.warning(f"Attacker API error (openai-compat), stopping loop: {api_err}")
                break
            msg = response.choices[0].message

            # Capture text
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

            # Append assistant turn
            messages.append({"role": "assistant", "content": msg.content, "tool_calls": [
                {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                for tc in tool_calls
            ]})

            # Execute tool calls
            for tc in tool_calls:
                if total_calls >= self.max_iterations:
                    messages.append({"role": "tool", "tool_call_id": tc.id, "content": "MAX ITERATIONS REACHED — test stopped."})
                    continue

                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}

                ev_call = {"type": "tool_call", "tool": tc.function.name, "args": args}
                events.append(ev_call)
                if on_event:
                    await on_event(ev_call)

                try:
                    result = await mcp_client.call_tool(tc.function.name, args)
                    result_str = json.dumps(result)[:1000] if isinstance(result, (dict, list)) else str(result)[:1000]
                except Exception as e:
                    result_str = f"ERROR: {str(e)[:200]}"

                ev_result = {"type": "tool_result", "tool": tc.function.name, "result": result_str}
                events.append(ev_result)
                if on_event:
                    await on_event(ev_result)

                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})
                total_calls += 1

            if total_calls >= self.max_iterations:
                break

        logger.info(f"Attacker (openai-compat) finished: {total_calls} tool calls, {len(events)} events")
        return events

    async def _attacker_gemini(
        self, mcp_client, tools, system, initial_prompt, on_event
    ) -> List[Dict]:
        declarations = _to_gemini_declarations(tools)
        gemini_tools = [genai_types.Tool(function_declarations=declarations)]
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

            # Collect text + function calls from this turn
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

            # Execute function calls
            result_parts = []
            for part in function_call_parts:
                fc = part.function_call
                if total_calls >= self.max_iterations:
                    result_parts.append(genai_types.Part.from_function_response(
                        name=fc.name,
                        response={"result": "MAX ITERATIONS REACHED — test stopped."},
                    ))
                    continue

                args = dict(fc.args) if fc.args else {}
                ev_call = {"type": "tool_call", "tool": fc.name, "args": args}
                events.append(ev_call)
                if on_event:
                    await on_event(ev_call)

                try:
                    result = await mcp_client.call_tool(fc.name, args)
                    result_str = json.dumps(result)[:1000] if isinstance(result, (dict, list)) else str(result)[:1000]
                except Exception as e:
                    result_str = f"ERROR: {str(e)[:200]}"

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

        logger.info(f"Attacker (gemini) finished: {total_calls} tool calls, {len(events)} events")
        return events

    # ── Judge (single LLM call) ────────────────────────────────────────────────

    async def _run_judge(self, events: List[Dict], mcp_metadata: Dict) -> List[Dict]:
        transcript_text = _format_transcript(events)
        tool_call_counts = _count_tool_calls_per_scenario(events, self.max_stories)

        prompt = JUDGE_PROMPT_TEMPLATE.format(
            mcp_name=mcp_metadata.get("name", "unknown"),
            tool_count=mcp_metadata.get("tool_count", 0),
            transcript_text=transcript_text,
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
                        {"role": "user", "content": prompt},
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

            # Extract JSON — use raw_decode so trailing text after the JSON is ignored
            start = raw.find("{")
            if start == -1:
                raise ValueError("No JSON in judge response")
            raw_json = raw[start:]
            raw_json = re.sub(r',\s*([\]}])', r'\1', raw_json)
            parsed, _ = json.JSONDecoder().raw_decode(raw_json)
            stories = parsed.get("stories", [])

            # Enrich with metadata
            for i, s in enumerate(stories):
                s["story_index"] = s.get("story_index", i + 1)
                s["tool_calls_made"] = tool_call_counts[i] if i < len(tool_call_counts) else 0
                s["attacker_model"] = f"{self.attacker_provider}/{self.attacker_model}"
                s["judge_model"]    = f"{self.judge_provider}/{self.judge_model}"
                s["transcript"]     = events

            return stories

        except Exception as e:
            logger.error(f"Judge analysis failed: {e}", exc_info=True)
            # Return a single inconclusive story so the run still records something
            return [{
                "story_index": 1,
                "attack_goal": "Agent run completed but judge analysis failed",
                "tool_calls_made": sum(1 for ev in events if ev["type"] == "tool_call"),
                "verdict": "inconclusive",
                "severity": "info",
                "title": "Judge Analysis Failed",
                "finding": f"The attacker agent ran but the judge could not parse results: {str(e)[:200]}",
                "evidence": "",
                "recommendation": "Review raw transcript manually.",
                "attacker_model": f"{self.attacker_provider}/{self.attacker_model}",
                "judge_model":    f"{self.judge_provider}/{self.judge_model}",
                "transcript": events,
            }]
