"use client";

import { useState, useEffect } from 'react';
import { mcpApi } from '@/lib/mcpApi';

interface LogsModalProps {
  isOpen: boolean;
  onClose: () => void;
  serverId: number;
  serverName: string;
  logType: 'health' | 'audit';
}

interface HealthLog {
  id: number;
  timestamp: string;
  status: string;
  response_time_ms: number;
  error_message?: string;
  event_type: string;
  meta_data?: any;
}

interface AuditLog {
  id: number;
  tool_name: string;
  user_id: string;
  environment: string;
  parameters: any;
  result_status: string;
  result_summary?: string;
  error_message?: string;
  execution_time_ms: number;
  workflow_run_id?: string;
  session_id?: string;
  created_at: string;
}

export default function LogsModal({ isOpen, onClose, serverId, serverName, logType }: LogsModalProps) {
  const [logs, setLogs] = useState<(HealthLog | AuditLog)[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    status: '',
    search: '',
    limit: 100
  });

  useEffect(() => {
    if (isOpen) {
      loadLogs();
    }
  }, [isOpen, serverId, logType, filters]);

  const loadLogs = async () => {
    if (!serverId || serverId === 0) {
      setError('Invalid server ID');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      let response;
      if (logType === 'health') {
        response = await mcpApi.getMCPHealthLogs(serverId);
      } else {
        response = await mcpApi.getMCPAuditLogs(serverId, filters);
      }
      
      setLogs(response.logs || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load logs');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const colors = {
      success: 'bg-green-100 text-green-800',
      error: 'bg-red-100 text-red-800',
      healthy: 'bg-green-100 text-green-800',
      unhealthy: 'bg-red-100 text-red-800',
      timeout: 'bg-yellow-100 text-yellow-800'
    };
    return colors[status as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              {logType === 'health' ? '📊 Health Logs' : '🔍 Audit Logs'} - {serverName}
            </h2>
            <p className="text-sm text-gray-600">
              {logType === 'health' ? 'Server connectivity and health check logs' : 'Tool execution and user activity logs'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
          >
            ×
          </button>
        </div>

        {/* Filters for audit logs */}
        {logType === 'audit' && (
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
            <div className="flex gap-4 items-center">
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Status</label>
                <select
                  value={filters.status}
                  onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
                  className="px-3 py-1 border border-gray-300 rounded-md text-sm"
                >
                  <option value="">All</option>
                  <option value="success">Success</option>
                  <option value="error">Error</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Search</label>
                <input
                  type="text"
                  value={filters.search}
                  onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                  placeholder="Tool name, summary, error..."
                  className="px-3 py-1 border border-gray-300 rounded-md text-sm w-64"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Limit</label>
                <select
                  value={filters.limit}
                  onChange={(e) => setFilters(prev => ({ ...prev, limit: parseInt(e.target.value) }))}
                  className="px-3 py-1 border border-gray-300 rounded-md text-sm"
                >
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={200}>200</option>
                  <option value={500}>500</option>
                </select>
              </div>
            </div>
          </div>
        )}
        
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {loading ? (
            <div className="text-center py-8">
              <div className="text-gray-600">Loading logs...</div>
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <div className="text-red-600">{error}</div>
            </div>
          ) : logs.length === 0 ? (
            <div className="text-center py-8">
              <div className="text-gray-600">No logs found</div>
            </div>
          ) : (
            <div className="space-y-3">
              {logs.map((log) => (
                <div key={log.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-sm">
                  {logType === 'health' ? (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge((log as HealthLog).status)}`}>
                            {(log as HealthLog).status}
                          </span>
                          <span className="text-sm text-gray-600">
                            {(log as HealthLog).event_type}
                          </span>
                          <span className="text-sm text-gray-500">
                            {(log as HealthLog).response_time_ms}ms
                          </span>
                        </div>
                        <span className="text-sm text-gray-500">
                          {new Date((log as HealthLog).timestamp).toLocaleString()}
                        </span>
                      </div>
                      {(log as HealthLog).error_message && (
                        <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                          {(log as HealthLog).error_message}
                        </div>
                      )}
                      {(log as HealthLog).meta_data && (
                        <div className="text-xs text-gray-500 bg-gray-50 p-2 rounded">
                          <pre>{JSON.stringify((log as HealthLog).meta_data, null, 2)}</pre>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="font-medium text-gray-900">
                            {(log as AuditLog).tool_name}
                          </span>
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusBadge((log as AuditLog).result_status)}`}>
                            {(log as AuditLog).result_status}
                          </span>
                          <span className="text-sm text-gray-500">
                            {(log as AuditLog).execution_time_ms}ms
                          </span>
                        </div>
                        <span className="text-sm text-gray-500">
                          {new Date((log as AuditLog).created_at).toLocaleString()}
                        </span>
                      </div>
                      <div className="text-sm text-gray-600">
                        User: {(log as AuditLog).user_id} | Environment: {(log as AuditLog).environment}
                      </div>
                      {(log as AuditLog).result_summary && (
                        <div className="text-sm text-gray-700">
                          {(log as AuditLog).result_summary}
                        </div>
                      )}
                      {(log as AuditLog).error_message && (
                        <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
                          {(log as AuditLog).error_message}
                        </div>
                      )}
                      {(log as AuditLog).parameters && (
                        <details className="text-xs">
                          <summary className="cursor-pointer text-gray-500 hover:text-gray-700">Parameters</summary>
                          <pre className="mt-1 bg-gray-50 p-2 rounded overflow-x-auto">
                            {JSON.stringify((log as AuditLog).parameters, null, 2)}
                          </pre>
                        </details>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}