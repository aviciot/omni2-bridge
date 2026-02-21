"use client";

import { useState, useEffect, useMemo } from "react";
import { omni2Api } from "@/lib/omni2Api";
import AIRedTeamResults from "./AIRedTeamResults";

interface PTRunDetailsProps {
  runId: number;
  onClose: () => void;
}

const SEVERITY_STYLE: Record<string, string> = {
  critical: "bg-red-600 text-white",
  high:     "bg-orange-500 text-white",
  medium:   "bg-yellow-500 text-white",
  low:      "bg-blue-400 text-white",
  info:     "bg-gray-300 text-gray-700",
};

const CATEGORY_ICON: Record<string, string> = {
  protocol_robustness: "🔌",
  tool_schema_abuse:   "🧩",
  tool_boundary:       "🚧",
  auth_validation:     "🔑",
  resource_exhaustion: "⚡",
  data_leakage:        "💧",
  ai_security:         "🤖",
};

export default function PTRunDetails({ runId, onClose }: PTRunDetailsProps) {
  const [activeTab, setActiveTab] = useState<"summary" | "profile" | "results" | "plan" | "discovery" | "redteam">("summary");
  const [runData, setRunData]   = useState<any>(null);
  const [discovery, setDiscovery] = useState<any>(null);
  const [results, setResults]   = useState<any[]>([]);
  const [agentStoryCount, setAgentStoryCount] = useState<number>(0);
  const [loading, setLoading]   = useState(true);
  const [resultFilter, setResultFilter] = useState<"all" | "fail" | "error" | "pass">("all");

  useEffect(() => { loadData(); }, [runId]);

  const loadData = async () => {
    try {
      const [runRes, discoveryRes, resultsRes, storiesRes] = await Promise.all([
        omni2Api.get(`/api/v1/mcp-pt/runs/${runId}`),
        omni2Api.get(`/api/v1/mcp-pt/runs/${runId}/discovery`).catch(() => ({ data: null })),
        omni2Api.get(`/api/v1/mcp-pt/runs/${runId}/results`).catch(() => ({ data: [] })),
        omni2Api.get(`/api/v1/mcp-pt/runs/${runId}/agent-stories`).catch(() => ({ data: [] })),
      ]);
      setRunData(runRes.data);
      setDiscovery(discoveryRes.data);
      setResults(Array.isArray(resultsRes.data) ? resultsRes.data : []);
      setAgentStoryCount(Array.isArray(storiesRes.data) ? storiesRes.data.length : 0);
    } catch (e) {
      console.error("Failed to load run details", e);
    } finally {
      setLoading(false);
    }
  };

  // ── Derived data ────────────────────────────────────────────────────────────

  // API returns these as double-encoded JSON strings (stored as JSONB text) — parse if needed
  const testPlan = useMemo(() => {
    const raw = runData?.test_plan;
    if (!raw) return null;
    if (typeof raw === "string") { try { return JSON.parse(raw); } catch { return null; } }
    return raw;
  }, [runData]);
  const securityProfile = useMemo(() => {
    const raw = runData?.security_profile;
    if (!raw) return null;
    if (typeof raw === "string") { try { return JSON.parse(raw); } catch { return null; } }
    return raw;
  }, [runData]);

  // Normalise discovery field names (backend uses tool_count, UI expected tools_count)
  const disc = useMemo(() => {
    if (!discovery) return null;
    return {
      tools_count:     discovery.tool_count     ?? discovery.tools_count     ?? 0,
      prompts_count:   discovery.prompt_count   ?? discovery.prompts_count   ?? 0,
      resources_count: discovery.resource_count ?? discovery.resources_count ?? 0,
      tools:     discovery.tools     ?? [],
      prompts:   discovery.prompts   ?? [],
      resources: discovery.resources ?? [],
    };
  }, [discovery]);

  // Normalise plan tests (LLM returns `test`, UI expected `test_name`)
  const planTests = useMemo(() =>
    (testPlan?.tests ?? []).map((t: any) => ({
      ...t,
      test_name: t.test_name ?? t.test ?? "unknown",
    }))
  , [testPlan]);

  // Per-category stats computed from results
  const categoryStats = useMemo(() => {
    const stats: Record<string, { pass: number; fail: number; error: number; critical: number; high: number; medium: number }> = {};
    for (const r of results) {
      const cat = r.category ?? "unknown";
      if (!stats[cat]) stats[cat] = { pass: 0, fail: 0, error: 0, critical: 0, high: 0, medium: 0 };
      if (r.status === "pass")       stats[cat].pass++;
      else if (r.status === "fail") {
        stats[cat].fail++;
        if (r.severity === "critical") stats[cat].critical++;
        else if (r.severity === "high") stats[cat].high++;
        else if (r.severity === "medium") stats[cat].medium++;
      } else                         stats[cat].error++;
    }
    return stats;
  }, [results]);

  const totalFails  = results.filter(r => r.status === "fail").length;
  const totalErrors = results.filter(r => r.status === "error").length;
  const totalPass   = results.filter(r => r.status === "pass").length;
  const totalTests  = results.length;

  const filteredResults = resultFilter === "all" ? results : results.filter(r => r.status === resultFilter);

  // ── Helpers ─────────────────────────────────────────────────────────────────

  const riskColor = (score: number) =>
    score >= 8 ? "from-red-600 to-red-500" : score >= 5 ? "from-orange-500 to-yellow-500" : "from-green-600 to-green-500";

  const riskLabel = (score: number) =>
    score >= 8 ? "Critical Risk" : score >= 5 ? "Medium Risk" : "Low Risk";

  // ── Loading ──────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
        <div className="bg-white rounded-2xl p-10 flex flex-col items-center gap-4">
          <div className="animate-spin rounded-full h-14 w-14 border-4 border-sky-500 border-t-transparent" />
          <p className="text-gray-600 font-medium">Loading run details…</p>
        </div>
      </div>
    );
  }

  const TABS = [
    { id: "summary",   icon: "📊", label: "Summary"  },
    { id: "profile",   icon: "🛡️", label: "Security Profile" },
    { id: "results",   icon: "🧪", label: `Results${totalFails > 0 ? ` (${totalFails} fail)` : ""}` },
    { id: "plan",      icon: "📋", label: "Test Plan" },
    { id: "discovery", icon: "🔍", label: "Discovery" },
    { id: "redteam",   icon: "🤖", label: `Red Team${agentStoryCount > 0 ? ` (${agentStoryCount})` : ""}` },
  ];

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-gray-50 rounded-2xl shadow-2xl w-full max-w-6xl max-h-[92vh] flex flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* ── Modal Header ── */}
        <div className="bg-gradient-to-r from-slate-800 to-slate-700 text-white px-6 py-5 flex-shrink-0">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-white/10 rounded-xl flex items-center justify-center text-2xl">🛡️</div>
              <div>
                <div className="flex items-center gap-3 flex-wrap">
                  <h3 className="text-xl font-black">PT Run #{runId}</h3>
                  {(() => {
                    const src = runData?.plan_source || (runData?.llm_provider === 'template' ? 'template' : 'llm');
                    if (src === 'template') return <span className="px-2 py-0.5 bg-indigo-500 text-white text-xs font-bold rounded-full">⚙️ Deterministic</span>;
                    if (src === 'cached')   return <span className="px-2 py-0.5 bg-purple-500 text-white text-xs font-bold rounded-full">📋 Cached Plan</span>;
                    return <span className="px-2 py-0.5 bg-sky-500 text-white text-xs font-bold rounded-full">🧠 LLM Generated</span>;
                  })()}
                </div>
                <p className="text-slate-300 text-sm">
                  {runData?.mcp_name} · {runData?.preset} preset
                  {runData?.llm_provider && runData.llm_provider !== 'template' && ` · ${runData.llm_provider}/${runData.llm_model}`}
                  {runData?.llm_cost_usd > 0 && ` · $${Number(runData.llm_cost_usd).toFixed(4)} LLM cost`}
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="w-9 h-9 bg-white/10 hover:bg-white/20 rounded-full flex items-center justify-center transition-colors text-lg"
            >✕</button>
          </div>
          {/* Tabs */}
          <div className="flex gap-1 overflow-x-auto">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`px-4 py-2 rounded-lg text-sm font-semibold whitespace-nowrap transition-all ${
                  activeTab === tab.id
                    ? "bg-white text-slate-800 shadow"
                    : "text-slate-300 hover:bg-white/10"
                }`}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* ── Tab Content ── */}
        <div className="flex-1 overflow-y-auto p-6 space-y-5">

          {/* ═══════════════════════════ SUMMARY ═══════════════════════════ */}
          {activeTab === "summary" && (
            <>
              {/* Top row: risk score + stat cards */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                {/* Risk Score */}
                <div className={`col-span-2 md:col-span-1 bg-gradient-to-br ${riskColor(securityProfile?.risk_score ?? 0)} rounded-2xl p-5 text-white flex flex-col items-center justify-center`}>
                  <div className="text-5xl font-black">{securityProfile?.risk_score ?? "—"}</div>
                  <div className="text-xs font-bold mt-1 opacity-80">/ 10</div>
                  <div className="text-sm font-semibold mt-2 text-center">{riskLabel(securityProfile?.risk_score ?? 0)}</div>
                </div>
                {/* Test stats */}
                {[
                  { label: "Total",  value: totalTests,  color: "bg-white border-2 border-gray-200",          text: "text-gray-900" },
                  { label: "Passed", value: totalPass,   color: "bg-green-50 border-2 border-green-200",      text: "text-green-700" },
                  { label: "Failed", value: totalFails,  color: "bg-red-50 border-2 border-red-200",          text: "text-red-700" },
                  { label: "Errors", value: totalErrors, color: "bg-yellow-50 border-2 border-yellow-200",    text: "text-yellow-700" },
                ].map(s => (
                  <div key={s.label} className={`${s.color} rounded-2xl p-5 flex flex-col items-center justify-center`}>
                    <div className={`text-4xl font-black ${s.text}`}>{s.value}</div>
                    <div className={`text-xs font-bold mt-1 ${s.text} opacity-70`}>{s.label}</div>
                  </div>
                ))}
              </div>

              {/* Per-category breakdown */}
              {Object.keys(categoryStats).length > 0 && (
                <div className="bg-white rounded-2xl border-2 border-gray-200 p-5">
                  <h4 className="text-base font-bold text-gray-800 mb-4 flex items-center gap-2">📂 Results by Category</h4>
                  <div className="space-y-3">
                    {Object.entries(categoryStats).map(([cat, s]) => {
                      const total = s.pass + s.fail + s.error;
                      const passRate = total > 0 ? Math.round((s.pass / total) * 100) : 0;
                      const hasIssues = s.fail > 0;
                      return (
                        <div key={cat} className={`p-4 rounded-xl border ${hasIssues ? "bg-red-50 border-red-200" : "bg-green-50 border-green-200"}`}>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className="text-lg">{CATEGORY_ICON[cat] ?? "🔧"}</span>
                              <span className="font-semibold text-gray-800 text-sm">{cat.replace(/_/g, " ")}</span>
                            </div>
                            <div className="flex items-center gap-2 text-xs font-bold">
                              {s.fail > 0 && <span className="px-2 py-0.5 bg-red-600 text-white rounded-full">✗ {s.fail} fail</span>}
                              {s.error > 0 && <span className="px-2 py-0.5 bg-yellow-500 text-white rounded-full">⚠ {s.error} err</span>}
                              <span className="px-2 py-0.5 bg-green-600 text-white rounded-full">✓ {s.pass}</span>
                              <span className="text-gray-500 ml-1">{passRate}%</span>
                            </div>
                          </div>
                          {/* Progress bar */}
                          <div className="h-2 bg-gray-200 rounded-full overflow-hidden flex">
                            <div className="bg-green-500 h-full transition-all" style={{ width: `${(s.pass / total) * 100}%` }} />
                            <div className="bg-red-500 h-full transition-all" style={{ width: `${(s.fail / total) * 100}%` }} />
                            <div className="bg-yellow-400 h-full transition-all" style={{ width: `${(s.error / total) * 100}%` }} />
                          </div>
                          {/* Critical/high badges */}
                          {(s.critical > 0 || s.high > 0) && (
                            <div className="flex gap-2 mt-2">
                              {s.critical > 0 && <span className="text-xs px-2 py-0.5 bg-red-600 text-white rounded-full font-bold">🔴 {s.critical} Critical</span>}
                              {s.high > 0 && <span className="text-xs px-2 py-0.5 bg-orange-500 text-white rounded-full font-bold">🟠 {s.high} High</span>}
                              {s.medium > 0 && <span className="text-xs px-2 py-0.5 bg-yellow-500 text-white rounded-full font-bold">🟡 {s.medium} Medium</span>}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* MCP Summary */}
              {securityProfile?.mcp_summary && (
                <div className="bg-slate-800 rounded-2xl p-5 text-white">
                  <h4 className="text-sm font-bold text-slate-300 mb-2 uppercase tracking-wider">📝 MCP Summary</h4>
                  <p className="text-slate-100 leading-relaxed text-sm">{securityProfile.mcp_summary}</p>
                </div>
              )}

              {/* Recommendations */}
              {testPlan?.recommendations && testPlan.recommendations.length > 0 && (
                <div className="bg-white rounded-2xl border-2 border-indigo-200 p-5">
                  <h4 className="text-base font-bold text-indigo-700 mb-4">💡 Recommendations</h4>
                  <div className="space-y-3">
                    {testPlan.recommendations.map((rec: any, i: number) => (
                      <div key={i} className="flex items-start gap-3 p-3 bg-indigo-50 rounded-xl border border-indigo-200">
                        <span className={`mt-0.5 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                          rec.priority === "high" ? "bg-red-500 text-white" :
                          rec.priority === "medium" ? "bg-yellow-500 text-white" : "bg-blue-400 text-white"
                        }`}>{i + 1}</span>
                        <div>
                          <div className="font-semibold text-gray-800 text-sm">{rec.category?.replace(/_/g, " ")}</div>
                          <div className="text-xs text-gray-600 mt-0.5">{rec.reason}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Duration + cost footer */}
              <div className="flex gap-4 text-sm text-gray-500">
                {runData?.duration_ms && <span>⏱️ Duration: <b>{(runData.duration_ms / 1000).toFixed(1)}s</b></span>}
                {runData?.llm_cost_usd && <span>💰 LLM cost: <b>${Number(runData.llm_cost_usd).toFixed(4)}</b></span>}
                {runData?.created_at && <span>📅 {new Date(runData.created_at).toLocaleString()}</span>}
              </div>
            </>
          )}

          {/* ═══════════════════════════ SECURITY PROFILE ═══════════════════════════ */}
          {activeTab === "profile" && (
            <>
              {securityProfile ? (
                <>
                  {/* Summary paragraph */}
                  {(securityProfile.mcp_summary || securityProfile.overview) && (
                    <div className="bg-slate-800 rounded-2xl p-5 text-white">
                      <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">📝 MCP Summary</p>
                      <p className="text-slate-100 leading-relaxed text-sm">{securityProfile.mcp_summary || securityProfile.overview}</p>
                    </div>
                  )}

                  {/* Risk score + tool breakdown */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className={`bg-gradient-to-br ${riskColor(securityProfile.risk_score)} rounded-2xl p-6 text-white`}>
                      <div className="text-xs font-bold opacity-70 uppercase tracking-wider mb-2">Overall Risk Score</div>
                      <div className="text-6xl font-black">{securityProfile.risk_score}<span className="text-2xl opacity-60">/10</span></div>
                      <div className="text-sm font-bold mt-2 opacity-80">{riskLabel(securityProfile.risk_score)}</div>
                    </div>
                    {securityProfile.tool_summary && (
                      <div className="bg-white rounded-2xl border-2 border-gray-200 p-6">
                        <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-4">Tool Risk Breakdown</p>
                        {[
                          { label: "Total tools",  val: securityProfile.tool_summary.total,       color: "text-gray-800" },
                          { label: "High risk",    val: securityProfile.tool_summary.high_risk,   color: "text-red-600" },
                          { label: "Medium risk",  val: securityProfile.tool_summary.medium_risk, color: "text-yellow-600" },
                          { label: "Low risk",     val: securityProfile.tool_summary.low_risk,    color: "text-green-600" },
                        ].map(row => (
                          <div key={row.label} className="flex justify-between items-center py-1.5 border-b border-gray-100 last:border-0">
                            <span className="text-sm text-gray-600">{row.label}</span>
                            <span className={`font-bold text-lg ${row.color}`}>{row.val}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Weaknesses */}
                  {securityProfile.weaknesses?.length > 0 && (
                    <div className="bg-white rounded-2xl border-2 border-red-200 p-5">
                      <h5 className="font-bold text-red-700 mb-3 flex items-center gap-2">🔓 Identified Weaknesses</h5>
                      <div className="space-y-2">
                        {securityProfile.weaknesses.map((w: string, i: number) => (
                          <div key={i} className="flex items-start gap-2 p-3 bg-red-50 rounded-lg border border-red-100 text-sm text-gray-800">
                            <span className="text-red-400 font-bold mt-0.5">•</span>{w}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* High-risk tools */}
                  {(() => {
                    const tools = securityProfile.tool_summary?.high_risk_tools ?? securityProfile.high_risk_tools ?? [];
                    return tools.length > 0 ? (
                      <div className="bg-white rounded-2xl border-2 border-orange-200 p-5">
                        <h5 className="font-bold text-orange-600 mb-3 flex items-center gap-2">⚠️ High-Risk Tools</h5>
                        <div className="space-y-2">
                          {tools.map((t: string, i: number) => (
                            <div key={i} className="p-3 bg-orange-50 rounded-lg border border-orange-100 text-sm text-gray-800">🔧 {t}</div>
                          ))}
                        </div>
                      </div>
                    ) : null;
                  })()}

                  {/* Attack Vectors */}
                  {securityProfile.attack_vectors?.length > 0 && (
                    <div className="bg-white rounded-2xl border-2 border-orange-200 p-5">
                      <h5 className="font-bold text-orange-600 mb-3 flex items-center gap-2">🎯 Attack Vectors</h5>
                      <div className="space-y-3">
                        {securityProfile.attack_vectors.map((v: any, i: number) => (
                          <div key={i} className={`p-4 rounded-xl border-2 ${
                            v.severity === "critical" ? "bg-red-50 border-red-300" :
                            v.severity === "high"     ? "bg-orange-50 border-orange-300" :
                            v.severity === "medium"   ? "bg-yellow-50 border-yellow-300" : "bg-blue-50 border-blue-300"
                          }`}>
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-bold text-gray-900">{v.vector}</span>
                              <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${SEVERITY_STYLE[v.severity] ?? SEVERITY_STYLE.info}`}>
                                {v.severity?.toUpperCase()}
                              </span>
                            </div>
                            <p className="text-sm text-gray-700 mb-2">{v.description}</p>
                            {v.affected_tools?.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {v.affected_tools.map((t: string, j: number) => (
                                  <span key={j} className="px-2 py-0.5 bg-white rounded text-xs text-gray-600 border border-gray-300">{t}</span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Data Sensitivity */}
                  <div className="bg-white rounded-2xl border-2 border-purple-200 p-5">
                    <h5 className="font-bold text-purple-600 mb-4 flex items-center gap-2">🔐 Data Sensitivity</h5>
                    <div className="grid grid-cols-3 gap-3">
                      {[
                        { label: "PII",         val: securityProfile.data_sensitivity?.handles_pii },
                        { label: "Credentials", val: securityProfile.data_sensitivity?.handles_credentials },
                        { label: "Financial",   val: securityProfile.data_sensitivity?.handles_financial ?? securityProfile.data_sensitivity?.handles_system_access },
                      ].map(({ label, val }) => (
                        <div key={label} className={`p-4 rounded-xl text-center border-2 ${val ? "bg-red-50 border-red-300" : "bg-green-50 border-green-200"}`}>
                          <div className="text-2xl mb-1">{val ? "⚠️" : "✅"}</div>
                          <div className="font-bold text-gray-800 text-sm">{label}</div>
                          <div className={`text-xs mt-0.5 ${val ? "text-red-600 font-semibold" : "text-green-600"}`}>{val ? "Handles" : "Clean"}</div>
                        </div>
                      ))}
                    </div>
                    {securityProfile.data_sensitivity?.evidence?.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-purple-100 space-y-1">
                        {securityProfile.data_sensitivity.evidence.map((e: string, i: number) => (
                          <div key={i} className="text-xs text-gray-600 flex gap-1"><span>•</span>{e}</div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* LLM-Suggested Additional Tests */}
                  {securityProfile.suggested_additional_tests?.length > 0 && (
                    <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-2xl border-2 border-indigo-200 p-5">
                      <h5 className="font-bold text-indigo-700 mb-1 flex items-center gap-2">💡 LLM-Suggested Additional Tests</h5>
                      <p className="text-xs text-indigo-400 mb-4">Tests the AI identified as valuable but not included in this run</p>
                      <div className="space-y-2">
                        {securityProfile.suggested_additional_tests.map((s: any, i: number) => (
                          <div key={i} className="flex items-start gap-3 p-3 bg-white rounded-xl border border-indigo-200">
                            <span className="text-indigo-400 mt-0.5">→</span>
                            <div>
                              <span className="font-bold text-indigo-600 text-sm">{s.category}</span>
                              <span className="text-gray-400 mx-1 text-sm">/</span>
                              <span className="font-semibold text-gray-800 text-sm">{s.test}</span>
                              <p className="text-xs text-gray-500 mt-0.5">{s.reason}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <Empty icon="⏳" text="Security profile not available for this run." />
              )}
            </>
          )}

          {/* ═══════════════════════════ RESULTS ═══════════════════════════ */}
          {activeTab === "results" && (
            <>
              {/* Legend */}
              <div className="bg-blue-50 border-2 border-blue-200 rounded-xl p-4 text-sm text-blue-800">
                <span className="font-bold">How to read results:</span>
                {" "}<span className="font-bold text-red-600">FAIL</span> = the MCP did <em>not</em> enforce this security control (real finding).
                {" "}<span className="font-bold text-yellow-600">ERROR</span> = the test could not execute (protocol limitation, timeout, or missing method — not a security finding).
                {" "}<span className="font-bold text-green-600">PASS</span> = security control is working correctly.
              </div>

              {/* Filter */}
              <div className="flex gap-2">
                {[
                  { id: "all",   label: `All (${totalTests})`,    active: "bg-slate-700 text-white" },
                  { id: "fail",  label: `⛔ Fails (${totalFails})`, active: "bg-red-600 text-white" },
                  { id: "error", label: `⚠️ Errors (${totalErrors})`, active: "bg-yellow-500 text-white" },
                  { id: "pass",  label: `✅ Passed (${totalPass})`, active: "bg-green-600 text-white" },
                ].map(f => (
                  <button key={f.id}
                    onClick={() => setResultFilter(f.id as any)}
                    className={`px-4 py-2 rounded-xl text-sm font-bold transition-all ${
                      resultFilter === f.id ? f.active : "bg-white border-2 border-gray-200 text-gray-600 hover:border-gray-300"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>

              {/* Results list */}
              <div className="space-y-3">
                {filteredResults.length === 0 ? (
                  <Empty icon="🔍" text="No results match this filter." />
                ) : filteredResults.map((r, i) => (
                  <div key={i} className={`rounded-xl border-2 p-4 ${
                    r.status === "fail"  ? "bg-red-50 border-red-300" :
                    r.status === "error" ? "bg-yellow-50 border-yellow-300" : "bg-green-50 border-green-200"
                  }`}>
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-xs font-black px-2 py-1 rounded-lg ${
                          r.status === "fail"  ? "bg-red-600 text-white" :
                          r.status === "error" ? "bg-yellow-500 text-white" : "bg-green-600 text-white"
                        }`}>
                          {r.status === "fail" ? "✗ SECURITY FAIL" : r.status === "error" ? "⚠ TEST ERROR" : "✓ PASS"}
                        </span>
                        <span className="text-sm font-bold text-gray-800">
                          <span className="text-gray-400">{CATEGORY_ICON[r.category] ?? "🔧"} {r.category?.replace(/_/g, " ")} /</span>
                          {" "}{r.test_name?.replace(/_/g, " ")}
                        </span>
                        {r.tool_name && <span className="text-xs text-gray-500 bg-white border border-gray-200 px-2 py-0.5 rounded">{r.tool_name}</span>}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {r.status === "fail" && r.severity !== "info" && (
                          <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${SEVERITY_STYLE[r.severity] ?? SEVERITY_STYLE.info}`}>
                            {r.severity?.toUpperCase()}
                          </span>
                        )}
                        {r.latency_ms > 0 && <span className="text-xs text-gray-400">{r.latency_ms}ms</span>}
                      </div>
                    </div>
                    {/* Evidence */}
                    <p className="text-sm text-gray-700 leading-relaxed">{r.evidence}</p>
                    {/* Error message for errors */}
                    {r.status === "error" && r.error_message && r.error_message !== r.evidence && (
                      <p className="text-xs text-yellow-700 mt-1 font-mono bg-yellow-100 px-2 py-1 rounded">{r.error_message}</p>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}

          {/* ═══════════════════════════ TEST PLAN ═══════════════════════════ */}
          {activeTab === "plan" && (
            <>
              {planTests.length > 0 ? (
                <>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    <div className="bg-sky-50 border-2 border-sky-200 rounded-xl p-4 text-center">
                      <div className="text-3xl font-black text-sky-700">{planTests.length}</div>
                      <div className="text-xs font-bold text-sky-500 mt-1">Planned Tests</div>
                    </div>
                    <div className="bg-blue-50 border-2 border-blue-200 rounded-xl p-4 text-center">
                      <div className="text-3xl font-black text-blue-700">{testPlan?.selected_categories?.length ?? new Set(planTests.map((t: any) => t.category)).size}</div>
                      <div className="text-xs font-bold text-blue-500 mt-1">Categories</div>
                    </div>
                    <div className="bg-purple-50 border-2 border-purple-200 rounded-xl p-4 text-center">
                      <div className="text-3xl font-black text-purple-700">{runData?.llm_provider ?? "—"}</div>
                      <div className="text-xs font-bold text-purple-500 mt-1">LLM Provider</div>
                    </div>
                  </div>

                  {/* Tests grouped by category */}
                  {Array.from(new Set(planTests.map((t: any) => t.category))).map((cat: any) => (
                    <div key={cat} className="bg-white rounded-2xl border-2 border-gray-200 p-5">
                      <h5 className="font-bold text-gray-800 mb-3 flex items-center gap-2 text-sm uppercase tracking-wider">
                        <span>{CATEGORY_ICON[cat] ?? "🔧"}</span> {cat.replace(/_/g, " ")}
                        <span className="text-gray-400 font-normal normal-case tracking-normal">
                          ({planTests.filter((t: any) => t.category === cat).length} tests)
                        </span>
                      </h5>
                      <div className="space-y-2">
                        {planTests.filter((t: any) => t.category === cat).map((test: any, i: number) => (
                          <div key={i} className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-gray-800 text-sm">{test.test_name.replace(/_/g, " ")}</span>
                              {test.tool && <span className="text-xs text-gray-500 bg-white border border-gray-200 px-2 py-0.5 rounded">{test.tool}</span>}
                            </div>
                            {test.params && Object.keys(test.params).length > 0 && (
                              <details className="mt-2">
                                <summary className="text-xs text-sky-600 cursor-pointer select-none">View params</summary>
                                <pre className="mt-1 p-2 bg-white rounded text-xs overflow-x-auto text-gray-600 border border-gray-200">
                                  {JSON.stringify(test.params, null, 2)}
                                </pre>
                              </details>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </>
              ) : (
                <Empty icon="📋" text="Test plan not available for this run." />
              )}
            </>
          )}

          {/* ═══════════════════════════ DISCOVERY ═══════════════════════════ */}
          {activeTab === "discovery" && (
            <>
              {disc ? (
                <>
                  <div className="grid grid-cols-3 gap-4">
                    {[
                      { label: "Tools",     count: disc.tools_count,     color: "from-blue-500 to-blue-600" },
                      { label: "Prompts",   count: disc.prompts_count,   color: "from-purple-500 to-purple-600" },
                      { label: "Resources", count: disc.resources_count, color: "from-green-500 to-green-600" },
                    ].map(c => (
                      <div key={c.label} className={`bg-gradient-to-br ${c.color} rounded-xl p-5 text-white text-center`}>
                        <div className="text-4xl font-black">{c.count}</div>
                        <div className="text-sm opacity-80 mt-1">{c.label}</div>
                      </div>
                    ))}
                  </div>

                  {disc.tools.length > 0 && (
                    <div className="bg-white rounded-2xl border-2 border-blue-200 p-5">
                      <h5 className="font-bold text-gray-800 mb-3 flex items-center gap-2">🔧 Tools</h5>
                      <div className="space-y-2">
                        {disc.tools.map((tool: any, i: number) => (
                          <div key={i} className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                            <div className="font-semibold text-gray-900 text-sm">{tool.name}</div>
                            <div className="text-xs text-gray-600 mt-0.5">{tool.description}</div>
                            {tool.inputSchema && (
                              <details className="mt-2">
                                <summary className="text-xs text-blue-600 cursor-pointer select-none">Schema</summary>
                                <pre className="mt-1 p-2 bg-white rounded text-xs overflow-x-auto border border-blue-100">
                                  {JSON.stringify(tool.inputSchema, null, 2)}
                                </pre>
                              </details>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {disc.prompts.length > 0 && (
                    <div className="bg-white rounded-2xl border-2 border-purple-200 p-5">
                      <h5 className="font-bold text-gray-800 mb-3 flex items-center gap-2">💬 Prompts</h5>
                      {disc.prompts.map((p: any, i: number) => (
                        <div key={i} className="p-3 bg-purple-50 rounded-lg border border-purple-200 mb-2">
                          <div className="font-semibold text-gray-900 text-sm">{p.name}</div>
                          <div className="text-xs text-gray-600">{p.description}</div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <Empty icon="🔍" text="Discovery data expired or not available." />
              )}
            </>
          )}

          {/* ═══════════════════════════ RED TEAM ═══════════════════════════ */}
          {activeTab === "redteam" && (
            <>
              {agentStoryCount === 0 ? (
                <div className="text-center py-16 text-gray-400">
                  <div className="text-5xl mb-3">🤖</div>
                  <p className="font-semibold text-gray-500 mb-2">No AI Red Team stories for this run</p>
                  <p className="text-sm text-gray-400">
                    Re-run with the <span className="font-mono bg-gray-100 px-1 rounded">ai_red_team</span> category selected to generate attack scenarios.
                  </p>
                </div>
              ) : (
                <AIRedTeamResults runId={runId} />
              )}
            </>
          )}

        </div>
      </div>
    </div>
  );
}

function Empty({ icon, text }: { icon: string; text: string }) {
  return (
    <div className="text-center py-16 text-gray-400">
      <div className="text-5xl mb-3">{icon}</div>
      <p className="font-medium">{text}</p>
    </div>
  );
}
