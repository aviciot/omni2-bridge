"use client";

import { useState } from 'react';
import { MCPServer, MCPCapabilities, ToolCallRequest } from '@/lib/mcpApi';

interface MCPServerTableProps {
  servers: MCPServer[];
  capabilities: Record<string, MCPCapabilities>;
  onReloadServer: (serverName: string) => void;
  onCallTool: (request: ToolCallRequest) => Promise<any>;
}

export default function MCPServerTable({ 
  servers, 
  capabilities, 
  onReloadServer, 
  onCallTool 
}: MCPServerTableProps) {
  const [selectedServer, setSelectedServer] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);

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

  const handleViewDetails = (serverName: string) => {
    setSelectedServer(serverName);
    setShowDetails(true);
  };

  const selectedServerData = selectedServer ? servers.find(s => s.name === selectedServer) : null;
  const selectedCapabilities = selectedServer ? capabilities[selectedServer] : null;

  return (
    <>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">MCP Servers ({servers.length})</h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Server
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Protocol
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Tools
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Last Check
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {servers.map((server) => (
                <tr key={server.name} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{server.name}</div>
                      <div className="text-sm text-gray-500 truncate max-w-xs">{server.description}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {getStatusBadge(server.health_status, server.enabled)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {server.protocol.toUpperCase()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {capabilities[server.name] ? (
                      <div className="flex items-center gap-4">
                        <span className="text-blue-600 font-medium">
                          {capabilities[server.name].metadata.tool_count}
                        </span>
                        <span className="text-green-600">
                          {capabilities[server.name].metadata.prompt_count}P
                        </span>
                        <span className="text-purple-600">
                          {capabilities[server.name].metadata.resource_count}R
                        </span>
                      </div>
                    ) : (
                      <span className="text-gray-400">Loading...</span>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {server.last_health_check ? (
                      new Date(server.last_health_check).toLocaleString()
                    ) : (
                      'Never'
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => handleViewDetails(server.name)}
                        className="text-blue-600 hover:text-blue-900 px-3 py-1 rounded-md hover:bg-blue-50"
                      >
                        Details
                      </button>
                      <button
                        onClick={() => onReloadServer(server.name)}
                        className="text-gray-600 hover:text-gray-900 px-3 py-1 rounded-md hover:bg-gray-50"
                        title="Reload Server"
                      >
                        ↻
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
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-gray-900">{selectedServerData.name}</h2>
                <p className="text-sm text-gray-600">{selectedServerData.description}</p>
              </div>
              <button
                onClick={() => setShowDetails(false)}
                className="text-gray-400 hover:text-gray-600 text-2xl"
              >
                ×
              </button>
            </div>
            
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
              {/* Server Info */}
              <div className="mb-6">
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

              {/* Tools */}
              <div className="mb-6">
                <h3 className="text-lg font-medium text-gray-900 mb-3">
                  Tools ({selectedCapabilities.tools.length})
                </h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {selectedCapabilities.tools.map((tool, index) => (
                    <div key={index} className="p-3 border border-gray-200 rounded-md">
                      <div className="font-medium text-sm">{tool.name}</div>
                      <div className="text-xs text-gray-600 mt-1">{tool.description}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Prompts & Resources */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {selectedCapabilities.prompts.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-3">
                      Prompts ({selectedCapabilities.prompts.length})
                    </h3>
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {selectedCapabilities.prompts.map((prompt: any, index: number) => (
                        <div key={index} className="p-2 border border-gray-200 rounded text-sm">
                          {prompt.name}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {selectedCapabilities.resources.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-3">
                      Resources ({selectedCapabilities.resources.length})
                    </h3>
                    <div className="space-y-2 max-h-32 overflow-y-auto">
                      {selectedCapabilities.resources.map((resource: any, index: number) => (
                        <div key={index} className="p-2 border border-gray-200 rounded text-sm">
                          {resource.name || resource.uri}
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
    </>
  );
}