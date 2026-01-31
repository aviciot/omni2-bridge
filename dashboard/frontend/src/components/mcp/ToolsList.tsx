"use client";

import { useState } from 'react';
import { MCPTool, ToolCallRequest } from '@/lib/mcpApi';

interface ToolsListProps {
  serverName: string;
  tools: MCPTool[];
  onCallTool?: (request: ToolCallRequest) => Promise<any>;
}

export default function ToolsList({ serverName, tools, onCallTool }: ToolsListProps) {
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null);
  const [toolArgs, setToolArgs] = useState<Record<string, any>>({});
  const [isExecuting, setIsExecuting] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleToolCall = async () => {
    if (!selectedTool || !onCallTool) return;
    
    setIsExecuting(true);
    try {
      const response = await onCallTool({
        server: serverName,
        tool: selectedTool.name,
        arguments: toolArgs
      });
      setResult(response);
    } catch (error) {
      setResult({ error: error instanceof Error ? error.message : 'Unknown error' });
    } finally {
      setIsExecuting(false);
    }
  };

  const renderInputField = (property: string, schema: any) => {
    const type = schema.type || 'string';
    
    switch (type) {
      case 'boolean':
        return (
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={toolArgs[property] || false}
              onChange={(e) => setToolArgs(prev => ({ ...prev, [property]: e.target.checked }))}
              className="rounded"
            />
            <span className="text-sm">{property}</span>
          </label>
        );
      case 'number':
      case 'integer':
        return (
          <input
            type="number"
            placeholder={property}
            value={toolArgs[property] || ''}
            onChange={(e) => setToolArgs(prev => ({ ...prev, [property]: Number(e.target.value) }))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
          />
        );
      default:
        return (
          <input
            type="text"
            placeholder={property}
            value={toolArgs[property] || ''}
            onChange={(e) => setToolArgs(prev => ({ ...prev, [property]: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
          />
        );
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="font-semibold text-gray-900 mb-4">Tools ({tools.length})</h3>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Available Tools</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {tools.map((tool) => (
              <div
                key={tool.name}
                className={`p-3 border rounded-md cursor-pointer transition-colors ${
                  selectedTool?.name === tool.name
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => {
                  setSelectedTool(tool);
                  setToolArgs({});
                  setResult(null);
                }}
              >
                <div className="font-medium text-sm">{tool.name}</div>
                <div className="text-xs text-gray-600 mt-1">{tool.description}</div>
              </div>
            ))}
          </div>
        </div>

        <div>
          {selectedTool && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Execute Tool: {selectedTool.name}</h4>
              
              {selectedTool.inputSchema?.properties && (
                <div className="space-y-3 mb-4">
                  {Object.entries(selectedTool.inputSchema.properties).map(([property, schema]: [string, any]) => (
                    <div key={property}>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        {property}
                        {selectedTool.inputSchema.required?.includes(property) && (
                          <span className="text-red-500">*</span>
                        )}
                      </label>
                      {renderInputField(property, schema)}
                      {schema.description && (
                        <p className="text-xs text-gray-500 mt-1">{schema.description}</p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <button
                onClick={handleToolCall}
                disabled={isExecuting}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 text-sm"
              >
                {isExecuting ? 'Executing...' : 'Execute Tool'}
              </button>

              {result && (
                <div className="mt-4">
                  <h5 className="text-sm font-medium text-gray-700 mb-2">Result:</h5>
                  <pre className="bg-gray-100 p-3 rounded-md text-xs overflow-auto max-h-32">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}