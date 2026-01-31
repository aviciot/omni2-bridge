'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/stores/authStore';
import { useRouter } from 'next/navigation';

interface ConfigItem {
  key: string;
  value: any;
  description: string;
  type: 'json' | 'number' | 'boolean' | 'string';
}

const CONFIG_METADATA: Record<string, { description: string; type: 'json' | 'number' | 'boolean' | 'string' }> = {
  alert_thresholds: { description: 'Alert thresholds (cost_daily, error_rate, response_time_p99)', type: 'json' },
  chart_settings: { description: 'Chart display settings (cost_period, queries_hours, response_time_hours)', type: 'json' },
  dev_features: { description: 'Development features (websocket_debug, quick_login, quick_login_email, quick_login_password)', type: 'json' },
  dev_mode: { description: 'Development mode toggle', type: 'string' },
  live_updates: { description: 'Live updates settings (max_stored_events: number of events to keep in memory)', type: 'json' },
  refresh_interval: { description: 'Auto-refresh intervals in seconds (stats, charts, activity)', type: 'json' },
  logging: { description: 'Logging verbosity settings (websocket_verbose, mcp_registry_verbose, circuit_breaker_verbose, frontend_verbose)', type: 'json' },
  notifications: { description: 'Notification settings (enabled, sound_enabled, auto_dismiss times, critical_always_show, max_visible)', type: 'json' },
};

export default function AdminPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading, fetchUser, logout } = useAuthStore();
  const [config, setConfig] = useState<ConfigItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    const initAuth = async () => {
      await fetchUser();
    };
    initAuth();
  }, [fetchUser]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadConfig();
    }
  }, [isAuthenticated]);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('http://localhost:8500/api/v1/config', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      
      if (data.success) {
        const items: ConfigItem[] = Object.entries(data.config).map(([key, value]) => ({
          key,
          value,
          description: CONFIG_METADATA[key]?.description || 'No description',
          type: CONFIG_METADATA[key]?.type || 'json'
        }));
        setConfig(items);
      }
    } catch (e) {
      console.error('Failed to load config:', e);
      showMessage('error', 'Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const startEdit = (item: ConfigItem) => {
    setEditingKey(item.key);
    setEditValue(typeof item.value === 'string' ? item.value : JSON.stringify(item.value, null, 2));
  };

  const cancelEdit = () => {
    setEditingKey(null);
    setEditValue('');
  };

  const saveEdit = async (key: string, type: string) => {
    setSaving(true);
    try {
      let parsedValue: any;
      
      if (type === 'json') {
        parsedValue = JSON.parse(editValue);
      } else if (type === 'number') {
        parsedValue = Number(editValue);
      } else if (type === 'boolean') {
        parsedValue = editValue === 'true';
      } else {
        parsedValue = editValue;
      }

      const token = localStorage.getItem('access_token');
      const res = await fetch('http://localhost:8500/api/v1/config', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ key, value: parsedValue })
      });

      const data = await res.json();
      
      if (data.success) {
        showMessage('success', data.message);
        setEditingKey(null);
        setEditValue('');
        await loadConfig();
      } else {
        showMessage('error', 'Failed to update configuration');
      }
    } catch (e: any) {
      console.error('Failed to save config:', e);
      showMessage('error', e.message || 'Invalid JSON format');
    } finally {
      setSaving(false);
    }
  };

  const showMessage = (type: 'success' | 'error', text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
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

      {/* Navigation */}
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
            <Link href="/analytics" className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">
              Analytics
            </Link>
            <Link href="/live-updates" className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">
              Live Updates
            </Link>
            <Link href="/admin" className="border-b-2 border-purple-600 py-4 px-1 text-sm font-medium text-purple-600">
              Admin
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">⚙️ Dashboard Configuration</h2>
              <p className="text-gray-600 mt-1">View and manage dashboard settings</p>
            </div>
            <button
              onClick={loadConfig}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-400 text-white rounded-lg text-sm font-medium transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Reload
            </button>
          </div>
        </div>

        {/* Message Toast */}
        {message && (
          <div className={`mb-6 p-4 rounded-lg border ${
            message.type === 'success' 
              ? 'bg-green-50 border-green-200 text-green-800' 
              : 'bg-red-50 border-red-200 text-red-800'
          }`}>
            <div className="flex items-center gap-2">
              <span className="text-lg">{message.type === 'success' ? '✅' : '❌'}</span>
              <span className="font-medium">{message.text}</span>
            </div>
          </div>
        )}

        {/* Configuration Cards */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
            <p className="mt-4 text-gray-600">Loading configuration...</p>
          </div>
        ) : (
          <div className="space-y-4">
            {config.map((item) => (
              <div key={item.key} className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
                <div className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">{item.key}</h3>
                      <p className="text-sm text-gray-600 mt-1">{item.description}</p>
                      <span className="inline-block mt-2 px-2 py-1 text-xs font-mono bg-gray-100 text-gray-700 rounded">
                        {item.type}
                      </span>
                    </div>
                    {editingKey !== item.key && (
                      <button
                        onClick={() => startEdit(item)}
                        className="px-3 py-1.5 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm font-medium border border-blue-200 transition-colors"
                      >
                        ✏️ Edit
                      </button>
                    )}
                  </div>

                  {editingKey === item.key ? (
                    <div className="space-y-3">
                      <textarea
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        rows={item.type === 'json' ? 8 : 3}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                      />
                      <div className="flex gap-2">
                        <button
                          onClick={() => saveEdit(item.key, item.type)}
                          disabled={saving}
                          className="px-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white rounded-lg text-sm font-medium transition-colors"
                        >
                          {saving ? 'Saving...' : '💾 Save'}
                        </button>
                        <button
                          onClick={cancelEdit}
                          disabled={saving}
                          className="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium border border-gray-300 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <pre className="bg-gray-50 p-4 rounded-lg border border-gray-200 overflow-x-auto text-sm text-gray-700 font-mono">
                      {typeof item.value === 'string' ? item.value : JSON.stringify(item.value, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
