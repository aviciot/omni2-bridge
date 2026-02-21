"""LLM Test Planner."""

import hashlib
import json
from typing import Dict, List, Tuple
from llm_client import get_llm_client
from logger import logger


# ── Cache helpers ──────────────────────────────────────────────────────────────

def compute_cache_key(mcp_name: str, preset: str, tools: list) -> Tuple[str, str]:
    """Return (cache_key, tools_hash) for test-plan caching.

    cache_key  – full SHA-256 of (mcp_name:preset:tools_hash), used as PK in DB
    tools_hash – short 16-char hex of the sorted tool-name list (for readability)
    """
    tool_names = sorted(t.get("name", "") for t in tools)
    tools_hash = hashlib.sha256(json.dumps(tool_names).encode()).hexdigest()[:16]
    raw = f"{mcp_name}:{preset}:{tools_hash}"
    cache_key = hashlib.sha256(raw.encode()).hexdigest()
    return cache_key, tools_hash


# ── Template (deterministic) plan generator ───────────────────────────────────

def generate_template_plan(mcp_metadata: dict, categories: list) -> dict:
    """Generate a deterministic test plan without calling an LLM.

    Runs every registered test in the selected categories against every
    discovered tool / prompt / resource as appropriate.
    TEST_TARGET_TYPE drives which target the "tool" field receives:
      "tool"     → iterate over discovered tools (default)
      "prompt"   → iterate over discovered prompts (tool = prompt name)
      "resource" → iterate over discovered resources (tool = resource URI)
      "once"     → append a single entry with tool="" (no specific target)
    No security-profile analysis is performed.
    """
    from test_registry import TEST_REGISTRY, TEST_TARGET_TYPE  # local import to avoid circular

    tools     = mcp_metadata.get("tools", [])
    prompts   = mcp_metadata.get("prompts", [])
    resources = mcp_metadata.get("resources", [])
    tests = []

    for cat in categories:
        for test_name in TEST_REGISTRY.get(cat, {}):
            target_type = TEST_TARGET_TYPE.get(test_name, "tool")

            if target_type == "tool":
                for tool in tools:
                    tests.append({
                        "category": cat,
                        "test": test_name,
                        "tool": tool.get("name", ""),
                        "params": {},
                    })

            elif target_type == "prompt":
                if not prompts:
                    logger.debug(f"Template plan: {cat}.{test_name} skipped — no prompts discovered")
                    continue
                for p in prompts:
                    tests.append({
                        "category": cat,
                        "test": test_name,
                        "tool": p.get("name", ""),   # "tool" field = prompt name
                        "params": {},
                    })

            elif target_type == "resource":
                if not resources:
                    logger.debug(f"Template plan: {cat}.{test_name} skipped — no resources discovered")
                    continue
                for r in resources:
                    tests.append({
                        "category": cat,
                        "test": test_name,
                        "tool": r.get("uri", r.get("name", "")),  # "tool" = resource URI
                        "params": {},
                    })

            elif target_type == "once":
                # Runs once regardless of how many prompts/resources exist
                tests.append({
                    "category": cat,
                    "test": test_name,
                    "tool": "",
                    "params": {},
                })

    tool_count     = len(tools)
    prompt_count   = len(prompts)
    resource_count = len(resources)
    test_count     = len(tests)
    logger.info(
        f"Template plan: {tool_count} tools, {prompt_count} prompts, {resource_count} resources "
        f"→ {test_count} test combinations across {len(categories)} categories"
    )

    return {
        "tests": tests,
        "security_profile": {
            "risk_score": None,
            "mcp_summary": (
                f"Deterministic run — no LLM analysis. "
                f"{tool_count} tool(s), {prompt_count} prompt(s), {resource_count} resource(s) "
                f"→ {test_count} test combinations."
            ),
            "weaknesses": [],
            "attack_vectors": [],
            "data_sensitivity": {},
            "suggested_additional_tests": [],
            "tool_summary": {
                "total": tool_count,
                "high_risk": 0,
                "medium_risk": 0,
                "low_risk": tool_count,
                "high_risk_tools": [],
            },
        },
        "recommendations": [],
        "selected_categories": categories,
    }


SYSTEM_PROMPT = """You are an MCP security analyst and penetration testing planner.

Your job:
1. Analyze MCP security profile (capabilities, risks, data sensitivity)
2. Select appropriate test categories
3. Select predefined tests per category
4. Provide recommendations for additional testing
5. Output STRICT JSON matching provided schema

Available Categories:
- protocol_robustness: Protocol-level robustness — malformed frames for tools, prompts, and resources
- tool_schema_abuse: Schema validation and parameter abuse for tools
- tool_boundary: Boundary violations (path traversal, injection, SSRF) for tools, prompts, and resources
- auth_validation: Authentication checks for tools, prompts, and resources
- resource_exhaustion: DoS / resource exhaustion for tools
- data_leakage: Sensitive data exposure scanning for tools and resources
- ai_security: AI-specific attack surfaces (prompt injection via tool parameters)

Available Tests per Category:
protocol_robustness: invalid_json, missing_fields, oversized_frame, partial_stream, prompt_malformed_args, resource_invalid_uri
tool_schema_abuse: unknown_param, wrong_type, missing_required, oversized_param
tool_boundary: db_select_star, db_no_limit, file_traversal, internal_http, command_injection, sql_injection, resource_path_traversal, prompt_injection_args, prompt_missing_args
auth_validation: no_token, expired_token, forbidden_tool, prompt_no_auth, resource_no_auth, resource_list_no_auth
resource_exhaustion: parallel_connections, slow_client, hanging_tool
data_leakage: presidio_scan, trufflehog_scan, information_disclosure, resource_sensitive_content, resource_list_disclosure
ai_security: prompt_injection

Prompt / resource test rules:
- prompt_malformed_args, prompt_injection_args, prompt_missing_args, prompt_no_auth:
    Use ONLY when prompt_count > 0. Set "tool" to a prompt NAME from the discovered prompts list.
- resource_path_traversal, resource_no_auth, resource_sensitive_content, resource_invalid_uri:
    Use ONLY when resource_count > 0. Set "tool" to a resource URI from the discovered resources list.
- resource_list_no_auth, resource_list_disclosure:
    Runs once regardless of resource count. Set "tool" to "".

Rules:
- Use ONLY the categories and test names listed above
- Do NOT invent new categories or test names
- Produce JSON ONLY — no markdown, no commentary outside the JSON
- Maximize security coverage based on MCP tools, prompts, and resources
- Keep each "params" object small (under 5 keys)

Output JSON Schema:
{
  "mcp_id": "string",
  "security_profile": {
    "overview": "2-3 sentence description of what this MCP does",
    "tool_summary": {
      "total": 10,
      "high_risk": 2,
      "medium_risk": 5,
      "low_risk": 3,
      "high_risk_tools": ["tool_name: reason"]
    },
    "risk_surface": ["Key security concern 1", "Key security concern 2"],
    "data_sensitivity": {
      "handles_pii": true,
      "handles_credentials": false,
      "handles_financial": false,
      "evidence": ["tool_name returns email/phone"]
    },
    "attack_vectors": [
      {
        "vector": "SQL Injection",
        "severity": "critical",
        "affected_tools": ["tool1"],
        "description": "Brief explanation"
      }
    ],
    "recommended_focus": ["category1", "category2"],
    "risk_score": 7,
    "weaknesses": ["Weakness 1", "Weakness 2"],
    "mcp_summary": "One paragraph plain-English summary of what this MCP does and its security posture",
    "suggested_additional_tests": [
      {
        "category": "tool_boundary",
        "test": "sql_injection",
        "reason": "Tool accepts raw SQL input"
      }
    ]
  },
  "selected_categories": ["category1", "category2"],
  "tests": [
    {
      "category": "tool_schema_abuse",
      "test": "unknown_param",
      "tool": "sql_query",
      "params": {"query": "SELECT 1"}
    }
  ],
  "recommendations": [
    {
      "category": "data_leakage",
      "reason": "MCP returns user data, should scan for PII",
      "priority": "high",
      "estimated_tests": 2
    }
  ]
}"""


# Maps category -> valid test names (kept in sync with TEST_REGISTRY)
VALID_TESTS = {
    "protocol_robustness": {
        "invalid_json", "missing_fields", "oversized_frame", "partial_stream",
        "prompt_malformed_args", "resource_invalid_uri",
    },
    "tool_schema_abuse": {"unknown_param", "wrong_type", "missing_required", "oversized_param"},
    "tool_boundary": {
        "db_select_star", "db_no_limit", "file_traversal", "internal_http",
        "command_injection", "sql_injection",
        "resource_path_traversal", "prompt_injection_args", "prompt_missing_args",
    },
    "auth_validation": {
        "no_token", "expired_token", "forbidden_tool",
        "prompt_no_auth", "resource_no_auth", "resource_list_no_auth",
    },
    "resource_exhaustion": {"parallel_connections", "slow_client", "hanging_tool"},
    "data_leakage": {
        "presidio_scan", "trufflehog_scan", "information_disclosure",
        "resource_sensitive_content", "resource_list_disclosure",
    },
    "ai_security": {"prompt_injection"},
}


class PTPlanner:
    """LLM-based test planner."""

    def __init__(self, llm_provider: str = None, llm_model: str = None):
        self.llm = get_llm_client(provider=llm_provider, model=llm_model)

    async def generate_test_plan(self, mcp_metadata: Dict, preset: str,
                                 categories: List[str] = None) -> Dict:
        """Generate test plan from MCP metadata, with up to 2 retries on parse failure."""

        prompt = self._build_prompt(mcp_metadata, preset, categories)
        logger.info(f"Generating test plan for {mcp_metadata.get('name')} preset={preset}")

        last_error = None
        for attempt in range(3):
            response = await self.llm.generate(prompt, SYSTEM_PROMPT, json_mode=True)
            try:
                # json_mode=True means Gemini/Groq guarantee valid JSON — parse directly.
                # For Anthropic (no native JSON mode) extract_json is the fallback.
                content = response["content"]
                try:
                    test_plan = json.loads(content)
                except json.JSONDecodeError:
                    json_str = self.llm.extract_json(content)
                    test_plan = json.loads(json_str)
                self._validate_test_plan(test_plan)
                logger.info(f"Test plan OK: {len(test_plan.get('tests', []))} tests "
                            f"(attempt {attempt + 1})")
                return {
                    "test_plan": test_plan,
                    "llm_cost": response["cost_usd"],
                    "llm_tokens": response["input_tokens"] + response["output_tokens"]
                }
            except Exception as e:
                last_error = e
                raw_preview = content[:800] if isinstance(content, str) else repr(content)[:800]
                logger.warning(
                    f"Attempt {attempt + 1} failed to parse test plan: {e}\n"
                    f"  Raw response (first 800 chars): {raw_preview!r}"
                )

        logger.error(f"All attempts failed: {last_error}")
        logger.warning(
            f"LLM plan generation failed after 3 attempts for {mcp_metadata.get('name')} — "
            f"falling back to template (deterministic) plan. Error: {last_error}"
        )
        fallback_categories = categories or list(VALID_TESTS.keys())
        fallback_plan = generate_template_plan(mcp_metadata, fallback_categories)
        return {
            "test_plan": fallback_plan,
            "llm_cost": 0.0,
            "llm_tokens": 0,
        }

    def _build_prompt(self, mcp_metadata: Dict, preset: str, categories: List[str]) -> str:
        """Build LLM prompt."""

        tools = mcp_metadata.get("tools", [])
        tool_list = "\n".join(
            [f"- {t.get('name')}: {t.get('description', '')}" for t in tools[:20]]
        )

        if categories:
            category_instruction = f"Focus on these categories ONLY: {', '.join(categories)}"
        else:
            category_instruction = f"Use preset: {preset} (cover all relevant categories)"

        prompts = mcp_metadata.get("prompts", [])
        resources = mcp_metadata.get("resources", [])

        prompt_list = "\n".join(
            [f"- {p.get('name')}: {p.get('description', '')} "
             f"(args: {[a.get('name') for a in p.get('arguments', [])]})"
             for p in prompts[:10]]
        ) or "(none)"

        resource_list = "\n".join(
            [f"- {r.get('name', r.get('uri', '?'))}: {r.get('description', '')} [uri: {r.get('uri', '')}]"
             for r in resources[:10]]
        ) or "(none)"

        prompt = f"""Analyze this MCP and generate a security profile + penetration test plan.

MCP Name: {mcp_metadata.get('name')}
MCP ID: {mcp_metadata.get('id')}
Protocol: {mcp_metadata.get('protocol')}
URL: {mcp_metadata.get('url')}
Total Tools: {len(tools)}
Total Prompts: {len(prompts)}
Total Resources: {len(resources)}

AVAILABLE TOOLS (use ONLY these exact names in the "tool" field for tool-based tests):
{tool_list}
{f'... and {len(tools) - 20} more tools' if len(tools) > 20 else ''}

AVAILABLE PROMPTS (for prompt_security tests, use the prompt NAME in the "tool" field):
{prompt_list}

AVAILABLE RESOURCES (for resource_security tests, use the resource URI in the "tool" field):
{resource_list}

{category_instruction}

TASK 1 — Security Profile
- overview: What does this MCP do?
- mcp_summary: Plain-English paragraph about this MCP and its security posture
- weaknesses: List concrete weaknesses you can infer from the tool names/descriptions
- tool_summary: Categorize tools by risk level
- attack_vectors: Which attack vectors are relevant (SQL injection, path traversal, SSRF, etc.)
- data_sensitivity: Does it handle PII, credentials, financial data?
- risk_score: 1-10
- suggested_additional_tests: Tests NOT in your selected list that you believe would be valuable

TASK 2 — Test Plan
- Select tests from the available categories and test names ONLY
- For each test specify a REAL tool name from the list above
- Parametrize tests appropriately per tool

TASK 3 — Recommendations
- Suggest categories for future testing with priority and reason

Output ONLY a single valid JSON object. No markdown fences, no comments, no trailing commas.
"""
        return prompt

    def _validate_test_plan(self, plan: Dict):
        """Validate test plan; remove invalid tests rather than raising."""
        if "tests" not in plan:
            raise ValueError("Missing 'tests' field")

        valid_tests = []
        skipped = 0
        for test in plan["tests"]:
            category = test.get("category")
            test_name = test.get("test")

            if category not in VALID_TESTS:
                logger.warning(f"Skipping unknown category in LLM output: {category}")
                skipped += 1
                continue

            if test_name not in VALID_TESTS[category]:
                logger.warning(f"Skipping unknown test in LLM output: {category}.{test_name}")
                skipped += 1
                continue

            valid_tests.append(test)

        if skipped:
            logger.warning(f"Removed {skipped} invalid tests from LLM plan")

        plan["tests"] = valid_tests

        if not valid_tests:
            raise ValueError("No valid tests remain after validation")
