"use client";

import { useState, useEffect } from "react";
import { omni2Api } from "@/lib/omni2Api";

interface AgentStory {
  id: number;
  run_id: number;
  story_index: number;
  attack_goal: string;
  tool_calls_made: number;
  verdict: "vulnerability_found" | "secure" | "inconclusive";
  severity: "critical" | "high" | "medium" | "low" | "info";
  title: string;
  finding: string;
  evidence: string;
  recommendation: string;
  attacker_model: string;
  judge_model: string;
  created_at: string;
  transcript?: TranscriptEvent[];
  was_planned?: boolean;
  coverage_pct?: number;
  surprises?: string[];
}

interface TranscriptEvent {
  type: "thinking" | "tool_call" | "tool_result" | "scenario_marker";
  content?: string;
  tool?: string;
  args?: Record<string, unknown>;
  result?: string;
  index?: number;
}

interface MissionBriefing {
  domain: string;
  risk_rating: string;
  risk_surface: string;
  priority_targets: Array<{ tool: string; risk: string; payloads?: string[] }>;
  chains: Array<{ steps: string[]; goal: string }>;
  scenarios: Array<{
    index: number;
    attack_goal: string;
    target_tools: string[];
    technique: string;
    payload_hints?: string[];
  }>;
  _cached_at?: string;
  _is_stale?: boolean;
  cache_hit?: boolean;
}

const VERDICT_CONFIG = {
  vulnerability_found: { bg: "bg-red-50", border: "border-red-400", badge: "bg-red-600 text-white", label: "VULNERABILITY FOUND" },
  secure:              { bg: "bg-green-50", border: "border-green-400", badge: "bg-green-600 text-white", label: "SECURE" },
  inconclusive:        { bg: "bg-yellow-50", border: "border-yellow-400", badge: "bg-yellow-500 text-white", label: "INCONCLUSIVE" },
};

const SEV_BADGE: Record<string, string> = {
  critical: "bg-red-700 text-white",
  high:     "bg-red-500 text-white",
  medium:   "bg-yellow-500 text-white",
  low:      "bg-blue-500 text-white",
  info:     "bg-gray-400 text-white",
};

const RISK_COLOR: Record<string, string> = {
  critical: "bg-red-700 text-white",
  high:     "bg-red-500 text-white",
  medium:   "bg-yellow-500 text-white",
  low:      "bg-green-500 text-white",
};

export default function AIRedTeamResults({ runId }: { runId: number }) {
  const [stories, setStories] = useState<AgentStory[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedStory, setExpandedStory] = useState<number | null>(null);
  const [missionBriefing, setMissionBriefing] = useState<MissionBriefing | null>(null);
  const [briefingExpanded, setBriefingExpanded] = useState(false);

  useEffect(() => {
    loadAll();
  }, [runId]);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [storiesRes, briefingRes] = await Promise.allSettled([
        omni2Api.get(`/api/v1/mcp-pt/runs/${runId}/agent-stories`),
        omni2Api.get(`/api/v1/mcp-pt/runs/${runId}/mission-briefing`),
      ]);
      if (storiesRes.status === "fulfilled") {
        setStories(Array.isArray(storiesRes.value.data) ? storiesRes.value.data : []);
      }
      if (briefingRes.status === "fulfilled" && briefingRes.value.data?.domain) {
        setMissionBriefing(briefingRes.value.data);
      }
    } finally {
      setLoading(false);
    }
  };

  const toggleStory = (storyId: number) =>
    setExpandedStory(prev => (prev === storyId ? null : storyId));

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-gray-500 py-6">
        <span className="animate-spin text-lg">⚙️</span>
        <span className="text-sm">Loading AI Red Team results…</span>
      </div>
    );
  }

  if (stories.length === 0) {
    return (
      <div className="text-center py-10 text-gray-400 text-sm">
        No AI Red Team stories for this run.
      </div>
    );
  }

  const vulnCount = stories.filter(s => s.verdict === "vulnerability_found").length;
  const critCount = stories.filter(s => s.severity === "critical" && s.verdict === "vulnerability_found").length;
  const avgCoverage =
    stories.length > 0 && stories.some(s => s.coverage_pct != null)
      ? Math.round(stories.reduce((acc, s) => acc + (s.coverage_pct ?? 0), 0) / stories.length)
      : null;

  return (
    <div className="space-y-4">
      {/* ── Mission Briefing / Attack Surface card ── */}
      {missionBriefing && (
        <div className="border border-gray-200 bg-white rounded-xl overflow-hidden shadow-sm">
          <button
            onClick={() => setBriefingExpanded(v => !v)}
            className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors border-b border-gray-100"
          >
            <span className="text-gray-500 text-base">🎯</span>
            <span className="text-gray-700 font-semibold text-sm flex-1">Attack Surface Analysis</span>
            {missionBriefing.risk_rating && (
              <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${RISK_COLOR[missionBriefing.risk_rating] ?? "bg-gray-400 text-white"}`}>
                {missionBriefing.risk_rating.toUpperCase()}
              </span>
            )}
            {missionBriefing.cache_hit && (
              <span className="px-2 py-0.5 bg-gray-100 text-gray-500 rounded-full text-xs border border-gray-200">cached</span>
            )}
            {missionBriefing._is_stale && (
              <span className="px-2 py-0.5 bg-amber-50 text-amber-600 rounded-full text-xs border border-amber-200">stale</span>
            )}
            <span className="text-gray-400 text-xs ml-1">{briefingExpanded ? "▲" : "▼"}</span>
          </button>

          {briefingExpanded && (
            <div className="px-4 pb-4 pt-3 space-y-3 text-sm">
              {/* Domain + risk surface */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                  <p className="text-gray-400 text-xs font-semibold uppercase tracking-wide mb-1">Domain</p>
                  <p className="text-gray-800 font-medium text-sm">{missionBriefing.domain || "—"}</p>
                </div>
                <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
                  <p className="text-gray-400 text-xs font-semibold uppercase tracking-wide mb-1">Risk Surface</p>
                  <p className="text-gray-800 font-medium text-sm">{missionBriefing.risk_surface || "—"}</p>
                </div>
              </div>

              {/* Priority targets */}
              {(missionBriefing.priority_targets?.length ?? 0) > 0 && (
                <div>
                  <p className="text-gray-400 text-xs font-semibold uppercase tracking-wide mb-2">Priority Targets</p>
                  <div className="space-y-1.5">
                    {missionBriefing.priority_targets.map((t, i) => (
                      <div key={i} className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                        <div className="flex items-start gap-2">
                          <span className="text-gray-400 text-xs mt-0.5 flex-shrink-0">▸</span>
                          <div>
                            <span className="text-gray-800 font-mono text-xs font-semibold">{t.tool}</span>
                            <span className="text-gray-500 text-xs ml-2">— {t.risk}</span>
                            {(t.payloads?.length ?? 0) > 0 && (
                              <div className="flex flex-wrap gap-1 mt-1">
                                {t.payloads!.slice(0, 3).map((p, j) => (
                                  <code key={j} className="text-xs bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded border border-gray-200">
                                    {p}
                                  </code>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Attack chains */}
              {(missionBriefing.chains?.length ?? 0) > 0 && (
                <div>
                  <p className="text-gray-400 text-xs font-semibold uppercase tracking-wide mb-2">Attack Chains</p>
                  <div className="space-y-1.5">
                    {missionBriefing.chains.map((c, i) => (
                      <div key={i} className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                        <p className="text-gray-600 text-xs mb-1.5">{c.goal}</p>
                        <div className="flex items-center gap-1 flex-wrap">
                          {c.steps.map((s, j) => (
                            <span key={j} className="flex items-center gap-1">
                              <code className="text-xs bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded font-mono border border-gray-200">{s}</code>
                              {j < c.steps.length - 1 && <span className="text-gray-400 text-xs">→</span>}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Pre-assigned scenarios */}
              {(missionBriefing.scenarios?.length ?? 0) > 0 && (
                <div>
                  <p className="text-gray-400 text-xs font-semibold uppercase tracking-wide mb-2">Pre-Assigned Scenarios</p>
                  <div className="space-y-1.5">
                    {missionBriefing.scenarios.map(sc => (
                      <div key={sc.index} className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="w-5 h-5 rounded-full bg-gray-200 text-gray-600 text-xs flex items-center justify-center font-bold flex-shrink-0">
                            {sc.index}
                          </span>
                          <span className="text-gray-800 text-xs font-medium">{sc.attack_goal}</span>
                        </div>
                        <div className="flex flex-wrap gap-1 pl-7">
                          {sc.target_tools?.map((t, j) => (
                            <code key={j} className="text-xs bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded font-mono border border-gray-200">{t}</code>
                          ))}
                          {sc.technique && (
                            <span className="text-xs text-gray-500 italic ml-1">{sc.technique}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Summary bar ── */}
      <div className="flex items-center gap-3 px-4 py-3 bg-slate-50 border border-slate-200 rounded-lg text-sm flex-wrap">
        <span className="text-slate-600 font-semibold text-sm">🤖 AI Red Team</span>
        <span className="text-slate-700 font-medium text-sm">{stories.length} scenarios</span>
        {vulnCount > 0 && (
          <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded-full text-xs font-bold border border-red-200">
            {vulnCount} {vulnCount === 1 ? "vulnerability" : "vulnerabilities"}
          </span>
        )}
        {critCount > 0 && (
          <span className="px-2 py-0.5 bg-red-600 text-white rounded-full text-xs font-bold">
            {critCount} critical
          </span>
        )}
        {avgCoverage !== null && (
          <span className="px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full text-xs font-medium border border-slate-200">
            {avgCoverage}% plan coverage
          </span>
        )}
        <span className="ml-auto text-slate-400 text-xs">
          Attacker: {stories[0]?.attacker_model} · Judge: {stories[0]?.judge_model}
        </span>
      </div>

      {/* ── Story cards ── */}
      {stories.map(story => {
        const vc = VERDICT_CONFIG[story.verdict] ?? VERDICT_CONFIG.inconclusive;
        const isExpanded = expandedStory === story.id;
        const storyTranscript: TranscriptEvent[] = Array.isArray(story.transcript) ? story.transcript : [];

        return (
          <div key={story.id} className={`border-2 ${vc.border} ${vc.bg} rounded-xl overflow-hidden`}>
            {/* Header */}
            <div className="flex items-start gap-3 p-4">
              <div className="flex-shrink-0 w-7 h-7 rounded-full bg-gray-800 text-white text-xs flex items-center justify-center font-bold">
                {story.story_index}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${vc.badge}`}>
                    {vc.label}
                  </span>
                  {story.verdict === "vulnerability_found" && (
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${SEV_BADGE[story.severity] ?? SEV_BADGE.info}`}>
                      {story.severity.toUpperCase()}
                    </span>
                  )}
                  {story.was_planned === true && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-purple-100 text-purple-700 border border-purple-300">
                      🗺 Planned
                    </span>
                  )}
                  {story.was_planned === false && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-orange-100 text-orange-700 border border-orange-300">
                      ⚡ Surprise
                    </span>
                  )}
                  <span className="text-gray-500 text-xs">{story.tool_calls_made} tool calls</span>
                  {story.coverage_pct != null && (
                    <span className="text-gray-400 text-xs">{story.coverage_pct}% plan coverage</span>
                  )}
                </div>
                <h3 className="font-bold text-gray-900 text-sm leading-tight">
                  {story.title || story.attack_goal}
                </h3>
                <p className="text-gray-600 text-xs mt-0.5 italic">{story.attack_goal}</p>
              </div>
            </div>

            {/* Body */}
            <div className="px-4 pb-3 space-y-2">
              {story.finding && (
                <p className="text-sm text-gray-800">{story.finding}</p>
              )}
              {story.evidence && (
                <div className="bg-white border border-gray-200 rounded-lg p-2">
                  <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Evidence</span>
                  <p className="text-xs text-gray-700 font-mono mt-0.5 whitespace-pre-wrap">{story.evidence}</p>
                </div>
              )}
              {(story.surprises?.length ?? 0) > 0 && (
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-2">
                  <span className="text-xs font-semibold text-orange-600 uppercase tracking-wide">Unexpected Findings</span>
                  <ul className="mt-1 space-y-0.5">
                    {story.surprises!.map((s, i) => (
                      <li key={i} className="text-xs text-orange-800 flex items-start gap-1">
                        <span className="flex-shrink-0">•</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {story.recommendation && story.verdict === "vulnerability_found" && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-2">
                  <span className="text-xs font-semibold text-blue-600 uppercase tracking-wide">Recommendation</span>
                  <p className="text-xs text-blue-800 mt-0.5">{story.recommendation}</p>
                </div>
              )}
            </div>

            {/* Transcript toggle — uses per-story transcript stored in DB */}
            {storyTranscript.length > 0 && (
              <div className="border-t border-gray-200 px-4 py-2">
                <button
                  onClick={() => toggleStory(story.id)}
                  className="text-xs text-purple-600 hover:text-purple-800 font-medium flex items-center gap-1"
                >
                  {isExpanded ? "▲ Hide transcript" : `▼ View agent transcript (${storyTranscript.length} events)`}
                </button>

                {isExpanded && (
                  <div className="mt-3 bg-gray-950 rounded-lg p-3 max-h-96 overflow-y-auto">
                    <div className="space-y-1 font-mono text-xs">
                      {storyTranscript.map((ev, i) => {
                        if (ev.type === "scenario_marker") {
                          return (
                            <p key={i} className="text-purple-400 border-t border-purple-800 pt-1 mt-1">
                              ── Scenario {ev.index} ──
                            </p>
                          );
                        }
                        if (ev.type === "thinking" && ev.content) {
                          return <p key={i} className="text-green-400 whitespace-pre-wrap">{ev.content}</p>;
                        }
                        if (ev.type === "tool_call") {
                          return (
                            <p key={i} className="text-yellow-400">
                              → {ev.tool}({JSON.stringify(ev.args ?? {}).slice(0, 120)})
                            </p>
                          );
                        }
                        if (ev.type === "tool_result") {
                          return (
                            <p key={i} className="text-cyan-300 pl-4">
                              ← {String(ev.result ?? "").slice(0, 200)}
                            </p>
                          );
                        }
                        return null;
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
