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
    desc: "ONE LLM call reads all schemas and selected categories → returns a tailored JSON test plan. Skipped in Template mode. Result is cached.",
  },
  {
    n: 4, icon: "⚙️", label: "Test Execution",
    color: "border-orange-200 bg-orange-50", dot: "bg-orange-400",
    desc: "Python executor runs deterministic test functions from the catalog. The LLM never runs tests — it only planned which ones to run.",
  },
  {
    n: 5, icon: "🤖", label: "AI Red Team",
    color: "border-purple-200 bg-purple-50", dot: "bg-purple-500",
    desc: "Agentic attacker LLM makes real MCP tool calls autonomously, adapting to each response. A separate Judge LLM evaluates findings.",
    highlight: true,
  },
];

function OverviewTab() {
  return (
    <div className="space-y-6">
      <Card>
        <SectionHeader emoji="🗺️" title="The 5 Stages of a PT Run" sub="Every run passes through these stages in order. Stage 5 is optional and must be selected explicitly." />
        <div className="space-y-3">
          {STAGES.map((s, i) => (
            <div key={s.n} className="flex gap-4">
              <div className="flex flex-col items-center w-8 flex-shrink-0">
                <div className={`w-8 h-8 rounded-full ${s.dot} text-white text-xs font-black flex items-center justify-center`}>{s.n}</div>
                {i < STAGES.length - 1 && <div className="w-0.5 flex-1 bg-gray-200 my-1" />}
              </div>
              <div className={`flex-1 rounded-xl border-2 ${s.color} p-4 ${(s as any).highlight ? "ring-2 ring-purple-300" : ""}`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">{s.icon}</span>
                  <span className="font-bold text-sm text-gray-800">{s.label}</span>
                  {(s as any).highlight && (
                    <span className="ml-auto text-xs px-2 py-0.5 bg-purple-100 text-purple-700 rounded-full font-medium">optional</span>
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
          <div className="text-sm font-bold text-orange-700 mb-3 flex items-center gap-2">⚙️ Stages 1–4 — Regular Testing</div>
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
          <div className="text-sm font-bold text-purple-700 mb-3 flex items-center gap-2">🤖 Stage 5 — AI Red Team</div>
          <ul className="text-xs text-gray-600 space-y-2">
            {[
              "Non-deterministic — creative, adaptive attacks",
              "Chains multiple tool calls using real MCP responses",
              "Discovers semantic vulnerabilities predefined tests miss",
              "Separate Judge agent prevents self-justification bias",
              "Always a live agentic run — no caching by design",
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

function AgentLoopDiagram() {
  return (
    <div className="space-y-2">
      {/* Attacker phase */}
      <div className="rounded-xl border-2 border-red-200 bg-red-50 p-4">
        <div className="text-xs font-bold text-red-600 uppercase tracking-wider mb-3">⚔️ Attacker Phase — Agentic Loop</div>
        <div className="flex flex-col items-stretch gap-1">
          <div className="bg-white border-2 border-red-300 rounded-xl px-4 py-2 text-xs font-medium text-red-800 text-center">
            🎯 Attacker LLM initialized with: MCP name, tool schemas, attack goal
          </div>
          <div className="text-center text-gray-400 text-sm">▼ starts scenario 1</div>

          {/* Loop box */}
          <div className="border-2 border-dashed border-red-300 rounded-xl p-3 bg-white/60">
            <div className="text-xs text-red-500 font-bold text-center mb-2">
              ↻ NON-DETERMINISTIC LOOP — repeats until end_turn or max_iterations
            </div>
            <div className="flex flex-col items-stretch gap-1">
              <div className="bg-red-100 border border-red-200 rounded-lg px-3 py-2 text-xs text-red-900 text-center">
                LLM reasons about next move → emits <code className="bg-white/80 px-1 rounded">tool_use</code> block
              </div>
              <div className="text-center text-gray-400 text-xs">▼ execute</div>
              <div className="bg-blue-100 border border-blue-200 rounded-lg px-3 py-2 text-xs text-blue-900 text-center">
                🔌 <strong>MCPClient.call_tool()</strong> — real HTTP-Streamable / stdio call to target MCP
              </div>
              <div className="text-center text-gray-400 text-xs">▼ real MCP response</div>
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-3 py-2 text-xs text-yellow-900 text-center">
                Response appended to conversation → LLM reads it and adapts its next move
              </div>
            </div>
            <div className="flex gap-2 justify-center mt-2 flex-wrap text-xs">
              <span className="bg-red-100 border border-red-200 px-2 py-0.5 rounded text-red-700">New scenario → === SCENARIO N: goal ===</span>
              <span className="text-gray-400">or</span>
              <span className="bg-gray-100 border border-gray-200 px-2 py-0.5 rounded text-gray-600">end_turn → exit loop</span>
            </div>
          </div>
          <div className="text-center text-xs text-gray-400 italic mt-1">
            Each run may take completely different paths — the MCP's real responses guide every decision
          </div>
        </div>
      </div>

      {/* Separator */}
      <div className="flex items-center gap-2 py-1">
        <div className="h-0.5 flex-1 bg-gray-200" />
        <div className="text-xs text-gray-400 whitespace-nowrap">full transcript passes to Judge</div>
        <div className="text-gray-400">▼</div>
        <div className="h-0.5 flex-1 bg-gray-200" />
      </div>

      {/* Judge phase */}
      <div className="rounded-xl border-2 border-blue-200 bg-blue-50 p-4">
        <div className="text-xs font-bold text-blue-600 uppercase tracking-wider mb-3">⚖️ Judge Phase — Single Call, No Tools</div>
        <div className="flex flex-col items-stretch gap-1">
          <div className="bg-white border-2 border-blue-300 rounded-xl px-4 py-2 text-xs font-medium text-blue-800 text-center">
            Judge LLM receives: complete transcript (all tool calls + MCP responses + thinking text)
          </div>
          <div className="text-center text-gray-400 text-sm">▼ one structured output call</div>
          <div className="grid grid-cols-2 gap-2">
            <div className="bg-blue-100 border border-blue-200 rounded-lg px-3 py-2 text-xs text-blue-900">
              <div className="font-bold mb-1">Per scenario extracts:</div>
              <ul className="space-y-0.5 text-blue-800">
                <li>• verdict (vuln / secure / inconclusive)</li>
                <li>• severity (critical → info)</li>
                <li>• title + finding + evidence</li>
                <li>• recommendation</li>
              </ul>
            </div>
            <div className="bg-blue-100 border border-blue-200 rounded-lg px-3 py-2 text-xs text-blue-900">
              <div className="font-bold mb-1">Strict evidence rule:</div>
              <p className="text-blue-800">
                Must quote or paraphrase actual MCP response text. Cannot invent findings from imagination.
                No finding without evidence.
              </p>
            </div>
          </div>
          <div className="text-center text-gray-400 text-sm">▼</div>
          <div className="bg-purple-100 border-2 border-purple-300 rounded-xl px-4 py-2 text-xs font-medium text-purple-800 text-center">
            🏆 Agent Story persisted — viewable in run results with full expandable transcript
          </div>
        </div>
      </div>
    </div>
  );
}

function WhyNoPlanning() {
  return (
    <div className="rounded-xl border-2 border-amber-200 bg-amber-50 p-4">
      <div className="text-xs font-bold text-amber-700 uppercase tracking-wider mb-3">
        💡 Why no upfront planning?
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
        {/* Bad: upfront plan */}
        <div className="rounded-xl border-2 border-red-200 bg-red-50 p-3">
          <div className="text-xs font-bold text-red-600 mb-2">❌ Upfront plan (without real data)</div>
          <div className="space-y-1 text-xs text-red-800 font-mono">
            <div className="bg-red-100 rounded px-2 py-1">Step 1: Try path traversal on… something</div>
            <div className="bg-red-100 rounded px-2 py-1">Step 2: Try SQL injection on… something</div>
            <div className="bg-red-100 rounded px-2 py-1">Step 3: Try auth bypass on… something</div>
          </div>
          <p className="text-xs text-red-700 mt-2 italic">Generic guesses — ignores what the MCP actually has</p>
        </div>
        {/* Good: reactive */}
        <div className="rounded-xl border-2 border-green-200 bg-green-50 p-3">
          <div className="text-xs font-bold text-green-700 mb-2">✅ Reactive loop (uses real responses)</div>
          <div className="space-y-1 text-xs text-green-900 font-mono">
            <div className="bg-green-100 rounded px-2 py-1">calls list_containers() →</div>
            <div className="bg-white border border-green-200 rounded px-2 py-1 ml-2 text-green-700">["prod-db", "payment-svc"]</div>
            <div className="bg-green-100 rounded px-2 py-1">→ restart_container("prod-db") no auth →</div>
            <div className="bg-white border border-green-200 rounded px-2 py-1 ml-2 text-green-700">"Success" ← 🚨 CRITICAL</div>
          </div>
          <p className="text-xs text-green-700 mt-2 italic">Each move is based on what the MCP just returned</p>
        </div>
      </div>
      <p className="text-xs text-amber-800 leading-relaxed">
        The <strong>one-line scenario header</strong> (<code className="bg-white px-1 rounded border border-amber-200">=== SCENARIO 1: Auth bypass via missing token ===</code>)
        IS the plan — it's brief because the attacker doesn't know more than that until it starts probing.
        Scenario 2 often builds directly on what Scenario 1 found (e.g. using a leaked credential to escalate).
        That chain is impossible to plan before Scenario 1 runs.
      </p>
    </div>
  );
}

function AIRedTeamTab() {
  return (
    <div className="space-y-6">
      {/* Intro + loop diagram */}
      <Card className="border-purple-100">
        <SectionHeader emoji="🤖" title="AI Red Team — How the Agentic Loop Works" sub="Stage 5: the LLM becomes the executor, making real MCP calls and adapting to every response." />
        <div className="mb-4 p-4 bg-purple-50 rounded-xl border border-purple-200">
          <p className="text-sm text-gray-700 leading-relaxed">
            Unlike regular tests where Python functions call the MCP with a predetermined request, in AI Red Team
            the <strong>Attacker LLM decides what to call next</strong> — based on the real MCP response it just received.
            This loop is <strong>non-deterministic</strong>: two runs against the same MCP may explore completely different
            attack paths. The loop ends when the LLM signals it is done (<code className="bg-white px-1 rounded text-xs">end_turn</code>) or when the
            <code className="bg-white px-1 rounded text-xs mx-1">max_iterations</code> tool-call cap is hit.
          </p>
        </div>
        <WhyNoPlanning />
        <div className="mt-4">
          <AgentLoopDiagram />
        </div>
      </Card>

      {/* Two-agent design */}
      <Card>
        <SectionHeader emoji="⚔️" title="Why Two Separate Agents?" sub="Attacker and Judge are intentionally different LLMs with different roles and prompts." />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
          {[
            {
              icon: "🎯", color: "border-red-200 bg-red-50",
              title: "Attacker maximises aggression",
              desc: "The Attacker is prompted to be creative and persistent. It chains tool calls, pivots on results, and tries every angle — not constrained by fairness.",
            },
            {
              icon: "⚖️", color: "border-blue-200 bg-blue-50",
              title: "Judge applies strict evidence rules",
              desc: "The Judge reads the transcript cold with no prior context. It cannot mark a finding without quoting actual MCP response text — hallucinated findings are structurally impossible.",
            },
            {
              icon: "🚫", color: "border-gray-200 bg-gray-50",
              title: "Prevents self-justification bias",
              desc: "A single agent judging its own work rationalises failures as successes. Separating the roles eliminates this conflict of interest entirely.",
            },
          ].map(({ icon, color, title, desc }) => (
            <div key={title} className={`rounded-xl border-2 ${color} p-4`}>
              <div className="text-2xl mb-2">{icon}</div>
              <div className="font-bold text-gray-800 text-sm mb-1">{title}</div>
              <p className="text-xs text-gray-600 leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>

        {/* Stage 4 vs Stage 5 */}
        <div className="rounded-xl border-2 border-gray-200 bg-gray-50 p-4">
          <div className="font-bold text-gray-800 mb-3 text-sm">🔍 Stage 4 vs Stage 5 — Key Difference</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs text-gray-700">
            <div>
              <div className="font-semibold text-orange-700 mb-1">⚙️ Stage 4 (Regular)</div>
              <ul className="space-y-1">
                <li>• LLM plans all tests once upfront</li>
                <li>• Python runs each test independently</li>
                <li>• No reaction to previous test results</li>
                <li>• Deterministic, cacheable, fast</li>
              </ul>
            </div>
            <div>
              <div className="font-semibold text-purple-700 mb-1">🤖 Stage 5 (AI Red Team)</div>
              <ul className="space-y-1">
                <li>• LLM decides one call at a time</li>
                <li>• Each real MCP response shapes the next call</li>
                <li>• Can chain: tool A result → feeds tool B attack</li>
                <li>• Non-deterministic, uncacheable, creative</li>
              </ul>
            </div>
          </div>
        </div>
      </Card>

      {/* Technical */}
      <Card className="border-gray-100">
        <SectionHeader emoji="🔧" title="Technical Details" sub="Schema conversion, provider support, and data persistence." />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <div className="text-xs font-bold text-gray-500 uppercase mb-2">Tool Schema Conversion (MCP → LLM format)</div>
            <div className="rounded-xl bg-gray-900 text-gray-100 p-4 text-xs font-mono space-y-1">
              <div className="text-gray-500 mb-2">// Each provider needs a different tool format</div>
              <div><span className="text-purple-300">MCP inputSchema</span> <span className="text-gray-500">→</span> <span className="text-yellow-300">Anthropic</span><span className="text-gray-400">: {"{ name, input_schema }"}</span></div>
              <div><span className="text-purple-300">MCP inputSchema</span> <span className="text-gray-500">→</span> <span className="text-blue-300">Gemini</span><span className="text-gray-400">: FunctionDeclaration</span></div>
              <div><span className="text-purple-300">MCP inputSchema</span> <span className="text-gray-500">→</span> <span className="text-orange-300">Groq/OpenAI</span><span className="text-gray-400">: {"{ type:'function', … }"}</span></div>
              <div className="text-gray-500 mt-2">// Real MCP call — identical to any real client</div>
              <div><span className="text-cyan-300">mcp_client</span>.<span className="text-yellow-200">call_tool</span>(<span className="text-orange-200">name</span>, <span className="text-orange-200">args</span>)</div>
              <div className="text-gray-500 pl-2">→ HTTP-Streamable / stdio</div>
            </div>
          </div>
          <div className="space-y-3 text-sm">
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-3">
              <div className="font-semibold text-gray-800 text-xs mb-1">📦 No Caching (by design)</div>
              <p className="text-xs text-gray-600">AI Red Team runs are always live. Caching would defeat the purpose — the value is in discovering novel attack paths on each run.</p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-3">
              <div className="font-semibold text-gray-800 text-xs mb-1">🔁 Scenarios vs Iterations</div>
              <p className="text-xs text-gray-600">
                <code className="bg-white px-1 rounded border border-gray-200">max_stories</code> — how many attack scenarios the Attacker explores.<br />
                <code className="bg-white px-1 rounded border border-gray-200">max_iterations</code> — total tool-call cap across all scenarios (safety guard).
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-3">
              <div className="font-semibold text-gray-800 text-xs mb-1">💾 Agent Stories</div>
              <p className="text-xs text-gray-600">Each scenario becomes an Agent Story in the DB — verdict, finding, evidence, recommendation, and the full transcript. Viewable per-story in run results.</p>
            </div>
          </div>
        </div>
      </Card>
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
