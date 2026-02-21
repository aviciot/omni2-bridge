MCP PT Automation — Claude-Oriented Design
Goal

Build an automated MCP penetration-testing system where:

LLM analyzes MCP metadata

LLM selects predefined test categories + test functions

LLM generates a structured test plan JSON

LLM can Suggest future improvements (free-form, advisory) - as side job for continous imrprovment....(we can store in dedciated table)
Python executor runs tests deterministically

Results stored in DB

Optional LLM summary of findings

LLM NEVER executes tests.
LLM NEVER decides PASS/FAIL.

Architecture
MCP Metadata
    ↓
LLM (Claude / Gemini)
    ↓
Test Plan JSON
    ↓
Python Executor
    ↓
Results DB
    ↓
(Optional) LLM Summary
Predefined Categories (Hardcoded in System)

Each category maps to real Python test functions.

Categories

protocol_robustness

tool_schema_abuse

tool_boundary

auth_validation

resource_exhaustion

data_leakage

These are ENUMs.

LLM must choose from these only.

Predefined Test Functions

Each category exposes concrete tests:

protocol_robustness

invalid_json

missing_fields

oversized_frame

partial_stream

tool_schema_abuse

unknown_param

wrong_type

missing_required

oversized_param

tool_boundary

db_select_star

db_no_limit

file_traversal

internal_http

auth_validation

no_token

expired_token

forbidden_tool

resource_exhaustion

parallel_connections

slow_client

hanging_tool

data_leakage

presidio_scan

trufflehog_scan

LLM cannot invent tests.

Only select + parametrize.

LLM PROMPT (SYSTEM)

Give Claude this:

You are an MCP penetration-testing planner.

Your job:

Analyze MCP metadata (tools, schemas, auth, resources).

Select appropriate test categories.

Select predefined tests per category.

Fill parameters per tool.

Output STRICT JSON matching provided schema.

Rules:

Use only provided categories and test names.

Do not invent new tests.

Do not evaluate results.

Do not write explanations.

Produce JSON only.

Additionally:

Add optional "internal_notes" suggesting future test enrichment.

Your goal is to maximize MCP security coverage.

Test Plan JSON Template (LLM OUTPUT)
{
  "mcp_id": "string",

  "selected_categories": [
    "tool_schema_abuse",
    "tool_boundary",
    "protocol_robustness"
  ],

  "tests": [
    {
      "category": "tool_schema_abuse",
      "test": "unknown_param",
      "tool": "sql_query",
      "params": {
        "query": "select 1",
        "evil": "hack"
      }
    },

    {
      "category": "tool_boundary",
      "test": "db_select_star",
      "tool": "sql_query",
      "params": {
        "query": "SELECT * FROM users"
      }
    },

    {
      "category": "protocol_robustness",
      "test": "invalid_json"
    }
  ],

  "internal_notes": [
    "Consider adding row-count heuristic for sql_query",
    "File tools may require symlink escape testing"
  ]
}
Python Executor Responsibilities

Input: test_plan.json

For each test:

Call corresponding Python function

Capture:

request

response

latency

Run Presidio + TruffleHog on response

Compute PASS / FAIL (deterministic)

Store in DB:

{
  "test_id": "...",
  "category": "...",
  "status": "FAIL",
  "severity": "HIGH",
  "evidence": "...",
  "timestamp": "..."
}
Result Summary

Stored in DB:

total_tests

critical

high

medium

low

Optional:

Feed failures back to LLM for human-readable summary + recommendations.

Final Outcome

You get:

✅ LLM-generated PT plans
✅ deterministic execution
✅ reproducible results
✅ stored evidence
✅ optional LLM reporting

This becomes:

👉 CI-style automated MCP penetration testin