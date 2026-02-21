"use client";

import { useState, useEffect } from "react";
import { omni2Api } from "@/lib/omni2Api";
import PTRunDetails from "./PTRunDetails";
import AIRedTeamResults from "./AIRedTeamResults";
import MCPPTAboutTab from "./MCPPTAboutTab";

interface PTRun {
  run_id: number;
  mcp_name: string;
  preset: string;
  status: string;
  total_tests: number;
  passed: number;
  failed: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  duration_ms: number;
  created_at: string;
  completed_at?: string;
  plan_source?: string;  // 'llm' | 'cached' | 'template'
  llm_provider?: string;
}

interface PTCategory {
  category_id: number;
  name: string;
  description: string;
  enabled: boolean;
}

interface PTPreset {
  preset_id: number;
  name: string;
  description: string;
  max_parallel: number;
  timeout_seconds: number;
}

interface MCP {
  id: number;
  name: string;
  url: string;
  health_status: string;
}

export default function MCPPTDashboard() {
  const [mcps, setMcps] = useState<MCP[]>([]);
  const [categories, setCategories] = useState<PTCategory[]>([]);
  const [presets, setPresets] = useState<PTPreset[]>([]);
  const [runs, setRuns] = useState<PTRun[]>([]);
  const [selectedMcp, setSelectedMcp] = useState<string>("");
  const [selectedPreset, setSelectedPreset] = useState<string>("quick");
  const [selectedCategories, setSelectedCategories] = useState<string[]>([]);
  const [configMode, setConfigMode] = useState<"preset" | "advanced">("preset");
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [activeTab, setActiveTab] = useState<"run" | "history" | "compare" | "config" | "about">("run");
  const [aiRedTeamConfig, setAiRedTeamConfig] = useState<any>(null);
  const [aiRedTeamProviders, setAiRedTeamProviders] = useState<Record<string, any>>({});
  const [savingAiConfig, setSavingAiConfig] = useState(false);
  const [selectedMcpFilter, setSelectedMcpFilter] = useState<string>("");
  const [compareRun1, setCompareRun1] = useState<number | null>(null);
  const [compareRun2, setCompareRun2] = useState<number | null>(null);
  const [comparisonResult, setComparisonResult] = useState<any>(null);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [selectedRunIds, setSelectedRunIds] = useState<Set<number>>(new Set());
  const [testCatalog, setTestCatalog] = useState<Record<string, any>>({});
  const [configSearch, setConfigSearch] = useState<string>("");
  const [activeRunId, setActiveRunId] = useState<number | null>(null);
  const [activeRunData, setActiveRunData] = useState<any>(null);
  const [llmOptions, setLlmOptions] = useState<{ providers: Record<string, { models: string[]; default_model: string }>; default_provider: string } | null>(null);
  const [selectedLlmProvider, setSelectedLlmProvider] = useState<string>("");
  const [selectedLlmModel, setSelectedLlmModel] = useState<string>("");
  const [liveResults, setLiveResults] = useState<any[]>([]);
  const [templateMode, setTemplateMode] = useState<boolean>(false);
  const [forceRegenerate, setForceRegenerate] = useState<boolean>(false);
  const [cancelling, setCancelling] = useState<boolean>(false);

  const PT_STAGES = [
    { key: "initialization", label: "Initializing", icon: "⚙️", desc: "Creating PT run" },
    { key: "health_check", label: "MCP Explorer", icon: "🔍", desc: "Discovering tools & capabilities" },
    { key: "llm_analysis", label: "LLM Analysis", icon: "🧠", desc: "Analyzing security profile & building test plan" },
    { key: "test_execution", label: "Test Execution", icon: "⚡", desc: "Running security tests in parallel" },
    { key: "ai_red_team", label: "AI Red Team", icon: "🤖", desc: "Agentic attacker probing MCP" },
    { key: "completed", label: "Complete", icon: "✅", desc: "PT run finished" },
  ];

  useEffect(() => {
    loadData();
  }, []);

  // Only poll when there are active runs
  useEffect(() => {
    const hasActiveRuns = runs.some(r => r.status === 'running' || r.status === 'pending');
    if (hasActiveRuns) {
      const interval = setInterval(loadRuns, 5000);
      return () => clearInterval(interval);
    }
  }, [runs]);

  // Poll active run stage every 2s for live step tracking + inline results
  useEffect(() => {
    if (!activeRunId) return;
    const poll = async () => {
      try {
        const response = await omni2Api.get(`/api/v1/mcp-pt/runs/${activeRunId}`);
        const data = response.data;
        setActiveRunData(data);

        // Fetch live test results during execution or on completion
        if (data.current_stage === 'test_execution' || data.status === 'completed') {
          try {
            const resultsRes = await omni2Api.get(`/api/v1/mcp-pt/runs/${activeRunId}/results`);
            if (Array.isArray(resultsRes.data)) setLiveResults(resultsRes.data);
          } catch (_) {}
        }

        if (['completed', 'failed', 'cancelled'].includes(data.status)) {
          setActiveRunId(null);
          setCancelling(false);
          loadRuns();
        }
      } catch (e) {
        console.error("Failed to poll run status", e);
      }
    };
    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [activeRunId]);

  const loadData = async () => {
    try {
      const [mcpsRes, categoriesRes, presetsRes, runsRes, llmRes, testsRes, aiCfgRes] = await Promise.all([
        omni2Api.get("/api/v1/mcp-pt/mcps"),
        omni2Api.get("/api/v1/mcp-pt/categories"),
        omni2Api.get("/api/v1/mcp-pt/presets"),
        omni2Api.get("/api/v1/mcp-pt/runs?limit=20"),
        omni2Api.get("/api/v1/mcp-pt/llm-options").catch(() => ({ data: null })),
        omni2Api.get("/api/v1/mcp-pt/tests").catch(() => ({ data: {} })),
        omni2Api.get("/api/v1/mcp-pt/ai-red-team-config").catch(() => ({ data: null })),
      ]);

      setMcps(Array.isArray(mcpsRes.data) ? mcpsRes.data : []);
      setCategories(Array.isArray(categoriesRes.data) ? categoriesRes.data : []);
      setPresets(Array.isArray(presetsRes.data) ? presetsRes.data : []);
      setRuns(Array.isArray(runsRes.data) ? runsRes.data : []);
      if (testsRes.data && typeof testsRes.data === "object") setTestCatalog(testsRes.data);

      if (llmRes.data?.providers) {
        setLlmOptions(llmRes.data);
        const defaultProvider = llmRes.data.default_provider || Object.keys(llmRes.data.providers)[0] || "";
        setSelectedLlmProvider(defaultProvider);
        setSelectedLlmModel(llmRes.data.providers[defaultProvider]?.default_model || "");
      }
      if (aiCfgRes.data) {
        setAiRedTeamConfig(aiCfgRes.data.config);
        setAiRedTeamProviders(aiCfgRes.data.providers || {});
      }
    } catch (error) {
      console.error("Failed to load data", error);
      setMcps([]);
      setCategories([]);
      setPresets([]);
      setRuns([]);
    } finally {
      setLoading(false);
    }
  };

  const loadRuns = async () => {
    try {
      const response = await omni2Api.get("/api/v1/mcp-pt/runs?limit=20");
      setRuns(response.data);
    } catch (error) {
      console.error("Failed to load runs", error);
    }
  };

  const deleteSelectedRuns = async () => {
    if (selectedRunIds.size === 0) return;
    const ids = Array.from(selectedRunIds);
    let failed = 0;
    for (const id of ids) {
      try {
        await omni2Api.delete(`/api/v1/mcp-pt/runs/${id}`);
      } catch {
        failed++;
      }
    }
    setSelectedRunIds(new Set());
    await loadRuns();
    if (failed > 0) alert(`${failed} run(s) could not be deleted (they may still be in progress).`);
  };

  const cancelRun = async (runId: number) => {
    if (cancelling) return;
    setCancelling(true);
    try {
      await omni2Api.post(`/api/v1/mcp-pt/runs/${runId}/cancel`, {});
    } catch (e) {
      console.error("Failed to cancel run", e);
      setCancelling(false);
    }
  };

  const compareRuns = async () => {
    if (!compareRun1 || !compareRun2) return;
    try {
      const response = await omni2Api.post("/api/v1/mcp-pt/compare", {
        run_id_1: compareRun1,
        run_id_2: compareRun2,
      });
      setComparisonResult(response.data);
    } catch (error) {
      console.error("Failed to compare runs", error);
    }
  };

  const filteredRuns = selectedMcpFilter
    ? runs.filter((r) => r.mcp_name === selectedMcpFilter)
    : runs;

  const mcpNames = Array.from(new Set(runs.map((r) => r.mcp_name)));

  const startPTRun = async () => {
    if (!selectedMcp) return;

    setRunning(true);
    setActiveRunData(null);
    setLiveResults([]);
    try {
      const response = await omni2Api.post("/api/v1/mcp-pt/run", {
        mcp_id: selectedMcp,
        preset: configMode === "preset" ? selectedPreset : "custom",
        categories: configMode === "advanced" ? selectedCategories : undefined,
        created_by: 1, // TODO: Get from auth
        llm_provider: templateMode ? undefined : (selectedLlmProvider || undefined),
        llm_model: templateMode ? undefined : (selectedLlmModel || undefined),
        template_mode: templateMode,
        force_regenerate: !templateMode && forceRegenerate,
      });
      const runId = response.data?.run_id;
      if (runId) {
        setActiveRunId(runId);
        setActiveRunData({ run_id: runId, status: "pending", current_stage: "initialization" });
      }
      setTimeout(loadRuns, 2000);
    } catch (error: any) {
      console.error("Failed to start PT run", error);
      alert(error.response?.data?.detail || "Failed to start PT run");
    } finally {
      setRunning(false);
    }
  };

  const getPlanSourceBadge = (planSource: string | undefined, llmProvider?: string) => {
    const src = planSource || (llmProvider === 'template' ? 'template' : 'llm');
    if (src === 'template') return { label: "⚙️ Deterministic", cls: "bg-indigo-100 text-indigo-700" };
    if (src === 'cached')   return { label: "📋 Cached Plan",   cls: "bg-purple-100 text-purple-700" };
    return                         { label: "🧠 LLM",           cls: "bg-sky-100 text-sky-700" };
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      pending: "bg-gray-100 text-gray-800",
      running: "bg-blue-100 text-blue-800 animate-pulse",
      completed: "bg-green-100 text-green-800",
      failed: "bg-red-100 text-red-800",
    };
    return styles[status as keyof typeof styles] || styles.pending;
  };

  const getPresetIcon = (preset: string) => {
    const icons = { fast: "⚡", quick: "🎯", deep: "🔍" };
    return icons[preset as keyof typeof icons] || "🎯";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-sky-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-3">
            <div className="w-16 h-16 bg-gradient-to-br from-sky-500 via-blue-500 to-cyan-500 rounded-2xl flex items-center justify-center shadow-2xl">
              <span className="text-3xl">🛡️</span>
            </div>
            <div>
              <h1 className="text-4xl font-black bg-gradient-to-r from-sky-500 via-blue-500 to-cyan-500 bg-clip-text text-transparent">
                MCP Penetration Testing
              </h1>
              <p className="text-gray-600 font-medium">AI-Powered Security Testing with LLM Planning</p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: "run", label: "🚀 Run PT" },
            { id: "history", label: "📊 History" },
            { id: "compare", label: "🔄 Compare" },
            { id: "config", label: "⚙️ Config" },
            { id: "about", label: "💡 How it Works" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-6 py-3 rounded-xl font-bold transition-all ${
                activeTab === tab.id
                  ? "bg-gradient-to-r from-sky-500 to-pink-600 text-white shadow-lg scale-105"
                  : "bg-white text-gray-700 hover:bg-gray-50 shadow"
              }`}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Run PT Tab */}
        {activeTab === "run" && (
          <>
          {/* Live Stage Tracker */}
          {activeRunData && (
            <div className={`mb-6 rounded-2xl shadow-xl p-6 border-2 ${
              activeRunData.status === 'failed'     ? 'bg-red-50 border-red-300'   :
              activeRunData.status === 'completed'  ? 'bg-green-50 border-green-300' :
              activeRunData.status === 'cancelled'  ? 'bg-gray-50 border-gray-300' :
              activeRunData.status === 'cancelling' ? 'bg-orange-50 border-orange-300' :
              'bg-gradient-to-r from-sky-50 to-blue-50 border-sky-200'
            }`}>
              <div className="flex items-center justify-between mb-5">
                <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                  {activeRunData.status === 'failed'     ? '❌' :
                   activeRunData.status === 'completed'  ? '✅' :
                   activeRunData.status === 'cancelled'  ? '🚫' :
                   activeRunData.status === 'cancelling' ? <span className="animate-pulse inline-block">⏹️</span> :
                   <span className="animate-spin inline-block">⚙️</span>}
                  PT Run #{activeRunData.run_id} — {activeRunData.mcp_name || selectedMcp}
                </h3>
                <div className="flex items-center gap-2">
                  {activeRunData.status === 'failed' && (
                    <span className="px-3 py-1 bg-red-100 text-red-700 rounded-full text-xs font-bold">FAILED</span>
                  )}
                  {activeRunData.status === 'completed' && (
                    <span className="px-3 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold">COMPLETED</span>
                  )}
                  {activeRunData.status === 'cancelled' && (
                    <span className="px-3 py-1 bg-gray-200 text-gray-600 rounded-full text-xs font-bold">CANCELLED</span>
                  )}
                  {activeRunData.status === 'cancelling' && (
                    <span className="px-3 py-1 bg-orange-100 text-orange-700 rounded-full text-xs font-bold animate-pulse">STOPPING…</span>
                  )}
                  {/* Abort button — visible while run is active */}
                  {['running', 'pending'].includes(activeRunData.status) && (
                    <button
                      onClick={() => cancelRun(activeRunData.run_id)}
                      disabled={cancelling}
                      className="px-4 py-1.5 bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white text-xs font-bold rounded-lg flex items-center gap-1.5 transition-colors"
                      title="Stop the run after current tests finish"
                    >
                      {cancelling ? <span className="animate-spin">⏳</span> : '⏹'}
                      {cancelling ? 'Stopping…' : 'Abort Run'}
                    </button>
                  )}
                </div>
              </div>

              {/* Steps */}
              <div className="flex items-start gap-0">
                {PT_STAGES.map((stage, idx) => {
                  const isTemplateRun = activeRunData.plan_source === 'template' || activeRunData.llm_provider === 'template';
                  const isCachedRun = activeRunData.plan_source === 'cached';
                  const currentIdx = activeRunData.status === 'failed'
                    ? PT_STAGES.findIndex(s => s.key === (activeRunData.current_stage || 'initialization'))
                    : activeRunData.status === 'completed'
                    ? PT_STAGES.length
                    : PT_STAGES.findIndex(s => s.key === (activeRunData.current_stage || 'initialization'));
                  const isCompleted = idx < currentIdx;
                  const isActive = idx === currentIdx && activeRunData.status !== 'completed' && activeRunData.status !== 'failed';
                  const isFailed = activeRunData.status === 'failed' && idx === currentIdx;
                  // LLM stage special states
                  const isLlmStage = stage.key === 'llm_analysis';
                  const isSkipped = isLlmStage && isTemplateRun;
                  const isCached  = isLlmStage && isCachedRun && isCompleted;

                  return (
                    <div key={stage.key} className="flex-1 flex flex-col items-center relative">
                      {/* Connector line */}
                      {idx < PT_STAGES.length - 1 && (
                        <div className={`absolute top-5 left-1/2 w-full h-0.5 ${isCompleted ? 'bg-green-400' : 'bg-gray-200'}`} style={{left: '50%'}} />
                      )}
                      {/* Circle */}
                      <div className={`relative z-10 w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold border-2 transition-all ${
                        isSkipped  ? 'bg-gray-100 border-gray-300 text-gray-400'
                        : isCached  ? 'bg-purple-500 border-purple-500 text-white'
                        : isFailed  ? 'bg-red-100 border-red-500 text-red-600'
                        : isCompleted ? 'bg-green-500 border-green-500 text-white'
                        : isActive ? 'bg-sky-500 border-sky-500 text-white animate-pulse'
                        : 'bg-white border-gray-300 text-gray-400'
                      }`}>
                        {isSkipped ? '⏭' : isCached ? '📋' : isFailed ? '✗' : isCompleted ? '✓' : stage.icon}
                      </div>
                      {/* Label */}
                      <div className="mt-2 text-center">
                        <p className={`text-xs font-bold ${
                          isSkipped ? 'text-gray-400' : isCached ? 'text-purple-600'
                          : isActive ? 'text-sky-700' : isCompleted ? 'text-green-700'
                          : isFailed ? 'text-red-600' : 'text-gray-400'
                        }`}>
                          {isSkipped ? 'Skipped' : isCached ? 'Cached' : stage.label}
                        </p>
                        {isActive && (
                          <p className="text-xs text-gray-500 mt-1 max-w-[100px]">
                            {activeRunData.stage_details?.message || stage.desc}
                          </p>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Test execution progress + live results */}
              {(activeRunData.current_stage === 'test_execution' || (activeRunData.status === 'completed' && liveResults.length > 0)) && (
                <div className="mt-4 pt-4 border-t border-sky-200">
                  {activeRunData.current_stage === 'test_execution' && activeRunData.status !== 'completed' && (
                    <div className="flex items-center gap-3 mb-3">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-sky-600 flex-shrink-0"></div>
                      <p className="text-sm text-sky-700 font-medium">
                        {liveResults.length > 0
                          ? `${liveResults.length} test${liveResults.length > 1 ? 's' : ''} completed...`
                          : "Running security tests in parallel..."}
                      </p>
                    </div>
                  )}
                  {liveResults.length > 0 && (
                    <div className="max-h-64 overflow-y-auto rounded-xl border border-gray-200 bg-white">
                      <table className="w-full text-xs">
                        <thead className="bg-gray-50 sticky top-0">
                          <tr>
                            <th className="px-3 py-2 text-left font-bold text-gray-600">Status</th>
                            <th className="px-3 py-2 text-left font-bold text-gray-600">Category</th>
                            <th className="px-3 py-2 text-left font-bold text-gray-600">Test</th>
                            <th className="px-3 py-2 text-left font-bold text-gray-600">Severity</th>
                            <th className="px-3 py-2 text-left font-bold text-gray-600">ms</th>
                          </tr>
                        </thead>
                        <tbody>
                          {liveResults.map((r, idx) => (
                            <tr key={idx} className={`border-t border-gray-100 ${r.status === 'fail' ? 'bg-red-50' : r.status === 'error' ? 'bg-yellow-50' : ''}`}>
                              <td className="px-3 py-1.5 font-bold">
                                {r.status === 'pass' ? <span className="text-green-600">✓ PASS</span>
                                  : r.status === 'fail' ? <span className="text-red-600">✗ FAIL</span>
                                  : <span className="text-yellow-600">⚠ ERR</span>}
                              </td>
                              <td className="px-3 py-1.5 text-gray-600">{r.category?.replace(/_/g, ' ')}</td>
                              <td className="px-3 py-1.5 text-gray-800 font-medium">{r.test_name?.replace(/_/g, ' ')}</td>
                              <td className="px-3 py-1.5">
                                {r.status === 'fail' && (
                                  <span className={`px-2 py-0.5 rounded-full font-bold text-white ${
                                    r.severity === 'critical' ? 'bg-red-600'
                                    : r.severity === 'high' ? 'bg-orange-500'
                                    : r.severity === 'medium' ? 'bg-yellow-500'
                                    : 'bg-blue-400'
                                  }`}>{r.severity}</span>
                                )}
                              </td>
                              <td className="px-3 py-1.5 text-gray-400">{r.latency_ms}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* Completion summary */}
              {activeRunData.status === 'completed' && activeRunData.total_tests > 0 && (
                <div className="mt-4 pt-4 border-t border-green-200 flex gap-4">
                  <span className="px-3 py-1 bg-white border border-gray-200 rounded-lg text-sm font-bold">{activeRunData.total_tests} tests</span>
                  <span className="px-3 py-1 bg-green-100 text-green-700 rounded-lg text-sm font-bold">✓ {activeRunData.passed} passed</span>
                  {activeRunData.failed > 0 && <span className="px-3 py-1 bg-red-100 text-red-700 rounded-lg text-sm font-bold">✗ {activeRunData.failed} failed</span>}
                  {activeRunData.critical > 0 && <span className="px-3 py-1 bg-red-600 text-white rounded-lg text-sm font-bold">🔴 {activeRunData.critical} critical</span>}
                </div>
              )}

              {/* AI Red Team Results */}
              {activeRunData.status === 'completed' && (
                <div className="mt-4 pt-4 border-t border-purple-200">
                  <AIRedTeamResults runId={activeRunData.run_id} />
                </div>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Start PT Panel */}
            <div className="lg:col-span-1">
              <div className="bg-white rounded-2xl shadow-xl p-6 border-2 border-sky-100">
                <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                  <span>🎯</span> Start New PT Run
                </h3>

                {/* Mode Toggle */}
                <div className="mb-6 flex gap-2 p-1 bg-gray-100 rounded-xl">
                  <button
                    onClick={() => setConfigMode("preset")}
                    className={`flex-1 px-4 py-2 rounded-lg font-bold text-sm transition-all ${
                      configMode === "preset"
                        ? "bg-white text-sky-600 shadow"
                        : "text-gray-600 hover:text-gray-900"
                    }`}
                  >
                    🎯 Preset Mode
                  </button>
                  <button
                    onClick={() => setConfigMode("advanced")}
                    className={`flex-1 px-4 py-2 rounded-lg font-bold text-sm transition-all ${
                      configMode === "advanced"
                        ? "bg-white text-sky-600 shadow"
                        : "text-gray-600 hover:text-gray-900"
                    }`}
                  >
                    ⚙️ Advanced
                  </button>
                </div>

                {/* Select MCP */}
                <div className="mb-6">
                  <label className="block text-sm font-bold text-gray-700 mb-2">
                    Select MCP Server
                  </label>
                  <select
                    value={selectedMcp}
                    onChange={(e) => setSelectedMcp(e.target.value)}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-sky-500 focus:outline-none font-medium"
                  >
                    <option value="">Choose MCP ({mcps.length} available)...</option>
                    {Array.isArray(mcps) && mcps.map((mcp) => (
                      <option key={mcp.name} value={mcp.name}>
                        {mcp.health_status === 'healthy' ? '🟢' : mcp.health_status === 'unhealthy' ? '🟡' : '⚪'} {mcp.name}
                      </option>
                    ))}
                  </select>
                  {selectedMcp && mcps.find(m => m.name === selectedMcp)?.health_status !== 'healthy' && (
                    <p className="mt-1.5 text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-1.5">
                      ⚠️ This server's last health check was unhealthy — PT will attempt to connect anyway.
                    </p>
                  )}
                </div>

                {/* Plan Mode Toggle */}
                <div className="mb-6">
                  <label className="block text-sm font-bold text-gray-700 mb-2">Plan Mode</label>
                  <div className="flex gap-2 p-1 bg-gray-100 rounded-xl">
                    <button
                      onClick={() => setTemplateMode(false)}
                      className={`flex-1 px-3 py-2 rounded-lg font-bold text-sm transition-all ${
                        !templateMode ? "bg-white text-sky-600 shadow" : "text-gray-600 hover:text-gray-900"
                      }`}
                    >
                      🧠 LLM
                    </button>
                    <button
                      onClick={() => { setTemplateMode(true); setForceRegenerate(false); }}
                      className={`flex-1 px-3 py-2 rounded-lg font-bold text-sm transition-all ${
                        templateMode ? "bg-white text-indigo-600 shadow" : "text-gray-600 hover:text-gray-900"
                      }`}
                    >
                      ⚙️ Deterministic
                    </button>
                  </div>
                  {templateMode ? (
                    <p className="mt-2 text-xs text-indigo-600 bg-indigo-50 rounded-lg px-3 py-2">
                      Runs all tests against all tools — no LLM, zero AI cost, fully deterministic.
                    </p>
                  ) : (
                    <label className="flex items-center gap-2 mt-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={forceRegenerate}
                        onChange={e => setForceRegenerate(e.target.checked)}
                        className="w-4 h-4 text-sky-600 rounded"
                      />
                      <span className="text-xs text-gray-600">
                        ♻️ Force regenerate <span className="text-gray-400">(bypass cache)</span>
                      </span>
                    </label>
                  )}
                </div>

                {/* LLM Selection — hidden in deterministic mode */}
                {!templateMode && llmOptions && Object.keys(llmOptions.providers).length > 0 && (
                  <div className="mb-6 p-4 bg-gray-50 rounded-xl border border-gray-200">
                    <label className="block text-sm font-bold text-gray-700 mb-3">🧠 LLM Model</label>
                    <div className="flex gap-2 mb-2">
                      {Object.keys(llmOptions.providers).map((provider) => (
                        <button
                          key={provider}
                          onClick={() => {
                            setSelectedLlmProvider(provider);
                            setSelectedLlmModel(llmOptions.providers[provider].default_model);
                          }}
                          className={`flex-1 px-3 py-2 rounded-lg text-xs font-bold capitalize border transition-all ${
                            selectedLlmProvider === provider
                              ? "bg-sky-500 text-white border-sky-500"
                              : "bg-white text-gray-600 border-gray-300 hover:border-sky-400"
                          }`}
                        >
                          {provider === "anthropic" ? "🤖 Anthropic" : provider === "groq" ? "⚡ Groq" : "✨ Gemini"}
                        </button>
                      ))}
                    </div>
                    {selectedLlmProvider && llmOptions.providers[selectedLlmProvider] && (
                      <select
                        value={selectedLlmModel}
                        onChange={(e) => setSelectedLlmModel(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:border-sky-500 focus:outline-none"
                      >
                        {llmOptions.providers[selectedLlmProvider].models.map((m) => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </select>
                    )}
                  </div>
                )}

                {/* Select Preset */}
                {configMode === "preset" && (
                <div className="mb-6">
                  <label className="block text-sm font-bold text-gray-700 mb-2">
                    Test Preset
                  </label>
                  <p className="text-xs text-gray-600 mb-3">Presets automatically select test categories for you</p>
                  <div className="space-y-2">
                    {presets?.map((preset) => (
                      <label
                        key={preset.name}
                        className={`flex items-center gap-3 p-4 border-2 rounded-xl cursor-pointer transition-all ${
                          selectedPreset === preset.name
                            ? "bg-sky-50 border-sky-400 shadow-md"
                            : "border-gray-200 hover:bg-gray-50"
                        }`}
                      >
                        <input
                          type="radio"
                          name="preset"
                          value={preset.name}
                          checked={selectedPreset === preset.name}
                          onChange={(e) => setSelectedPreset(e.target.value)}
                          className="w-5 h-5 text-sky-600"
                        />
                        <div className="flex-1">
                          <div className="flex items-center gap-2">
                            <span className="text-2xl">{getPresetIcon(preset.name)}</span>
                            <span className="font-bold text-gray-900 capitalize">{preset.name}</span>
                          </div>
                          <p className="text-xs text-gray-600 mt-1">{preset.description}</p>
                          <div className="flex gap-3 mt-2 text-xs text-gray-500">
                            <span>⚡ {preset.max_parallel} parallel</span>
                            <span>⏱️ {preset.timeout_seconds}s timeout</span>
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
                )}

                {/* Start Button */}
                <button
                  onClick={startPTRun}
                  disabled={!selectedMcp || running || (configMode === "advanced" && selectedCategories.length === 0)}
                  className="w-full px-6 py-4 bg-gradient-to-r from-sky-500 via-blue-500 to-cyan-500 hover:from-sky-600 hover:via-blue-600 hover:to-cyan-600 text-white font-bold rounded-xl shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {running ? "🔄 Starting..." : "🚀 Start PT Run"}
                </button>
                {configMode === "advanced" && selectedCategories.length === 0 && (
                  <p className="mt-2 text-xs text-red-600 text-center">Select at least one category</p>
                )}
              </div>

              {/* Categories Selection */}
              {configMode === "advanced" && (
              <div className="mt-6 bg-white rounded-2xl shadow-xl p-6 border-2 border-blue-100">
                <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <span>📋</span> Test Categories
                </h3>
                <p className="text-xs text-gray-600 mb-3">Select specific categories to test</p>
                <div className="space-y-2">
                  {categories?.map((cat) => (
                    <label key={cat.name} className="flex items-center gap-3 p-2 hover:bg-gray-50 rounded-lg cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedCategories.includes(cat.name)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedCategories([...selectedCategories, cat.name]);
                          } else {
                            setSelectedCategories(selectedCategories.filter(c => c !== cat.name));
                          }
                        }}
                        className="w-4 h-4 text-sky-600 rounded"
                      />
                      <span className="font-medium text-gray-700 text-sm">{cat.name.replace(/_/g, " ")}</span>
                    </label>
                  ))}
                </div>
                {selectedCategories.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <p className="text-xs text-sky-600 font-medium">{selectedCategories.length} categories selected</p>
                  </div>
                )}
              </div>
              )}

              {/* Test Plan Preview */}
              {selectedMcp && (
              <div className="mt-6 bg-gradient-to-br from-sky-50 to-blue-50 rounded-2xl shadow-xl p-6 border-2 border-sky-200">
                <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                  <span>📊</span> Test Plan Preview
                </h3>
                {configMode === "preset" ? (
                  <div>
                    <p className="text-sm text-gray-700 mb-3">
                      <span className="font-bold">{selectedPreset.charAt(0).toUpperCase() + selectedPreset.slice(1)}</span> preset will test:
                    </p>
                    <div className="space-y-2">
                      {presets.find(p => p.name === selectedPreset)?.categories?.map((cat: string) => (
                        <div key={cat} className="flex items-center gap-2 text-sm">
                          <span className="text-green-600">✓</span>
                          <span className="font-medium text-gray-800">{cat.replace(/_/g, " ")}</span>
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 pt-4 border-t border-sky-200">
                      <p className="text-xs text-gray-600">
                        ⚡ {presets.find(p => p.name === selectedPreset)?.max_parallel} parallel tests
                        • ⏱️ {presets.find(p => p.name === selectedPreset)?.timeout_seconds}s timeout
                      </p>
                    </div>
                  </div>
                ) : (
                  <div>
                    {selectedCategories.length > 0 ? (
                      <div className="space-y-2">
                        {selectedCategories.map(cat => (
                          <div key={cat} className="flex items-center gap-2 text-sm">
                            <span className="text-green-600">✓</span>
                            <span className="font-medium text-gray-800">{cat.replace(/_/g, " ")}</span>
                          </div>
                        ))}
                        <div className="mt-4 pt-4 border-t border-sky-200">
                          <p className="text-xs text-gray-600">
                            {selectedCategories.length} categories selected
                          </p>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-gray-500 italic">Select categories to see preview</p>
                    )}
                  </div>
                )}
              </div>
              )}
            </div>

            {/* Recent Runs */}
            <div className="lg:col-span-2">
              <div className="bg-white rounded-2xl shadow-xl p-6 border-2 border-green-100">
                <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                  <span>📊</span> Recent PT Runs
                </h3>

                <div className="space-y-4">
                  {runs.length === 0 ? (
                    <div className="text-center py-12 text-gray-500">
                      <span className="text-6xl mb-4 block">🎯</span>
                      <p className="font-medium">No PT runs yet. Start your first scan!</p>
                    </div>
                  ) : (
                    runs.slice(0, 10).map((run) => {
                      const planBadge = getPlanSourceBadge(run.plan_source, run.llm_provider);
                      return (
                      <div
                        key={run.run_id}
                        className="p-5 border-2 border-gray-200 rounded-xl hover:shadow-lg transition-all cursor-pointer"
                        onClick={() => setSelectedRunId(run.run_id)}
                      >
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-3">
                            <span className="text-2xl">{getPresetIcon(run.preset)}</span>
                            <div>
                              <div className="flex items-center gap-2">
                                <h4 className="font-bold text-gray-900">{run.mcp_name}</h4>
                                <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${planBadge.cls}`}>{planBadge.label}</span>
                              </div>
                              <p className="text-xs text-gray-500">
                                {new Date(run.created_at).toLocaleString()}
                              </p>
                            </div>
                          </div>
                          <span className={`px-4 py-2 rounded-lg text-sm font-bold ${getStatusBadge(run.status)}`}>
                            {run.status?.toUpperCase() || 'PENDING'}
                          </span>
                        </div>

                        {run.status === "completed" && (
                          <>
                            {/* Test Results */}
                            <div className="grid grid-cols-4 gap-3 mb-3">
                              <div className="text-center p-3 bg-gray-50 rounded-lg">
                                <div className="text-2xl font-bold text-gray-900">{run.total_tests}</div>
                                <div className="text-xs text-gray-600">Total</div>
                              </div>
                              <div className="text-center p-3 bg-green-50 rounded-lg">
                                <div className="text-2xl font-bold text-green-600">{run.passed}</div>
                                <div className="text-xs text-green-600">Passed</div>
                              </div>
                              <div className="text-center p-3 bg-red-50 rounded-lg">
                                <div className="text-2xl font-bold text-red-600">{run.failed}</div>
                                <div className="text-xs text-red-600">Failed</div>
                              </div>
                              <div className="text-center p-3 bg-blue-50 rounded-lg">
                                <div className="text-2xl font-bold text-blue-600">{Math.round(run.duration_ms / 1000)}s</div>
                                <div className="text-xs text-blue-600">Duration</div>
                              </div>
                            </div>

                            {/* Severity Badges */}
                            {(run.critical + run.high + run.medium + run.low) > 0 && (
                              <div className="flex gap-2 flex-wrap">
                                {run.critical > 0 && (
                                  <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-xs font-bold">
                                    🔴 {run.critical} Critical
                                  </span>
                                )}
                                {run.high > 0 && (
                                  <span className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-xs font-bold">
                                    🟠 {run.high} High
                                  </span>
                                )}
                                {run.medium > 0 && (
                                  <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-xs font-bold">
                                    🟡 {run.medium} Medium
                                  </span>
                                )}
                                {run.low > 0 && (
                                  <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-bold">
                                    🔵 {run.low} Low
                                  </span>
                                )}
                              </div>
                            )}
                          </>
                        )}

                        {run.status === "running" && (
                          <div className="flex items-center gap-2 text-blue-600">
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                            <span className="text-sm font-medium">Tests in progress...</span>
                          </div>
                        )}
                      </div>
                      );
                    })
                  )}
                </div>
              </div>
            </div>
          </div>
          </>
        )}

        {/* History Tab */}
        {activeTab === "history" && (
          <div className="space-y-6">
            {/* Filters */}
            <div className="bg-white rounded-2xl shadow-xl p-6 border-2 border-sky-100">
              <div className="flex items-center gap-4 flex-wrap">
                <label className="text-sm font-bold text-gray-700">Filter by MCP:</label>
                <select
                  value={selectedMcpFilter}
                  onChange={(e) => setSelectedMcpFilter(e.target.value)}
                  className="px-4 py-2 border-2 border-gray-200 rounded-lg focus:border-sky-500 focus:outline-none"
                >
                  <option value="">All MCPs</option>
                  {mcpNames.map((name) => (
                    <option key={name} value={name}>{name}</option>
                  ))}
                </select>
                <div className="flex-1"></div>
                {selectedRunIds.size > 0 && (
                  <button
                    onClick={deleteSelectedRuns}
                    className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white text-sm font-bold rounded-lg transition-all flex items-center gap-2"
                  >
                    🗑️ Delete Selected ({selectedRunIds.size})
                  </button>
                )}
                <div className="text-sm text-gray-600">
                  <span className="font-bold">{filteredRuns.length}</span> runs found
                </div>
              </div>
            </div>

            {/* Timeline View */}
            <div className="bg-white rounded-2xl shadow-xl p-6 border-2 border-blue-100">
              <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                <span>📈</span> PT Run Timeline
              </h3>

              <div className="space-y-4">
                {filteredRuns.map((run, idx) => (
                  <div key={run.run_id} className="relative">
                    {/* Timeline Line */}
                    {idx < filteredRuns.length - 1 && (
                      <div className="absolute left-6 top-16 bottom-0 w-0.5 bg-gradient-to-b from-sky-300 to-transparent"></div>
                    )}

                    <div className="flex gap-4 items-start">
                      {/* Checkbox */}
                      <div className="pt-1 flex-shrink-0">
                        <input
                          type="checkbox"
                          checked={selectedRunIds.has(run.run_id)}
                          disabled={run.status === 'running' || run.status === 'pending'}
                          onChange={(e) => {
                            const next = new Set(selectedRunIds);
                            if (e.target.checked) next.add(run.run_id);
                            else next.delete(run.run_id);
                            setSelectedRunIds(next);
                          }}
                          className="w-4 h-4 text-red-500 rounded cursor-pointer mt-4"
                          onClick={(e) => e.stopPropagation()}
                        />
                      </div>

                      {/* Timeline Dot */}
                      <div className="relative z-10">
                        <div className={`w-12 h-12 rounded-full flex items-center justify-center text-2xl shadow-lg ${
                          run.status === 'completed' ? 'bg-green-500' :
                          run.status === 'running' ? 'bg-blue-500 animate-pulse' :
                          run.status === 'failed' ? 'bg-red-500' : 'bg-gray-400'
                        }`}>
                          {run.status === 'completed' ? '✅' :
                           run.status === 'running' ? '⚡' :
                           run.status === 'failed' ? '❌' : '⏳'}
                        </div>
                      </div>

                      {/* Run Card */}
                      <div className="flex-1 bg-gradient-to-r from-white to-gray-50 rounded-xl p-5 border-2 border-gray-200 hover:shadow-lg transition-all cursor-pointer"
                           onClick={() => setSelectedRunId(run.run_id)}>
                        <div className="flex items-center justify-between mb-3">
                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
                              <h4 className="text-lg font-bold text-gray-900">{run.mcp_name}</h4>
                              {(() => { const b = getPlanSourceBadge(run.plan_source, run.llm_provider); return <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${b.cls}`}>{b.label}</span>; })()}
                            </div>
                            <p className="text-sm text-gray-600">
                              {new Date(run.created_at).toLocaleString()} • {getPresetIcon(run.preset)} {run.preset}
                            </p>
                          </div>
                          <span className={`px-4 py-2 rounded-lg text-sm font-bold ${getStatusBadge(run.status)}`}>
                            {run.status?.toUpperCase() || 'PENDING'}
                          </span>
                        </div>

                        {run.status === 'completed' && (
                          <div className="grid grid-cols-5 gap-2">
                            <div className="text-center p-2 bg-white rounded-lg border border-gray-200">
                              <div className="text-lg font-bold text-gray-900">{run.total_tests}</div>
                              <div className="text-xs text-gray-600">Tests</div>
                            </div>
                            <div className="text-center p-2 bg-green-50 rounded-lg border border-green-200">
                              <div className="text-lg font-bold text-green-600">{run.passed}</div>
                              <div className="text-xs text-green-600">Pass</div>
                            </div>
                            <div className="text-center p-2 bg-red-50 rounded-lg border border-red-200">
                              <div className="text-lg font-bold text-red-600">{run.failed}</div>
                              <div className="text-xs text-red-600">Fail</div>
                            </div>
                            <div className="text-center p-2 bg-orange-50 rounded-lg border border-orange-200">
                              <div className="text-lg font-bold text-orange-600">{run.critical + run.high}</div>
                              <div className="text-xs text-orange-600">Critical</div>
                            </div>
                            <div className="text-center p-2 bg-blue-50 rounded-lg border border-blue-200">
                              <div className="text-lg font-bold text-blue-600">{Math.round(run.duration_ms / 1000)}s</div>
                              <div className="text-xs text-blue-600">Time</div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

          </div>
        )}

        {/* Compare Tab */}
        {activeTab === "compare" && (
          <div className="space-y-6">
            {/* Select Runs */}
            <div className="bg-white rounded-2xl shadow-xl p-6 border-2 border-sky-100">
              <h3 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                <span>🔄</span> Compare PT Runs
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Run 1 */}
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-2">Run 1 (Baseline)</label>
                  <select
                    value={compareRun1 || ""}
                    onChange={(e) => setCompareRun1(Number(e.target.value))}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-sky-500 focus:outline-none"
                  >
                    <option value="">Select run...</option>
                    {runs.filter(r => r.status === 'completed').map((run) => (
                      <option key={run.run_id} value={run.run_id}>
                        #{run.run_id} - {run.mcp_name} ({new Date(run.created_at).toLocaleDateString()})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Run 2 */}
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-2">Run 2 (Compare)</label>
                  <select
                    value={compareRun2 || ""}
                    onChange={(e) => setCompareRun2(Number(e.target.value))}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-sky-500 focus:outline-none"
                  >
                    <option value="">Select run...</option>
                    {runs.filter(r => r.status === 'completed' && r.run_id !== compareRun1).map((run) => (
                      <option key={run.run_id} value={run.run_id}>
                        #{run.run_id} - {run.mcp_name} ({new Date(run.created_at).toLocaleDateString()})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                onClick={compareRuns}
                disabled={!compareRun1 || !compareRun2}
                className="mt-6 w-full px-6 py-4 bg-gradient-to-r from-sky-500 to-pink-600 hover:from-sky-600 hover:to-pink-700 text-white font-bold rounded-xl shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                🔍 Compare Runs
              </button>
            </div>

            {/* Comparison Results */}
            {comparisonResult && (
              <div className="space-y-6">
                {/* Summary Cards */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* New Failures */}
                  <div className="bg-gradient-to-br from-red-500 to-cyan-500 rounded-2xl shadow-xl p-6 text-white">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-4xl">🔴</span>
                      <div>
                        <div className="text-4xl font-black">{comparisonResult.comparison.new_failures.length}</div>
                        <div className="text-red-100 font-medium">New Failures</div>
                      </div>
                    </div>
                    <div className="text-sm text-red-100">Tests that started failing</div>
                  </div>

                  {/* Fixed Issues */}
                  <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-2xl shadow-xl p-6 text-white">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-4xl">✅</span>
                      <div>
                        <div className="text-4xl font-black">{comparisonResult.comparison.fixed_issues.length}</div>
                        <div className="text-green-100 font-medium">Fixed Issues</div>
                      </div>
                    </div>
                    <div className="text-sm text-green-100">Tests that now pass</div>
                  </div>

                  {/* Unchanged */}
                  <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl shadow-xl p-6 text-white">
                    <div className="flex items-center gap-3 mb-3">
                      <span className="text-4xl">🔵</span>
                      <div>
                        <div className="text-4xl font-black">{comparisonResult.comparison.unchanged}</div>
                        <div className="text-blue-100 font-medium">Unchanged</div>
                      </div>
                    </div>
                    <div className="text-sm text-blue-100">Tests with same result</div>
                  </div>
                </div>

                {/* Regressions */}
                {comparisonResult.comparison.new_failures.length > 0 && (
                  <div className="bg-white rounded-2xl shadow-xl p-6 border-2 border-red-200">
                    <h4 className="text-xl font-bold text-red-600 mb-4 flex items-center gap-2">
                      <span>⚠️</span> Regressions Detected
                    </h4>
                    <div className="space-y-3">
                      {comparisonResult.comparison.new_failures.map((failure: any, idx: number) => (
                        <div key={idx} className="p-4 bg-red-50 rounded-lg border-2 border-red-200">
                          <div className="flex items-center justify-between">
                            <div>
                              <span className="font-bold text-gray-900">{failure.category}.{failure.test}</span>
                              {failure.tool && <span className="text-sm text-gray-600 ml-2">({failure.tool})</span>}
                            </div>
                            <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                              failure.severity === 'critical' ? 'bg-red-600 text-white' :
                              failure.severity === 'high' ? 'bg-orange-500 text-white' : 'bg-yellow-500 text-white'
                            }`}>
                              {failure.severity?.toUpperCase()}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Improvements */}
                {comparisonResult.comparison.fixed_issues.length > 0 && (
                  <div className="bg-white rounded-2xl shadow-xl p-6 border-2 border-green-200">
                    <h4 className="text-xl font-bold text-green-600 mb-4 flex items-center gap-2">
                      <span>🎉</span> Improvements
                    </h4>
                    <div className="space-y-3">
                      {comparisonResult.comparison.fixed_issues.map((fix: any, idx: number) => (
                        <div key={idx} className="p-4 bg-green-50 rounded-lg border-2 border-green-200">
                          <div className="flex items-center gap-2">
                            <span className="text-xl">✅</span>
                            <span className="font-bold text-gray-900">{fix.category}.{fix.test}</span>
                            {fix.tool && <span className="text-sm text-gray-600">({fix.tool})</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Side-by-Side Comparison */}
                <div className="bg-white rounded-2xl shadow-xl p-6 border-2 border-sky-100">
                  <h4 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <span>🔎</span> Side-by-Side Comparison
                  </h4>
                  <div className="grid grid-cols-2 gap-6">
                    {/* Run 1 */}
                    <div className="p-4 bg-gray-50 rounded-xl">
                      <h5 className="font-bold text-gray-900 mb-3">Run #{comparisonResult.run_1.run_id}</h5>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600">MCP:</span>
                          <span className="font-bold">{comparisonResult.run_1.mcp_name}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Total Tests:</span>
                          <span className="font-bold">{comparisonResult.run_1.total_tests}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Failed:</span>
                          <span className="font-bold text-red-600">{comparisonResult.run_1.failed}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Date:</span>
                          <span className="font-bold">{new Date(comparisonResult.run_1.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>

                    {/* Run 2 */}
                    <div className="p-4 bg-sky-50 rounded-xl">
                      <h5 className="font-bold text-gray-900 mb-3">Run #{comparisonResult.run_2.run_id}</h5>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600">MCP:</span>
                          <span className="font-bold">{comparisonResult.run_2.mcp_name}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Total Tests:</span>
                          <span className="font-bold">{comparisonResult.run_2.total_tests}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Failed:</span>
                          <span className="font-bold text-red-600">{comparisonResult.run_2.failed}</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Date:</span>
                          <span className="font-bold">{new Date(comparisonResult.run_2.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Config Tab */}
        {activeTab === "config" && (
          <div className="space-y-6">
            {/* Test Catalog */}
            <div className="bg-white rounded-2xl shadow-xl p-6 border-2 border-sky-100">
              <div className="flex items-center gap-4 mb-6">
                <h3 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                  <span>📋</span> Test Catalog
                </h3>
                <div className="flex-1"></div>
                <input
                  type="text"
                  placeholder="Search tests, categories, descriptions..."
                  value={configSearch}
                  onChange={(e) => setConfigSearch(e.target.value)}
                  className="px-4 py-2 border-2 border-gray-200 rounded-xl focus:border-sky-500 focus:outline-none w-72 text-sm"
                />
              </div>
              <p className="text-sm text-gray-500 mb-6">
                All test categories and functions defined in the MCP PT service. These are the security checks that the LLM selects from and the executor runs against each MCP tool.
              </p>

              {Object.keys(testCatalog).length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                  <span className="text-5xl block mb-3">📭</span>
                  <p>No test catalog data available</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {Object.entries(testCatalog)
                    .filter(([catName, catData]: [string, any]) => {
                      if (!configSearch) return true;
                      const q = configSearch.toLowerCase();
                      if (catName.toLowerCase().includes(q)) return true;
                      if (catData.description?.toLowerCase().includes(q)) return true;
                      return catData.tests?.some((t: any) =>
                        t.name?.toLowerCase().includes(q) ||
                        t.description?.toLowerCase().includes(q)
                      );
                    })
                    .map(([catName, catData]: [string, any]) => {
                      const filteredTests = configSearch
                        ? catData.tests?.filter((t: any) => {
                            const q = configSearch.toLowerCase();
                            return catName.toLowerCase().includes(q) ||
                              catData.description?.toLowerCase().includes(q) ||
                              t.name?.toLowerCase().includes(q) ||
                              t.description?.toLowerCase().includes(q);
                          })
                        : catData.tests || [];

                      const SEVERITY_COLORS: Record<string, string> = {
                        critical: "bg-red-100 text-red-700 border-red-200",
                        high: "bg-orange-100 text-orange-700 border-orange-200",
                        medium: "bg-yellow-100 text-yellow-700 border-yellow-200",
                        low: "bg-blue-100 text-blue-700 border-blue-200",
                        info: "bg-gray-100 text-gray-600 border-gray-200",
                      };
                      const severityClass = SEVERITY_COLORS[catData.severity_default] || SEVERITY_COLORS.info;

                      return (
                        <details key={catName} className="group border-2 border-gray-200 rounded-xl overflow-hidden">
                          <summary className="flex items-center gap-4 p-4 bg-gray-50 hover:bg-sky-50 cursor-pointer list-none transition-all">
                            <span className="text-gray-400 group-open:rotate-90 transition-transform inline-block">▶</span>
                            <div className="flex-1">
                              <div className="flex items-center gap-3">
                                <span className="font-bold text-gray-900 text-base">{catName.replace(/_/g, " ").toUpperCase()}</span>
                                <span className={`px-2 py-0.5 text-xs font-bold rounded-full border ${severityClass}`}>
                                  {catData.severity_default}
                                </span>
                                {!catData.enabled && (
                                  <span className="px-2 py-0.5 text-xs font-bold rounded-full bg-gray-200 text-gray-500">disabled</span>
                                )}
                              </div>
                              {catData.description && (
                                <p className="text-sm text-gray-500 mt-1">{catData.description}</p>
                              )}
                            </div>
                            <span className="text-sm font-bold text-sky-600 flex-shrink-0">
                              {filteredTests.length} test{filteredTests.length !== 1 ? "s" : ""}
                            </span>
                          </summary>

                          <div className="divide-y divide-gray-100">
                            {filteredTests.map((test: any) => (
                              <div key={test.name} className={`flex items-start gap-4 px-6 py-3 ${!test.enabled ? "opacity-50" : ""}`}>
                                <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${test.enabled ? "bg-green-500" : "bg-gray-300"}`} />
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="font-semibold text-gray-800 text-sm">{test.name.replace(/_/g, " ")}</span>
                                    {!test.enabled && (
                                      <span className="text-xs text-gray-400 italic">disabled</span>
                                    )}
                                  </div>
                                  {test.description && (
                                    <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{test.description}</p>
                                  )}
                                </div>
                                <code className="text-xs text-sky-600 bg-sky-50 px-2 py-0.5 rounded font-mono flex-shrink-0 max-w-[200px] truncate">
                                  {test.python_function}
                                </code>
                              </div>
                            ))}
                          </div>
                        </details>
                      );
                    })}
                </div>
              )}
            </div>

            {/* AI Red Team Config */}
            {aiRedTeamConfig && (
              <div className="bg-white rounded-2xl shadow-xl p-6 border-2 border-purple-100">
                <h3 className="text-xl font-bold text-gray-900 mb-1 flex items-center gap-2">
                  <span>🤖</span> AI Red Team Configuration
                </h3>
                <p className="text-sm text-gray-500 mb-5">
                  Configure the attacker and judge agents independently — use a fast model for attacking and a precise model for judging.
                </p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Attacker */}
                  <div className="p-4 bg-red-50 border-2 border-red-100 rounded-xl">
                    <div className="text-sm font-bold text-red-700 mb-3 flex items-center gap-2">⚔️ Attacker Agent</div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">Provider</label>
                    <select
                      value={aiRedTeamConfig.attacker_provider || "gemini"}
                      onChange={e => setAiRedTeamConfig((c: any) => ({ ...c, attacker_provider: e.target.value, attacker_model: aiRedTeamProviders[e.target.value]?.default_model || "" }))}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm mb-3 focus:border-purple-400 focus:outline-none"
                    >
                      {Object.keys(aiRedTeamProviders).map(p => (
                        <option key={p} value={p}>{p === "anthropic" ? "🤖 Anthropic" : p === "groq" ? "⚡ Groq" : "✨ Gemini"} — {p}</option>
                      ))}
                    </select>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">Model</label>
                    <select
                      value={aiRedTeamConfig.attacker_model || ""}
                      onChange={e => setAiRedTeamConfig((c: any) => ({ ...c, attacker_model: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:border-purple-400 focus:outline-none"
                    >
                      {(aiRedTeamProviders[aiRedTeamConfig.attacker_provider]?.models || []).map((m: string) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </div>
                  {/* Judge */}
                  <div className="p-4 bg-blue-50 border-2 border-blue-100 rounded-xl">
                    <div className="text-sm font-bold text-blue-700 mb-3 flex items-center gap-2">⚖️ Judge Agent</div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">Provider</label>
                    <select
                      value={aiRedTeamConfig.judge_provider || "gemini"}
                      onChange={e => setAiRedTeamConfig((c: any) => ({ ...c, judge_provider: e.target.value, judge_model: aiRedTeamProviders[e.target.value]?.default_model || "" }))}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm mb-3 focus:border-purple-400 focus:outline-none"
                    >
                      {Object.keys(aiRedTeamProviders).map(p => (
                        <option key={p} value={p}>{p === "anthropic" ? "🤖 Anthropic" : p === "groq" ? "⚡ Groq" : "✨ Gemini"} — {p}</option>
                      ))}
                    </select>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">Model</label>
                    <select
                      value={aiRedTeamConfig.judge_model || ""}
                      onChange={e => setAiRedTeamConfig((c: any) => ({ ...c, judge_model: e.target.value }))}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:border-purple-400 focus:outline-none"
                    >
                      {(aiRedTeamProviders[aiRedTeamConfig.judge_provider]?.models || []).map((m: string) => (
                        <option key={m} value={m}>{m}</option>
                      ))}
                    </select>
                  </div>
                </div>
                {/* Numeric params */}
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">Max Stories (scenarios)</label>
                    <input type="number" min={1} max={10}
                      value={aiRedTeamConfig.max_stories || 3}
                      onChange={e => setAiRedTeamConfig((c: any) => ({ ...c, max_stories: parseInt(e.target.value) || 3 }))}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:border-purple-400 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-600 mb-1">Max Iterations (tool calls)</label>
                    <input type="number" min={5} max={100}
                      value={aiRedTeamConfig.max_iterations || 25}
                      onChange={e => setAiRedTeamConfig((c: any) => ({ ...c, max_iterations: parseInt(e.target.value) || 25 }))}
                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:border-purple-400 focus:outline-none"
                    />
                  </div>
                </div>
                <div className="mt-4 flex items-center justify-between">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox"
                      checked={aiRedTeamConfig.enabled !== false}
                      onChange={e => setAiRedTeamConfig((c: any) => ({ ...c, enabled: e.target.checked }))}
                      className="w-4 h-4 text-purple-600 rounded"
                    />
                    <span className="text-sm font-medium text-gray-700">Enabled (available as a category in runs)</span>
                  </label>
                  <button
                    onClick={async () => {
                      setSavingAiConfig(true);
                      try {
                        await omni2Api.put("/api/v1/mcp-pt/ai-red-team-config", aiRedTeamConfig);
                        alert("✅ AI Red Team configuration saved.");
                      } catch (e: any) {
                        const msg = e?.response?.data?.detail || e?.message || "Unknown error";
                        alert(`❌ Failed to save configuration: ${msg}`);
                        console.error(e);
                      } finally { setSavingAiConfig(false); }
                    }}
                    disabled={savingAiConfig}
                    className="px-5 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-300 text-white text-sm font-bold rounded-xl transition-colors"
                  >
                    {savingAiConfig ? "Saving…" : "💾 Save Config"}
                  </button>
                </div>
              </div>
            )}

            {/* Presets Reference */}
            <div className="bg-white rounded-2xl shadow-xl p-6 border-2 border-blue-100">
              <h3 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                <span>🎯</span> Preset Configurations
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {presets.map((preset) => (
                  <div key={preset.name} className="p-4 border-2 border-gray-200 rounded-xl">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-2xl">{getPresetIcon(preset.name)}</span>
                      <span className="font-bold text-gray-900 capitalize text-lg">{preset.name}</span>
                    </div>
                    <p className="text-sm text-gray-600 mb-3">{preset.description}</p>
                    <div className="text-xs text-gray-500 space-y-1 mb-3">
                      <div>⚡ <span className="font-medium">{preset.max_parallel}</span> parallel</div>
                      <div>⏱️ <span className="font-medium">{preset.timeout_seconds}s</span> timeout</div>
                    </div>
                    {(preset as any).categories && (
                      <div className="flex flex-wrap gap-1">
                        {(preset as any).categories.map((cat: string) => (
                          <span key={cat} className="px-2 py-0.5 bg-sky-50 text-sky-700 text-xs rounded-full border border-sky-200">
                            {cat.replace(/_/g, " ")}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* About / How it Works tab */}
        {activeTab === "about" && (
          <MCPPTAboutTab
            testCatalog={testCatalog}
            presets={presets}
            categories={categories}
          />
        )}

        {/* Global Run Details Modal — works from any tab */}
        {selectedRunId && (
          <PTRunDetails runId={selectedRunId} onClose={() => setSelectedRunId(null)} />
        )}
    </div>
  );
}
