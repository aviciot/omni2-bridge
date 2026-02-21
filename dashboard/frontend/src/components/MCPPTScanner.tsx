"use client";

import { useState, useEffect } from "react";
import { omni2Api } from "@/lib/omni2Api";
import { mcpApi, MCPServer } from "@/lib/mcpApi";

interface MCPPTConfig {
  enabled: boolean;
  tools: {
    presidio: boolean;
    truffleHog: boolean;
    nuclei: boolean;
    semgrep: boolean;
  };
  scan_depth: string;
  auto_scan: boolean;
  schedule_cron: string;
}

interface MCP {
  id: number;
  name: string;
  url: string;
  enabled: boolean;
  health_status: string;
}

interface ScanResult {
  id: number;
  mcp_name: string;
  mcp_url: string;
  score: number;
  findings: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  scanned_at: string;
}

export default function MCPPTScanner() {
  const [config, setConfig] = useState<MCPPTConfig | null>(null);
  const [mcps, setMcps] = useState<MCP[]>([]);
  const [selectedMcps, setSelectedMcps] = useState<string[]>([]);
  const [scans, setScans] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    loadConfig();
    loadMcps();
    loadScans();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await omni2Api.get('/api/v1/mcp-pt/config');
      setConfig(response.data.config_value);
    } catch (error: any) {
      showMessage("error", "Failed to load configuration");
    } finally {
      setLoading(false);
    }
  };

  const loadMcps = async () => {
    try {
      const response = await mcpApi.getServers(false, true);
      setMcps(response.servers.map(s => ({
        id: s.id,
        name: s.name,
        url: s.url,
        enabled: s.enabled,
        health_status: s.health_status
      })));
    } catch (error: any) {
      console.error("Failed to load MCPs", error);
      setMcps([]);
    }
  };

  const loadScans = async () => {
    try {
      const response = await omni2Api.get('/api/v1/mcp-pt/scans?limit=10');
      setScans(Array.isArray(response.data) ? response.data : []);
    } catch (error: any) {
      console.error("Failed to load scans", error);
      setScans([]);
    }
  };

  const showMessage = (type: "success" | "error", text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  const handleSaveConfig = async () => {
    if (!config) return;
    try {
      await omni2Api.put('/api/v1/mcp-pt/config', config);
      showMessage("success", "Configuration saved successfully");
    } catch (error: any) {
      showMessage("error", "Failed to save configuration");
    }
  };

  const handleStartScan = async () => {
    if (selectedMcps.length === 0) {
      showMessage("error", "Please select at least one MCP");
      return;
    }

    setScanning(true);
    try {
      await omni2Api.post('/api/v1/mcp-pt/scan', {
        mcp_names: selectedMcps,
        test_prompts: []
      });
      showMessage("success", `Scan started for ${selectedMcps.length} MCP(s)`);
      
      // Reload scans after 5 seconds
      setTimeout(() => {
        loadScans();
        setScanning(false);
      }, 5000);
    } catch (error: any) {
      showMessage("error", "Failed to start scan");
      setScanning(false);
    }
  };

  const toggleMcp = (name: string) => {
    setSelectedMcps(prev =>
      prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name]
    );
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-green-600 bg-green-100";
    if (score >= 70) return "text-yellow-600 bg-yellow-100";
    if (score >= 50) return "text-orange-600 bg-orange-100";
    return "text-red-600 bg-red-100";
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical": return "bg-red-600";
      case "high": return "bg-orange-500";
      case "medium": return "bg-yellow-500";
      case "low": return "bg-blue-500";
      default: return "bg-gray-500";
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Failed to load configuration</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-12 h-12 bg-gradient-to-br from-red-600 to-orange-600 rounded-xl flex items-center justify-center shadow-lg">
              <span className="text-2xl">🔍</span>
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">MCP Penetration Testing</h1>
              <p className="text-gray-600">Security scanning with PII/Secrets detection</p>
            </div>
          </div>
        </div>

        {/* Message */}
        {message && (
          <div className={`mb-6 p-5 rounded-xl shadow-lg border-2 ${
            message.type === "success" 
              ? "bg-green-50 text-green-900 border-green-300" 
              : "bg-red-50 text-red-900 border-red-300"
          }`}>
            <div className="flex items-center gap-3">
              <span className="text-2xl">{message.type === "success" ? "✅" : "❌"}</span>
              <span className="font-semibold text-lg">{message.text}</span>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Scanner Panel */}
          <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-200">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <span className="text-xl">🎯</span>
              </div>
              <h3 className="text-xl font-bold text-gray-900">Start Scan</h3>
            </div>

            {/* Select MCPs */}
            <div className="mb-6">
              <label className="block text-sm font-bold text-gray-700 mb-3">
                Select MCPs to Scan
              </label>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {mcps.map((mcp) => (
                  <label
                    key={mcp.name}
                    className={`flex items-center space-x-3 p-3 border-2 rounded-xl cursor-pointer transition-all ${
                      selectedMcps.includes(mcp.name)
                        ? "bg-purple-50 border-purple-300"
                        : "border-gray-200 hover:bg-gray-50"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={selectedMcps.includes(mcp.name)}
                      onChange={() => toggleMcp(mcp.name)}
                      disabled={!mcp.enabled || mcp.health_status !== 'healthy'}
                      className="w-5 h-5 text-purple-600 border-gray-300 rounded"
                    />
                    <div className="flex-1">
                      <span className="text-sm font-semibold text-gray-700">{mcp.name}</span>
                      <p className="text-xs text-gray-500">{mcp.url}</p>
                    </div>
                    {!mcp.enabled && (
                      <span className="text-xs text-red-600 font-semibold">Disabled</span>
                    )}
                    {mcp.enabled && mcp.health_status !== 'healthy' && (
                      <span className="text-xs text-orange-600 font-semibold">Unhealthy</span>
                    )}
                  </label>
                ))}
              </div>
            </div>

            {/* Scan Depth */}
            <div className="mb-6">
              <label className="block text-sm font-bold text-gray-700 mb-3">
                Scan Depth
              </label>
              <select
                value={config.scan_depth}
                onChange={(e) => setConfig({ ...config, scan_depth: e.target.value })}
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-purple-500 focus:outline-none"
              >
                <option value="quick">⚡ Quick (5 min)</option>
                <option value="standard">🎯 Standard (15 min)</option>
                <option value="deep">🔍 Deep (30 min)</option>
              </select>
            </div>

            {/* Tools */}
            <div className="mb-6">
              <label className="block text-sm font-bold text-gray-700 mb-3">
                Detection Tools
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="flex items-center space-x-2 p-3 border-2 border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.tools.presidio}
                    onChange={(e) => setConfig({
                      ...config,
                      tools: { ...config.tools, presidio: e.target.checked }
                    })}
                    className="w-4 h-4 text-purple-600"
                  />
                  <span className="text-sm font-semibold">Presidio (PII)</span>
                </label>
                <label className="flex items-center space-x-2 p-3 border-2 border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={config.tools.truffleHog}
                    onChange={(e) => setConfig({
                      ...config,
                      tools: { ...config.tools, truffleHog: e.target.checked }
                    })}
                    className="w-4 h-4 text-purple-600"
                  />
                  <span className="text-sm font-semibold">TruffleHog</span>
                </label>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={handleStartScan}
                disabled={scanning || selectedMcps.length === 0}
                className="flex-1 px-6 py-4 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-bold rounded-xl shadow-lg transition-all disabled:opacity-50"
              >
                {scanning ? "🔄 Scanning..." : "🚀 Start Scan"}
              </button>
              <button
                onClick={handleSaveConfig}
                className="px-6 py-4 bg-gray-600 hover:bg-gray-700 text-white font-bold rounded-xl shadow-lg transition-all"
              >
                💾 Save
              </button>
            </div>
          </div>

          {/* Recent Scans */}
          <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-200">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <span className="text-xl">📊</span>
              </div>
              <h3 className="text-xl font-bold text-gray-900">Recent Scans</h3>
            </div>

            <div className="space-y-4 max-h-96 overflow-y-auto">
              {scans.length === 0 ? (
                <p className="text-gray-500 text-center py-8">No scans yet</p>
              ) : (
                scans.map((scan) => (
                  <div
                    key={scan.id}
                    className="p-4 border-2 border-gray-200 rounded-xl hover:shadow-md transition-all"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h4 className="font-bold text-gray-900">{scan.mcp_name}</h4>
                        <p className="text-xs text-gray-500">
                          {new Date(scan.scanned_at).toLocaleString()}
                        </p>
                      </div>
                      <div className={`px-4 py-2 rounded-lg font-bold text-2xl ${getScoreColor(scan.score)}`}>
                        {scan.score}
                      </div>
                    </div>

                    {/* Findings Bar */}
                    <div className="flex gap-2 mb-2">
                      {scan.findings.critical > 0 && (
                        <div className="flex items-center gap-1">
                          <div className={`w-3 h-3 rounded-full ${getSeverityColor("critical")}`}></div>
                          <span className="text-xs font-semibold">{scan.findings.critical}</span>
                        </div>
                      )}
                      {scan.findings.high > 0 && (
                        <div className="flex items-center gap-1">
                          <div className={`w-3 h-3 rounded-full ${getSeverityColor("high")}`}></div>
                          <span className="text-xs font-semibold">{scan.findings.high}</span>
                        </div>
                      )}
                      {scan.findings.medium > 0 && (
                        <div className="flex items-center gap-1">
                          <div className={`w-3 h-3 rounded-full ${getSeverityColor("medium")}`}></div>
                          <span className="text-xs font-semibold">{scan.findings.medium}</span>
                        </div>
                      )}
                      {scan.findings.low > 0 && (
                        <div className="flex items-center gap-1">
                          <div className={`w-3 h-3 rounded-full ${getSeverityColor("low")}`}></div>
                          <span className="text-xs font-semibold">{scan.findings.low}</span>
                        </div>
                      )}
                    </div>

                    {/* Progress Bar */}
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all ${
                          scan.score >= 90 ? "bg-green-500" :
                          scan.score >= 70 ? "bg-yellow-500" :
                          scan.score >= 50 ? "bg-orange-500" : "bg-red-500"
                        }`}
                        style={{ width: `${scan.score}%` }}
                      ></div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
