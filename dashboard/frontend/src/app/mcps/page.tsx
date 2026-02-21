"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/stores/authStore";
import { mcpApi, MCPServer, MCPCapabilities, ToolCallRequest } from "@/lib/mcpApi";
import MCPTable from "@/components/mcp/MCPTable";
import LogsModal from "@/components/mcp/LogsModal";

export default function MCPsPage() {
  const router = useRouter();
  const { user, isAuthenticated, fetchUser, logout } = useAuthStore();
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [capabilities, setCapabilities] = useState<Record<string, MCPCapabilities>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showLogsModal, setShowLogsModal] = useState<{
    isOpen: boolean;
    serverId: number | null;
    serverName: string;
    logType: 'health' | 'audit';
  }>({ isOpen: false, serverId: null, serverName: '', logType: 'health' });

  useEffect(() => {
    const initAuth = async () => {
      await fetchUser();
      if (!isAuthenticated) {
        router.push("/login");
      }
    };
    initAuth();
  }, [isAuthenticated, fetchUser, router]);

  useEffect(() => {
    if (isAuthenticated) {
      setLoading(true);
      loadMCPData();
      
      // Set up auto-refresh every 30 seconds
      const interval = setInterval(() => {
        loadMCPData(); // Quiet refresh without loading state
      }, 30000);
      
      return () => clearInterval(interval);
    }
  }, [isAuthenticated]);

  const loadMCPData = async () => {
    try {
      setError(null);
      
      const [serversData, capabilitiesData] = await Promise.all([
        mcpApi.getServers(false, true),
        mcpApi.getCapabilities()
      ]);
      
      setServers(serversData.servers);
      setCapabilities(capabilitiesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load MCP data');
    } finally {
      setLoading(false);
    }
  };

  const handleReloadServer = async (serverName: string) => {
    try {
      // Reload MCP connection
      await mcpApi.reloadMCPs(serverName);
      
      // Fetch fresh data
      await loadMCPData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reload server');
    }
  };

  const handleReloadAll = async () => {
    try {
      await mcpApi.reloadMCPs();
      await loadMCPData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reload all servers');
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    await loadMCPData();
  };

  const handleDeleteServer = async (serverName: string) => {
    try {
      // Find server by name to get ID
      const server = servers.find(s => s.name === serverName);
      if (!server) {
        setError('Server not found');
        return;
      }
      
      await mcpApi.deleteServer(server.id);
      await loadMCPData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete server');
    }
  };

  const handleUpdateServer = async (serverId: number, updates: any) => {
    try {
      await mcpApi.updateServer(serverId, updates);
      await loadMCPData();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update server');
      throw err;
    }
  };

  const handleViewLogs = (serverId: number, serverName: string) => {
    setShowLogsModal({ isOpen: true, serverId, serverName, logType: 'health' });
  };

  const handleViewAuditLogs = (serverId: number, serverName: string) => {
    setShowLogsModal({ isOpen: true, serverId, serverName, logType: 'audit' });
  };

  const handleToolCall = async (request: ToolCallRequest) => {
    return await mcpApi.callTool(request);
  };

  if (!user) return null;

  return (
    <main className="px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">MCP Servers</h2>
              <p className="text-gray-600">Manage and monitor your Model Context Protocol servers</p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleRefresh}
                disabled={loading}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
              >
                {loading ? 'Loading...' : 'Refresh'}
              </button>
              <button
                onClick={handleReloadAll}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
              >
                Reload All
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <div className="text-gray-600">Loading MCP servers...</div>
          </div>
        ) : servers.length === 0 ? (
          <div className="bg-white rounded-xl p-12 text-center border border-gray-200">
            <div className="text-6xl mb-4">🔌</div>
            <h3 className="text-2xl font-bold text-gray-900 mb-2">No MCP Servers</h3>
            <p className="text-gray-600 mb-6">No MCP servers are currently configured</p>
            <Link href="/dashboard" className="inline-block px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700">
              Back to Dashboard
            </Link>
          </div>
        ) : (
          <MCPTable
            servers={servers}
            capabilities={capabilities}
            onReloadServer={handleReloadServer}
            onCallTool={handleToolCall}
            onRefresh={handleRefresh}
            onDeleteServer={handleDeleteServer}
            onViewLogs={handleViewLogs}
            onViewAuditLogs={handleViewAuditLogs}
            onUpdateServer={handleUpdateServer}
          />
        )}
        
        {/* Logs Modal */}
        <LogsModal
          isOpen={showLogsModal.isOpen}
          onClose={() => setShowLogsModal({ isOpen: false, serverId: null, serverName: '', logType: 'health' })}
          serverId={showLogsModal.serverId || 0}
          serverName={showLogsModal.serverName}
          logType={showLogsModal.logType}
        />
      </main>
  );
}
