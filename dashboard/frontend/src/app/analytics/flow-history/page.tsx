'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/stores/authStore';
import { useRouter } from 'next/navigation';

interface FlowSession {
  session_id: string;
  started_at: string;
  completed_at: string;
  event_count: number;
  events: any[];
}

export default function FlowHistoryPage() {
  const router = useRouter();
  const { user, isAuthenticated, fetchUser, logout } = useAuthStore();
  const [users, setUsers] = useState<any[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [sessions, setSessions] = useState<FlowSession[]>([]);
  const [selectedSession, setSelectedSession] = useState<FlowSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());

  useEffect(() => {
    const initAuth = async () => {
      await fetchUser();
      if (!isAuthenticated) {
        router.push('/login');
      }
    };
    initAuth();
  }, [isAuthenticated, fetchUser, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadUsers();
    }
  }, [isAuthenticated]);

  const loadUsers = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:8500/api/v1/monitoring/users', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setUsers(data.users || []);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const loadSessions = async (userId: number) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`http://localhost:8500/api/v1/flows/user/${userId}/sessions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setSessions(data.sessions || []);
      setSelectedSession(null);
    } catch (error) {
      console.error('Failed to load sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUserSelect = (userId: number) => {
    setSelectedUserId(userId);
    loadSessions(userId);
  };

  const getCheckpointColor = (checkpoint: string) => {
    const colors: Record<string, string> = {
      auth_check: '#3b82f6',        // Blue - Security
      block_check: '#8b5cf6',       // Purple - Blocking
      usage_check: '#06b6d4',       // Cyan - Usage/Quota
      mcp_permission_check: '#10b981', // Green - Permissions
      tool_filter: '#f59e0b',       // Amber - Filtering
      llm_thinking: '#ec4899',      // Pink - AI Processing
      tool_call: '#6366f1',         // Indigo - Tool Execution
      llm_complete: '#22c55e',      // Green - Success
      error: '#ef4444',             // Red - Error
    };
    return colors[checkpoint] || '#6b7280';
  };

  const getCheckpointIcon = (checkpoint: string) => {
    const icons: Record<string, string> = {
      auth_check: '🔐',
      block_check: '🚫',
      usage_check: '📊',
      mcp_permission_check: '✅',
      tool_filter: '🔍',
      llm_thinking: '🤖',
      tool_call: '⚡',
      llm_complete: '✨',
      error: '❌',
    };
    return icons[checkpoint] || '📌';
  };

  const formatTimestamp = (timestamp: string | number) => {
    const ts = typeof timestamp === 'string' ? parseFloat(timestamp) : timestamp;
    return new Date(ts * 1000).toLocaleTimeString();
  };

  const toggleNodeExpansion = (nodeId: string) => {
    setExpandedNodes(prev => {
      const newSet = new Set(prev);
      if (newSet.has(nodeId)) {
        newSet.delete(nodeId);
      } else {
        newSet.add(nodeId);
      }
      return newSet;
    });
  };

  const parseJsonField = (field: string) => {
    try {
      // Try to parse if it's a stringified array or object
      if (field.startsWith('[') || field.startsWith('{')) {
        const parsed = JSON.parse(field.replace(/'/g, '"'));
        if (Array.isArray(parsed)) {
          return parsed.join(', ');
        }
        return JSON.stringify(parsed, null, 2);
      }
      return field;
    } catch {
      // If parsing fails, clean up the string
      return field.replace(/[\[\]']/g, '');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-purple-800 bg-clip-text text-transparent">
                Omni2 Admin
              </h1>
              <p className="text-sm text-gray-600 mt-1">MCP Hub Management Dashboard</p>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">
                Welcome, <span className="font-semibold">{user?.email}</span>
              </span>
              <button
                onClick={logout}
                className="px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <Link href="/dashboard" className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">
              Dashboard
            </Link>
            <Link href="/mcps" className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">
              MCP Servers
            </Link>
            <Link href="/iam" className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">
              IAM
            </Link>
            <Link href="/analytics" className="border-b-2 border-purple-600 py-4 px-1 text-sm font-medium text-purple-600">
              Analytics
            </Link>
            <Link href="/live-updates" className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">
              Live Updates
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900">🔍 Flow History Analytics</h2>
          <p className="text-gray-600 mt-1">Analyze user interaction flows and request lifecycle</p>
        </div>

        {/* Checkpoint Legend */}
        <div className="mb-6 bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl border border-purple-200 p-4">
          <div className="text-sm font-semibold text-gray-700 mb-3">Checkpoint Types:</div>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {[
              { type: 'auth_check', label: 'Authentication' },
              { type: 'block_check', label: 'Block Check' },
              { type: 'usage_check', label: 'Usage/Quota' },
              { type: 'mcp_permission_check', label: 'MCP Permissions' },
              { type: 'tool_filter', label: 'Tool Filter' },
              { type: 'llm_thinking', label: 'AI Processing' },
              { type: 'tool_call', label: 'Tool Execution' },
              { type: 'llm_complete', label: 'Complete' },
              { type: 'error', label: 'Error' },
            ].map(({ type, label }) => (
              <div key={type} className="flex items-center gap-2 bg-white rounded-lg px-3 py-2 border border-gray-200">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-sm"
                  style={{ backgroundColor: getCheckpointColor(type) }}
                >
                  <span>{getCheckpointIcon(type)}</span>
                </div>
                <span className="text-xs font-medium text-gray-700">{label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-3 bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">👤 Select User</h3>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {users.map(user => (
                <button
                  key={user.id}
                  onClick={() => handleUserSelect(user.id)}
                  className={`w-full text-left px-4 py-3 rounded-lg border transition-colors ${
                    selectedUserId === user.id
                      ? 'bg-purple-50 border-purple-300 text-purple-900'
                      : 'bg-white border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="font-medium">{user.email}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="lg:col-span-3 bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              📋 Recent Sessions {loading && <span className="text-sm text-gray-500">(Loading...)</span>}
            </h3>
            {!selectedUserId ? (
              <div className="text-center py-12 text-gray-500">
                <div className="text-4xl mb-3">👈</div>
                <p>Select a user to view flow history</p>
              </div>
            ) : sessions.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <div className="text-4xl mb-3">📭</div>
                <p>No sessions found</p>
              </div>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {sessions.map((session, idx) => (
                  <button
                    key={session.session_id}
                    onClick={() => setSelectedSession(session)}
                    className={`w-full text-left px-4 py-3 rounded-lg border transition-colors ${
                      selectedSession?.session_id === session.session_id
                        ? 'bg-blue-50 border-blue-300'
                        : 'bg-white border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-xs font-semibold text-gray-700">
                        Request #{sessions.length - idx}
                      </span>
                      <span className="text-xs bg-gray-100 px-2 py-1 rounded">
                        {session.event_count} steps
                      </span>
                    </div>
                    <div className="text-xs text-gray-500">
                      {new Date(session.started_at).toLocaleString()}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="lg:col-span-6 bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">🔄 Flow Graph</h3>
              {selectedSession && (
                <div className="flex items-center gap-3 text-sm">
                  <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full font-medium border border-purple-300">
                    {selectedSession.events.length} steps
                  </span>
                  <span className="text-gray-500">
                    {new Date(selectedSession.started_at).toLocaleTimeString()}
                  </span>
                </div>
              )}
            </div>
            {!selectedSession ? (
              <div className="text-center py-12 text-gray-500">
                <div className="text-4xl mb-3">👈</div>
                <p>Select a session to view flow</p>
              </div>
            ) : (
              <div className="max-h-[calc(100vh-300px)] overflow-y-auto pr-2">
                <div className="relative">
                  {selectedSession.events.map((event: any, idx: number) => {
                    const isExpanded = expandedNodes.has(event.node_id || idx.toString());
                    const hasAdditionalData = event.mcp_access || event.available_mcps ||
                                             event.tool_restrictions || (event.mcp && event.tool) ||
                                             event.error;

                    return (
                      <div key={event.node_id || idx} className="relative">
                        {idx < selectedSession.events.length - 1 && (
                          <div className="absolute left-6 top-12 w-0.5 h-full bg-gray-300 z-0" />
                        )}

                        <div className="relative z-10 flex items-start gap-3 mb-4">
                          <div
                            className="flex-shrink-0 w-12 h-12 rounded-full flex flex-col items-center justify-center shadow-lg border-2 border-white"
                            style={{ backgroundColor: getCheckpointColor(event.event_type) }}
                          >
                            <span className="text-lg">{getCheckpointIcon(event.event_type)}</span>
                            <span className="text-white font-bold text-[10px]">{idx + 1}</span>
                          </div>

                          <div className="flex-1 bg-white rounded-lg p-4 border-2 border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                            {/* Header */}
                            <div className="flex items-start justify-between mb-3">
                              <div>
                                <div className="font-bold text-base mb-1" style={{ color: getCheckpointColor(event.event_type) }}>
                                  {event.event_type.replace(/_/g, ' ').toUpperCase()}
                                </div>
                                <div className="text-xs text-gray-500">
                                  ⏱️ {formatTimestamp(event.timestamp)}
                                </div>
                              </div>

                              {/* Status Badge */}
                              {event.status && (
                                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                                  event.status === 'passed'
                                    ? 'bg-green-100 text-green-700 border border-green-300'
                                    : 'bg-red-100 text-red-700 border border-red-300'
                                }`}>
                                  {event.status === 'passed' ? '✓ Passed' : '✗ Failed'}
                                </span>
                              )}
                            </div>

                            {/* Quick Info */}
                            <div className="space-y-2">
                              {/* Remaining Credits */}
                              {event.remaining && (
                                <div className="flex items-center gap-2 text-sm">
                                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center text-blue-600">
                                    💰
                                  </span>
                                  <span className="text-gray-700">
                                    <span className="font-medium">Credits Remaining:</span>{' '}
                                    <span className="font-semibold text-blue-600">{event.remaining}</span>
                                  </span>
                                </div>
                              )}

                              {/* Tokens Used */}
                              {event.tokens && (
                                <div className="flex items-center gap-2 text-sm">
                                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-100 flex items-center justify-center text-purple-600">
                                    🎯
                                  </span>
                                  <span className="text-gray-700">
                                    <span className="font-medium">Tokens Used:</span>{' '}
                                    <span className="font-semibold text-purple-600">{event.tokens}</span>
                                  </span>
                                </div>
                              )}

                              {/* Tool Call */}
                              {event.mcp && event.tool && (
                                <div className="flex items-center gap-2 text-sm bg-gradient-to-r from-purple-50 to-blue-50 p-3 rounded-lg border border-purple-200">
                                  <span className="flex-shrink-0 text-lg">🔧</span>
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-gray-600 font-medium">Tool Called:</span>
                                    <span className="px-2 py-1 bg-purple-600 text-white rounded font-mono text-xs">
                                      {event.mcp}
                                    </span>
                                    <span className="text-gray-400">→</span>
                                    <span className="px-2 py-1 bg-blue-600 text-white rounded font-mono text-xs">
                                      {event.tool}
                                    </span>
                                  </div>
                                </div>
                              )}

                              {/* Error */}
                              {event.error && (
                                <div className="flex items-start gap-2 text-sm bg-red-50 p-3 rounded-lg border border-red-200">
                                  <span className="flex-shrink-0 text-lg">❌</span>
                                  <div className="flex-1">
                                    <span className="font-medium text-red-700">Error:</span>
                                    <div className="mt-1 text-red-600 font-mono text-xs">
                                      {event.error}
                                    </div>
                                  </div>
                                </div>
                              )}
                            </div>

                            {/* Expandable Detailed Info */}
                            {hasAdditionalData && (
                              <div className="mt-3">
                                <button
                                  onClick={() => toggleNodeExpansion(event.node_id || idx.toString())}
                                  className="text-xs text-purple-600 hover:text-purple-700 font-medium flex items-center gap-1"
                                >
                                  {isExpanded ? '▼' : '▶'} {isExpanded ? 'Hide' : 'Show'} Detailed Info
                                </button>

                                {isExpanded && (
                                  <div className="mt-3 space-y-3 border-t border-gray-200 pt-3">
                                    {/* MCP Access */}
                                    {event.mcp_access && (
                                      <div className="bg-green-50 p-3 rounded-lg border border-green-200">
                                        <div className="flex items-center gap-2 mb-2">
                                          <span className="text-green-600 font-semibold text-sm">✅ MCP Access Granted</span>
                                        </div>
                                        <div className="flex flex-wrap gap-1">
                                          {parseJsonField(event.mcp_access).split(',').map((mcp: string, i: number) => (
                                            <span key={i} className="px-2 py-1 bg-green-600 text-white rounded-full text-xs font-medium">
                                              {mcp.trim()}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}

                                    {/* Available MCPs */}
                                    {event.available_mcps && (
                                      <div className="bg-blue-50 p-3 rounded-lg border border-blue-200">
                                        <div className="flex items-center gap-2 mb-2">
                                          <span className="text-blue-600 font-semibold text-sm">📋 Available MCPs</span>
                                        </div>
                                        <div className="flex flex-wrap gap-1">
                                          {parseJsonField(event.available_mcps).split(',').map((mcp: string, i: number) => (
                                            <span key={i} className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs border border-blue-300">
                                              {mcp.trim()}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}

                                    {/* Tool Restrictions */}
                                    {event.tool_restrictions && (
                                      <div className="bg-amber-50 p-3 rounded-lg border border-amber-200">
                                        <div className="flex items-center gap-2 mb-2">
                                          <span className="text-amber-700 font-semibold text-sm">🔒 Tool Restrictions Applied</span>
                                        </div>
                                        <pre className="text-xs text-amber-800 font-mono bg-amber-100 p-2 rounded overflow-x-auto">
                                          {parseJsonField(event.tool_restrictions)}
                                        </pre>
                                      </div>
                                    )}

                                    {/* Raw Data (Debug) */}
                                    <details className="text-xs">
                                      <summary className="cursor-pointer text-gray-500 hover:text-gray-700 font-medium">
                                        🔍 View Raw Data
                                      </summary>
                                      <pre className="mt-2 bg-gray-100 p-3 rounded text-xs overflow-x-auto border border-gray-300">
                                        {JSON.stringify(event, null, 2)}
                                      </pre>
                                    </details>
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}