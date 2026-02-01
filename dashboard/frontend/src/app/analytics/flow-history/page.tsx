'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
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
      const response = await axios.get('http://localhost:8500/api/v1/monitoring/users');
      setUsers(response.data.users || []);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const loadSessions = async (userId: number) => {
    setLoading(true);
    try {
      const response = await axios.get('http://localhost:8500/api/v1/flows/user/' + userId + '/sessions');
      setSessions(response.data.sessions || []);
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
      auth_check: '#3b82f6',
      block_check: '#8b5cf6',
      usage_check: '#06b6d4',
      mcp_permission_check: '#10b981',
      tool_filter: '#f59e0b',
      llm_thinking: '#ec4899',
      tool_call: '#6366f1',
      llm_complete: '#22c55e',
      error: '#ef4444',
    };
    return colors[checkpoint] || '#6b7280';
  };

  const formatTimestamp = (timestamp: string | number) => {
    const ts = typeof timestamp === 'string' ? parseFloat(timestamp) : timestamp;
    return new Date(ts * 1000).toLocaleTimeString();
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

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
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

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
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

          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🔄 Flow Graph</h3>
            {!selectedSession ? (
              <div className="text-center py-12 text-gray-500">
                <div className="text-4xl mb-3">👈</div>
                <p>Select a session to view flow</p>
              </div>
            ) : (
              <div className="max-h-96 overflow-y-auto">
                <div className="relative">
                  {selectedSession.events.map((event: any, idx: number) => (
                    <div key={event.node_id || idx} className="relative">
                      {idx < selectedSession.events.length - 1 && (
                        <div className="absolute left-6 top-12 w-0.5 h-8 bg-gray-300 z-0" />
                      )}
                      
                      <div className="relative z-10 flex items-start gap-3 mb-4">
                        <div
                          className="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center shadow-md"
                          style={{ backgroundColor: getCheckpointColor(event.event_type) }}
                        >
                          <span className="text-white font-bold text-sm">{idx + 1}</span>
                        </div>
                        
                        <div className="flex-1 bg-gray-50 rounded-lg p-3 border border-gray-200">
                          <div className="font-semibold text-sm mb-1" style={{ color: getCheckpointColor(event.event_type) }}>
                            {event.event_type.replace(/_/g, ' ').toUpperCase()}
                          </div>
                          <div className="text-xs text-gray-600 mb-2">
                            ⏱️ {formatTimestamp(event.timestamp)}
                          </div>
                          {event.status && (
                            <div className="text-xs mb-1">
                              <span className="font-medium">Status:</span>{' '}
                              <span className={event.status === 'passed' ? 'text-green-600' : 'text-red-600'}>
                                {event.status}
                              </span>
                            </div>
                          )}
                          {event.remaining && (
                            <div className="text-xs text-gray-600">
                              <span className="font-medium">Remaining:</span> {event.remaining}
                            </div>
                          )}
                          {event.tokens && (
                            <div className="text-xs text-gray-600">
                              <span className="font-medium">Tokens:</span> {event.tokens}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}