"use client";

import { useState, useEffect } from 'react';
import { MCPServer } from '@/lib/mcpApi';

interface ServerStatusProps {
  server: MCPServer;
  onReload?: (serverName: string) => void;
}

export default function ServerStatus({ server, onReload }: ServerStatusProps) {
  const [isReloading, setIsReloading] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'text-green-600 bg-green-100';
      case 'unhealthy': return 'text-red-600 bg-red-100';
      case 'unknown': return 'text-gray-600 bg-gray-100';
      default: return 'text-yellow-600 bg-yellow-100';
    }
  };

  const handleReload = async () => {
    if (!onReload) return;
    setIsReloading(true);
    try {
      await onReload(server.name);
    } finally {
      setIsReloading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold text-gray-900">{server.name}</h3>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(server.health_status)}`}>
            {server.health_status}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {server.enabled ? (
            <span className="text-green-600 text-sm">●</span>
          ) : (
            <span className="text-gray-400 text-sm">●</span>
          )}
          {onReload && (
            <button
              onClick={handleReload}
              disabled={isReloading}
              className="text-blue-600 hover:text-blue-800 text-sm disabled:opacity-50"
            >
              {isReloading ? '⟳' : '↻'}
            </button>
          )}
        </div>
      </div>
      
      <div className="space-y-2 text-sm text-gray-600">
        <p>{server.description}</p>
        <div className="flex items-center gap-4">
          <span>URL: {server.url}</span>
          <span>Protocol: {server.protocol}</span>
          <span>Timeout: {server.timeout_seconds}s</span>
        </div>
        {server.last_health_check && (
          <p className="text-xs">
            Last check: {new Date(server.last_health_check).toLocaleString()}
          </p>
        )}
      </div>
    </div>
  );
}