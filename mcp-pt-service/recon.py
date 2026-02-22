"""
MCP Red Team Reconnaissance — Mission Briefing Engine.

Layer 1 — Fast Scan (no LLM, instant):
  Classifies tool/prompt/resource schemas by risk-signal patterns.
  Builds a tool-chain graph (read tool → destructive tool via shared params).

Layer 2 — Intel Pass (single LLM call, ~3 s):
  Reads Layer 1 output + full asset schemas.
  Produces a structured Mission Briefing:
    - MCP domain + risk surface rating
    - Prioritized attack targets with specific payloads
    - Attack chains to exploit
    - Per-scenario assignments (one per story slot)

Cache: briefing is keyed by SHA-256 of all tool/prompt/resource schemas.
Valid forever unless the MCP's schema changes (no TTL — only schema-change
invalidation via is_stale flag in pt_prescan_cache).
"""

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from logger import logger


# ── Layer 1: Risk Signal Catalogue ─────────────────────────────────────────────

_PARAM_RISKS: List[Dict] = [
    {
        "signal":   "path_traversal",
        "params":   {"path", "file", "filename", "filepath", "dir", "directory",
                     "location", "src", "dest", "target", "output", "input_file",
                     "report", "template_path", "log_path"},
        "attack":   "Path Traversal",
        "payloads": ["../../../etc/passwd", "../../.env", "../../../../etc/shadow",
                     "..\\..\\..\\Windows\\system.ini", "/proc/self/environ"],
        "severity": "critical",
    },
    {
        "signal":   "ssrf",
        "params":   {"url", "endpoint", "host", "uri", "link", "webhook",
                     "callback", "redirect", "remote", "fetch", "source", "proxy"},
        "attack":   "Server-Side Request Forgery (SSRF)",
        "payloads": ["http://169.254.169.254/latest/meta-data/",
                     "http://localhost:22", "http://internal/admin",
                     "file:///etc/passwd"],
        "severity": "high",
    },
    {
        "signal":   "idor",
        "params":   {"user_id", "userid", "account_id", "accountid", "owner_id",
                     "profile_id", "customer_id", "record_id", "uid", "id",
                     "entity_id", "object_id"},
        "attack":   "Insecure Direct Object Reference (IDOR)",
        "payloads": ["1", "2", "0", "-1", "999999", "admin"],
        "severity": "high",
    },
    {
        "signal":   "injection",
        "params":   {"query", "filter", "search", "sql", "where", "order", "sort",
                     "expression", "command", "cmd", "exec", "shell", "script",
                     "eval", "input", "raw"},
        "attack":   "Injection (SQL / Command / Code)",
        "payloads": ["' OR '1'='1", "'; DROP TABLE users;--", "$(id)",
                     "${7*7}", "| ls -la", "; cat /etc/passwd"],
        "severity": "critical",
    },
    {
        "signal":   "template_injection",
        "params":   {"template", "format", "pattern", "message", "body",
                     "content", "text", "render", "subject", "layout"},
        "attack":   "Server-Side Template Injection",
        "payloads": ["{{7*7}}", "${7*7}", "<%=7*7%>", "#{7*7}"],
        "severity": "high",
    },
    {
        "signal":   "privilege_escalation",
        "params":   {"role", "admin", "permission", "privilege", "is_admin",
                     "superuser", "access_level", "group", "scope", "grant",
                     "rights", "capabilities"},
        "attack":   "Privilege Escalation / Mass Assignment",
        "payloads": ["admin", "superuser", "true", "1", "root", "manager"],
        "severity": "high",
    },
    {
        "signal":   "auth_bypass",
        "params":   {"token", "key", "secret", "password", "auth", "credential",
                     "api_key", "bearer", "session", "jwt", "cookie"},
        "attack":   "Authentication Bypass",
        "payloads": ["null", "", "undefined", "admin", "AAAA", "Bearer invalid"],
        "severity": "critical",
    },
]

_DESTRUCTIVE_VERBS = {"delete", "remove", "drop", "destroy", "purge", "reset",
                      "clear", "wipe", "kill", "terminate", "disable", "revoke"}
_READ_VERBS       = {"get", "fetch", "read", "list", "search", "find", "query",
                     "show", "retrieve", "dump", "export", "scan", "check"}

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

_URI_RISKS: Dict[str, Tuple[str, str]] = {
    "file://":  ("path_traversal", "critical"),
    "db://":    ("idor",           "high"),
    "http://":  ("ssrf",           "high"),
    "https://": ("ssrf",           "medium"),
    "{":        ("parameter_injection", "medium"),
}


# ── Layer 1 helpers ────────────────────────────────────────────────────────────

def _classify_params(params: Dict[str, Any]) -> List[Dict]:
    """Match parameter names against risk signal patterns. Returns hits."""
    hits = []
    for param_name, param_schema in params.items():
        lower = param_name.lower()
        for risk in _PARAM_RISKS:
            if lower in risk["params"] or any(
                kw in lower for kw in risk["params"] if len(kw) > 3
            ):
                hits.append({
                    "param":       param_name,
                    "signal":      risk["signal"],
                    "attack":      risk["attack"],
                    "payloads":    risk["payloads"],
                    "severity":    risk["severity"],
                    "param_type":  param_schema.get("type", "string") if isinstance(param_schema, dict) else "string",
                    "param_desc":  param_schema.get("description", "")[:100] if isinstance(param_schema, dict) else "",
                })
                break   # one signal per param is enough
    return hits


def _leading_verb(name: str) -> Optional[str]:
    """Extract the leading verb from a snake_case or camelCase name."""
    lower = name.lower().replace("-", "_")
    for verb in _DESTRUCTIVE_VERBS | _READ_VERBS:
        if lower.startswith(verb):
            return verb
    return None


def _top_severity(param_hits: List[Dict], is_destructive: bool) -> str:
    severities = [h["severity"] for h in param_hits]
    if "critical" in severities:
        return "critical"
    if "high" in severities or is_destructive:
        return "high"
    if "medium" in severities:
        return "medium"
    return "low"


# ── Layer 1 main ───────────────────────────────────────────────────────────────

def layer1_scan(
    tools:     List[Dict],
    prompts:   List[Dict],
    resources: List[Dict],
) -> Dict:
    """
    Deterministic risk scan — no LLM needed.
    Returns a structured risk map: tool_risks, prompt_risks, resource_risks, chains.
    """
    # ── Tools ──────────────────────────────────────────────────────────────────
    tool_risks = []
    for tool in tools:
        schema = tool.get("inputSchema", {}) or {}
        params = schema.get("properties", {}) or {}
        param_hits   = _classify_params(params)
        verb         = _leading_verb(tool.get("name", ""))
        is_destructive = verb in _DESTRUCTIVE_VERBS if verb else False
        is_read        = verb in _READ_VERBS       if verb else False

        if param_hits or is_destructive:
            tool_risks.append({
                "name":          tool["name"],
                "description":   tool.get("description", "")[:200],
                "param_names":   list(params.keys()),
                "param_hits":    param_hits,
                "is_destructive": is_destructive,
                "is_read":        is_read,
                "top_severity":  _top_severity(param_hits, is_destructive),
            })

    tool_risks.sort(key=lambda x: _SEVERITY_ORDER.get(x["top_severity"], 4))

    # ── Prompts ────────────────────────────────────────────────────────────────
    prompt_risks = []
    for p in prompts:
        # MCP prompt arguments are a list of {name, description, required}
        arg_list = p.get("arguments") or []
        arg_dict = {
            a.get("name", ""): {
                "type": "string",
                "description": a.get("description", ""),
            }
            for a in arg_list if a.get("name")
        }
        param_hits = _classify_params(arg_dict)
        if param_hits:
            prompt_risks.append({
                "name":        p.get("name", ""),
                "description": p.get("description", "")[:200],
                "arguments":   [a.get("name") for a in arg_list],
                "param_hits":  param_hits,
                "top_severity": _top_severity(param_hits, False),
            })

    # ── Resources ──────────────────────────────────────────────────────────────
    resource_risks = []
    for r in resources:
        uri = r.get("uri") or r.get("uriTemplate") or ""
        for scheme, (signal, severity) in _URI_RISKS.items():
            if scheme in uri:
                resource_risks.append({
                    "name":        r.get("name") or uri[:50],
                    "uri":         uri,
                    "signal":      signal,
                    "severity":    severity,
                    "description": r.get("description", "")[:200],
                })
                break

    # ── Chain graph: read tools that feed into destructive tools ───────────────
    chains = []
    seen_pairs = set()
    read_tools = [t for t in tool_risks if t["is_read"]]
    dest_tools = [t for t in tool_risks if t["is_destructive"]]

    for rt in read_tools:
        rt_signals = {h["signal"] for h in rt["param_hits"]}
        for dt in dest_tools:
            pair = (rt["name"], dt["name"])
            if pair in seen_pairs:
                continue
            dt_signals = {h["signal"] for h in dt["param_hits"]}
            shared = rt_signals & dt_signals
            # Chain if: shared param signals (e.g. both have 'idor') OR simply read→destroy
            if shared or (rt["is_read"] and dt["is_destructive"]):
                chains.append({
                    "steps":           [rt["name"], dt["name"]],
                    "goal":            f"Use {rt['name']} output to drive {dt['name']}",
                    "shared_signals":  list(shared),
                })
                seen_pairs.add(pair)

    total = len(tool_risks) + len(prompt_risks) + len(resource_risks)
    logger.info(
        f"Layer 1 scan: {len(tool_risks)} tool risks, {len(prompt_risks)} prompt risks, "
        f"{len(resource_risks)} resource risks, {len(chains)} chains"
    )
    return {
        "tool_risks":      tool_risks,
        "prompt_risks":    prompt_risks,
        "resource_risks":  resource_risks,
        "chains":          chains,
        "total_risks":     total,
    }


# ── Cache key ──────────────────────────────────────────────────────────────────

def compute_schemas_hash(
    tools:     List[Dict],
    prompts:   List[Dict],
    resources: List[Dict],
) -> str:
    """SHA-256 of all schemas — used as the prescan cache key."""
    blob = json.dumps({
        "tools": sorted(
            [{k: t.get(k) for k in ("name", "description", "inputSchema")} for t in tools],
            key=lambda x: x.get("name", ""),
        ),
        "prompts": sorted(
            [{k: p.get(k) for k in ("name", "description", "arguments")} for p in prompts],
            key=lambda x: x.get("name", ""),
        ),
        "resources": sorted(
            [r.get("uri") or r.get("uriTemplate") or r.get("name", "") for r in resources]
        ),
    }, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


# ── Layer 2: LLM Intel Pass ────────────────────────────────────────────────────

_INTEL_SYSTEM = """\
You are an elite penetration tester specializing in MCP (Model Context Protocol) security.

You have been given:
  1. An automated risk scan of an MCP server's tools, prompts, and resources
  2. The full schemas of those assets

Your job: produce a MISSION BRIEFING for an AI attacker agent.

Rules:
  - Base everything strictly on the actual schemas and scan results — no hallucination.
  - Assign exactly {max_stories} DISTINCT scenarios — one per story slot.
  - Each scenario must target a DIFFERENT attack vector or asset.
  - Payloads must be SPECIFIC (e.g. "../../../etc/passwd", not "try path traversal").
  - For chains: specify the exact tool sequence and what data flows between them.
  - Keep the briefing concise — the attacker will use it as a mission card.
  - Return ONLY valid JSON. No markdown fences. No commentary outside the JSON.
"""

_INTEL_PROMPT = """\
MCP: {mcp_name}
Assets: {tool_count} tools | {prompt_count} prompts | {resource_count} resources

=== AUTOMATED RISK SCAN ===
{scan_summary}
===========================

=== ASSET SCHEMAS ===
{asset_schemas}
====================

Produce the mission briefing for {max_stories} attack scenarios.
Return JSON exactly matching:

{{
  "mcp_domain": "short description of what this MCP does",
  "risk_surface": "low|medium|medium-high|high|critical",
  "attack_surface_summary": "1-2 sentence overview of the attack surface",
  "prioritized_targets": [
    {{
      "priority": 1,
      "asset_type": "tool|prompt|resource",
      "asset_name": "exact name",
      "attack": "attack category name",
      "target_param": "the specific parameter to attack, or null",
      "payloads": ["payload1", "payload2", "payload3"],
      "reason": "one sentence: why this is high priority"
    }}
  ],
  "attack_chains": [
    {{
      "steps": ["tool_a", "tool_b"],
      "goal": "what the chain achieves in one sentence",
      "method": "call tool_a with X to get Y, feed Y into tool_b as Z"
    }}
  ],
  "scenario_assignments": [
    "Scenario 1: <specific goal> — <specific method with named tools and payloads>",
    "Scenario 2: ..."
  ]
}}
"""


async def layer2_intel(
    mcp_name:     str,
    scan:         Dict,
    tools:        List[Dict],
    prompts:      List[Dict],
    resources:    List[Dict],
    max_stories:  int,
    llm_provider: str,
    llm_model:    str,
    api_key:      str,
) -> Dict:
    """Single LLM call → structured mission briefing JSON."""
    from llm_client import LLMClient

    # ── Build concise scan summary ─────────────────────────────────────────────
    parts = []
    for tr in scan["tool_risks"][:10]:
        hits = ", ".join(f"{h['signal']}({h['param']})" for h in tr["param_hits"])
        tag = "DESTRUCTIVE" if tr["is_destructive"] and not hits else ""
        parts.append(
            f"  TOOL {tr['name']} [{tr['top_severity'].upper()}]: "
            f"{hits or tag or 'suspicious op'}"
        )
    for pr in scan["prompt_risks"][:4]:
        hits = ", ".join(f"{h['signal']}({h['param']})" for h in pr["param_hits"])
        parts.append(f"  PROMPT {pr['name']} [HIGH]: {hits}")
    for rr in scan["resource_risks"][:4]:
        parts.append(
            f"  RESOURCE {rr['name']} [{rr['severity'].upper()}]: "
            f"{rr['signal']} via URI"
        )
    for ch in scan["chains"][:4]:
        parts.append(
            f"  CHAIN: {' → '.join(ch['steps'])} ({ch['goal']})"
        )
    scan_summary = "\n".join(parts) or "No high-risk patterns detected automatically."

    # ── Build abbreviated asset schemas ───────────────────────────────────────
    asset_parts = []
    for t in tools:
        schema = t.get("inputSchema", {}) or {}
        props  = schema.get("properties", {}) or {}
        params_str = ", ".join(
            f"{k}:{v.get('type','?') if isinstance(v,dict) else '?'}"
            for k, v in props.items()
        )
        asset_parts.append(
            f"TOOL {t['name']}({params_str}): {t.get('description','')[:120]}"
        )
    for p in prompts:
        args = [a.get("name", "") for a in (p.get("arguments") or [])]
        asset_parts.append(
            f"PROMPT {p['name']}({', '.join(args)}): {p.get('description','')[:120]}"
        )
    for r in resources:
        uri = r.get("uri") or r.get("uriTemplate") or ""
        asset_parts.append(
            f"RESOURCE {r.get('name', uri[:40])}: {r.get('description','')[:80]}"
        )

    prompt = _INTEL_PROMPT.format(
        mcp_name      = mcp_name,
        tool_count    = len(tools),
        prompt_count  = len(prompts),
        resource_count= len(resources),
        scan_summary  = scan_summary,
        asset_schemas = "\n".join(asset_parts),
        max_stories   = max_stories,
    )
    system = _INTEL_SYSTEM.format(max_stories=max_stories)

    client = LLMClient(
        provider       = llm_provider,
        api_key        = api_key,
        model          = llm_model,
        max_concurrent = 1,
    )
    result  = await client.generate(prompt, system_prompt=system, json_mode=True)
    content = result["content"]

    try:
        briefing = json.loads(client.extract_json(content))
    except Exception as e:
        logger.error(f"Layer 2 JSON parse failed: {e} — raw: {content[:400]!r}")
        raise

    briefing["llm_cost_usd"] = result.get("cost_usd", 0)
    briefing["duration_ms"]  = result.get("duration_ms", 0)

    logger.info(
        f"Mission briefing ready: domain='{briefing.get('mcp_domain')}' "
        f"risk={briefing.get('risk_surface')} "
        f"targets={len(briefing.get('prioritized_targets', []))} "
        f"scenarios={len(briefing.get('scenario_assignments', []))}"
    )
    return briefing


# ── Public entry point ─────────────────────────────────────────────────────────

async def run_prescan(
    mcp_name:      str,
    mcp_server_id: int,
    tools:         List[Dict],
    prompts:       List[Dict],
    resources:     List[Dict],
    max_stories:   int,
    llm_provider:  str,
    llm_model:     str,
    api_key:       str,
) -> Dict:
    """
    Full pre-scan pipeline: cache lookup → Layer 1 → Layer 2 → cache write.
    Returns the mission briefing dict. briefing['cache_hit'] is True on a hit.
    """
    import db

    tools_hash = compute_schemas_hash(tools, prompts, resources)

    # Cache lookup
    cached = await db.get_prescan(mcp_server_id, tools_hash)
    if cached:
        logger.info(
            f"Prescan cache HIT for '{mcp_name}' "
            f"mcp_server_id={mcp_server_id} hash={tools_hash}"
        )
        cached["cache_hit"] = True
        return cached

    logger.info(
        f"Prescan cache MISS for '{mcp_name}' — running full scan "
        f"mcp_server_id={mcp_server_id} hash={tools_hash}"
    )

    # Layer 1
    scan = layer1_scan(tools, prompts, resources)

    # Layer 2
    briefing = await layer2_intel(
        mcp_name      = mcp_name,
        scan          = scan,
        tools         = tools,
        prompts       = prompts,
        resources     = resources,
        max_stories   = max_stories,
        llm_provider  = llm_provider,
        llm_model     = llm_model,
        api_key       = api_key,
    )

    # Attach Layer 1 raw data for UI display
    briefing["layer1_scan"]  = scan
    briefing["tools_hash"]   = tools_hash
    briefing["cache_hit"]    = False

    # Persist to cache
    await db.save_prescan(mcp_server_id, tools_hash, briefing)

    return briefing
