"use client";

/**
 * MCPPTInfoPanel — shown when no PT run is active.
 * Explains the three test modes and how the LLM participates.
 */

const MODES = [
  {
    icon: "🔧",
    name: "Template Mode",
    badge: "No LLM",
    badgeColor: "bg-gray-200 text-gray-600",
    borderColor: "border-gray-200",
    headingColor: "text-gray-800",
    points: [
      "Runs every standard test case for selected categories",
      "Inputs are fixed, pre-defined payloads",
      "Instant — zero API cost, always reproducible",
    ],
    llmCalls: "0 LLM calls",
    llmCallsColor: "text-gray-500",
  },
  {
    icon: "🧠",
    name: "LLM Mode",
    badge: "Smart",
    badgeColor: "bg-sky-100 text-sky-700",
    borderColor: "border-sky-200",
    headingColor: "text-sky-800",
    points: [
      "LLM reads all your MCP tool schemas (names, descriptions, parameters)",
      "Makes ONE decision — a complete test plan covering ALL selected categories at once",
      "Picks the highest-risk tools and crafts tailored attack inputs per tool",
      "Plan is cached: same MCP + preset skips the LLM call on re-runs",
    ],
    llmCalls: "1 LLM call per unique run",
    llmCallsColor: "text-sky-600",
    detail: "One call → LLM sees the full MCP context and returns a prioritized JSON plan with custom inputs for every category simultaneously. Not one call per category.",
  },
  {
    icon: "🤖",
    name: "AI Red Team",
    badge: "Agentic",
    badgeColor: "bg-purple-100 text-purple-700",
    borderColor: "border-purple-200",
    headingColor: "text-purple-800",
    points: [
      "Runs after regular tests as a separate stage",
      "An attacker LLM is given real access to MCP tools — it calls them directly",
      "Conducts N independent attack scenarios (auth bypass, injection, data extraction, chaining…)",
      "A judge LLM reviews the full transcript and extracts structured findings",
      "Different models for attacker (speed) and judge (precision) can be configured",
    ],
    llmCalls: "~25 attacker + 1 judge calls",
    llmCallsColor: "text-purple-600",
    detail: "The agent makes real tool calls against your MCP. Every response is analyzed for evidence of vulnerabilities, privilege escalation, or data leakage.",
  },
];

export default function MCPPTInfoPanel() {
  return (
    <div className="mb-6 rounded-2xl border border-gray-100 bg-white shadow-sm p-6">
      <div className="flex items-center gap-2 mb-5">
        <span className="text-xl">🛡️</span>
        <h3 className="text-base font-bold text-gray-800">How MCP Penetration Testing Works</h3>
        <span className="ml-auto text-xs text-gray-400">Choose a mode in the panel below to start</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {MODES.map((m) => (
          <div
            key={m.name}
            className={`rounded-xl border-2 ${m.borderColor} p-4 flex flex-col gap-2`}
          >
            {/* Header */}
            <div className="flex items-center gap-2">
              <span className="text-2xl">{m.icon}</span>
              <div>
                <div className="flex items-center gap-1.5">
                  <span className={`font-bold text-sm ${m.headingColor}`}>{m.name}</span>
                  <span className={`px-1.5 py-0.5 rounded-full text-xs font-semibold ${m.badgeColor}`}>
                    {m.badge}
                  </span>
                </div>
                <span className={`text-xs font-medium ${m.llmCallsColor}`}>{m.llmCalls}</span>
              </div>
            </div>

            {/* Points */}
            <ul className="space-y-1 mt-1">
              {m.points.map((p, i) => (
                <li key={i} className="flex items-start gap-1.5 text-xs text-gray-600">
                  <span className="mt-0.5 shrink-0 text-gray-400">•</span>
                  {p}
                </li>
              ))}
            </ul>

            {/* Detail callout */}
            {m.detail && (
              <div className={`mt-auto pt-2 border-t ${m.borderColor}`}>
                <p className="text-xs text-gray-500 italic">{m.detail}</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* LLM decisions footnote */}
      <div className="mt-4 pt-3 border-t border-gray-100 flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-500">
        <span>
          <strong className="text-gray-700">LLM plan decisions:</strong> Template = 0 calls &nbsp;·&nbsp;
          LLM mode = <strong>1 call</strong> covering all categories at once (cached) &nbsp;·&nbsp;
          AI Red Team = many calls (agentic loop)
        </span>
        <span className="ml-auto">
          Mix modes freely — AI Red Team can run alongside any other categories in the same test
        </span>
      </div>
    </div>
  );
}
