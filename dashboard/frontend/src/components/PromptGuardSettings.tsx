"use client";

import { useState, useEffect } from "react";
import { omni2Api } from "@/lib/omni2Api";

interface PromptGuardConfig {
  enabled: boolean;
  threshold: number;
  mode: string;
  ml_model: string;
  cache_ttl_seconds: number;
  bypass_roles: string[];
  behavioral_tracking: {
    enabled: boolean;
    warning_threshold: number;
    block_threshold: number;
    window_hours: number;
  };
  actions: {
    warn: boolean;
    block_message: boolean;
    block_user: boolean;
  };
  messages: {
    warning: string;
    blocked_message: string;
    blocked_user: string;
  };
}

export default function PromptGuardSettings() {
  const [config, setConfig] = useState<PromptGuardConfig | null>(null);
  const [allRoles, setAllRoles] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    loadConfig();
    loadRoles();
  }, []);

  const loadConfig = async () => {
    try {
      const response = await omni2Api.get('/api/v1/prompt-guard/config');
      const configValue = response.data.config_value;
      
      // Normalize behavioral_tracking structure
      if (configValue.behavioral_tracking) {
        if ('window' in configValue.behavioral_tracking) {
          configValue.behavioral_tracking.window_hours = 24;
          delete configValue.behavioral_tracking.window;
        }
        if (!('window_hours' in configValue.behavioral_tracking)) {
          configValue.behavioral_tracking.window_hours = 24;
        }
      }
      
      setConfig(configValue);
    } catch (error: any) {
      showMessage("error", "Failed to load configuration");
    } finally {
      setLoading(false);
    }
  };

  const loadRoles = async () => {
    try {
      const response = await omni2Api.get('/api/v1/prompt-guard/roles');
      setAllRoles(response.data.all_roles || []);
    } catch (error: any) {
      console.error("Failed to load roles", error);
      setAllRoles([]);
    }
  };

  const showMessage = (type: "success" | "error", text: string) => {
    setMessage({ type, text });
    setTimeout(() => setMessage(null), 5000);
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      console.log('Saving config:', config);
      const response = await omni2Api.put('/api/v1/prompt-guard/config', config);
      console.log('Save response:', response.data);
      showMessage("success", "Configuration saved successfully");
      await loadConfig(); // Reload to confirm
    } catch (error: any) {
      console.error('Save error:', error);
      showMessage("error", "Failed to save configuration");
    } finally {
      setSaving(false);
    }
  };

  const toggleEnabled = async () => {
    if (!config) return;
    setSaving(true);
    try {
      const endpoint = config.enabled ? 'disable' : 'enable';
      await omni2Api.post(`/api/v1/prompt-guard/config/${endpoint}`);
      setConfig({ ...config, enabled: !config.enabled });
      showMessage("success", `Prompt Guard ${!config.enabled ? "enabled" : "disabled"}`);
    } catch (error: any) {
      showMessage("error", "Failed to toggle guard");
    } finally {
      setSaving(false);
    }
  };

  const toggleBypassRole = (role: string) => {
    if (!config) return;
    const bypass_roles = config.bypass_roles.includes(role)
      ? config.bypass_roles.filter((r) => r !== role)
      : [...config.bypass_roles, role];
    setConfig({ ...config, bypass_roles });
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
            <div className="w-12 h-12 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg">
              <span className="text-2xl">🛡️</span>
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Prompt Guard Security</h1>
              <p className="text-gray-600">AI-powered prompt injection detection and prevention</p>
            </div>
          </div>
        </div>

        {/* Status Banner */}
        <div className={`mb-6 p-6 rounded-2xl shadow-lg border-2 ${
          config.enabled 
            ? "bg-gradient-to-r from-green-50 to-emerald-50 border-green-200" 
            : "bg-gradient-to-r from-gray-50 to-slate-50 border-gray-300"
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className={`w-16 h-16 rounded-full flex items-center justify-center ${
                config.enabled ? "bg-green-500" : "bg-gray-400"
              } shadow-lg`}>
                <span className="text-3xl">{config.enabled ? "✓" : "○"}</span>
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">
                  {config.enabled ? "Protection Active" : "Protection Disabled"}
                </h2>
                <p className="text-gray-600">
                  {config.enabled 
                    ? "Real-time monitoring and threat detection enabled" 
                    : "Click to enable security protection"}
                </p>
              </div>
            </div>
            <button
              onClick={toggleEnabled}
              disabled={saving}
              className={`px-8 py-4 rounded-xl font-bold text-lg shadow-lg transition-all transform hover:scale-105 ${
                config.enabled
                  ? "bg-red-600 hover:bg-red-700 text-white"
                  : "bg-green-600 hover:bg-green-700 text-white"
              } disabled:opacity-50 disabled:transform-none`}
            >
              {config.enabled ? "🔴 Disable" : "🟢 Enable"}
            </button>
          </div>
        </div>

      {/* Message */}
      {message && (
        <div className={`mb-6 p-5 rounded-xl shadow-lg border-2 animate-pulse ${
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

      {/* Settings Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Detection Settings */}
        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-200 hover:shadow-2xl transition-shadow">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <span className="text-xl">🎯</span>
            </div>
            <h3 className="text-xl font-bold text-gray-900">Detection Settings</h3>
          </div>
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-3">
                Detection Mode
              </label>
              <select
                value={config.mode || 'hybrid'}
                onChange={(e) => setConfig({ ...config, mode: e.target.value })}
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-purple-500 focus:outline-none font-medium"
              >
                <option value="regex">⚡ Regex Only (Fast)</option>
                <option value="ml">🤖 ML Only (Accurate)</option>
                <option value="hybrid">🔥 Hybrid (Recommended)</option>
              </select>
              <p className="text-xs text-gray-500 mt-2">
                {config.mode === 'regex' && 'Fast pattern matching - may miss encoded injections'}
                {config.mode === 'ml' && 'AI model detection - slower but catches encoded attacks'}
                {config.mode === 'hybrid' && 'Regex first, then ML for suspicious content - best balance'}
              </p>
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-3">
                ML Model
              </label>
              <select
                value={config.ml_model || 'protectai'}
                onChange={(e) => setConfig({ ...config, ml_model: e.target.value })}
                disabled={config.mode === 'regex'}
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-purple-500 focus:outline-none font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <option value="protectai">🛡️ ProtectAI DeBERTa (Fast)</option>
                <option value="llama">🦙 Llama Guard 2 (Accurate)</option>
              </select>
              <p className="text-xs text-gray-500 mt-2">
                {config.mode === 'regex' && 'ML model not used in regex-only mode'}
                {config.ml_model === 'protectai' && config.mode !== 'regex' && 'Lightweight model, faster inference'}
                {config.ml_model === 'llama' && config.mode !== 'regex' && 'Meta\'s Llama Guard 2 - more accurate'}
              </p>
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-3">
                Detection Threshold: <span className="text-purple-600">{config.threshold.toFixed(2)}</span>
              </label>
              <input type="range" min="0" max="1" step="0.05" value={config.threshold} onChange={(e) => setConfig({ ...config, threshold: parseFloat(e.target.value) })} className="w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer" />
              <div className="flex justify-between text-xs text-gray-500 mt-2 font-medium">
                <span>🔴 More Sensitive</span>
                <span>🟢 Less Sensitive</span>
              </div>
            </div>
          </div>
        </div>

        {/* Bypass Roles */}
        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-200 hover:shadow-2xl transition-shadow">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
              <span className="text-xl">👥</span>
            </div>
            <h3 className="text-xl font-bold text-gray-900">Bypass Roles</h3>
          </div>
          <p className="text-sm text-gray-600 mb-4">Users with these roles skip all security checks</p>
          <div className="grid grid-cols-2 gap-3 max-h-64 overflow-y-auto">
            {allRoles.map((role) => (
              <label key={role} className="flex items-center space-x-3 p-3 border-2 border-gray-200 rounded-xl hover:bg-purple-50 hover:border-purple-300 cursor-pointer transition-all">
                <input type="checkbox" checked={config.bypass_roles.includes(role)} onChange={() => toggleBypassRole(role)} className="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500" />
                <span className="text-sm font-semibold text-gray-700">{role}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Behavioral Tracking */}
        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-200 hover:shadow-2xl transition-shadow lg:col-span-2">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
              <span className="text-xl">📊</span>
            </div>
            <h3 className="text-xl font-bold text-gray-900">Behavioral Tracking</h3>
          </div>
          <p className="text-sm text-gray-600 mb-6">Track user violations over time and escalate actions automatically</p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">
                Warning Threshold
              </label>
              <input 
                type="number" 
                min="1" 
                max="10" 
                value={config.behavioral_tracking.warning_threshold} 
                onChange={(e) => setConfig({ 
                  ...config, 
                  behavioral_tracking: { 
                    ...config.behavioral_tracking, 
                    warning_threshold: parseInt(e.target.value) 
                  } 
                })} 
                className="w-full px-4 py-2 border-2 border-gray-200 rounded-lg focus:border-purple-500 focus:outline-none" 
              />
              <p className="text-xs text-gray-500 mt-1">Violations before warning</p>
            </div>

            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">
                Block Threshold
              </label>
              <input 
                type="number" 
                min="1" 
                max="20" 
                value={config.behavioral_tracking.block_threshold} 
                onChange={(e) => setConfig({ 
                  ...config, 
                  behavioral_tracking: { 
                    ...config.behavioral_tracking, 
                    block_threshold: parseInt(e.target.value) 
                  } 
                })} 
                className="w-full px-4 py-2 border-2 border-gray-200 rounded-lg focus:border-purple-500 focus:outline-none" 
              />
              <p className="text-xs text-gray-500 mt-1">Violations before auto-block</p>
            </div>

            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">
                Time Window (hours)
              </label>
              <input 
                type="number" 
                min="1" 
                max="168" 
                value={config.behavioral_tracking.window_hours} 
                onChange={(e) => setConfig({ 
                  ...config, 
                  behavioral_tracking: { 
                    ...config.behavioral_tracking, 
                    window_hours: parseInt(e.target.value) 
                  } 
                })} 
                className="w-full px-4 py-2 border-2 border-gray-200 rounded-lg focus:border-purple-500 focus:outline-none" 
              />
              <p className="text-xs text-gray-500 mt-1">Count violations in last X hours</p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-200 hover:shadow-2xl transition-shadow lg:col-span-2">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
              <span className="text-xl">⚡</span>
            </div>
            <h3 className="text-xl font-bold text-gray-900">Immediate Actions</h3>
          </div>
          <p className="text-sm text-gray-600 mb-6">Configure how the system responds to detected injections</p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <label className="flex items-center space-x-3 p-4 border-2 border-gray-200 rounded-xl hover:bg-yellow-50 hover:border-yellow-300 cursor-pointer transition-all">
              <input 
                type="checkbox" 
                checked={config.actions.warn} 
                onChange={(e) => setConfig({ 
                  ...config, 
                  actions: { 
                    ...config.actions, 
                    warn: e.target.checked 
                  } 
                })} 
                className="w-5 h-5 text-yellow-600 border-gray-300 rounded focus:ring-yellow-500" 
              />
              <div>
                <span className="text-sm font-bold text-gray-700">⚠️ Warn</span>
                <p className="text-xs text-gray-500">Log detection, block message from LLM</p>
              </div>
            </label>

            <label className="flex items-center space-x-3 p-4 border-2 border-gray-200 rounded-xl hover:bg-red-50 hover:border-red-300 cursor-pointer transition-all">
              <input 
                type="checkbox" 
                checked={config.actions.block_message || false} 
                onChange={(e) => setConfig({ 
                  ...config, 
                  actions: { 
                    ...config.actions, 
                    block_message: e.target.checked,
                    block: e.target.checked
                  } 
                })} 
                className="w-5 h-5 text-red-600 border-gray-300 rounded focus:ring-red-500" 
              />
              <div>
                <span className="text-sm font-bold text-gray-700">🚫 Block High-Score Messages</span>
                <p className="text-xs text-gray-500">Block messages with score &gt; 0.8</p>
              </div>
            </label>
          </div>
        </div>

        {/* Custom Messages */}
        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-200 hover:shadow-2xl transition-shadow lg:col-span-2">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
              <span className="text-xl">💬</span>
            </div>
            <h3 className="text-xl font-bold text-gray-900">Custom Messages</h3>
          </div>
          <p className="text-sm text-gray-600 mb-6">Customize messages shown to users when security actions are triggered</p>
          
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">
                ⚠️ Warning Message
              </label>
              <input 
                type="text" 
                value={config.messages.warning} 
                onChange={(e) => setConfig({ 
                  ...config, 
                  messages: { 
                    ...config.messages, 
                    warning: e.target.value 
                  } 
                })} 
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-purple-500 focus:outline-none" 
                placeholder="Your message contains suspicious content. Please rephrase."
              />
              <p className="text-xs text-gray-500 mt-1">Shown when a suspicious prompt is detected</p>
            </div>

            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">
                🚫 Blocked Message
              </label>
              <input 
                type="text" 
                value={config.messages.blocked_message} 
                onChange={(e) => setConfig({ 
                  ...config, 
                  messages: { 
                    ...config.messages, 
                    blocked_message: e.target.value 
                  } 
                })} 
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-purple-500 focus:outline-none" 
                placeholder="Your message was blocked due to security concerns."
              />
              <p className="text-xs text-gray-500 mt-1">Shown when a high-score message is blocked</p>
            </div>

            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">
                🔒 User Blocked Message
              </label>
              <input 
                type="text" 
                value={config.messages.blocked_user} 
                onChange={(e) => setConfig({ 
                  ...config, 
                  messages: { 
                    ...config.messages, 
                    blocked_user: e.target.value 
                  } 
                })} 
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-purple-500 focus:outline-none" 
                placeholder="Your account has been suspended due to multiple security violations."
              />
              <p className="text-xs text-gray-500 mt-1">Shown when a user is auto-blocked after repeated violations</p>
            </div>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="mt-8 flex justify-center">
        <button onClick={handleSave} disabled={saving} className="px-12 py-5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white text-xl font-bold rounded-2xl shadow-2xl transition-all transform hover:scale-105 disabled:opacity-50 disabled:transform-none">
          {saving ? "🔄 Saving..." : "💾 Save Configuration"}
        </button>
      </div>
    </div>
  </div>
);
}
