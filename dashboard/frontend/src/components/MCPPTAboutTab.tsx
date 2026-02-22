"use client";

import { useState } from "react";

interface Props {
  testCatalog: Record<string, any>;
  presets: any[];
  categories: any[];
}

// ── Small helpers ────────────────────────────────────────────────────────────

function SectionHeader({ emoji, title, sub }: { emoji: string; title: string; sub?: string }) {
  return (
    <div className="mb-4">
      <h3 className="text-xl font-black text-gray-900 flex items-center gap-2">
        <span>{emoji}</span> {title}
      </h3>
      {sub && <p className="text-sm text-gray-500 mt-0.5">{sub}</p>}
    </div>
  );
}

function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`bg-white rounded-2xl border-2 border-gray-100 p-6 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

// ── Tab navigation ───────────────────────────────────────────────────────────

const TABS = [
  { id: "overview",      label: "Overview",      icon: "🗺️" },
  { id: "regular",       label: "Regular Tests",  icon: "⚙️" },
  { id: "red_team",      label: "AI Red Team",    icon: "🤖" },
  { id: "configuration", label: "Configuration",  icon: "🔧" },
  { id: "catalog",       label: "Test Catalog",   icon: "📋" },
];

// ── Overview tab ─────────────────────────────────────────────────────────────

const STAGES = [
  {
    n: 1, icon: "🔌", label: "Initialization",
    color: "border-gray-300 bg-gray-50", dot: "bg-gray-400",
    desc: "Connect to the MCP server, verify it's healthy, read the run configuration.",
  },
  {
    n: 2, icon: "🔍", label: "Discovery",
    color: "border-blue-200 bg-blue-50", dot: "bg-blue-400",
    desc: "Enumerate all tools, prompt templates, and resources. Capture full JSON schemas — names, descriptions, every input parameter and type.",
  },
  {
    n: 3, icon: "🧠", label: "LLM Analysis",
    color: "border-sky-200 bg-sky-50", dot: "bg-sky-500",
    desc: "ONE LLM call reads all schemas and selected categories → returns a tailored JSON test plan. Skipped in Template mode. Result is cached for future runs.",
  },
  {
    n: 4, icon: "⚙️", label: "Test Execution",
    color: "border-orange-200 bg-orange-50", dot: "bg-orange-400",
    desc: "Python executor runs deterministic test functions from the catalog. The LLM never runs tests — it only planned which ones to run.",
  },
  {
    n: 5, icon: "🎯", label: "Mission Briefing",
    color: "border-purple-200 bg-purple-50", dot: "bg-purple-400",
    desc: "Pre-scan intelligence phase. A risk classifier analyzes tool schemas, then one LLM call produces a structured mission briefing — attack domain, risk rating, priority targets, attack chains, and scenario assignments. Cached per MCP and reused until schemas change.",
    optional: true,
  },
  {
    n: 6, icon: "🤖", label: "AI Red Team",
    color: "border-red-200 bg-red-50", dot: "bg-red-500",
    desc: "Agentic attacker LLM makes real MCP tool calls autonomously, adapting to each response. The mission briefing is injected directly into the attacker's system prompt. A separate Judge LLM evaluates findings for each story.",
    highlight: true,
  },
];

function OverviewTab() {
  return (
    <div className="space-y-6">
      <Card>
        <SectionHeader emoji="🗺️" title="The 6 Stages of a PT Run" sub="Stages 1–4 always run. Stages 5–6 are optional and require AI Red Team to be enabled." />
        <div className="space-y-3">
          {STAGES.map((s, i) => (
            <div key={s.n} className="flex gap-4">
              <div className="flex flex-col items-center w-8 flex-shrink-0">
                <div className={`w-8 h-8 rounded-full ${s.dot} text-white text-xs font-black flex items-center justify-center`}>{s.n}</div>
                {i < STAGES.length - 1 && <div className="w-0.5 flex-1 bg-gray-200 my-1" />}
              </div>
              <div className={`flex-1 rounded-xl border-2 ${s.color} p-4 ${(s as any).highlight ? "ring-2 ring-red-300" : (s as any).optional ? "ring-2 ring-purple-200" : ""}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">{s.icon}</span>
                  <span className="font-bold text-sm text-gray-800">{s.label}</span>
                  {(s as any).optional && !((s as any).highlight) && (
                    <span className="ml-auto text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full font-medium">optional • cached</span>
                  )}
                  {(s as any).highlight && (
                    <span className="ml-auto text-xs px-2 py-0.5 bg-red-100 text-red-700 rounded-full font-medium">optional • live</span>
                  )}
                </div>
                <p className="text-xs leading-relaxed text-gray-600">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Quick comparison cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="border-orange-100">
          <div className="text-sm font-bold text-orange-700 mb-3 flex items-center gap-2">⚙️ Stages 1–4 — Regular Testing (always runs)</div>
          <ul className="text-xs text-gray-600 space-y-2">
            {[
              "Deterministic, reproducible, fast",
              "Covers tools, prompts, and resources — all MCP capabilities",
              "LLM picks which tests + inputs — Python runs them",
              "Test plan is cached — 0 LLM calls on repeat runs",
              "Ideal for CI/CD regression checks",
            ].map((t, i) => (
              <li key={i} className="flex gap-2"><span className="text-green-500 flex-shrink-0">✓</span>{t}</li>
            ))}
          </ul>
        </Card>
        <Card className="border-purple-100">
          <div className="text-sm font-bold text-purple-700 mb-3 flex items-center gap-2">🎯🤖 Stages 5–6 — Mission Briefing + AI Red Team (optional)</div>
          <ul className="text-xs text-gray-600 space-y-2">
            {[
              "Mission Briefing pre-scans attack surface — cached per MCP",
              "Attacker receives structured intel: targets, chains, scenarios",
              "Non-deterministic — creative, adaptive tool call chains",
              "Discovers semantic vulnerabilities predefined tests miss",
              "Separate Judge LLM evaluates findings with was_planned tracking",
            ].map((t, i) => (
              <li key={i} className="flex gap-2"><span className="text-purple-500 flex-shrink-0">◆</span>{t}</li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}

// ── Regular Tests tab ─────────────────────────────────────────────────────────

function FlowNode({ children, color = "bg-white border-gray-200", className = "" }: {
  children: React.ReactNode; color?: string; className?: string;
}) {
  return (
    <div className={`rounded-xl border-2 px-4 py-3 text-center ${color} ${className}`}>
      {children}
    </div>
  );
}

function DownArrow({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center my-1 gap-0.5">
      {label && <span className="text-xs text-gray-400">{label}</span>}
      <div className="text-gray-400 text-lg leading-none">▼</div>
    </div>
  );
}

function RegularTestsTab() {
  return (
    <div className="space-y-6">
      {/* Flow diagram */}
      <Card>
        <SectionHeader emoji="🔀" title="Two Paths to Test Execution" sub="The path a run takes through stages 3–4 depends on plan_source." />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* LLM path */}
          <div>
            <div className="text-center mb-4">
              <span className="inline-block px-3 py-1 bg-sky-100 text-sky-800 text-xs font-bold rounded-full border border-sky-200">
                🧠 LLM Path — plan_source = llm
              </span>
            </div>
            <div className="flex flex-col items-stretch">
              <FlowNode color="bg-blue-50 border-blue-300">
                <div className="text-xs font-bold text-blue-800">🔍 Stage 2: Discovery</div>
                <div className="text-xs text-blue-600 mt-0.5">Tool schemas collected</div>
              </FlowNode>
              <DownArrow label="schemas" />
              <div className="relative">
                <FlowNode color="bg-sky-50 border-sky-400">
                  <div className="text-xs font-bold text-sky-800">🧠 Stage 3: LLM Analysis</div>
                  <div className="text-xs text-sky-600 mt-0.5">1 API call → JSON test plan</div>
                </FlowNode>
                <div className="mt-1 text-center">
                  <span className="inline-block bg-purple-50 border border-purple-300 rounded-lg px-3 py-1 text-xs text-purple-700">
                    📦 Cached by MCP + preset + SHA256(schemas)
                  </span>
                </div>
              </div>
              <DownArrow label="test plan" />
              <FlowNode color="bg-orange-50 border-orange-400">
                <div className="text-xs font-bold text-orange-800">⚙️ Stage 4: Execution</div>
                <div className="text-xs text-orange-600 mt-0.5">Python functions run deterministically</div>
              </FlowNode>
              <DownArrow label="results" />
              <FlowNode color="bg-green-50 border-green-300">
                <div className="text-xs font-bold text-green-800">📊 Results Saved</div>
                <div className="text-xs text-green-600 mt-0.5">pass / fail / error per test</div>
              </FlowNode>
            </div>
          </div>

          {/* Template path */}
          <div>
            <div className="text-center mb-4">
              <span className="inline-block px-3 py-1 bg-gray-100 text-gray-700 text-xs font-bold rounded-full border border-gray-300">
                📝 Template Path — plan_source = template
              </span>
            </div>
            <div className="flex flex-col items-stretch">
              <FlowNode color="bg-blue-50 border-blue-300">
                <div className="text-xs font-bold text-blue-800">🔍 Stage 2: Discovery</div>
                <div className="text-xs text-blue-600 mt-0.5">Tool schemas collected</div>
              </FlowNode>
              <DownArrow />
              <div className="rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 px-4 py-3 text-center opacity-60">
                <div className="text-xs font-bold text-gray-500">⬜ Stage 3: SKIPPED</div>
                <div className="text-xs text-gray-400 mt-0.5">No LLM call — static catalog used</div>
              </div>
              <DownArrow />
              <FlowNode color="bg-orange-50 border-orange-400">
                <div className="text-xs font-bold text-orange-800">⚙️ Stage 4: Execution</div>
                <div className="text-xs text-orange-600 mt-0.5">All enabled catalog tests run as-is</div>
              </FlowNode>
              <DownArrow label="results" />
              <FlowNode color="bg-green-50 border-green-300">
                <div className="text-xs font-bold text-green-800">📊 Results Saved</div>
                <div className="text-xs text-green-600 mt-0.5">pass / fail / error per test</div>
              </FlowNode>
            </div>
            <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 leading-relaxed">
              <strong>When to use Template:</strong> No LLM cost, fully reproducible. Useful for quick checks or when you want the exact same tests every time without LLM variability.
            </div>
          </div>
        </div>
      </Card>

      {/* Stage 3 deep-dive */}
      <Card className="border-sky-100">
        <SectionHeader emoji="🧠" title="Stage 3 — LLM Analysis (Single Call)" sub="The LLM reads schemas and writes a JSON plan. It never calls MCP tools in this stage." />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <p className="text-sm text-gray-600 mb-4 leading-relaxed">
              The LLM receives all discovered tool schemas — names, descriptions, every input parameter and type.
              In a <strong>single API call</strong> it:
            </p>
            <ol className="space-y-2">
              {[
                "Identifies high-risk tools (exec, file access, auth, data reads)",
                "Maps each selected category to the most relevant tools",
                "Chooses specific test functions from the catalog per tool",
                "Generates tailored attack inputs (e.g. path traversal strings for a 'read_file' tool)",
                "Returns a JSON plan: tests[], security_profile{}, recommendations[]",
              ].map((item, i) => (
                <li key={i} className="flex gap-2 text-sm">
                  <span className="w-5 h-5 rounded-full bg-sky-100 text-sky-700 text-xs font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{i + 1}</span>
                  <span className="text-gray-600">{item}</span>
                </li>
              ))}
            </ol>
          </div>
          <div className="space-y-3">
            <div className="rounded-xl bg-gray-900 p-3 text-xs font-mono text-gray-300 space-y-0.5">
              <div className="text-gray-500 mb-1">// What the LLM returns (simplified)</div>
              <div>{"{"}</div>
              <div className="pl-4"><span className="text-yellow-300">"selected_categories"</span>: [<span className="text-green-300">"auth_validation"</span>],</div>
              <div className="pl-4"><span className="text-yellow-300">"tests"</span>: [{"{"}</div>
              <div className="pl-8"><span className="text-yellow-300">"category"</span>: <span className="text-green-300">"auth_validation"</span>,</div>
              <div className="pl-8"><span className="text-yellow-300">"test"</span>: <span className="text-green-300">"no_token"</span>,</div>
              <div className="pl-8"><span className="text-yellow-300">"tool"</span>: <span className="text-green-300">"restart_container"</span>,</div>
              <div className="pl-8"><span className="text-yellow-300">"params"</span>: {"{"}<span className="text-green-300">"container_name"</span>: <span className="text-green-300">"prod-db"</span>{"}"}</div>
              <div className="pl-4">{"}"}],</div>
              <div className="pl-4"><span className="text-yellow-300">"security_profile"</span>: {"{ … }"}</div>
              <div>{"}"}</div>
            </div>
            <div className="text-xs text-gray-600 p-3 bg-purple-50 border border-purple-200 rounded-xl leading-relaxed">
              <strong className="text-purple-700">Caching:</strong> The plan is stored keyed by{" "}
              <code className="bg-white px-1 mx-0.5 rounded border border-purple-200">MCP name + preset + SHA256(tool schemas)</code>.
              Re-running the same MCP with the same preset reuses the cached plan instantly — 0 LLM calls.
            </div>
          </div>
        </div>
      </Card>

      {/* Prompt & Resource Coverage */}
      <Card className="border-teal-100">
        <SectionHeader
          emoji="📝"
          title="Prompt & Resource Coverage"
          sub="Prompt and resource tests live inside standard categories — no extra category to configure."
        />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Which categories were extended */}
          <div className="space-y-2">
            <div className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">Extended categories</div>
            {[
              {
                cat: "🔑 auth_validation", color: "border-sky-200 bg-sky-50",
                tests: ["prompt_no_auth", "resource_no_auth", "resource_list_no_auth"],
              },
              {
                cat: "🚧 tool_boundary", color: "border-orange-200 bg-orange-50",
                tests: ["resource_path_traversal", "prompt_injection_args", "prompt_missing_args"],
              },
              {
                cat: "💧 data_leakage", color: "border-purple-200 bg-purple-50",
                tests: ["resource_sensitive_content", "resource_list_disclosure"],
              },
              {
                cat: "🔌 protocol_robustness", color: "border-gray-200 bg-gray-50",
                tests: ["prompt_malformed_args", "resource_invalid_uri"],
              },
            ].map(({ cat, color, tests }) => (
              <div key={cat} className={`rounded-lg border-2 ${color} p-3`}>
                <div className="text-xs font-bold text-gray-700 mb-2">{cat}</div>
                <div className="flex flex-wrap gap-1">
                  {tests.map(t => (
                    <code key={t} className="text-xs bg-white px-1.5 py-0.5 rounded border border-gray-200 text-gray-600">{t}</code>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* How the executor knows what to call */}
          <div>
            <div className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3">How the executor knows what to call</div>
            <p className="text-xs text-gray-600 mb-3 leading-relaxed">
              Each test name is registered in <code className="bg-gray-100 px-1 rounded">TEST_TARGET_TYPE</code>.
              The template plan generator reads this to decide what goes in the <code className="bg-gray-100 px-1 rounded">"tool"</code> field —
              tests absent from the map default to <code className="bg-gray-100 px-1 rounded">"tool"</code>.
            </p>
            <div className="rounded-xl bg-gray-900 p-3 text-xs font-mono text-gray-300 space-y-1 mb-3">
              <div className="text-gray-500 mb-1">// "tool" field carries different things per test</div>
              <div><span className="text-yellow-300">"test"</span>: <span className="text-green-300">"no_token"</span>            → <span className="text-green-300">tool name</span></div>
              <div><span className="text-yellow-300">"test"</span>: <span className="text-teal-300">"prompt_no_auth"</span>      → <span className="text-teal-300">prompt name</span></div>
              <div><span className="text-yellow-300">"test"</span>: <span className="text-indigo-300">"resource_no_auth"</span>    → <span className="text-indigo-300">resource URI</span></div>
              <div><span className="text-yellow-300">"test"</span>: <span className="text-orange-300">"resource_list_no_auth"</span> → <span className="text-orange-300">""</span> (runs once)</div>
            </div>
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-800 leading-relaxed">
              Prompt and resource tests are <strong>silently skipped</strong> if the MCP exposes no prompts or no resources — no configuration required.
            </div>
          </div>
        </div>
      </Card>

      {/* Stage 4 deep-dive */}
      <Card className="border-orange-100">
        <SectionHeader emoji="⚙️" title="Stage 4 — Test Execution (Deterministic)" sub="Python functions, not the LLM, actually call the MCP tools." />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-3 text-sm text-gray-700">
            <p>
              <strong>Who calls the tools?</strong><br />
              Python test functions — deterministic code, not an LLM. Examples:{" "}
              <code className="bg-gray-100 px-1 rounded text-xs">test_invalid_json</code>,{" "}
              <code className="bg-gray-100 px-1 rounded text-xs">test_no_token</code>,{" "}
              <code className="bg-gray-100 px-1 rounded text-xs">test_path_traversal</code>.
            </p>
            <p>
              <strong>What does each function do?</strong><br />
              Crafts one specific malformed or malicious request, sends it to the MCP via the real protocol, reads the response,
              and evaluates it against a pass/fail rule. Each function tests exactly one vulnerability pattern.
            </p>
            <p>
              <strong>What did the LLM contribute?</strong><br />
              The LLM (Stage 3) decided <em>which</em> tools to target, <em>which</em> test functions to run on each,
              and <em>what inputs</em> to use. It acts as an intelligent planner, not the executor.
            </p>
          </div>
          <div className="rounded-xl border-2 border-orange-200 bg-orange-50 p-4">
            <div className="text-xs font-bold text-orange-700 mb-3">Per-test execution loop:</div>
            <div className="space-y-2 text-xs">
              {[
                { step: "1", text: "Executor picks next test from plan", bg: "bg-orange-200 text-orange-800" },
                { step: "2", text: "Calls Python fn: test_no_token(tool, params)", bg: "bg-orange-200 text-orange-800" },
                { step: "3", text: "Function sends crafted request → MCP (HTTP/stdio)", bg: "bg-blue-200 text-blue-800" },
                { step: "4", text: "Function reads response, evaluates pass/fail rule", bg: "bg-orange-200 text-orange-800" },
                { step: "5", text: "Result saved: status, evidence, latency_ms", bg: "bg-green-200 text-green-800" },
              ].map(({ step, text, bg }) => (
                <div key={step} className="flex gap-2 items-start">
                  <span className={`w-5 h-5 rounded-full ${bg} text-xs font-bold flex items-center justify-center flex-shrink-0`}>{step}</span>
                  <span className="text-gray-700">{text}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}

// ── AI Red Team tab ───────────────────────────────────────────────────────────

function PipelineFlow() {
  const steps = [
    {
      stage: "5a · Pre-scan",
      icon: "🔍",
      bg: "bg-purple-950 border-purple-500",
      labelColor: "text-purple-300",
      title: "Attack Surface Discovery",
      bullets: ["SHA-256 hash of all tool/prompt/resource schemas", "Cache lookup → skip LLM if hash matches", "Layer 1: deterministic risk classifier (no LLM)", "Layer 2: single LLM call → Mission Briefing JSON"],
    },
    {
      stage: "Cache",
      icon: "📦",
      bg: "bg-indigo-950 border-indigo-400",
      labelColor: "text-indigo-300",
      title: "pt_prescan_cache",
      bullets: ["Stored per MCP in PostgreSQL JSONB", "No TTL — valid until schemas change", "is_stale flag triggers re-scan on next run", "Cache hit = 0 LLM calls, instant briefing"],
    },
    {
      stage: "5b · Attacker",
      icon: "⚔️",
      bg: "bg-red-950 border-red-500",
      labelColor: "text-red-300",
      title: "Mission-Briefed Attacker Agent",
      bullets: ["Mission Briefing injected into system prompt", "Pre-assigned scenarios with target tools + payloads", "budget_per_story = max_iterations ÷ max_stories", "Agentic loop: reason → call_tool() → adapt"],
    },
    {
      stage: "5c · Judge",
      icon: "⚖️",
      bg: "bg-blue-950 border-blue-500",
      labelColor: "text-blue-300",
      title: "Evidence-Based Judge",
      bullets: ["Receives per-story transcript slice (not full log)", "Compares findings to planned scenarios", "Outputs: verdict, severity, was_planned, coverage_pct", "Strict rule: no finding without MCP response evidence"],
    },
    {
      stage: "DB",
      icon: "💾",
      bg: "bg-gray-800 border-gray-500",
      labelColor: "text-gray-300",
      title: "Persisted Results",
      bullets: ["pt_runs.mission_briefing — briefing used for the run", "pt_agent_stories — one row per scenario", "pt_test_results — pass/fail per deterministic test", "mcp_servers.pt_score / pt_status — at-a-glance"],
    },
  ];

  return (
    <div className="overflow-x-auto pb-2">
      <div className="flex items-stretch gap-0 min-w-[700px]">
        {steps.map((s, i) => (
          <div key={s.stage} className="flex items-stretch flex-1">
            <div className={`flex-1 rounded-xl border-2 ${s.bg} p-3`}>
              <div className={`text-xs font-bold uppercase tracking-wider mb-1 ${s.labelColor}`}>{s.stage}</div>
              <div className="text-white text-xs font-semibold mb-2 flex items-center gap-1.5">
                <span>{s.icon}</span>{s.title}
              </div>
              <ul className="space-y-1">
                {s.bullets.map((b, j) => (
                  <li key={j} className="text-gray-300 text-xs flex gap-1.5">
                    <span className="flex-shrink-0 text-gray-500 mt-0.5">›</span>
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
            </div>
            {i < steps.length - 1 && (
              <div className="flex items-center px-1 flex-shrink-0">
                <div className="text-gray-500 text-lg">→</div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function MissionBriefingAnatomy() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* What it contains */}
      <div className="rounded-xl border-2 border-purple-300 bg-purple-950 p-4">
        <div className="text-xs font-bold text-purple-300 uppercase tracking-wider mb-3">🎯 Mission Briefing Contents</div>
        <div className="space-y-2">
          {[
            { field: "domain", color: "text-cyan-300", desc: "What this MCP does (e.g. 'file management system')" },
            { field: "risk_rating", color: "text-red-300", desc: "critical / high / medium / low — overall attack surface severity" },
            { field: "risk_surface", color: "text-yellow-300", desc: "One-sentence summary of the main attack surface" },
            { field: "priority_targets[]", color: "text-orange-300", desc: "Ranked tools with: attack type, target param, concrete payloads, reason" },
            { field: "attack_chains[]", color: "text-green-300", desc: "Multi-step chained attacks (e.g. search_users → delete_user)" },
            { field: "scenario_assignments[]", color: "text-pink-300", desc: "Pre-assigned attack goals — one per story slot, injected into attacker prompt" },
          ].map(({ field, color, desc }) => (
            <div key={field} className="flex gap-2">
              <code className={`text-xs font-mono ${color} flex-shrink-0 mt-0.5`}>{field}</code>
              <span className="text-gray-400 text-xs leading-relaxed">{desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* How it reaches the attacker */}
      <div className="rounded-xl border-2 border-red-800 bg-gray-950 p-4">
        <div className="text-xs font-bold text-red-400 uppercase tracking-wider mb-3">⚔️ Injected into Attacker Prompt</div>
        <div className="font-mono text-xs text-gray-300 space-y-0.5 leading-relaxed">
          <div className="text-purple-400">╔══ MISSION BRIEFING ══════════════╗</div>
          <div><span className="text-yellow-300">DOMAIN</span>: <span className="text-gray-300">File management system</span></div>
          <div><span className="text-yellow-300">RISK</span>: <span className="text-red-400">CRITICAL</span></div>
          <div className="mt-1 text-purple-400">── PRIORITY TARGETS ──</div>
          <div><span className="text-cyan-300">read_file</span> <span className="text-gray-500">path_traversal</span></div>
          <div className="pl-2 text-yellow-200">payload: ../../../etc/passwd</div>
          <div className="mt-1 text-purple-400">── ATTACK CHAINS ──</div>
          <div><span className="text-green-300">list_files</span> <span className="text-gray-500">→</span> <span className="text-green-300">delete_file</span></div>
          <div className="mt-1 text-purple-400">── YOUR SCENARIOS ──</div>
          <div className="text-pink-300">Scenario 1: Extract /etc/passwd via read_file</div>
          <div className="text-pink-300">Scenario 2: Mass delete via chained calls</div>
          <div className="text-purple-400">╚══════════════════════════════════╝</div>
        </div>
        <p className="text-xs text-gray-500 mt-2 italic">
          The attacker starts each run knowing exactly what to attack and how — eliminating exploratory warm-up iterations.
        </p>
      </div>
    </div>
  );
}

function CacheArchitecture() {
  return (
    <div className="space-y-3">
      {/* Flow */}
      <div className="flex flex-col gap-1">
        <div className="rounded-xl border-2 border-blue-200 bg-blue-50 p-3 text-xs text-center font-medium text-blue-800">
          🔍 Discovery completes → schemas collected (tools + prompts + resources)
        </div>
        <DownArrow label="SHA-256(sorted schemas)" />
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl border-2 border-green-300 bg-green-50 p-3">
            <div className="text-xs font-bold text-green-700 mb-2">✅ Cache HIT</div>
            <div className="space-y-1 text-xs text-green-800">
              <div className="bg-green-100 rounded px-2 py-1">hash matches + is_stale = false</div>
              <div className="text-center text-green-600 text-xs">▼ 0 LLM calls</div>
              <div className="bg-green-100 rounded px-2 py-1 font-medium">→ briefing returned instantly</div>
            </div>
          </div>
          <div className="rounded-xl border-2 border-orange-300 bg-orange-50 p-3">
            <div className="text-xs font-bold text-orange-700 mb-2">❌ Cache MISS / STALE</div>
            <div className="space-y-1 text-xs text-orange-800">
              <div className="bg-orange-100 rounded px-2 py-1">no row, hash mismatch, or is_stale</div>
              <div className="text-center text-orange-500 text-xs">▼</div>
              <div className="bg-orange-100 rounded px-2 py-1">Layer 1: classify risk patterns (no LLM)</div>
              <div className="text-center text-orange-500 text-xs">▼</div>
              <div className="bg-orange-100 rounded px-2 py-1">Layer 2: 1 LLM call → Mission Briefing JSON</div>
              <div className="text-center text-orange-500 text-xs">▼</div>
              <div className="bg-orange-100 rounded px-2 py-1 font-medium">→ UPSERT into pt_prescan_cache</div>
            </div>
          </div>
        </div>
        <DownArrow label="briefing dict" />
        <div className="rounded-xl border-2 border-purple-300 bg-purple-50 p-3 text-xs font-medium text-purple-800 text-center">
          🎯 Mission Briefing injected into Attacker prompt + stored in <code className="bg-white px-1 rounded border border-purple-200">pt_runs.mission_briefing</code>
        </div>
      </div>

      {/* When does cache invalidate */}
      <div className="rounded-xl border-2 border-amber-200 bg-amber-50 p-4">
        <div className="text-xs font-bold text-amber-700 uppercase tracking-wider mb-3">🔄 Cache Invalidation Rules</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          {[
            {
              trigger: "Tool schema changes",
              icon: "🔧",
              desc: "Any tool added, removed, or its description/parameters modified → SHA-256 changes → cache miss on next run → fresh pre-scan automatically.",
              auto: true,
            },
            {
              trigger: "Manual invalidation",
              icon: "🗑️",
              desc: "DELETE /api/v1/mcp-pt/mcp-servers/{id}/mission-briefing sets is_stale = true. The cached row is kept but the next run ignores it and regenerates.",
              auto: false,
            },
            {
              trigger: "Stale flag",
              icon: "⚠️",
              desc: "is_stale = true means the briefing exists but is outdated. It's still visible in the UI for reference, but the next red team run will replace it.",
              auto: false,
            },
          ].map(({ trigger, icon, desc, auto }) => (
            <div key={trigger} className="rounded-lg border border-amber-300 bg-white p-3">
              <div className="flex items-center gap-1.5 mb-1 font-semibold text-amber-800">
                <span>{icon}</span>{trigger}
                {auto && <span className="ml-auto bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full text-xs">automatic</span>}
              </div>
              <p className="text-amber-800 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function DBStorageMap() {
  const tables = [
    {
      table: "omni2.pt_prescan_cache",
      color: "border-purple-300 bg-purple-950",
      labelColor: "text-purple-300",
      icon: "🎯",
      desc: "One row per MCP — the cached Mission Briefing",
      columns: [
        { col: "mcp_server_id", note: "FK → mcp_servers, UNIQUE" },
        { col: "tools_hash", note: "SHA-256 of all schemas" },
        { col: "briefing JSONB", note: "Full mission briefing object" },
        { col: "is_stale BOOLEAN", note: "true = re-scan on next run" },
        { col: "created_at / updated_at", note: "Timestamps" },
      ],
    },
    {
      table: "omni2.pt_runs",
      color: "border-blue-300 bg-blue-950",
      labelColor: "text-blue-300",
      icon: "🏃",
      desc: "One row per PT run",
      columns: [
        { col: "run_id", note: "PK" },
        { col: "mcp_name, preset, status", note: "Run metadata" },
        { col: "mission_briefing JSONB", note: "Briefing used for this specific run" },
        { col: "stage_details JSONB", note: "Live progress messages" },
        { col: "passed / failed / critical…", note: "Aggregate test counts" },
      ],
    },
    {
      table: "omni2.pt_agent_stories",
      color: "border-red-300 bg-red-950",
      labelColor: "text-red-300",
      icon: "📖",
      desc: "One row per attack scenario",
      columns: [
        { col: "verdict", note: "vulnerability_found / secure / inconclusive" },
        { col: "was_planned BOOLEAN", note: "Did Judge match to a planned scenario?" },
        { col: "coverage_pct INTEGER", note: "% of planned scenarios executed" },
        { col: "surprises TEXT[]", note: "Unexpected findings outside the plan" },
        { col: "transcript JSONB", note: "Per-story sliced event log" },
      ],
    },
    {
      table: "omni2.mcp_servers",
      color: "border-green-300 bg-green-950",
      labelColor: "text-green-300",
      icon: "🖥️",
      desc: "Updated after each completed run",
      columns: [
        { col: "pt_score INTEGER", note: "0–100 pass rate (errors excluded)" },
        { col: "pt_status", note: "pass / fail / inconclusive" },
        { col: "pt_last_run", note: "Timestamp of last PT run" },
      ],
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      {tables.map((t) => (
        <div key={t.table} className={`rounded-xl border-2 ${t.color} p-4`}>
          <div className={`text-xs font-bold uppercase tracking-wider mb-0.5 ${t.labelColor}`}>
            {t.icon} {t.table}
          </div>
          <div className="text-gray-400 text-xs mb-3 italic">{t.desc}</div>
          <div className="space-y-1.5">
            {t.columns.map(({ col, note }) => (
              <div key={col} className="flex gap-2 text-xs">
                <code className="text-yellow-300 font-mono flex-shrink-0">{col}</code>
                <span className="text-gray-400">{note}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function AttackerJudgeDesign() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Attacker loop */}
        <div className="rounded-xl border-2 border-red-800 bg-red-950 p-4">
          <div className="text-xs font-bold text-red-400 uppercase tracking-wider mb-3">⚔️ Attacker — Agentic Loop</div>
          <div className="space-y-2">
            <div className="bg-red-900 border border-red-700 rounded-lg px-3 py-2 text-xs text-red-100 text-center">
              System prompt = tool schemas + <span className="text-pink-300 font-bold">Mission Briefing block</span>
            </div>
            <div className="text-center text-red-700 text-sm">▼ starts Scenario 1</div>
            <div className="border-2 border-dashed border-red-700 rounded-xl p-3 bg-red-900/40">
              <div className="text-xs text-red-400 font-bold text-center mb-2">↻ loop until end_turn or budget_per_story exhausted</div>
              <div className="space-y-1">
                <div className="bg-red-900 border border-red-700 rounded px-2 py-1.5 text-xs text-red-100 text-center">LLM reasons → emits tool_use block</div>
                <div className="text-center text-red-700 text-xs">▼</div>
                <div className="bg-blue-900 border border-blue-700 rounded px-2 py-1.5 text-xs text-blue-100 text-center">MCPClient.call_tool() — real MCP call</div>
                <div className="text-center text-red-700 text-xs">▼ real response</div>
                <div className="bg-yellow-900 border border-yellow-700 rounded px-2 py-1.5 text-xs text-yellow-100 text-center">Response appended → LLM adapts next move</div>
              </div>
            </div>
            <div className="text-xs text-red-400 italic text-center">
              budget_per_story = max_iterations ÷ max_stories
            </div>
          </div>
        </div>

        {/* Judge */}
        <div className="rounded-xl border-2 border-blue-800 bg-blue-950 p-4">
          <div className="text-xs font-bold text-blue-400 uppercase tracking-wider mb-3">⚖️ Judge — Single Call</div>
          <div className="space-y-2">
            <div className="bg-blue-900 border border-blue-700 rounded-lg px-3 py-2 text-xs text-blue-100 text-center">
              Receives: per-story transcript + planned scenarios from Mission Briefing
            </div>
            <div className="text-center text-blue-700 text-sm">▼ one structured-output call</div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-blue-900 border border-blue-700 rounded-lg p-2">
                <div className="font-bold text-blue-300 mb-1">Always outputs:</div>
                <ul className="text-blue-200 space-y-0.5">
                  <li>• verdict + severity</li>
                  <li>• title + finding</li>
                  <li>• evidence (must quote MCP)</li>
                  <li>• recommendation</li>
                </ul>
              </div>
              <div className="bg-purple-900 border border-purple-700 rounded-lg p-2">
                <div className="font-bold text-purple-300 mb-1">New — plan comparison:</div>
                <ul className="text-purple-200 space-y-0.5">
                  <li>• was_planned (boolean)</li>
                  <li>• coverage_pct (0–100)</li>
                  <li>• surprises[ ] array</li>
                </ul>
              </div>
            </div>
            <div className="bg-green-900 border border-green-700 rounded-lg px-3 py-2 text-xs text-green-100 text-center">
              ✅ Agent Story saved — verdict, transcript slice, plan comparison
            </div>
          </div>
        </div>
      </div>

      {/* Why two agents */}
      <div className="rounded-xl border-2 border-gray-700 bg-gray-900 p-4">
        <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">💡 Why Two Separate Agents?</div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          {[
            { icon: "🎯", title: "Attacker maximises aggression", color: "text-red-400", desc: "Prompted to be creative, persistent, and exploitative. Chains tool calls, pivots on every response." },
            { icon: "⚖️", title: "Judge applies evidence rules", color: "text-blue-400", desc: "Reads the transcript cold. Cannot mark a finding without quoting actual MCP response text — hallucinated findings are structurally impossible." },
            { icon: "🚫", title: "No self-justification bias", color: "text-gray-400", desc: "A single agent judging its own attacks always rationalises failures as successes. Separate roles eliminate this conflict of interest entirely." },
          ].map(({ icon, title, color, desc }) => (
            <div key={title} className="rounded-lg border border-gray-700 bg-gray-800 p-3">
              <div className={`font-bold mb-1 flex items-center gap-1 ${color}`}><span>{icon}</span>{title}</div>
              <p className="text-gray-400 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function AIRedTeamTab() {
  const [section, setSection] = useState<"pipeline"|"briefing"|"cache"|"agents"|"db">("pipeline");

  const nav = [
    { id: "pipeline", label: "Full Pipeline" },
    { id: "briefing", label: "Mission Briefing" },
    { id: "cache",    label: "Cache Architecture" },
    { id: "agents",   label: "Attacker & Judge" },
    { id: "db",       label: "DB Storage" },
  ];

  return (
    <div className="space-y-4">
      {/* Hero */}
      <div className="rounded-2xl bg-gradient-to-br from-purple-950 via-gray-900 to-red-950 border-2 border-purple-700 p-6">
        <div className="flex items-center gap-3 mb-3">
          <span className="text-4xl">🎯</span>
          <div>
            <h3 className="text-xl font-black text-white">AI Red Team — Mission-Briefed Agentic Attack</h3>
            <p className="text-purple-300 text-sm">Stages 5a + 5b: Pre-scan the surface, then attack with strategic intelligence</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
          {[
            { icon: "🔍", label: "Pre-scan", desc: "Classify all tool/prompt/resource schemas for risk patterns before the first attack call" },
            { icon: "🧠", label: "Mission Briefing", desc: "LLM synthesises a prioritised attack plan with specific payloads and pre-assigned scenarios" },
            { icon: "⚔️", label: "Guided Attack", desc: "Attacker starts each scenario knowing exactly what to target — eliminating wasted exploration" },
          ].map(({ icon, label, desc }) => (
            <div key={label} className="bg-white/5 border border-white/10 rounded-xl p-3">
              <div className="text-white font-bold text-sm mb-1">{icon} {label}</div>
              <p className="text-gray-400 text-xs leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Sub-nav */}
      <div className="flex gap-1 flex-wrap">
        {nav.map(n => (
          <button
            key={n.id}
            onClick={() => setSection(n.id as any)}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              section === n.id
                ? "bg-purple-600 text-white shadow-lg"
                : "bg-white border border-gray-200 text-gray-600 hover:border-purple-300 hover:text-purple-700"
            }`}
          >
            {n.label}
          </button>
        ))}
      </div>

      {section === "pipeline" && (
        <Card className="border-gray-800 bg-gray-900">
          <SectionHeader emoji="🔀" title="The Full Red Team Pipeline" sub="From discovery to persisted results — every step, every decision point." />
          <PipelineFlow />
          <div className="mt-4 p-3 bg-gray-800 rounded-xl border border-gray-700">
            <p className="text-xs text-gray-400 leading-relaxed">
              <span className="text-purple-300 font-bold">Key insight:</span> Stage 5a (Pre-scan) is where strategic advantage is built.
              By classifying the attack surface <em>before</em> the first tool call, the attacker spends every iteration on targeted exploitation
              rather than exploration. The cache means this intelligence cost is paid once — subsequent runs are instant.
            </p>
          </div>
        </Card>
      )}

      {section === "briefing" && (
        <Card className="border-purple-200">
          <SectionHeader emoji="🎯" title="Mission Briefing — What It Contains and How It's Used"
            sub="A structured intelligence package generated by two-layer pre-scan and injected directly into the attacker's system prompt." />
          <MissionBriefingAnatomy />
          <div className="mt-4 p-4 bg-amber-50 border border-amber-200 rounded-xl">
            <div className="text-xs font-bold text-amber-700 mb-2">💡 Two-Layer Pre-scan</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-amber-800">
              <div>
                <div className="font-bold mb-1">Layer 1 — Deterministic (no LLM)</div>
                <p className="leading-relaxed">Pattern classifier reads every parameter name and type. Flags known risk signals:
                  <code className="bg-white px-1 rounded mx-0.5">path/file</code> → path traversal,
                  <code className="bg-white px-1 rounded mx-0.5">query/cmd</code> → injection,
                  <code className="bg-white px-1 rounded mx-0.5">url/host</code> → SSRF,
                  <code className="bg-white px-1 rounded mx-0.5">user_id</code> → IDOR.
                  Also detects read→write tool chains. Zero LLM cost, instant.
                </p>
              </div>
              <div>
                <div className="font-bold mb-1">Layer 2 — LLM Synthesis (one call)</div>
                <p className="leading-relaxed">The LLM receives Layer 1 results + full schemas and produces the Mission Briefing JSON:
                  prioritised targets with domain-specific payloads, multi-step attack chains, and scenario assignments tailored
                  to this MCP's exact functionality. One call, cached indefinitely.
                </p>
              </div>
            </div>
          </div>
        </Card>
      )}

      {section === "cache" && (
        <Card>
          <SectionHeader emoji="📦" title="Cache Architecture — Pre-scan stored in PostgreSQL"
            sub="One row per MCP in pt_prescan_cache. No TTL — valid until schemas change." />
          <CacheArchitecture />
        </Card>
      )}

      {section === "agents" && (
        <Card>
          <SectionHeader emoji="⚔️" title="Attacker + Judge Design"
            sub="Two agents, two roles, zero self-justification bias." />
          <AttackerJudgeDesign />
        </Card>
      )}

      {section === "db" && (
        <Card className="border-gray-800 bg-gray-900">
          <SectionHeader emoji="💾" title="Database Storage Map"
            sub="Where every piece of data lands across the 5 stages." />
          <DBStorageMap />
          <div className="mt-4 p-3 bg-gray-800 rounded-xl border border-gray-700 text-xs text-gray-400">
            <span className="text-yellow-300 font-bold">Schema tip:</span> All tables live in the <code className="bg-gray-700 px-1 rounded text-gray-200">omni2</code> schema.
            The prescan cache uses <code className="bg-gray-700 px-1 rounded text-gray-200">UNIQUE(mcp_server_id)</code> — one briefing per MCP at all times.
            Agent story transcripts are stored per-story (sliced), not as one shared log.
          </div>
        </Card>
      )}
    </div>
  );
}

// ── Configuration tab ─────────────────────────────────────────────────────────

function ConfigurationTab({ presets }: { presets: any[] }) {
  const icons: Record<string, string> = { fast: "⚡", quick: "🎯", deep: "🔍" };
  return (
    <div className="space-y-6">
      {/* Presets */}
      <Card>
        <SectionHeader emoji="🎯" title="Presets" sub="Presets bundle category selection with parallelism and timeout defaults." />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {presets.map((p) => (
            <div key={p.name} className="rounded-xl border-2 border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">{icons[p.name] || "🎯"}</span>
                <span className="font-bold text-gray-900 capitalize">{p.name}</span>
              </div>
              <p className="text-xs text-gray-600 mb-3 leading-relaxed">{p.description}</p>
              <div className="space-y-1 text-xs text-gray-500">
                <div>⚡ <span className="font-medium">{p.max_parallel}</span> parallel workers</div>
                <div>⏱️ <span className="font-medium">{p.timeout_seconds}s</span> per-test timeout</div>
              </div>
              {p.categories?.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                  {p.categories.map((c: string) => (
                    <span key={c} className="px-2 py-0.5 bg-sky-50 text-sky-700 text-xs rounded-full border border-sky-200">
                      {c.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="mt-4 p-3 bg-gray-50 rounded-xl border border-gray-200 text-xs text-gray-600">
          <strong>Custom preset:</strong> Select categories manually. You can mix any combination — including running{" "}
          <code className="bg-white px-1 rounded">ai_red_team</code> alone (skips all regular tests and goes straight to Stage 5)
          or alongside other categories (runs both).
        </div>
      </Card>

      {/* AI Red Team config */}
      <Card className="border-purple-100">
        <SectionHeader emoji="🤖" title="AI Red Team Configuration" sub="Settings in the Config tab that control Stage 5 behavior." />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { field: "enabled", type: "boolean", desc: "Master switch. When off, Stage 5 is skipped even if ai_red_team is in the selected categories.", badge: "critical" },
            { field: "attacker_provider", type: "string", desc: "LLM provider for the Attacker agent. Supported: anthropic, gemini, groq, openai-compat." },
            { field: "attacker_model", type: "string", desc: "Model name for the Attacker — use a capable model (e.g. claude-opus-4, gemini-2.0-flash). Creativity matters here." },
            { field: "judge_provider / judge_model", type: "string", desc: "Provider and model for the Judge agent. Can differ from the Attacker — a cheaper model often works well for structured extraction." },
            { field: "max_stories", type: "int", desc: "Number of distinct attack scenarios the Attacker will explore per run. More = more thorough but slower and costlier." },
            { field: "max_iterations", type: "int", desc: "Hard cap on total tool calls across ALL scenarios. Safety guard to prevent runaway loops regardless of max_stories." },
            { field: "temperature", type: "float", desc: "Sampling temperature for the Attacker. Higher values = more creative and unpredictable attack paths." },
          ].map(({ field, type, desc, badge }) => (
            <div key={field} className="rounded-xl border border-purple-200 bg-purple-50 p-3">
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                <code className="text-xs bg-white px-2 py-0.5 rounded font-mono text-purple-800 border border-purple-200">{field}</code>
                <span className="text-xs text-gray-400 italic">{type}</span>
                {badge && <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded-full font-medium">!</span>}
              </div>
              <p className="text-xs text-gray-600 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Per-run options */}
      <Card>
        <SectionHeader emoji="⚙️" title="Per-Run Options" sub="Settings you choose when starting a new PT run." />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { field: "preset", desc: "fast / quick / deep — or custom to pick categories manually. Determines parallelism, timeout, and default categories." },
            { field: "categories", desc: "When using custom preset: choose which category groups to run. Certain tests within auth_validation, tool_boundary, data_leakage, and protocol_robustness automatically target prompts and resources when discovered — no extra categories needed." },
            { field: "mcp_id", desc: "The MCP server to test. The service connects to it and discovers tools, prompts, and resources before any tests run." },
            { field: "plan_source", desc: "llm (default) — LLM generates a tailored test plan targeting tools, prompts, and resources. template — skip Stage 3, run all catalog tests statically with no LLM call." },
          ].map(({ field, desc }) => (
            <div key={field} className="rounded-xl border border-gray-200 bg-gray-50 p-3">
              <code className="text-xs bg-white px-2 py-0.5 rounded font-mono text-gray-700 border border-gray-200 block mb-1">{field}</code>
              <p className="text-xs text-gray-600 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ── Test Catalog tab ──────────────────────────────────────────────────────────

const SEV_COLOR: Record<string, string> = {
  critical: "bg-red-100 text-red-700 border-red-200",
  high:     "bg-orange-100 text-orange-700 border-orange-200",
  medium:   "bg-yellow-100 text-yellow-700 border-yellow-200",
  low:      "bg-blue-100 text-blue-700 border-blue-200",
  info:     "bg-gray-100 text-gray-600 border-gray-200",
};

function CatalogTab({ testCatalog }: { testCatalog: Record<string, any> }) {
  const [open, setOpen] = useState<string | null>(null);

  const catMeta: Record<string, { icon: string; why: string }> = {
    protocol_robustness: { icon: "🔌", why: "MCP servers must reject malformed protocol messages without crashing. This category also covers malformed arguments to prompts and invalid resource URIs — servers often validate tools/call but forget the other surfaces." },
    tool_schema_abuse:   { icon: "🧩", why: "Tools should validate every parameter and reject extra or wrongly-typed fields, not silently ignore them." },
    tool_boundary:       { icon: "🚧", why: "Path traversal, SQL injection, and command injection can hide in tool parameters — and equally in resource URIs and prompt arguments passed to underlying systems." },
    auth_validation:     { icon: "🔑", why: "Missing auth is the highest-risk finding in MCP. This category tests tools, prompt templates, and resource endpoints — prompts are often forgotten in access-control reviews, and resources commonly expose raw DB rows or file contents." },
    resource_exhaustion: { icon: "⚡", why: "Unbounded payloads or rapid repeated calls can take down a server or starve other clients." },
    data_leakage:        { icon: "💧", why: "Logs, error messages, and resource content may expose secrets, tokens, or PII. Resource tests use the same pattern library (Presidio + TruffleHog) as the tool-based scans. Resource URIs themselves can also leak what data the server holds." },
    ai_security:         { icon: "🤖", why: "LLM-backed MCP tools may be vulnerable to prompt injection that hijacks their behavior via tool inputs." },
    ai_red_team:         { icon: "🎯", why: "Autonomous attacker agent — finds complex, chained vulnerabilities that predefined tests cannot anticipate." },
  };

  if (Object.keys(testCatalog).length === 0) {
    return (
      <Card>
        <p className="text-gray-400 text-sm text-center py-8">Loading catalog…</p>
      </Card>
    );
  }

  return (
    <Card>
      <SectionHeader
        emoji="📋"
        title="Test Categories & Catalog"
        sub="Every test function in the system — what it does, why it matters, and how the executor runs it."
      />
      <div className="space-y-3">
        {Object.entries(testCatalog).map(([catName, catData]: [string, any]) => {
          const meta = catMeta[catName] || { icon: "🔬", why: "" };
          const isOpen = open === catName;
          const sev = catData.severity_default;
          const tests: any[] = catData.tests || [];

          return (
            <div key={catName} className={`rounded-xl border-2 overflow-hidden transition-all ${isOpen ? "border-sky-300" : "border-gray-200"}`}>
              <button
                onClick={() => setOpen(isOpen ? null : catName)}
                className="w-full flex items-center gap-3 p-4 bg-gray-50 hover:bg-sky-50 transition-colors text-left"
              >
                <span className="text-xl">{meta.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-bold text-gray-900">{catName.replace(/_/g, " ").toUpperCase()}</span>
                    {sev && (
                      <span className={`px-2 py-0.5 text-xs font-bold rounded-full border ${SEV_COLOR[sev] || SEV_COLOR.info}`}>
                        {sev}
                      </span>
                    )}
                    <span className="text-xs text-gray-500">{tests.length} test{tests.length !== 1 ? "s" : ""}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{catData.description}</p>
                </div>
                <span className={`text-gray-400 transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}>▼</span>
              </button>

              {isOpen && (
                <div className="p-4 space-y-4">
                  {meta.why && (
                    <div className="flex gap-2 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                      <span className="text-amber-500 flex-shrink-0">💡</span>
                      <p className="text-xs text-amber-800 leading-relaxed">
                        <strong>Why this matters:</strong> {meta.why}
                      </p>
                    </div>
                  )}
                  <div className="divide-y divide-gray-100">
                    {tests.map((test: any) => (
                      <div key={test.name} className={`py-3 flex gap-3 ${!test.enabled ? "opacity-40" : ""}`}>
                        <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${test.enabled ? "bg-green-500" : "bg-gray-300"}`} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-semibold text-gray-800 text-sm">{test.name.replace(/_/g, " ")}</span>
                            {!test.enabled && <span className="text-xs text-gray-400 italic">disabled</span>}
                            <code className="text-xs text-sky-600 bg-sky-50 px-1.5 py-0.5 rounded font-mono ml-auto border border-sky-100">
                              {test.python_function}()
                            </code>
                          </div>
                          {test.description && (
                            <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{test.description}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-4 p-3 bg-gray-50 rounded-xl border border-gray-200">
        <p className="text-xs text-gray-500">
          <strong>How Stage 4 runs these:</strong> For each test in the LLM-generated plan, the Executor calls the matching Python function
          with the LLM-chosen tool and parameters. The function sends a crafted request to the MCP, reads the response, and marks{" "}
          <code className="bg-white px-1 rounded">pass</code> / <code className="bg-white px-1 rounded">fail</code> based on whether the server
          behaved securely (rejected the bad input, didn't crash, didn't leak data).
        </p>
      </div>
    </Card>
  );
}

// ── Main export ───────────────────────────────────────────────────────────────

export default function MCPPTAboutTab({ testCatalog, presets, categories }: Props) {
  const [activeTab, setActiveTab] = useState("overview");

  return (
    <div>
      {/* Hero */}
      <div className="bg-gradient-to-r from-sky-50 to-purple-50 rounded-2xl border-2 border-sky-100 p-6 mb-5">
        <h2 className="text-2xl font-black text-gray-900 mb-2">🛡️ MCP Penetration Testing — How it Works</h2>
        <p className="text-gray-600 text-sm leading-relaxed max-w-3xl">
          MCP PT runs up to 5 stages per test. Stages 1–4 use pre-defined Python test functions driven by an LLM plan.
          Stage 5 (AI Red Team) is completely different — the LLM <em>is</em> the executor, making real MCP tool calls
          autonomously. Use the tabs below to explore each aspect in detail.
        </p>
      </div>

      {/* Tab navigation */}
      <div className="flex gap-1 border-b-2 border-gray-200 mb-6 overflow-x-auto pb-0">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-semibold whitespace-nowrap transition-all border-b-2 -mb-0.5 ${
              activeTab === tab.id
                ? "border-sky-500 text-sky-700 bg-sky-50 rounded-t-lg"
                : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
            }`}
          >
            {tab.icon} {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="space-y-6">
        {activeTab === "overview"      && <OverviewTab />}
        {activeTab === "regular"       && <RegularTestsTab />}
        {activeTab === "red_team"      && <AIRedTeamTab />}
        {activeTab === "configuration" && <ConfigurationTab presets={presets} />}
        {activeTab === "catalog"       && <CatalogTab testCatalog={testCatalog} />}
      </div>
    </div>
  );
}
