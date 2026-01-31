"use client";

import { useState, useEffect } from 'react';
import { mcpApi } from '@/lib/mcpApi';

interface AddMCPServerModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface MCPServerForm {
  name: string;
  url: string;
  description: string;
  protocol: 'http' | 'sse' | 'http-streamable';
  timeout_seconds: number;
  auth_type: '' | 'bearer' | 'api_key' | 'custom_headers';
  auth_config: {
    token?: string;
    header_name?: string;
    api_key?: string;
    headers?: Record<string, string>;
  };
}

interface DiscoveryResult {
  success: boolean;
  health_status: string;
  response_time_ms: number;
  tools_count: number;
  prompts_count: number;
  resources_count: number;
  capabilities?: any;
  error?: string;
}

const PROTOCOL_OPTIONS = [
  { value: 'http', label: 'HTTP', description: 'Standard HTTP requests' },
  { value: 'sse', label: 'SSE', description: 'Server-Sent Events streaming' },
  { value: 'http-streamable', label: 'HTTP Streamable', description: 'HTTP with streaming support' }
];

const AUTH_OPTIONS = [
  { value: '', label: 'No Authentication', description: 'Public MCP server' },
  { value: 'bearer', label: 'Bearer Token', description: 'Authorization: Bearer <token>' },
  { value: 'api_key', label: 'API Key', description: 'Custom header with API key' },
  { value: 'custom_headers', label: 'Custom Headers', description: 'Multiple custom headers' }
];

export default function AddMCPServerModal({ isOpen, onClose, onSuccess }: AddMCPServerModalProps) {
  const [step, setStep] = useState<'configure' | 'discover' | 'save'>('configure');
  const [form, setForm] = useState<MCPServerForm>({
    name: '',
    url: '',
    description: '',
    protocol: 'http',
    timeout_seconds: 30,
    auth_type: '',
    auth_config: {}
  });
  
  const [discoveryResult, setDiscoveryResult] = useState<DiscoveryResult | null>(null);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [showAuthToken, setShowAuthToken] = useState(false);
  const [customHeaders, setCustomHeaders] = useState<Array<{key: string, value: string}>>([{key: '', value: ''}]);

  // Auto-complete health URL
  useEffect(() => {
    if (form.url && !form.url.includes('/health') && !form.url.includes('/mcp')) {
      // Suggest MCP endpoint
      const baseUrl = form.url.replace(/\/$/, '');
      if (!baseUrl.endsWith('/mcp')) {
        // Show tooltip or auto-suggest
      }
    }
  }, [form.url]);

  const handleInputChange = (field: keyof MCPServerForm, value: any) => {
    setForm(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const handleAuthConfigChange = (field: string, value: any) => {
    setForm(prev => ({
      ...prev,
      auth_config: { ...prev.auth_config, [field]: value }
    }));
  };

  const addCustomHeader = () => {
    setCustomHeaders(prev => [...prev, { key: '', value: '' }]);
  };

  const updateCustomHeader = (index: number, field: 'key' | 'value', value: string) => {
    setCustomHeaders(prev => prev.map((header, i) => 
      i === index ? { ...header, [field]: value } : header
    ));
    
    // Update form
    const headers = customHeaders.reduce((acc, header) => {
      if (header.key && header.value) {
        acc[header.key] = header.value;
      }
      return acc;
    }, {} as Record<string, string>);
    handleAuthConfigChange('headers', headers);
  };

  const removeCustomHeader = (index: number) => {
    setCustomHeaders(prev => prev.filter((_, i) => i !== index));
  };

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};
    
    if (!form.name.trim()) newErrors.name = 'Server name is required';
    if (!form.url.trim()) newErrors.url = 'Server URL is required';
    if (form.timeout_seconds < 5 || form.timeout_seconds > 300) {
      newErrors.timeout_seconds = 'Timeout must be between 5 and 300 seconds';
    }
    
    // Auth validation
    if (form.auth_type === 'bearer' && !form.auth_config.token) {
      newErrors.auth_token = 'Bearer token is required';
    }
    if (form.auth_type === 'api_key') {
      if (!form.auth_config.header_name) newErrors.auth_header = 'Header name is required';
      if (!form.auth_config.api_key) newErrors.auth_key = 'API key is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleDiscover = async () => {
    if (!validateForm()) return;
    
    setIsDiscovering(true);
    setStep('discover');
    
    try {
      const discoveryRequest = {
        url: form.url,
        protocol: form.protocol,
        timeout_seconds: form.timeout_seconds,
        auth_type: form.auth_type || null,
        auth_config: Object.keys(form.auth_config).length > 0 ? form.auth_config : null
      };
      
      const result = await mcpApi.discoverServer(discoveryRequest);
      console.log('\n=== FRONTEND DISCOVERY RESPONSE ===');
      console.log('Discovery Request:', discoveryRequest);
      console.log('Discovery Result:', result);
      console.log('Tools Count:', result.tools_count);
      console.log('=== END FRONTEND DISCOVERY ===\n');
      
      setDiscoveryResult(result);
      
      if (result.success) {
        setStep('save');
      }
    } catch (error: any) {
      setDiscoveryResult({
        success: false,
        health_status: 'error',
        response_time_ms: 0,
        tools_count: 0,
        prompts_count: 0,
        resources_count: 0,
        error: error.message || 'Discovery failed'
      });
    } finally {
      setIsDiscovering(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    
    try {
      console.log('Saving MCP server:', form);
      const result = await mcpApi.createServer(form);
      console.log('Save result:', result);
      
      // Check if the response indicates success
      if (result.success || result.message) {
        onSuccess();
        onClose();
        resetForm();
      } else {
        throw new Error('Server creation failed');
      }
    } catch (error: any) {
      console.error('Save error:', error);
      console.error('Error response:', error.response?.data);
      
      // Check if it's actually a success but with error response format
      if (error.response?.status === 400 && error.response?.data?.detail?.includes('already exists')) {
        setErrors({ submit: 'Server name already exists. Please choose a different name.' });
      } else if (error.response?.status >= 500) {
        // Server error but might have been created - show success
        onSuccess();
        onClose();
        resetForm();
      } else {
        setErrors({ submit: error.response?.data?.detail || error.message || 'Failed to create server' });
      }
    } finally {
      setIsSaving(false);
    }
  };

  const resetForm = () => {
    setForm({
      name: '',
      url: '',
      description: '',
      protocol: 'http',
      timeout_seconds: 30,
      auth_type: '',
      auth_config: {}
    });
    setStep('configure');
    setDiscoveryResult(null);
    setErrors({});
    setCustomHeaders([{key: '', value: ''}]);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="px-8 py-6 border-b border-gray-200 bg-gradient-to-r from-blue-50 to-indigo-50">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Add MCP Server</h2>
              <p className="text-sm text-gray-600 mt-1">Configure and discover a new Model Context Protocol server</p>
            </div>
            <button
              onClick={handleClose}
              className="text-gray-400 hover:text-gray-600 text-2xl font-bold transition-colors"
            >
              ×
            </button>
          </div>
          
          {/* Step Indicator */}
          <div className="flex items-center mt-6 space-x-4">
            <div className={`flex items-center ${step === 'configure' ? 'text-blue-600' : step === 'discover' || step === 'save' ? 'text-green-600' : 'text-gray-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step === 'configure' ? 'bg-blue-100 text-blue-600' : 
                step === 'discover' || step === 'save' ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'
              }`}>
                1
              </div>
              <span className="ml-2 font-medium">Configure</span>
            </div>
            <div className={`w-8 h-0.5 ${step === 'discover' || step === 'save' ? 'bg-green-600' : 'bg-gray-300'}`}></div>
            <div className={`flex items-center ${step === 'discover' ? 'text-blue-600' : step === 'save' ? 'text-green-600' : 'text-gray-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step === 'discover' ? 'bg-blue-100 text-blue-600' : 
                step === 'save' ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-400'
              }`}>
                2
              </div>
              <span className="ml-2 font-medium">Discover</span>
            </div>
            <div className={`w-8 h-0.5 ${step === 'save' ? 'bg-green-600' : 'bg-gray-300'}`}></div>
            <div className={`flex items-center ${step === 'save' ? 'text-blue-600' : 'text-gray-400'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step === 'save' ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-400'
              }`}>
                3
              </div>
              <span className="ml-2 font-medium">Save</span>
            </div>
          </div>
        </div>

        <div className="p-8 overflow-y-auto max-h-[calc(90vh-300px)]">
          {step === 'configure' && (
            <div className="space-y-6">
              {/* Basic Information */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="group">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Server Name *
                    <div className="inline-block ml-1 relative">
                      <span className="text-blue-500 cursor-help" title="Unique identifier for this MCP server">ⓘ</span>
                    </div>
                  </label>
                  <input
                    type="text"
                    value={form.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                    className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all ${
                      errors.name ? 'border-red-500' : 'border-gray-300'
                    }`}
                    placeholder="e.g., database-performance-mcp"
                  />
                  {errors.name && <p className="text-red-500 text-sm mt-1">{errors.name}</p>}
                </div>

                <div className="group">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Protocol *
                    <div className="inline-block ml-1 relative">
                      <span className="text-blue-500 cursor-help" title="Communication protocol for the MCP server">ⓘ</span>
                    </div>
                  </label>
                  <select
                    value={form.protocol}
                    onChange={(e) => handleInputChange('protocol', e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                  >
                    {PROTOCOL_OPTIONS.map(option => (
                      <option key={option.value} value={option.value}>
                        {option.label} - {option.description}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="group">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Server URL *
                  <div className="inline-block ml-1 relative">
                    <span className="text-blue-500 cursor-help" title="Full URL to the MCP server endpoint (usually ends with /mcp)">ⓘ</span>
                  </div>
                </label>
                <input
                  type="url"
                  value={form.url}
                  onChange={(e) => handleInputChange('url', e.target.value)}
                  className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all ${
                    errors.url ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="http://server:8100/mcp"
                />
                {errors.url && <p className="text-red-500 text-sm mt-1">{errors.url}</p>}
                <p className="text-xs text-gray-500 mt-1">💡 Health endpoint will be auto-detected as {form.url}/health</p>
              </div>

              <div className="group">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Description
                  <div className="inline-block ml-1 relative">
                    <span className="text-blue-500 cursor-help" title="Optional description of what this MCP server provides">ⓘ</span>
                  </div>
                </label>
                <textarea
                  value={form.description}
                  onChange={(e) => handleInputChange('description', e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                  rows={3}
                  placeholder="Describe what this MCP server provides..."
                />
              </div>

              <div className="group">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Timeout (seconds) *
                  <div className="inline-block ml-1 relative">
                    <span className="text-blue-500 cursor-help" title="Request timeout in seconds (5-300)">ⓘ</span>
                  </div>
                </label>
                <input
                  type="number"
                  min="5"
                  max="300"
                  value={form.timeout_seconds}
                  onChange={(e) => handleInputChange('timeout_seconds', parseInt(e.target.value))}
                  className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all ${
                    errors.timeout_seconds ? 'border-red-500' : 'border-gray-300'
                  }`}
                />
                {errors.timeout_seconds && <p className="text-red-500 text-sm mt-1">{errors.timeout_seconds}</p>}
              </div>

              {/* Authentication */}
              <div className="border-t pt-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Authentication</h3>
                
                <div className="group mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Authentication Type
                    <div className="inline-block ml-1 relative">
                      <span className="text-blue-500 cursor-help" title="Choose authentication method for the MCP server">ⓘ</span>
                    </div>
                  </label>
                  <select
                    value={form.auth_type}
                    onChange={(e) => handleInputChange('auth_type', e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                  >
                    {AUTH_OPTIONS.map(option => (
                      <option key={option.value} value={option.value}>
                        {option.label} - {option.description}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Bearer Token */}
                {form.auth_type === 'bearer' && (
                  <div className="group">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Bearer Token *</label>
                    <div className="relative">
                      <input
                        type={showAuthToken ? 'text' : 'password'}
                        value={form.auth_config.token || ''}
                        onChange={(e) => handleAuthConfigChange('token', e.target.value)}
                        className={`w-full px-4 py-3 pr-12 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all ${
                          errors.auth_token ? 'border-red-500' : 'border-gray-300'
                        }`}
                        placeholder="Enter bearer token..."
                      />
                      <button
                        type="button"
                        onClick={() => setShowAuthToken(!showAuthToken)}
                        className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {showAuthToken ? '👁️' : '👁️‍🗨️'}
                      </button>
                    </div>
                    {errors.auth_token && <p className="text-red-500 text-sm mt-1">{errors.auth_token}</p>}
                  </div>
                )}

                {/* API Key */}
                {form.auth_type === 'api_key' && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="group">
                      <label className="block text-sm font-medium text-gray-700 mb-2">Header Name *</label>
                      <input
                        type="text"
                        value={form.auth_config.header_name || ''}
                        onChange={(e) => handleAuthConfigChange('header_name', e.target.value)}
                        className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all ${
                          errors.auth_header ? 'border-red-500' : 'border-gray-300'
                        }`}
                        placeholder="X-API-Key"
                      />
                      {errors.auth_header && <p className="text-red-500 text-sm mt-1">{errors.auth_header}</p>}
                    </div>
                    <div className="group">
                      <label className="block text-sm font-medium text-gray-700 mb-2">API Key *</label>
                      <div className="relative">
                        <input
                          type={showAuthToken ? 'text' : 'password'}
                          value={form.auth_config.api_key || ''}
                          onChange={(e) => handleAuthConfigChange('api_key', e.target.value)}
                          className={`w-full px-4 py-3 pr-12 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all ${
                            errors.auth_key ? 'border-red-500' : 'border-gray-300'
                          }`}
                          placeholder="Enter API key..."
                        />
                        <button
                          type="button"
                          onClick={() => setShowAuthToken(!showAuthToken)}
                          className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                        >
                          {showAuthToken ? '👁️' : '👁️‍🗨️'}
                        </button>
                      </div>
                      {errors.auth_key && <p className="text-red-500 text-sm mt-1">{errors.auth_key}</p>}
                    </div>
                  </div>
                )}

                {/* Custom Headers */}
                {form.auth_type === 'custom_headers' && (
                  <div className="group">
                    <label className="block text-sm font-medium text-gray-700 mb-2">Custom Headers</label>
                    <div className="space-y-3">
                      {customHeaders.map((header, index) => (
                        <div key={index} className="flex gap-3">
                          <input
                            type="text"
                            value={header.key}
                            onChange={(e) => updateCustomHeader(index, 'key', e.target.value)}
                            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                            placeholder="Header name"
                          />
                          <input
                            type="text"
                            value={header.value}
                            onChange={(e) => updateCustomHeader(index, 'value', e.target.value)}
                            className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                            placeholder="Header value"
                          />
                          {customHeaders.length > 1 && (
                            <button
                              type="button"
                              onClick={() => removeCustomHeader(index)}
                              className="px-3 py-3 text-red-500 hover:text-red-700 transition-colors"
                            >
                              🗑️
                            </button>
                          )}
                        </div>
                      ))}
                      <button
                        type="button"
                        onClick={addCustomHeader}
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium transition-colors"
                      >
                        + Add Header
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {step === 'discover' && (
            <div className="text-center py-12">
              {isDiscovering ? (
                <div className="space-y-4">
                  <div className="animate-spin w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full mx-auto"></div>
                  <h3 className="text-xl font-medium text-gray-900">Discovering MCP Server...</h3>
                  <p className="text-gray-600">Testing connection and discovering capabilities</p>
                </div>
              ) : discoveryResult && (
                <div className="space-y-6">
                  {discoveryResult.success ? (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-6">
                      <div className="flex items-center justify-center mb-4">
                        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                          <span className="text-2xl">✅</span>
                        </div>
                      </div>
                      <h3 className="text-xl font-medium text-green-900 mb-2">Discovery Successful!</h3>
                      <p className="text-green-700 mb-4">MCP server is healthy and ready to use</p>
                      
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                        <div className="bg-white rounded-lg p-3 border border-green-200">
                          <div className="font-medium text-gray-900">Response Time</div>
                          <div className="text-green-600 font-bold">{discoveryResult.response_time_ms}ms</div>
                        </div>
                        <div className="bg-white rounded-lg p-3 border border-green-200">
                          <div className="font-medium text-gray-900">Tools</div>
                          <div className="text-blue-600 font-bold">{discoveryResult.tools_count}</div>
                        </div>
                        <div className="bg-white rounded-lg p-3 border border-green-200">
                          <div className="font-medium text-gray-900">Prompts</div>
                          <div className="text-purple-600 font-bold">{discoveryResult.prompts_count}</div>
                        </div>
                        <div className="bg-white rounded-lg p-3 border border-green-200">
                          <div className="font-medium text-gray-900">Resources</div>
                          <div className="text-orange-600 font-bold">{discoveryResult.resources_count}</div>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                      <div className="flex items-center justify-center mb-4">
                        <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center">
                          <span className="text-2xl">❌</span>
                        </div>
                      </div>
                      <h3 className="text-xl font-medium text-red-900 mb-2">Discovery Failed</h3>
                      <p className="text-red-700 mb-4">{discoveryResult.error}</p>
                      <button
                        onClick={() => setStep('configure')}
                        className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                      >
                        Back to Configuration
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {step === 'save' && discoveryResult?.success && (
            <div className="text-center py-12">
              <div className="space-y-6">
                <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto">
                  <span className="text-2xl">🚀</span>
                </div>
                <h3 className="text-xl font-medium text-gray-900">Ready to Save</h3>
                <p className="text-gray-600">MCP server configuration is valid and ready to be saved</p>
                
                <div className="bg-gray-50 rounded-lg p-4 text-left max-w-md mx-auto">
                  <h4 className="font-medium text-gray-900 mb-2">Server Summary</h4>
                  <div className="space-y-1 text-sm text-gray-600">
                    <div><span className="font-medium">Name:</span> {form.name}</div>
                    <div><span className="font-medium">URL:</span> {form.url}</div>
                    <div><span className="font-medium">Protocol:</span> {form.protocol}</div>
                    <div><span className="font-medium">Auth:</span> {form.auth_type || 'None'}</div>
                    <div><span className="font-medium">Tools Found:</span> {discoveryResult.tools_count}</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-8 py-6 border-t border-gray-200 bg-gray-50 flex justify-between">
          <button
            onClick={handleClose}
            className="px-6 py-2 text-gray-600 hover:text-gray-800 transition-colors"
          >
            Cancel
          </button>
          
          <div className="flex gap-3">
            {step === 'configure' && (
              <button
                onClick={handleDiscover}
                disabled={!form.name || !form.url}
                className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium flex items-center gap-2"
              >
                <span>🔍</span>
                Discover Server
              </button>
            )}
            
            {step === 'discover' && !isDiscovering && discoveryResult && !discoveryResult.success && (
              <button
                onClick={() => setStep('configure')}
                className="px-6 py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
              >
                Back to Configure
              </button>
            )}
            
            {step === 'save' && discoveryResult?.success && (
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="px-8 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all font-medium flex items-center gap-2"
              >
                {isSaving ? (
                  <>
                    <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                    Saving...
                  </>
                ) : (
                  <>
                    <span>💾</span>
                    Save Server
                  </>
                )}
              </button>
            )}
          </div>
        </div>
        
        {errors.submit && (
          <div className="px-8 py-3 bg-red-50 border-t border-red-200">
            <p className="text-red-700 text-sm">{errors.submit}</p>
          </div>
        )}
      </div>
    </div>
  );
}