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
}

interface TranscriptEvent {
  type: "thinking" | "tool_call" | "tool_result" | "scenario_marker";
  content?: string;
  tool?: string;
  args?: Record<string, unknown>;
  result?: string;
  index?: number;
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

export default function AIRedTeamResults({ runId }: { runId: number }) {
  const [stories, setStories] = useState<AgentStory[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedStory, setExpandedStory] = useState<number | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEvent[] | null>(null);
  const [transcriptLoading, setTranscriptLoading] = useState(false);

  useEffect(() => {
    loadStories();
  }, [runId]);

  const loadStories = async () => {
    setLoading(true);
    try {
      const res = await omni2Api.get(`/api/v1/mcp-pt/runs/${runId}/agent-stories`);
      setStories(Array.isArray(res.data) ? res.data : []);
    } catch {
      setStories([]);
    } finally {
      setLoading(false);
    }
  };

  const loadTranscript = async (storyId: number) => {
    if (expandedStory === storyId) {
      setExpandedStory(null);
      setTranscript(null);
      return;
    }
    setExpandedStory(storyId);
    setTranscriptLoading(true);
    try {
      const res = await omni2Api.get(`/api/v1/mcp-pt/runs/${runId}/agent-stories/${storyId}/transcript`);
      setTranscript(Array.isArray(res.data) ? res.data : []);
    } catch {
      setTranscript([]);
    } finally {
      setTranscriptLoading(false);
    }
  };

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

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex items-center gap-4 px-4 py-3 bg-gray-900 rounded-lg text-sm">
        <span className="text-purple-400 font-bold text-base">🤖 AI Red Team</span>
        <span className="text-white font-semibold">{stories.length} scenarios</span>
        {vulnCount > 0 && (
          <span className="px-2 py-0.5 bg-red-600 text-white rounded-full text-xs font-bold">
            {vulnCount} vulnerabilities
          </span>
        )}
        {critCount > 0 && (
          <span className="px-2 py-0.5 bg-red-900 text-red-200 rounded-full text-xs font-bold">
            {critCount} critical
          </span>
        )}
        <span className="ml-auto text-gray-400 text-xs">
          Attacker: {stories[0]?.attacker_model} · Judge: {stories[0]?.judge_model}
        </span>
      </div>

      {/* Story cards */}
      {stories.map(story => {
        const vc = VERDICT_CONFIG[story.verdict] ?? VERDICT_CONFIG.inconclusive;
        const isExpanded = expandedStory === story.id;

        return (
          <div key={story.id} className={`border-2 ${vc.border} ${vc.bg} rounded-xl overflow-hidden`}>
            {/* Card header */}
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
                  <span className="text-gray-500 text-xs">{story.tool_calls_made} tool calls</span>
                </div>
                <h3 className="font-bold text-gray-900 text-sm leading-tight">
                  {story.title || story.attack_goal}
                </h3>
                <p className="text-gray-600 text-xs mt-0.5 italic">{story.attack_goal}</p>
              </div>
            </div>

            {/* Finding body */}
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
              {story.recommendation && story.verdict === "vulnerability_found" && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-2">
                  <span className="text-xs font-semibold text-blue-600 uppercase tracking-wide">Recommendation</span>
                  <p className="text-xs text-blue-800 mt-0.5">{story.recommendation}</p>
                </div>
              )}
            </div>

            {/* Transcript toggle */}
            <div className="border-t border-gray-200 px-4 py-2">
              <button
                onClick={() => loadTranscript(story.id)}
                className="text-xs text-purple-600 hover:text-purple-800 font-medium flex items-center gap-1"
              >
                {isExpanded ? "▲ Hide transcript" : "▼ View agent transcript"}
              </button>

              {isExpanded && (
                <div className="mt-3 bg-gray-950 rounded-lg p-3 max-h-96 overflow-y-auto">
                  {transcriptLoading ? (
                    <p className="text-gray-400 text-xs">Loading transcript…</p>
                  ) : transcript && transcript.length > 0 ? (
                    <div className="space-y-1 font-mono text-xs">
                      {transcript.map((ev, i) => {
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
                  ) : (
                    <p className="text-gray-500 text-xs">No transcript data.</p>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
