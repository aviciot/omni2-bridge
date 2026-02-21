'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Shield, AlertTriangle, Ban, Activity, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

interface SecurityIncident {
  id: number;
  user_id: number;
  user_email?: string;
  message: string;
  injection_score: number;
  action: string;
  detected_at: string;
}

interface BlockedUser {
  user_id: number;
  user_email?: string;
  block_count: number;
  last_blocked: string;
  block_reason?: string;
}

interface SecurityStats {
  total_incidents_24h: number;
  total_incidents_7d: number;
  total_incidents_30d: number;
  blocked_users: number;
  high_risk_incidents: number;
  policy_violations: number;
}

export default function SecurityPage() {
  const [stats, setStats] = useState<SecurityStats>({
    total_incidents_24h: 0,
    total_incidents_7d: 0,
    total_incidents_30d: 0,
    blocked_users: 0,
    high_risk_incidents: 0,
    policy_violations: 0,
  });
  const [incidents, setIncidents] = useState<SecurityIncident[]>([]);
  const [blockedUsers, setBlockedUsers] = useState<BlockedUser[]>([]);
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('24h');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSecurityData();
    const interval = setInterval(fetchSecurityData, 10000);
    return () => clearInterval(interval);
  }, [timeRange]);

  const fetchSecurityData = async () => {
    try {
      const [statsRes, incidentsRes, blockedRes] = await Promise.all([
        fetch('/api/v1/security/stats'),
        fetch(`/api/v1/security/incidents?range=${timeRange}&limit=50`),
        fetch('/api/v1/security/blocked-users'),
      ]);

      if (statsRes.ok) setStats(await statsRes.json());
      if (incidentsRes.ok) setIncidents(await incidentsRes.json());
      if (blockedRes.ok) setBlockedUsers(await blockedRes.json());
    } catch (error) {
      console.error('Failed to fetch security data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getSeverityColor = (score: number) => {
    if (score >= 0.8) return 'text-red-600 bg-red-50';
    if (score >= 0.6) return 'text-orange-600 bg-orange-50';
    if (score >= 0.4) return 'text-yellow-600 bg-yellow-50';
    return 'text-green-600 bg-green-50';
  };

  const getActionBadge = (action: string) => {
    const colors = {
      block: 'bg-red-100 text-red-700 border-red-200',
      warn: 'bg-yellow-100 text-yellow-700 border-yellow-200',
      filter: 'bg-orange-100 text-orange-700 border-orange-200',
      allow: 'bg-green-100 text-green-700 border-green-200',
    };
    return colors[action as keyof typeof colors] || colors.allow;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Link href="/analytics" className="text-gray-500 hover:text-gray-700">
              <ArrowLeft className="w-6 h-6" />
            </Link>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-purple-800 bg-clip-text text-transparent flex items-center gap-3">
              <Shield className="w-8 h-8 text-purple-600" />
              Security Incidents
            </h1>
          </div>
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as any)}
            className="px-4 py-2 bg-white border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
          >
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card className="bg-white border-gray-200">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">Total Incidents</CardTitle>
              <Activity className="w-4 h-4 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-gray-900">
                {timeRange === '24h' && stats.total_incidents_24h}
                {timeRange === '7d' && stats.total_incidents_7d}
                {timeRange === '30d' && stats.total_incidents_30d}
              </div>
              <p className="text-xs text-gray-500 mt-1">Injection attempts detected</p>
            </CardContent>
          </Card>

          <Card className="bg-white border-gray-200">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">High Risk</CardTitle>
              <AlertTriangle className="w-4 h-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-red-600">{stats.high_risk_incidents}</div>
              <p className="text-xs text-gray-500 mt-1">Score ≥ 0.8</p>
            </CardContent>
          </Card>

          <Card className="bg-white border-gray-200">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">Blocked Users</CardTitle>
              <Ban className="w-4 h-4 text-orange-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-orange-600">{stats.blocked_users}</div>
              <p className="text-xs text-gray-500 mt-1">Active blocks</p>
            </CardContent>
          </Card>

          <Card className="bg-white border-gray-200">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">Policy Violations</CardTitle>
              <Shield className="w-4 h-4 text-yellow-600" />
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-yellow-600">{stats.policy_violations}</div>
              <p className="text-xs text-gray-500 mt-1">Usage limit exceeded</p>
            </CardContent>
          </Card>
        </div>

        {/* Blocked Users History */}
        {blockedUsers.length > 0 && (
          <Card className="bg-white border-gray-200 mb-6">
            <CardHeader>
              <CardTitle className="text-gray-900 flex items-center gap-2">
                <Ban className="w-5 h-5 text-red-600" />
                Block History
              </CardTitle>
              <p className="text-sm text-gray-500 mt-1">Users who triggered security blocks (historical data)</p>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-3 px-4 text-gray-600 font-medium">User</th>
                      <th className="text-left py-3 px-4 text-gray-600 font-medium">Total Blocks</th>
                      <th className="text-left py-3 px-4 text-gray-600 font-medium">Last Blocked At</th>
                      <th className="text-left py-3 px-4 text-gray-600 font-medium">Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {blockedUsers.map((user) => (
                      <tr key={user.user_id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-3 px-4 text-gray-900">{user.user_email || `User ${user.user_id}`}</td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-1 rounded-full bg-red-100 text-red-700 text-sm font-medium">
                            {user.block_count}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-gray-600">
                          {new Date(user.last_blocked).toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-gray-600">{user.block_reason || 'Policy violation'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Recent Incidents */}
        <Card className="bg-white border-gray-200">
          <CardHeader>
            <CardTitle className="text-gray-900 flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-600" />
              Recent Incidents
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {incidents.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <Shield className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No security incidents detected</p>
                </div>
              ) : (
                incidents.map((incident) => (
                  <div
                    key={incident.id}
                    className="p-4 rounded-lg bg-gray-50 border border-gray-200 hover:border-gray-300 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-sm text-gray-700 font-medium">
                            {incident.user_email || `User ${incident.user_id}`}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-xs border font-medium ${getActionBadge(incident.action)}`}>
                            {incident.action.toUpperCase()}
                          </span>
                          <span className="text-xs text-gray-500">
                            {new Date(incident.detected_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-gray-900 text-sm mb-2 break-words">{incident.message}</p>
                      </div>
                      <div className={`flex-shrink-0 px-3 py-1 rounded-lg ${getSeverityColor(incident.injection_score)}`}>
                        <div className="text-xs font-medium">Score</div>
                        <div className="text-lg font-bold">{incident.injection_score.toFixed(2)}</div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
