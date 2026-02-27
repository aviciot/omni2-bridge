'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/stores/authStore';
import { useRouter } from 'next/navigation';

const API = 'http://localhost:8500/api/v1';

type Source = 'all' | 'chat' | 'mcp_gateway';

function SourceBadge({ source }: { source: string }) {
  if (source === 'mcp_gateway') return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-700 border border-purple-300">🔌 MCP Gateway</span>;
  return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 border border-blue-300">💬 Chat</span>;
}

function StatCard({ icon, label, value, sub }: { icon: string; label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm">
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-sm font-medium text-gray-700">{label}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}

function Bar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div className="h-2 rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs text-gray-600 w-8 text-right">{value}</span>
    </div>
  );
}

export default function MCPInsightsPage() {
  const router = useRouter();
  const { user, isAuthenticated, fetchUser } = useAuthStore();
  const [days, setDays] = useState(30);
  const [source, setSource] = useState<Source>('all');
  const [loading, setLoading] = useState(true);

  const [overview, setOverview] = useState<any[]>([]);
  const [topTools, setTopTools] = useState<any[]>([]);
  const [topMcps, setTopMcps] = useState<any[]>([]);
  const [userStats, setUserStats] = useState<any[]>([]);
  const [teamStats, setTeamStats] = useState<any[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [comparison, setComparison] = useState<any[]>([]);

  useEffect(() => { fetchUser(); }, [fetchUser]);
  useEffect(() => { if (!isAuthenticated) router.push('/login'); }, [isAuthenticated, router]);

  const token = () => localStorage.getItem('access_token');
  const headers = () => ({ Authorization: `Bearer ${token()}` });
  const srcParam = source !== 'all' ? `&source=${source}` : '';

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, tt, tm, us, ts, tl, cmp] = await Promise.all([
        fetch(`${API}/mcp-analytics/overview?days=${days}`, { headers: headers() }).then(r => r.json()),
        fetch(`${API}/mcp-analytics/top-tools?days=${days}${srcParam}&limit=10`, { headers: headers() }).then(r => r.json()),
        fetch(`${API}/mcp-analytics/top-mcps?days=${days}${srcParam}`, { headers: headers() }).then(r => r.json()),
        fetch(`${API}/mcp-analytics/user-stats?days=${days}${srcParam}`, { headers: headers() }).then(r => r.json()),
        fetch(`${API}/mcp-analytics/team-stats?days=${days}${srcParam}`, { headers: headers() }).then(r => r.json()),
        fetch(`${API}/mcp-analytics/activity-over-time?days=${days}`, { headers: headers() }).then(r => r.json()),
        fetch(`${API}/mcp-analytics/chat-vs-gateway?days=${days}`, { headers: headers() }).then(r => r.json()),
      ]);
      setOverview(ov.data || []);
      setTopTools(tt.data || []);
      setTopMcps(tm.data || []);
      setUserStats(us.data || []);
      setTeamStats(ts.data || []);
      setTimeline(tl.data || []);
      setComparison(cmp.data || []);
    } finally {
      setLoading(false);
    }
  }, [days, source]);

  useEffect(() => { if (isAuthenticated) load(); }, [isAuthenticated, load]);

  // Aggregate overview totals
  const totalSessions = overview.reduce((s, r) => s + Number(r.sessions), 0);
  const totalToolCalls = comparison.reduce((s, r) => s + Number(r.total_tool_calls || 0), 0);
  const totalUsers = overview.reduce((s, r) => s + Number(r.unique_users), 0);
  const chatRow = comparison.find(r => r.source === 'chat');
  const gwRow = comparison.find(r => r.source === 'mcp_gateway');

  // Timeline: build day labels + series
  const days_set = [...new Set(timeline.map(r => r.day))].sort();
  const chatSeries = days_set.map(d => timeline.find(r => r.day === d && r.source === 'chat')?.sessions || 0);
  const gwSeries = days_set.map(d => timeline.find(r => r.day === d && r.source === 'mcp_gateway')?.sessions || 0);
  const maxTimeline = Math.max(...chatSeries, ...gwSeries, 1);

  const maxToolCount = topTools[0]?.count || 1;
  const maxMcpCount = topMcps[0]?.count || 1;
  const maxUserCalls = userStats[0]?.tool_calls || 1;
  const maxTeamCalls = teamStats[0]?.tool_calls || 1;

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gray-50">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">📊 MCP Usage Insights</h2>
            <p className="text-gray-500 text-sm mt-1">Tool calls, user activity, and team usage across Chat and MCP Gateway</p>
          </div>
          <div className="flex items-center gap-3">
            {/* Days filter */}
            <select
              value={days}
              onChange={e => setDays(Number(e.target.value))}
              className="text-sm border border-gray-300 rounded-lg px-3 py-1.5 bg-white"
            >
              {[7, 14, 30, 90].map(d => <option key={d} value={d}>Last {d} days</option>)}
            </select>
            {/* Source filter */}
            <div className="flex gap-1">
              {(['all', 'chat', 'mcp_gateway'] as Source[]).map(s => (
                <button key={s} onClick={() => setSource(s)}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
                    source === s
                      ? s === 'mcp_gateway' ? 'bg-purple-600 text-white border-purple-600'
                        : s === 'chat' ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-gray-800 text-white border-gray-800'
                      : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
                  }`}>
                  {s === 'all' ? '🔀 All' : s === 'chat' ? '💬 Chat' : '🔌 Gateway'}
                </button>
              ))}
            </div>
            <button onClick={load} disabled={loading}
              className="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded-lg border border-gray-300 disabled:opacity-50">
              {loading ? '⟳' : '↺ Refresh'}
            </button>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard icon="🗂️" label="Total Sessions" value={totalSessions} sub={`last ${days} days`} />
          <StatCard icon="⚡" label="Tool Calls" value={totalToolCalls} sub="across all sources" />
          <StatCard icon="👥" label="Active Users" value={totalUsers} sub="unique" />
          <StatCard icon="🔌" label="MCPs Used" value={topMcps.length} sub="distinct servers" />
        </div>

        {/* Chat vs Gateway comparison */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {[chatRow, gwRow].filter(Boolean).map(row => (
            <div key={row.source} className={`rounded-xl border p-5 ${row.source === 'mcp_gateway' ? 'bg-purple-50 border-purple-200' : 'bg-blue-50 border-blue-200'}`}>
              <div className="flex items-center gap-2 mb-3">
                <SourceBadge source={row.source} />
                <span className="text-sm font-semibold text-gray-700">{row.source === 'mcp_gateway' ? 'MCP Gateway (direct API)' : 'Chat (LLM-driven)'}</span>
              </div>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div><div className="text-xl font-bold text-gray-900">{row.sessions}</div><div className="text-xs text-gray-500">Sessions</div></div>
                <div><div className="text-xl font-bold text-gray-900">{row.total_tool_calls}</div><div className="text-xs text-gray-500">Tool Calls</div></div>
                <div><div className="text-xl font-bold text-gray-900">{row.avg_steps}</div><div className="text-xs text-gray-500">Avg Steps</div></div>
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Top Tools */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <h3 className="font-semibold text-gray-900 mb-4">⚡ Top Tools</h3>
            {topTools.length === 0 ? <p className="text-gray-400 text-sm text-center py-6">No data</p> : (
              <div className="space-y-3">
                {topTools.map((t, i) => (
                  <div key={i}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-mono text-xs">
                        <span className="text-purple-600 font-semibold">{t.mcp}</span>
                        <span className="text-gray-400"> → </span>
                        <span className="text-blue-600">{t.tool}</span>
                      </span>
                    </div>
                    <Bar value={t.count} max={maxToolCount} color="#6366f1" />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Top MCPs */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <h3 className="font-semibold text-gray-900 mb-4">🔌 Top MCP Servers</h3>
            {topMcps.length === 0 ? <p className="text-gray-400 text-sm text-center py-6">No data</p> : (
              <div className="space-y-3">
                {topMcps.map((m, i) => (
                  <div key={i}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-semibold text-gray-800">{m.mcp}</span>
                      <span className="text-xs text-gray-500">{m.unique_users} users</span>
                    </div>
                    <Bar value={m.count} max={maxMcpCount} color="#8b5cf6" />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Activity Timeline */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 mb-6">
          <h3 className="font-semibold text-gray-900 mb-4">📈 Daily Activity (Chat vs Gateway)</h3>
          {days_set.length === 0 ? <p className="text-gray-400 text-sm text-center py-6">No data</p> : (
            <div className="overflow-x-auto">
              <div className="flex items-end gap-1 min-w-max" style={{ height: 120 }}>
                {days_set.map((day, i) => (
                  <div key={day} className="flex flex-col items-center gap-0.5" style={{ width: 32 }}>
                    <div className="flex items-end gap-0.5" style={{ height: 90 }}>
                      <div title={`Chat: ${chatSeries[i]}`}
                        style={{ height: `${Math.round((chatSeries[i] / maxTimeline) * 90)}px`, width: 12, backgroundColor: '#3b82f6', borderRadius: 2 }} />
                      <div title={`Gateway: ${gwSeries[i]}`}
                        style={{ height: `${Math.round((gwSeries[i] / maxTimeline) * 90)}px`, width: 12, backgroundColor: '#8b5cf6', borderRadius: 2 }} />
                    </div>
                    <span className="text-[9px] text-gray-400 rotate-45 origin-left mt-1">{day.slice(5)}</span>
                  </div>
                ))}
              </div>
              <div className="flex gap-4 mt-4 text-xs text-gray-600">
                <span><span className="inline-block w-3 h-3 rounded bg-blue-500 mr-1" />Chat</span>
                <span><span className="inline-block w-3 h-3 rounded bg-purple-500 mr-1" />MCP Gateway</span>
              </div>
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* User Stats */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <h3 className="font-semibold text-gray-900 mb-4">👤 Top Users by Tool Calls</h3>
            {userStats.length === 0 ? <p className="text-gray-400 text-sm text-center py-6">No data</p> : (
              <div className="space-y-3">
                {userStats.slice(0, 8).map((u, i) => (
                  <div key={i}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-medium text-gray-800">{u.username}</span>
                      <span className="text-xs text-gray-500">{u.sessions} sessions</span>
                    </div>
                    <Bar value={u.tool_calls || 0} max={maxUserCalls} color="#10b981" />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Team Stats */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-5">
            <h3 className="font-semibold text-gray-900 mb-4">🏢 Team MCP Usage</h3>
            {teamStats.length === 0 ? (
              <p className="text-gray-400 text-sm text-center py-6">No team data — assign users to teams in IAM</p>
            ) : (
              <div className="space-y-3">
                {teamStats.map((t, i) => (
                  <div key={i}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-medium text-gray-800">{t.team}</span>
                      <span className="text-xs text-gray-500">{t.members_active} active members</span>
                    </div>
                    <Bar value={t.tool_calls || 0} max={maxTeamCalls} color="#f59e0b" />
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
