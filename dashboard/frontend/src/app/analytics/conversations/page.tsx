'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { useAuthStore } from '@/stores/authStore';
import { useRouter } from 'next/navigation';

interface Conversation {
  conversation_id: string;
  user_id: number;
  started_at: string;
  ended_at: string;
  duration_seconds: number;
  activity_count: number;
  tool_calls: number;
  avg_tool_duration_ms: number | null;
  mcp_servers: string[];
  first_message: string;
}

interface User {
  id: number;
  email: string;
}

export default function ConversationsPage() {
  const router = useRouter();
  const { user, isAuthenticated, fetchUser } = useAuthStore();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [searchUserId, setSearchUserId] = useState('');
  const [searchUsername, setSearchUsername] = useState('');
  const [searchConvId, setSearchConvId] = useState('');
  const [searchDateFrom, setSearchDateFrom] = useState('');
  const [searchDateTo, setSearchDateTo] = useState('');

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
      loadConversations();
    }
  }, [isAuthenticated]);

  const loadUsers = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await axios.get('http://localhost:8500/api/v1/monitoring/users', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      setUsers(response.data.users || []);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const loadConversations = async () => {
    setLoading(true);
    try {
      const params: any = { limit: 50 };

      // Handle username search by converting to user_id
      if (searchUsername) {
        const matchedUser = users.find(u =>
          u.email.toLowerCase().includes(searchUsername.toLowerCase())
        );
        if (matchedUser) {
          params.user_id = matchedUser.id;
        }
      } else if (searchUserId) {
        params.user_id = parseInt(searchUserId);
      }

      if (searchDateFrom) params.date_from = searchDateFrom;
      if (searchDateTo) params.date_to = searchDateTo;

      const response = await axios.get('http://localhost:8500/api/v1/activities/conversations', { params });
      let results = response.data.conversations || [];

      // Client-side filter by conversation_id if provided
      if (searchConvId) {
        results = results.filter((c: Conversation) =>
          c.conversation_id.toLowerCase().includes(searchConvId.toLowerCase())
        );
      }

      setConversations(results);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = () => {
    loadConversations();
  };

  const handleClear = () => {
    setSearchUserId('');
    setSearchUsername('');
    setSearchConvId('');
    setSearchDateFrom('');
    setSearchDateTo('');
    loadConversations();
  };

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const getPerformanceBadge = (avgDuration: number | null) => {
    if (!avgDuration) return { label: 'N/A', color: 'bg-gray-100 text-gray-600' };
    if (avgDuration < 1000) return { label: '🟢 Fast', color: 'bg-green-100 text-green-700' };
    if (avgDuration < 5000) return { label: '🟡 Medium', color: 'bg-yellow-100 text-yellow-700' };
    return { label: '🔴 Slow', color: 'bg-red-100 text-red-700' };
  };

  const getUserDisplay = (userId: number) => {
    const user = users.find(u => u.id === userId);
    return user ? user.email : `User ${userId}`;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-purple-800 bg-clip-text text-transparent">
            Omni2 Dashboard
          </h1>
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
          <h2 className="text-2xl font-bold text-gray-900">🤖 AI Interaction Flows</h2>
          <p className="text-gray-600 mt-1">Visualize conversations, AI decisions, and MCP tool execution</p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">🔍 Search & Filter</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                👤 User ID
              </label>
              <input
                type="number"
                value={searchUserId}
                onChange={(e) => setSearchUserId(e.target.value)}
                placeholder="e.g., 1"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                📧 Username/Email
              </label>
              <input
                type="text"
                list="usernames"
                value={searchUsername}
                onChange={(e) => setSearchUsername(e.target.value)}
                placeholder="e.g., avi@omni.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
              <datalist id="usernames">
                {users.map(user => (
                  <option key={user.id} value={user.email} />
                ))}
              </datalist>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                🆔 Conversation ID
              </label>
              <input
                type="text"
                value={searchConvId}
                onChange={(e) => setSearchConvId(e.target.value)}
                placeholder="Full or partial ID"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                📅 From Date
              </label>
              <input
                type="datetime-local"
                value={searchDateFrom}
                onChange={(e) => setSearchDateFrom(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                📅 To Date
              </label>
              <input
                type="datetime-local"
                value={searchDateTo}
                onChange={(e) => setSearchDateTo(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
          </div>
          <div className="flex gap-3">
            <button
              onClick={handleSearch}
              className="px-6 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors font-medium"
            >
              🔍 Search
            </button>
            <button
              onClick={handleClear}
              className="px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors font-medium"
            >
              Clear
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
            <p className="text-gray-600">Loading...</p>
          </div>
        ) : conversations.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
            <div className="text-6xl mb-4">💬</div>
            <p className="text-gray-600">No conversations found</p>
          </div>
        ) : (
          <div className="space-y-4">
            {conversations.map((conv) => {
              const perfBadge = getPerformanceBadge(conv.avg_tool_duration_ms);
              return (
                <Link
                  key={conv.conversation_id}
                  href={`/analytics/conversations/id?id=${conv.conversation_id}`}
                  className="block bg-white rounded-xl border border-gray-200 p-6 hover:shadow-md transition-shadow"
                >
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <span className="text-2xl">💬</span>
                        <h3 className="text-lg font-semibold text-gray-900">
                          {conv.first_message || 'Conversation'}
                        </h3>
                      </div>
                      <div className="flex items-center gap-4 text-sm text-gray-600">
                        <span>👤 {getUserDisplay(conv.user_id)}</span>
                        <span>📅 {new Date(conv.started_at).toLocaleString()}</span>
                        <span>⏱️ {formatDuration(conv.duration_seconds)}</span>
                      </div>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${perfBadge.color}`}>
                      {perfBadge.label}
                    </span>
                  </div>

                  <div className="flex items-center gap-6 text-sm">
                    <span className="text-gray-600">Activities: <strong>{conv.activity_count}</strong></span>
                    <span className="text-gray-600">🔧 Tools: <strong>{conv.tool_calls}</strong></span>
                    {conv.mcp_servers.length > 0 && (
                      <div className="flex gap-1">
                        {conv.mcp_servers.map((mcp, idx) => (
                          <span key={idx} className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">
                            {mcp}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
