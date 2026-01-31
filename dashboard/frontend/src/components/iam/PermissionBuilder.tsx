"use client";

import { useState, useEffect } from 'react';

interface MCPServer {
  name: string;
  status: string;
  tools?: any[];
  resources?: any[];
  prompts?: any[];
}

interface PermissionBuilderProps {
  value: {
    mcp_access: string[];
    tool_restrictions: Record<string, any>;
  };
  onChange: (value: any) => void;
}

export default function PermissionBuilder({ value, onChange }: PermissionBuilderProps) {
  const [mcpServers, setMcpServers] = useState<MCPServer[]>([]);
  const [selectedMCP, setSelectedMCP] = useState<string | null>(null);
  const [mcpDetails, setMcpDetails] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadMCPs();
  }, []);

  const loadMCPs = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:8500/api/v1/events/mcp-list', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setMcpServers(data.filter((m: any) => m.status === 'active'));
    } catch (error) {
      console.error('Failed to load MCPs:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadMCPDetails = async (mcpName: string) => {
    if (mcpDetails[mcpName]) {
      console.log(`Details already loaded for ${mcpName}`);
      return;
    }
    
    console.log(`Loading details for ${mcpName}...`);
    try {
      const token = localStorage.getItem('access_token');
      const url = `http://localhost:8500/api/v1/mcp/tools/capabilities?server=${encodeURIComponent(mcpName)}`;
      console.log(`Fetching: ${url}`);
      
      const response = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      console.log(`Response status: ${response.status}`);
      const result = await response.json();
      console.log(`Response data:`, result);
      
      // Extract data for this specific MCP
      const mcpData = result.data?.[mcpName] || {};
      
      setMcpDetails(prev => ({
        ...prev,
        [mcpName]: {
          tools: mcpData.tools || [],
          resources: mcpData.resources || [],
          prompts: mcpData.prompts || []
        }
      }));
      console.log(`Details loaded for ${mcpName}`);
    } catch (error) {
      console.error(`Failed to load details for ${mcpName}:`, error);
      // Set empty arrays so UI shows "no items" message
      setMcpDetails(prev => ({
        ...prev,
        [mcpName]: { tools: [], resources: [], prompts: [] }
      }));
    }
  };

  const toggleMCP = (mcpName: string) => {
    const isEnabled = value.mcp_access.includes(mcpName);
    
    if (isEnabled) {
      // Remove MCP
      onChange({
        mcp_access: value.mcp_access.filter(m => m !== mcpName),
        tool_restrictions: Object.fromEntries(
          Object.entries(value.tool_restrictions).filter(([key]) => key !== mcpName)
        )
      });
    } else {
      // Add MCP with default "all" access
      onChange({
        mcp_access: [...value.mcp_access, mcpName],
        tool_restrictions: {
          ...value.tool_restrictions,
          [mcpName]: { mode: 'all' }
        }
      });
      loadMCPDetails(mcpName);
    }
  };

  const updateMCPMode = (mcpName: string, mode: string) => {
    onChange({
      ...value,
      tool_restrictions: {
        ...value.tool_restrictions,
        [mcpName]: { mode, tools: [], resources: [], prompts: [] }
      }
    });
    
    // Auto-expand when switching to ALLOW or DENY
    if (mode === 'allow' || mode === 'deny') {
      setSelectedMCP(mcpName);
      loadMCPDetails(mcpName);
    } else {
      setSelectedMCP(null);
    }
  };

  const toggleItem = (mcpName: string, type: 'tools' | 'resources' | 'prompts', itemName: string) => {
    const current = value.tool_restrictions[mcpName] || { mode: 'all' };
    const items = current[type] || [];
    
    onChange({
      ...value,
      tool_restrictions: {
        ...value.tool_restrictions,
        [mcpName]: {
          ...current,
          [type]: items.includes(itemName)
            ? items.filter((i: string) => i !== itemName)
            : [...items, itemName]
        }
      }
    });
  };

  const selectAll = (mcpName: string, type: 'tools' | 'resources' | 'prompts') => {
    const details = mcpDetails[mcpName];
    if (!details) return;
    
    const allItems = details[type]?.map((item: any) => item.name) || [];
    const current = value.tool_restrictions[mcpName] || { mode: 'all' };
    
    onChange({
      ...value,
      tool_restrictions: {
        ...value.tool_restrictions,
        [mcpName]: {
          ...current,
          [type]: allItems
        }
      }
    });
  };

  const deselectAll = (mcpName: string, type: 'tools' | 'resources' | 'prompts') => {
    const current = value.tool_restrictions[mcpName] || { mode: 'all' };
    
    onChange({
      ...value,
      tool_restrictions: {
        ...value.tool_restrictions,
        [mcpName]: {
          ...current,
          [type]: []
        }
      }
    });
  };

  const getModeColor = (mode: string) => {
    switch (mode) {
      case 'all': return 'bg-green-100 text-green-700 border-green-300';
      case 'allow': return 'bg-blue-100 text-blue-700 border-blue-300';
      case 'deny': return 'bg-amber-100 text-amber-700 border-amber-300';
      case 'none': return 'bg-red-100 text-red-700 border-red-300';
      default: return 'bg-gray-100 text-gray-700 border-gray-300';
    }
  };

  if (loading) {
    return <div className="text-center py-8 text-gray-500">Loading MCP servers...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-semibold text-gray-900">MCP Permissions</h4>
        <span className="text-sm text-gray-600">
          {value.mcp_access.length} of {mcpServers.length} enabled
        </span>
      </div>

      <div className="space-y-3">
        {mcpServers.map(mcp => {
          const isEnabled = value.mcp_access.includes(mcp.name);
          const restrictions = value.tool_restrictions[mcp.name] || { mode: 'all' };
          const details = mcpDetails[mcp.name];

          return (
            <div
              key={mcp.name}
              className={`border-2 rounded-lg transition-all ${
                isEnabled ? 'border-purple-300 bg-purple-50' : 'border-gray-200 bg-white'
              }`}
            >
              {/* MCP Header */}
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={isEnabled}
                      onChange={() => toggleMCP(mcp.name)}
                      className="w-5 h-5 text-purple-600 rounded"
                    />
                    <div>
                      <div className="font-semibold text-gray-900">{mcp.name}</div>
                      <div className="text-xs text-gray-500">MCP Server</div>
                    </div>
                  </div>
                  
                  {isEnabled && (
                    <button
                      onClick={() => {
                        const newSelected = selectedMCP === mcp.name ? null : mcp.name;
                        setSelectedMCP(newSelected);
                        if (newSelected) {
                          loadMCPDetails(mcp.name);
                        }
                      }}
                      className="text-sm text-purple-600 hover:text-purple-700 font-medium"
                    >
                      {selectedMCP === mcp.name ? '▼ Hide Details' : '▶ Configure'}
                    </button>
                  )}
                </div>

                {/* Access Mode Selector */}
                {isEnabled && (
                  <div className="mt-3 flex gap-2">
                    {['all', 'allow', 'deny', 'none'].map(mode => (
                      <button
                        key={mode}
                        onClick={() => updateMCPMode(mcp.name, mode)}
                        className={`px-3 py-1 text-xs font-medium rounded border-2 transition-all ${
                          restrictions.mode === mode
                            ? getModeColor(mode)
                            : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        {mode.toUpperCase()}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Expanded Details */}
              {isEnabled && selectedMCP === mcp.name && (
                <div className="border-t border-purple-200 bg-white">
                  {!details ? (
                    <div className="p-4">
                      <div className="text-center text-gray-500 mb-3">Loading MCP details...</div>
                      <div className="text-xs text-amber-600 bg-amber-50 p-3 rounded">
                        ⚠️ If tools don't load, the MCP server may not be responding or the endpoint is not available.
                        You can still configure access modes above.
                      </div>
                    </div>
                  ) : details.tools?.length === 0 && details.resources?.length === 0 && details.prompts?.length === 0 ? (
                    <div className="p-4">
                      <div className="text-center text-gray-500 mb-3">No tools, resources, or prompts available for this MCP</div>
                      <div className="text-xs text-blue-600 bg-blue-50 p-3 rounded">
                        ℹ️ This MCP may not expose any tools/resources/prompts, or they haven't been configured yet.
                        The access mode you selected above will still apply.
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 space-y-4">
                      {/* Tools */}
                      {details.tools && details.tools.length > 0 && (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <h5 className="font-medium text-gray-900">🔧 Tools ({details.tools.length})</h5>
                            <div className="flex gap-2">
                              <button
                                onClick={() => selectAll(mcp.name, 'tools')}
                                className="text-xs text-blue-600 hover:text-blue-700"
                              >
                                Select All
                              </button>
                              <button
                                onClick={() => deselectAll(mcp.name, 'tools')}
                                className="text-xs text-gray-600 hover:text-gray-700"
                              >
                                Deselect All
                              </button>
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                            {details.tools.map((tool: any) => {
                              const isSelected = restrictions.tools?.includes(tool.name);
                              const shouldBeChecked = restrictions.mode === 'allow' ? isSelected : !isSelected;
                              
                              return (
                                <label
                                  key={tool.name}
                                  className={`flex items-start gap-2 p-2 rounded border cursor-pointer transition-all ${
                                    shouldBeChecked
                                      ? 'bg-blue-50 border-blue-300'
                                      : 'bg-gray-50 border-gray-200 hover:border-gray-300'
                                  }`}
                                >
                                  <input
                                    type="checkbox"
                                    checked={shouldBeChecked}
                                    onChange={() => toggleItem(mcp.name, 'tools', tool.name)}
                                    className="mt-0.5"
                                  />
                                  <div className="flex-1 min-w-0">
                                    <div className="text-sm font-medium text-gray-900 truncate">{tool.name}</div>
                                    {tool.description && (
                                      <div className="text-xs text-gray-500 line-clamp-1">{tool.description}</div>
                                    )}
                                  </div>
                                </label>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Resources */}
                      {details.resources && details.resources.length > 0 && (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <h5 className="font-medium text-gray-900">📁 Resources ({details.resources.length})</h5>
                            <div className="flex gap-2">
                              <button
                                onClick={() => selectAll(mcp.name, 'resources')}
                                className="text-xs text-blue-600 hover:text-blue-700"
                              >
                                Select All
                              </button>
                              <button
                                onClick={() => deselectAll(mcp.name, 'resources')}
                                className="text-xs text-gray-600 hover:text-gray-700"
                              >
                                Deselect All
                              </button>
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                            {details.resources.map((resource: any) => {
                              const isSelected = restrictions.resources?.includes(resource.name);
                              const shouldBeChecked = restrictions.mode === 'allow' ? isSelected : !isSelected;
                              
                              return (
                                <label
                                  key={resource.name}
                                  className={`flex items-start gap-2 p-2 rounded border cursor-pointer transition-all ${
                                    shouldBeChecked
                                      ? 'bg-green-50 border-green-300'
                                      : 'bg-gray-50 border-gray-200 hover:border-gray-300'
                                  }`}
                                >
                                  <input
                                    type="checkbox"
                                    checked={shouldBeChecked}
                                    onChange={() => toggleItem(mcp.name, 'resources', resource.name)}
                                    className="mt-0.5"
                                  />
                                  <div className="flex-1 min-w-0">
                                    <div className="text-sm font-medium text-gray-900 truncate">{resource.name}</div>
                                    {resource.description && (
                                      <div className="text-xs text-gray-500 line-clamp-1">{resource.description}</div>
                                    )}
                                  </div>
                                </label>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Prompts */}
                      {details.prompts && details.prompts.length > 0 && (
                        <div>
                          <div className="flex items-center justify-between mb-2">
                            <h5 className="font-medium text-gray-900">💬 Prompts ({details.prompts.length})</h5>
                            <div className="flex gap-2">
                              <button
                                onClick={() => selectAll(mcp.name, 'prompts')}
                                className="text-xs text-blue-600 hover:text-blue-700"
                              >
                                Select All
                              </button>
                              <button
                                onClick={() => deselectAll(mcp.name, 'prompts')}
                                className="text-xs text-gray-600 hover:text-gray-700"
                              >
                                Deselect All
                              </button>
                            </div>
                          </div>
                          <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto">
                            {details.prompts.map((prompt: any) => {
                              const isSelected = restrictions.prompts?.includes(prompt.name);
                              const shouldBeChecked = restrictions.mode === 'allow' ? isSelected : !isSelected;
                              
                              return (
                                <label
                                  key={prompt.name}
                                  className={`flex items-start gap-2 p-2 rounded border cursor-pointer transition-all ${
                                    shouldBeChecked
                                      ? 'bg-purple-50 border-purple-300'
                                      : 'bg-gray-50 border-gray-200 hover:border-gray-300'
                                  }`}
                                >
                                  <input
                                    type="checkbox"
                                    checked={shouldBeChecked}
                                    onChange={() => toggleItem(mcp.name, 'prompts', prompt.name)}
                                    className="mt-0.5"
                                  />
                                  <div className="flex-1 min-w-0">
                                    <div className="text-sm font-medium text-gray-900 truncate">{prompt.name}</div>
                                    {prompt.description && (
                                      <div className="text-xs text-gray-500 line-clamp-1">{prompt.description}</div>
                                    )}
                                  </div>
                                </label>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Mode Legend */}
      <div className="mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
        <div className="text-xs font-semibold text-gray-700 mb-2">Access Modes:</div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          <div><span className="font-medium">ALL:</span> Full access to everything</div>
          <div><span className="font-medium">ALLOW:</span> Only selected items (whitelist)</div>
          <div><span className="font-medium">DENY:</span> Everything except selected (blacklist)</div>
          <div><span className="font-medium">NONE:</span> Block all access</div>
        </div>
      </div>
    </div>
  );
}
