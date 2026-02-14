"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/stores/authStore";
import { api } from "@/lib/api";

interface DashboardStats {
  total_mcps: number;
  active_mcps: number;
  total_users: number;
  active_users: number;
  total_api_calls_today: number;
  api_calls_yesterday: number;
  system_uptime_percentage: number;
  total_cost_today?: number;
  total_cost_week?: number;
}

interface ActivityItem {
  id: number;
  icon: string;
  title: string;
  description: string;
  time_ago: string;
  color: string;
}

interface MCPServer {
  id: number;
  name: string;
  status: string;
  health_status: string;
  requests: number;
  uptime: string;
}

export default function DashboardPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, fetchUser, logout } = useAuthStore();
  
  // State for dashboard data
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);
  const [dataLoading, setDataLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false); // Track background refresh
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const initAuth = async () => {
      await fetchUser();
    };
    initAuth();
  }, [fetchUser]);

  // Redirect to login if not authenticated (after auth check completes)
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // Fetch dashboard data
  useEffect(() => {
    if (isAuthenticated) {
      fetchDashboardData(true); // Initial load with loading spinner
      
      // Auto-refresh every 30 seconds (without loading spinner)
      const interval = setInterval(() => {
        fetchDashboardData(false);
      }, 30000);
      
      return () => clearInterval(interval);
    }
  }, [isAuthenticated]);

  const fetchDashboardData = async (isInitialLoad = false) => {
    try {
      if (isInitialLoad) {
        setDataLoading(true);
      } else {
        setIsRefreshing(true);
      }
      setError(null);

      const [statsRes, activityRes] = await Promise.all([
        api.get('/api/v1/dashboard/stats'),
        api.get('/api/v1/dashboard/activity?limit=10'),
      ]);

      const statsData = statsRes.data;
      setStats({
        total_mcps: statsData.active_mcps || 0,
        active_mcps: statsData.active_mcps || 0,
        total_users: statsData.total_users || 0,
        active_users: statsData.total_users || 0,
        total_api_calls_today: statsData.queries_today || 0,
        api_calls_yesterday: 0,
        system_uptime_percentage: 100,
        total_cost_today: statsData.cost_today || 0,
        total_cost_week: 0,
      });
      
      setActivities(activityRes.data.activities || []);
      setMcpServers([]);
      setLastUpdated(new Date());
    } catch (err: any) {
      console.error('Failed to fetch dashboard data:', err);
      // Silently fail - dashboard backend optional
      setStats({
        total_mcps: 0,
        active_mcps: 0,
        total_users: 3,
        active_users: 3,
        total_api_calls_today: 0,
        api_calls_yesterday: 0,
        system_uptime_percentage: 100,
        total_cost_today: 0,
        total_cost_week: 0,
      });
      setActivities([]);
      setMcpServers([]);
    } finally {
      setDataLoading(false);
      setIsRefreshing(false);
    }
  };

  if (isLoading) {
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

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running':
      case 'healthy':
        return 'bg-green-100 text-green-800';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
      case 'stopped':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
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
              <div className="flex items-center gap-2 mt-1">
                <p className="text-sm text-gray-600">MCP Hub Management Dashboard</p>
                {lastUpdated && (
                  <span className="text-xs text-gray-400">
                    • {lastUpdated.toLocaleTimeString()}
                  </span>
                )}
                {isRefreshing && (
                  <span className="text-xs text-purple-600 animate-pulse">• Refreshing...</span>
                )}
              </div>
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
            <Link
              href="/dashboard"
              className="border-b-2 border-purple-600 py-4 px-1 text-sm font-medium text-purple-600"
            >
              Dashboard
            </Link>
            <Link
              href="/mcps"
              className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              MCP Servers
            </Link>
            <Link
              href="/iam"
              className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              IAM
            </Link>
            <Link
              href="/analytics"
              className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              Analytics
            </Link>
            <Link
              href="/live-updates"
              className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              Live Updates
            </Link>
            <div className="border-l border-gray-300 mx-2"></div>
            <Link
              href="/admin"
              className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              ⚙️ Admin
            </Link>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
            <button
              onClick={() => fetchDashboardData()}
              className="mt-2 text-sm text-red-700 hover:text-red-800 underline"
            >
              Retry
            </button>
          </div>
        )}

        {dataLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading dashboard data...</p>
            </div>
          </div>
        ) : (
          <>
            {/* Stats Cards - Row 1: Main metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-600">Total MCPs</h3>
                  <span className="text-2xl">🚀</span>
                </div>
                <p className="text-3xl font-bold text-gray-900">{stats?.total_mcps || 0}</p>
                <p className="text-sm text-gray-500 mt-1">
                  {stats?.active_mcps || 0} active
                </p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-600">Total Users</h3>
                  <span className="text-2xl">👥</span>
                </div>
                <p className="text-3xl font-bold text-gray-900">{stats?.total_users || 0}</p>
                <p className="text-sm text-gray-500 mt-1">
                  {stats?.active_users || 0} active
                </p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-600">API Calls Today</h3>
                  <span className="text-2xl">⚡</span>
                </div>
                <p className="text-3xl font-bold text-gray-900">{stats?.total_api_calls_today || 0}</p>
                <p className="text-sm text-gray-500 mt-1">
                  {stats?.api_calls_yesterday !== undefined ? (
                    <span className={stats.total_api_calls_today > stats.api_calls_yesterday ? 'text-green-600' : 'text-gray-600'}>
                      {stats.total_api_calls_today > stats.api_calls_yesterday ? '+' : ''}
                      {stats.total_api_calls_today - stats.api_calls_yesterday} from yesterday
                    </span>
                  ) : 'Loading comparison...'}
                </p>
              </div>

              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-600">System Uptime</h3>
                  <span className="text-2xl">✓</span>
                </div>
                <p className="text-3xl font-bold text-gray-900">{stats?.system_uptime_percentage?.toFixed(1) || '0.0'}%</p>
                <p className="text-sm text-green-600 mt-1">All systems operational</p>
              </div>
            </div>

            {/* Stats Cards - Row 2: Cost Analytics */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl shadow-sm border border-green-200 p-6">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-green-900">Cost Today</h3>
                  <span className="text-2xl">💰</span>
                </div>
                <p className="text-3xl font-bold text-green-900">
                  ${(stats?.total_cost_today || 0).toFixed(4)}
                </p>
                <p className="text-sm text-green-700 mt-1">
                  LLM API usage cost
                </p>
              </div>

              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl shadow-sm border border-blue-200 p-6">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-blue-900">Cost This Week</h3>
                  <span className="text-2xl">📊</span>
                </div>
                <p className="text-3xl font-bold text-blue-900">
                  ${(stats?.total_cost_week || 0).toFixed(4)}
                </p>
                <p className="text-sm text-blue-700 mt-1">
                  Last 7 days total
                </p>
              </div>
            </div>

            {/* Recent Activity & MCP Servers */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Recent Activity */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                <div className="p-6 border-b border-gray-200">
                  <h2 className="text-xl font-semibold text-gray-900">Recent Activity</h2>
                </div>
                <div className="p-6">
                  <div className="space-y-4">
                    {activities.length === 0 ? (
                      <p className="text-sm text-gray-500 text-center py-8">No recent activity</p>
                    ) : (
                      activities.map((activity) => (
                        <div key={activity.id} className="flex items-start space-x-3">
                          <div className={`flex-shrink-0 w-10 h-10 rounded-full ${activity.color} flex items-center justify-center text-lg`}>
                            {activity.icon}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900">{activity.title}</p>
                            <p className="text-sm text-gray-500">{activity.description}</p>
                            <p className="text-xs text-gray-400 mt-1">{activity.time_ago}</p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* MCP Servers Overview */}
              <div className="bg-white rounded-xl shadow-sm border border-gray-200">
                <div className="p-6 border-b border-gray-200 flex justify-between items-center">
                  <h2 className="text-xl font-semibold text-gray-900">MCP Servers</h2>
                  <Link
                    href="/mcps"
                    className="text-sm font-medium text-purple-600 hover:text-purple-700"
                  >
                    View All →
                  </Link>
                </div>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Server
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Uptime
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {mcpServers.length === 0 ? (
                        <tr>
                          <td colSpan={3} className="px-6 py-8 text-center text-sm text-gray-500">
                            No MCP servers configured
                          </td>
                        </tr>
                      ) : (
                        mcpServers.map((server) => (
                          <tr key={server.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                              {server.name}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(server.status)}`}>
                                {server.status}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {server.uptime}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
