"use client";

import { useState } from 'react';
import { MCPServer, MCPCapabilities, ToolCallRequest, MCPTool } from '@/lib/mcpApi';
import ToolExecutionModal from './ToolExecutionModal';
import AddMCPServerModal from './AddMCPServerModal';
import EditMCPServerModal from './EditMCPServerModal';

interface MCPServerTableProps {
  servers: MCPServer[];
  capabilities: Record<string, MCPCapabilities>;
  onReloadServer: (serverName: string) => void;
  onCallTool: (request: ToolCallRequest) => Promise<any>;
  onRefresh: () => void;
  onDeleteServer: (serverName: string) => void;
  onViewLogs: (serverId: number, serverName: string) => void;
  onViewAuditLogs: (serverId: number, serverName: string) => void;
  onUpdateServer: (serverId: number, updates: any) => Promise<void>;
}

export default function MCPServerTable({ 
  servers, 
  capabilities, 
  onReloadServer, 
  onCallTool,
  onRefresh,
  onDeleteServer,
  onViewLogs,
  onViewAuditLogs,
  onUpdateServer
}: MCPServerTableProps) {
  const [selectedServer, setSelectedServer] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingServer, setEditingServer] = useState<MCPServer | null>(null);
  const [executionModal, setExecutionModal] = useState<{
    isOpen: boolean;
    tool: MCPTool | null;
    serverName: string;
  }>({ isOpen: false, tool: null, serverName: '' });

  const getButtonState = (server: MCPServer) => {
    switch (server.health_status) {
      case 'healthy':
        return { disabled: false, tooltip: 'Reload server' };
      case 'unhealthy':
        return { disabled: false, tooltip: 'Retry connection' };
      case 'disconnected':
        return { disabled: true, tooltip: 'MCP disconnected, retrying...' };
      case 'circuit_open':
        return { disabled: true, tooltip: 'Circuit breaker open' };
      case 'disabled':
        return { disabled: true, tooltip: 'Manually disabled' };
      default:
        return { disabled: false, tooltip: 'Check status' };
    }
  };

  const getStatusBadge = (status: string, enabled: boolean) => {
    if (!enabled) return <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-600 rounded-full">Disabled</span>;
    
    switch (status) {
      case 'healthy':
        return <span className="px-2 py-1 text-xs font-medium bg-green-100 text-green-700 rounded-full">Healthy</span>;
      case 'unhealthy':
        return <span className="px-2 py-1 text-xs font-medium bg-red-100 text-red-700 rounded-full">Unhealthy</span>;
      default:
        return <span className="px-2 py-1 text-xs font-medium bg-yellow-100 text-yellow-700 rounded-full">Unknown</span>;
    }
  };

  const getPTSecurityBadge = (server: MCPServer) => {
    if (server.pt_status === null || server.pt_last_run === null) {
      return (
        <div className="flex flex-col gap-1">
          <span className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-500 rounded-full w-fit">
            Never tested
          </span>
        </div>
      );
    }

    const scoreColor =
      server.pt_status === 'pass'         ? 'bg-green-100 text-green-800 border border-green-200' :
      server.pt_status === 'fail'         ? (server.pt_score! >= 50
                                             ? 'bg-yellow-100 text-yellow-800 border border-yellow-200'
                                             : 'bg-red-100 text-red-800 border border-red-200') :
      /* inconclusive */                    'bg-gray-100 text-gray-600 border border-gray-200';

    const statusIcon =
      server.pt_status === 'pass'         ? '✅' :
      server.pt_status === 'fail'         ? '❌' : '⚠️';

    const lastRun = new Date(server.pt_last_run);
    const daysAgo = Math.floor((Date.now() - lastRun.getTime()) / 86400000);
    const timeLabel = daysAgo === 0 ? 'Today' : daysAgo === 1 ? '1d ago' : `${daysAgo}d ago`;

    return (
      <div className="flex flex-col gap-1">
        <span className={`px-2 py-1 text-xs font-semibold rounded-full w-fit flex items-center gap-1 ${scoreColor}`}>
          {statusIcon}
          {server.pt_status === 'inconclusive'
            ? 'Inconclusive'
            : server.pt_score !== null
              ? `${server.pt_score}%`
              : server.pt_status === 'pass' ? 'Pass' : 'Fail'}
        </span>
        <span className="text-xs text-gray-400">{timeLabel}</span>
      </div>
    );
  };

  const handleViewDetails = (serverName: string) => {
    setSelectedServer(serverName);
    setShowDetails(true);
  };

  const handleExecuteTool = (tool: MCPTool, serverName: string) => {
    setExecutionModal({ isOpen: true, tool, serverName });
  };

  const handleDeleteServer = async (serverName: string) => {
    if (confirm(`Are you sure you want to delete the MCP server "${serverName}"?`)) {
      await onDeleteServer(serverName);
    }
  };

  const handleEditServer = (server: MCPServer) => {
    setEditingServer(server);
    setShowEditModal(true);
  };

  const handleToggleStatus = async (server: MCPServer) => {
    const newStatus = server.enabled ? 'inactive' : 'active';
    await onUpdateServer(server.id, { status: newStatus });
    onRefresh();
  };

  const selectedServerData = selectedServer ? servers.find(s => s.name === selectedServer) : null;
  const selectedCapabilities = selectedServer ? capabilities[selectedServer] : null;

  return (
    <>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">MCP Servers ({servers.length})</h3>
          <button
            onClick={() => setShowAddModal(true)}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors font-medium flex items-center gap-2"
          >
            <span>➕</span>
            Add Server
          </button>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Server
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  URL
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Protocol
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Capabilities
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Check
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  PT Security
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {servers.map((server) => (
                <tr key={server.name} id={`mcp-${server.name}`} className="hover:bg-gray-50 transition-all">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{server.name}</div>
                      <div className="text-sm text-gray-500 truncate max-w-xs">{server.description}</div>
                      <div className="text-xs text-gray-400">ID: {server.id}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-900 max-w-xs truncate" title={server.url}>
                      {server.url}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getStatusBadge(server.health_status, server.enabled)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {server.protocol.toUpperCase()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {capabilities[server.name]?.metadata ? (
                      <div className="flex items-center gap-3">
                        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">
                          {capabilities[server.name].metadata.tool_count || 0} Tools
                        </span>
                        <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs">
                          {capabilities[server.name].metadata.prompt_count || 0} Prompts
                        </span>
                        <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded-full text-xs">
                          {capabilities[server.name].metadata.resource_count || 0} Resources
                        </span>
                      </div>
                    ) : (
                      <span className="text-gray-400">
                        {server.health_status === 'healthy' ? 'Loading...' : 
                         server.health_status === 'disconnected' ? 'Disconnected' :
                         server.health_status === 'circuit_open' ? 'Circuit Open' :
                         server.health_status === 'disabled' ? 'Disabled' : 'Unavailable'}
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {server.last_health_check ? (
                      new Date(server.last_health_check).toLocaleString()
                    ) : (
                      'Never'
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getPTSecurityBadge(server)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleEditServer(server)}
                        className="bg-indigo-600 text-white px-3 py-1 rounded-md hover:bg-indigo-700 text-xs"
                        title="Edit server settings"
                      >
                        ✏️ Edit
                      </button>
                      <button
                        onClick={() => handleToggleStatus(server)}
                        className={`px-3 py-1 rounded-md text-xs font-medium ${
                          server.enabled 
                            ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200' 
                            : 'bg-green-100 text-green-700 hover:bg-green-200'
                        }`}
                        title={server.enabled ? 'Disable server' : 'Enable server'}
                      >
                        {server.enabled ? '⏸️ Disable' : '▶️ Enable'}
                      </button>
                      <button
                        onClick={() => handleViewDetails(server.name)}
                        className="bg-blue-600 text-white px-3 py-1 rounded-md hover:bg-blue-700 text-xs"
                        title="View server details and tools"
                      >
                        View Details
                      </button>
                      <button
                        onClick={() => onViewLogs(server.id, server.name)}
                        className="bg-green-600 text-white px-3 py-1 rounded-md hover:bg-green-700 text-xs"
                        title="View Health Logs"
                      >
                        📊
                      </button>
                      <button
                        onClick={() => onViewAuditLogs(server.id, server.name)}
                        className="bg-purple-600 text-white px-3 py-1 rounded-md hover:bg-purple-700 text-xs"
                        title="View Audit Logs"
                      >
                        🔍
                      </button>
                      <button
                        onClick={() => onReloadServer(server.name)}
                        disabled={getButtonState(server).disabled}
                        className={`px-2 py-1 rounded-md text-xs ${
                          getButtonState(server).disabled 
                            ? 'text-gray-400 bg-gray-100 cursor-not-allowed' 
                            : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                        }`}
                        title={getButtonState(server).disabled ? getButtonState(server).tooltip : 'Reload Server'}
                      >
                        ↻
                      </button>
                      <button
                        onClick={() => handleDeleteServer(server.name)}
                        className="text-red-600 hover:text-red-900 px-2 py-1 rounded-md hover:bg-red-100 text-xs"
                        title="Delete Server"
                      >
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Details Modal */}
      {showDetails && selectedServerData && selectedCapabilities && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-6xl w-full max-h-[90vh] overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">{selectedServerData.name}</h2>
                <p className="text-sm text-gray-600">{selectedServerData.description}</p>
              </div>
              <button
                onClick={() => setShowDetails(false)}
                className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
              >
                ×
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
              {/* Server Info */}
              <div className="mb-6 bg-gray-50 p-4 rounded-lg">
                <h3 className="text-lg font-medium text-gray-900 mb-3">Server Information</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">URL:</span>
                    <span className="ml-2 text-gray-600">{selectedServerData.url}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Protocol:</span>
                    <span className="ml-2 text-gray-600">{selectedServerData.protocol}</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Timeout:</span>
                    <span className="ml-2 text-gray-600">{selectedServerData.timeout_seconds}s</span>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">Status:</span>
                    <span className="ml-2">{getStatusBadge(selectedServerData.health_status, selectedServerData.enabled)}</span>
                  </div>
                </div>
              </div>

              {/* Tools Section */}
              <div className="mb-6">
                <h3 className="text-lg font-medium text-gray-900 mb-3">
                  Available Tools ({selectedCapabilities.tools?.length || 0})
                </h3>
                {selectedCapabilities.tools?.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-h-96 overflow-y-auto">
                    {selectedCapabilities.tools.map((tool, index) => (
                      <div key={index} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex items-start justify-between mb-2">
                          <h4 className="font-medium text-gray-900">{tool.name}</h4>
                          <button
                            onClick={() => handleExecuteTool(tool, selectedServer)}
                            className="bg-green-600 text-white px-2 py-1 rounded text-xs hover:bg-green-700"
                          >
                            Execute
                          </button>
                        </div>
                        <p className="text-sm text-gray-600 mb-3">{tool.description}</p>
                        {tool.inputSchema?.properties && (
                          <div className="text-xs text-gray-500">
                            Parameters: {Object.keys(tool.inputSchema.properties).join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    No tools available (server may be offline)
                  </div>
                )}
              </div>

              {/* Prompts & Resources */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {selectedCapabilities.prompts?.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-3">
                      Prompts ({selectedCapabilities.prompts.length})
                    </h3>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {selectedCapabilities.prompts.map((prompt: any, index: number) => (
                        <div key={index} className="p-3 border border-gray-200 rounded-md bg-green-50">
                          <div className="font-medium text-sm text-green-800">{prompt.name}</div>
                          {prompt.description && (
                            <div className="text-xs text-green-600 mt-1">{prompt.description}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {selectedCapabilities.resources?.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-3">
                      Resources ({selectedCapabilities.resources.length})
                    </h3>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {selectedCapabilities.resources.map((resource: any, index: number) => (
                        <div key={index} className="p-3 border border-gray-200 rounded-md bg-purple-50">
                          <div className="font-medium text-sm text-purple-800">{resource.name || resource.uri}</div>
                          {resource.description && (
                            <div className="text-xs text-purple-600 mt-1">{resource.description}</div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Add MCP Server Modal */}
      <AddMCPServerModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={() => {
          setShowAddModal(false);
          onRefresh();
        }}
      />

      {/* Edit MCP Server Modal */}
      <EditMCPServerModal
        isOpen={showEditModal}
        onClose={() => {
          setShowEditModal(false);
          setEditingServer(null);
        }}
        server={editingServer}
        onSave={async (serverId, updates) => {
          await onUpdateServer(serverId, updates);
          setShowEditModal(false);
          setEditingServer(null);
          onRefresh();
        }}
      />

      {/* Tool Execution Modal */}
      <ToolExecutionModal
        tool={executionModal.tool!}
        serverName={executionModal.serverName}
        isOpen={executionModal.isOpen}
        onClose={() => setExecutionModal({ isOpen: false, tool: null, serverName: '' })}
        onExecute={onCallTool}
      />
    </>
  );
}