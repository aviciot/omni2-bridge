'use client';

import { useState, useEffect, useRef } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/stores/authStore';
import { useRouter } from 'next/navigation';
import MultiUserFlowTracker from '@/components/MultiUserFlowTracker';
import MonitoringConfig from '@/components/MonitoringConfig';

interface LiveEvent {
  type: string;
  timestamp: string;
  data: any;
}

const EVENT_TYPES = [
  { id: 'mcp_status_change', label: 'MCP Status', icon: '🔄' },
  { id: 'circuit_breaker_state', label: 'Circuit Breaker', icon: '⚡' },
  { id: 'mcp_health_check', label: 'Health Check', icon: '🏥' },
  { id: 'mcp_auto_disabled', label: 'Auto-Disabled', icon: '🚫' },
  { id: 'system_health', label: 'System Health', icon: '💓' },
];

export default function LiveUpdatesPage() {
  const router = useRouter();
  const { user, isAuthenticated, fetchUser, logout } = useAuthStore();
  const [allEvents, setAllEvents] = useState<LiveEvent[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = sessionStorage.getItem('live_events');
      return saved ? JSON.parse(saved) : [];
    }
    return [];
  });
  const [isConnected, setIsConnected] = useState(false);
  const [debugInfo, setDebugInfo] = useState<any>(null);
  const [selectedEvents, setSelectedEvents] = useState<string[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('live_updates_selected_events');
      return saved ? JSON.parse(saved) : EVENT_TYPES.map(e => e.id);
    }
    return EVENT_TYPES.map(e => e.id);
  });
  const [displayFilter, setDisplayFilter] = useState<string[]>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('live_updates_display_filter');
      return saved ? JSON.parse(saved) : EVENT_TYPES.map(e => e.id);
    }
    return EVENT_TYPES.map(e => e.id);
  });
  const [autoScroll, setAutoScroll] = useState(true);
  const [pauseWhenInactive, setPauseWhenInactive] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('live_updates_pause_inactive');
      return saved ? JSON.parse(saved) : true;
    }
    return true;
  });
  const [maxEvents, setMaxEvents] = useState(50);
  const [maxStoredEvents, setMaxStoredEvents] = useState(1000);
  const [pingLatency, setPingLatency] = useState<number | null>(null);
  const [connectionUptime, setConnectionUptime] = useState(0);
  const [eventCount, setEventCount] = useState(0);
  const [monitoredUsers, setMonitoredUsers] = useState<Array<{user_id: number; email: string}>>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const isConnecting = useRef(false);
  const connectionStartTime = useRef<number | null>(null);
  const lastPingTime = useRef<number | null>(null);

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
      loadConfig();
      loadMonitoredUsers();
      // Refresh monitored users every 10 seconds
      const interval = setInterval(loadMonitoredUsers, 10000);
      return () => clearInterval(interval);
    }
  }, [isAuthenticated]);

  const loadConfig = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('http://localhost:8500/api/v1/config', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();

      if (data.success && data.config.live_updates) {
        setMaxStoredEvents(data.config.live_updates.max_stored_events || 1000);
      }
    } catch (e) {
      console.error('Failed to load config:', e);
    }
  };

  const loadMonitoredUsers = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const [usersRes, monitoredRes] = await Promise.all([
        fetch('http://localhost:8500/api/v1/monitoring/users', {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch('http://localhost:8500/api/v1/monitoring/list', {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ]);

      const usersData = await usersRes.json();
      const monitoredData = await monitoredRes.json();

      const users = usersData.users || [];
      const monitoredIds = (monitoredData.monitored_users || []).map((m: any) => m.user_id);

      const monitoredUsersList = users.filter((u: any) => monitoredIds.includes(u.id)).map((u: any) => ({
        user_id: u.id,
        email: u.email
      }));

      setMonitoredUsers(monitoredUsersList);
    } catch (e) {
      console.error('Failed to load monitored users:', e);
    }
  };

  useEffect(() => {
    if (!isAuthenticated) return;
    
    console.log('🚀 Initializing WebSocket connection...');
    connectWebSocket();
    
    // Update connection uptime every second
    const uptimeInterval = setInterval(() => {
      if (connectionStartTime.current) {
        setConnectionUptime(Math.floor((Date.now() - connectionStartTime.current) / 1000));
      }
    }, 1000);
    
    return () => {
      console.log('🛑 Cleaning up WebSocket...');
      clearInterval(uptimeInterval);
      isConnecting.current = false;
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting');
        wsRef.current = null;
      }
    };
  }, []);

  // Resubscribe when event selection changes
  useEffect(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      const subscribeMsg = {
        action: 'subscribe',
        event_types: selectedEvents,
        filters: {}
      };
      wsRef.current.send(JSON.stringify(subscribeMsg));
    }
    // Persist to localStorage
    localStorage.setItem('live_updates_selected_events', JSON.stringify(selectedEvents));
  }, [selectedEvents]);

  // Persist display filter changes
  useEffect(() => {
    localStorage.setItem('live_updates_display_filter', JSON.stringify(displayFilter));
  }, [displayFilter]);

  // Persist pause setting
  useEffect(() => {
    localStorage.setItem('live_updates_pause_inactive', JSON.stringify(pauseWhenInactive));
  }, [pauseWhenInactive]);

  // Handle page visibility - pause WebSocket when tab inactive
  useEffect(() => {
    if (!pauseWhenInactive) return;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        console.log('⏸️ Tab inactive - pausing WebSocket');
        if (wsRef.current) {
          wsRef.current.close(1000, 'Tab inactive');
          wsRef.current = null;
        }
        setIsConnected(false);
      } else {
        console.log('▶️ Tab active - resuming WebSocket');
        if (isAuthenticated) {
          connectWebSocket();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [pauseWhenInactive, isAuthenticated]);

  const connectWebSocket = () => {
    if (isConnecting.current || wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('⏭️ Skipping connection - already connecting or connected');
      return;
    }

    const token = localStorage.getItem('access_token');
    if (!token) {
      console.error('❌ No token found');
      return;
    }

    isConnecting.current = true;
    console.log('🔌 Connecting to WebSocket...');
    const ws = new WebSocket(`ws://localhost:8500/ws?token=${token}`);

    ws.onopen = () => {
      console.log('✅ WebSocket connected');
      setIsConnected(true);
      isConnecting.current = false;
      connectionStartTime.current = Date.now();
      
      // Subscribe to selected events
      const subscribeMsg = {
        action: 'subscribe',
        event_types: selectedEvents,
        filters: {}
      };
      console.log('📤 Sending subscription:', subscribeMsg);
      ws.send(JSON.stringify(subscribeMsg));
    };

    ws.onmessage = (event) => {
      console.log('📨 Raw message received:', event.data);
      try {
        const data = JSON.parse(event.data);
        console.log('📦 Parsed message:', data);
        
        if (data.type === 'subscribed') {
          console.log('✅ Subscription confirmed:', data.subscription_id);
        } else if (data.type === 'ping') {
          // Calculate ping latency
          if (lastPingTime.current) {
            const latency = Date.now() - lastPingTime.current;
            setPingLatency(latency);
          }
          lastPingTime.current = Date.now();
        } else if (data.type === 'initial_status') {
          console.log('📊 Initial status received:', data);
        } else {
          console.log('🎯 Event received:', data.type, data);
          setEventCount(prev => prev + 1);
          setAllEvents(prev => {
            const newEvents = [{
              type: data.type,
              timestamp: data.timestamp || new Date().toISOString(),
              data: data.data || data
            }, ...prev].slice(0, maxStoredEvents);
            sessionStorage.setItem('live_events', JSON.stringify(newEvents));
            return newEvents;
          });
        }
      } catch (e) {
        console.error('❌ Failed to parse message:', e, event.data);
      }
    };

    ws.onerror = (error) => {
      console.log('⚠️ WebSocket error (expected during restart)');
      setIsConnected(false);
      isConnecting.current = false;
    };

    ws.onclose = (event) => {
      console.log('🔌 WebSocket closed:', {
        code: event.code,
        reason: event.reason,
        wasClean: event.wasClean
      });
      setIsConnected(false);
      isConnecting.current = false;
      
      // Auto-reconnect after 3 seconds if authenticated
      if (isAuthenticated && event.code !== 1000) {
        console.log('🔄 Reconnecting in 3 seconds...');
        setTimeout(() => {
          console.log('🔄 Attempting reconnection...');
          connectWebSocket();
        }, 3000);
      }
    };

    wsRef.current = ws;
  };

  const fetchDebugInfo = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch('http://localhost:8500/api/v1/events/websocket/debug', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      setDebugInfo(data);
      console.log('🔍 Debug info:', data);
    } catch (e) {
      console.error('❌ Failed to fetch debug info:', e);
    }
  };

  const triggerTestEvent = async () => {
    try {
      console.log('🧪 Triggering test event...');
      const token = localStorage.getItem('access_token');
      const res = await fetch('http://localhost:8500/api/v1/events/test/broadcast', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      console.log('✅ Test event response:', data);
      alert('Test event triggered! Check console and event list.');
    } catch (e) {
      console.error('❌ Failed to trigger test event:', e);
      alert('Failed to trigger test event. Check console.');
    }
  };

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
            <Link href="/live-updates" className="border-b-2 border-purple-600 py-4 px-1 text-sm font-medium text-purple-600">
              Live Updates
            </Link>
            <div className="border-l border-gray-300 mx-2"></div>
            <Link href="/admin" className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">
              ⚙️ Admin
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Live Updates</h2>
              <p className="text-gray-600 mt-1">Real-time MCP events</p>
            </div>
            <div className="flex items-center gap-3">
              <div className={`flex items-center gap-2 px-4 py-2 rounded-lg border ${
                isConnected ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
              }`}>
                <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
                <div className="flex flex-col">
                  <span className={`text-sm font-medium ${isConnected ? 'text-green-700' : 'text-red-700'}`}>
                    {isConnected ? 'Connected' : 'Disconnected'}
                  </span>
                  {isConnected && pingLatency !== null && (
                    <span className="text-xs text-green-600">Ping: {pingLatency}ms</span>
                  )}
                </div>
              </div>
              <button
                onClick={triggerTestEvent}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium"
              >
                🧪 Test
              </button>
              <button
                onClick={fetchDebugInfo}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium"
              >
                🔍 Debug
              </button>
            </div>
          </div>
        </div>

        {/* Debug Info */}
        {debugInfo && (
          <div className="mb-6 bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <div className="flex justify-between items-center mb-2">
              <h3 className="text-lg font-semibold text-gray-900">Debug Information</h3>
              <button
                onClick={() => setDebugInfo(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                ✕
              </button>
            </div>
            <pre className="text-xs text-gray-600 overflow-x-auto bg-gray-50 p-3 rounded border border-gray-200">
              {JSON.stringify(debugInfo, null, 2)}
            </pre>
          </div>
        )}

        {/* Configuration Panel */}
        <div className="mb-6 bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Configuration</h3>
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Event Types */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">Subscribe to Events</label>
              <div className="space-y-2">
                {EVENT_TYPES.map(eventType => (
                  <label key={eventType.id} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedEvents.includes(eventType.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedEvents([...selectedEvents, eventType.id]);
                        } else {
                          setSelectedEvents(selectedEvents.filter(id => id !== eventType.id));
                        }
                      }}
                      className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
                    />
                    <span className="text-sm text-gray-700">{eventType.icon} {eventType.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Settings */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">Settings</label>
              <div className="space-y-3">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoScroll}
                    onChange={(e) => setAutoScroll(e.target.checked)}
                    className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
                  />
                  <span className="text-sm text-gray-700">Auto-scroll</span>
                </label>
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-700">Pause when tab inactive</span>
                    <button
                      onClick={() => setPauseWhenInactive(!pauseWhenInactive)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        pauseWhenInactive ? 'bg-purple-600' : 'bg-gray-300'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          pauseWhenInactive ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>
                  <span className="text-xs text-gray-500">Saves bandwidth</span>
                </div>
                <div>
                  <label className="block text-sm text-gray-700 mb-1">Max Events</label>
                  <select
                    value={maxEvents}
                    onChange={(e) => setMaxEvents(Number(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  >
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                    <option value={200}>200</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Stats */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">Statistics</label>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Events Received:</span>
                  <span className="font-semibold text-gray-900">{eventCount}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Uptime:</span>
                  <span className="font-semibold text-gray-900">
                    {Math.floor(connectionUptime / 60)}m {connectionUptime % 60}s
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Total Stored:</span>
                  <span className="font-semibold text-gray-900">{allEvents.length}/{maxStoredEvents}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Displayed:</span>
                  <span className="font-semibold text-gray-900">{allEvents.filter(e => displayFilter.includes(e.type)).slice(0, maxEvents).length}</span>
                </div>
                <button
                  onClick={() => {
                    setAllEvents([]);
                    setEventCount(0);
                    sessionStorage.removeItem('live_events');
                  }}
                  className="w-full mt-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium border border-gray-300"
                >
                  Clear All
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Debug Info */}
        {debugInfo && (
          <div className="mb-6 bg-white rounded-xl border border-gray-200 shadow-sm p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Debug Information</h3>
            <pre className="text-xs text-gray-600 overflow-x-auto bg-gray-50 p-3 rounded border border-gray-200">
              {JSON.stringify(debugInfo, null, 2)}
            </pre>
          </div>
        )}

        {/* Flow Monitoring Configuration */}
        <div className="mb-6">
          <MonitoringConfig onUpdate={loadMonitoredUsers} />
        </div>

        {/* Multi-User Flow Tracker */}
        <div className="mb-6">
          <MultiUserFlowTracker monitoredUsers={monitoredUsers} />
        </div>

        {/* Events List */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <div className="p-4 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Events ({allEvents.filter(e => displayFilter.includes(e.type)).slice(0, maxEvents).length})</h3>
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-500">
                  Subscribed: {selectedEvents.length} types
                </span>
                <div className="relative">
                  <button
                    onClick={() => {
                      const dropdown = document.getElementById('filter-dropdown');
                      dropdown?.classList.toggle('hidden');
                    }}
                    className="flex items-center gap-2 px-3 py-2 bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg text-sm font-medium border border-blue-200 transition-colors"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                    </svg>
                    Filter ({displayFilter.length})
                  </button>
                  <div
                    id="filter-dropdown"
                    className="hidden absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 z-10"
                  >
                    <div className="p-3">
                      <div className="text-xs font-semibold text-gray-700 mb-2">Display Filter</div>
                      <div className="space-y-2">
                        {EVENT_TYPES.map(eventType => (
                          <label key={eventType.id} className="flex items-center gap-2 cursor-pointer hover:bg-gray-50 p-1 rounded">
                            <input
                              type="checkbox"
                              checked={displayFilter.includes(eventType.id)}
                              onChange={(e) => {
                                if (e.target.checked) {
                                  setDisplayFilter([...displayFilter, eventType.id]);
                                } else {
                                  setDisplayFilter(displayFilter.filter(id => id !== eventType.id));
                                }
                              }}
                              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                            />
                            <span className="text-sm text-gray-700">{eventType.icon} {eventType.label}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="p-4 space-y-3 max-h-[calc(100vh-400px)] overflow-y-auto">
            {allEvents.filter(e => displayFilter.includes(e.type)).slice(0, maxEvents).length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <div className="text-4xl mb-3">📡</div>
                <p className="text-lg font-medium text-gray-700">Waiting for events...</p>
                <p className="text-sm mt-2 text-gray-500">Connected and listening for MCP status changes</p>
              </div>
            ) : (
              allEvents.filter(e => displayFilter.includes(e.type)).slice(0, maxEvents).map((event, idx) => (
                <div
                  key={idx}
                  className="bg-gray-50 rounded-lg border border-gray-200 p-4 hover:border-gray-300 hover:shadow-sm transition-all"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-1 rounded text-xs font-mono bg-purple-100 text-purple-700 border border-purple-200">
                        {event.type}
                      </span>
                      {event.data.severity && (
                        <span className={`px-2 py-1 rounded text-xs uppercase font-medium ${
                          event.data.severity === 'critical' ? 'text-red-700 bg-red-100' :
                          event.data.severity === 'high' ? 'text-orange-700 bg-orange-100' :
                          event.data.severity === 'medium' ? 'text-yellow-700 bg-yellow-100' :
                          'text-blue-700 bg-blue-100'
                        }`}>
                          {event.data.severity}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-gray-500 font-medium">
                      {new Date(event.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  
                  {event.data.mcp_name && (
                    <div className="text-sm font-semibold text-purple-600 mb-2">
                      MCP: {event.data.mcp_name}
                    </div>
                  )}
                  
                  <pre className="text-xs text-gray-600 overflow-x-auto bg-white p-2 rounded border border-gray-200">
                    {JSON.stringify(event.data, null, 2)}
                  </pre>
                </div>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
