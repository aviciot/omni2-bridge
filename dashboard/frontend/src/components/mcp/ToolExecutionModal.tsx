"use client";

import { useState } from 'react';
import { MCPTool, ToolCallRequest } from '@/lib/mcpApi';

interface ToolExecutionModalProps {
  tool: MCPTool;
  serverName: string;
  isOpen: boolean;
  onClose: () => void;
  onExecute: (request: ToolCallRequest) => Promise<any>;
}

export default function ToolExecutionModal({ 
  tool, 
  serverName, 
  isOpen, 
  onClose, 
  onExecute 
}: ToolExecutionModalProps) {
  const [toolArgs, setToolArgs] = useState<Record<string, any>>({});
  const [isExecuting, setIsExecuting] = useState(false);
  const [result, setResult] = useState<any>(null);

  const parseResult = (result: any) => {
    if (!result) return null;
    
    // If result is an array with TextContent objects
    if (Array.isArray(result) && result[0]?.type === 'text') {
      try {
        // Parse the escaped JSON from the text content
        const jsonText = result[0].text;
        return JSON.parse(jsonText);
      } catch {
        // If parsing fails, return the text as-is
        return result[0].text;
      }
    }
    
    return result;
  };

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
    }
  };

  if (!isOpen) return null;

  const handleExecute = async () => {
    setIsExecuting(true);
    try {
      const response = await onExecute({
        server: serverName,
        tool: tool.name,
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
          <textarea
            placeholder={property}
            value={toolArgs[property] || ''}
            onChange={(e) => setToolArgs(prev => ({ ...prev, [property]: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
            rows={3}
          />
        );
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Execute Tool: {tool.name}</h2>
            <p className="text-sm text-gray-600">{tool.description}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl font-bold"
          >
            ×
          </button>
        </div>
        
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-200px)]">
          {tool.inputSchema?.properties && (
            <div className="space-y-4 mb-6">
              <h3 className="text-lg font-medium text-gray-900">Parameters</h3>
              {Object.entries(tool.inputSchema.properties).map(([property, schema]: [string, any]) => (
                <div key={property}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {property}
                    {tool.inputSchema.required?.includes(property) && (
                      <span className="text-red-500 ml-1">*</span>
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

          <div className="flex gap-3 mb-4">
            <button
              onClick={handleExecute}
              disabled={isExecuting}
              className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
            >
              {isExecuting ? 'Executing...' : 'Execute Tool'}
            </button>
            <button
              onClick={() => {
                setToolArgs({});
                setResult(null);
              }}
              className="px-6 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700"
            >
              Clear
            </button>
          </div>

          {result && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-lg font-medium text-gray-900">Result:</h4>
                <button
                  onClick={() => copyToClipboard(JSON.stringify(parseResult(result.result) || result, null, 2))}
                  className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                >
                  Copy to Clipboard
                </button>
              </div>
              <div className="bg-gray-100 p-4 rounded-md">
                <pre className="text-sm overflow-auto max-h-64 whitespace-pre-wrap">
                  {JSON.stringify(parseResult(result.result) || result, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}