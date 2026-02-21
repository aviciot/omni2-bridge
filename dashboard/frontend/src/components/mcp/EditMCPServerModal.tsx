import { useState, useEffect } from 'react';

interface EditMCPServerModalProps {
  isOpen: boolean;
  onClose: () => void;
  server: {
    id: number;
    name: string;
    url: string;
    status: string;
    auth_type?: string;
    auth_config?: any;
  } | null;
  onSave: (serverId: number, updates: any) => Promise<void>;
}

export default function EditMCPServerModal({ isOpen, onClose, server, onSave }: EditMCPServerModalProps) {
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [status, setStatus] = useState('active');
  const [authType, setAuthType] = useState('none');
  const [authConfig, setAuthConfig] = useState('{}');
  const [bearerToken, setBearerToken] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (server) {
      setName(server.name);
      setUrl(server.url);
      setStatus(server.status);
      setAuthType(server.auth_type || 'none');
      setAuthConfig(JSON.stringify(server.auth_config || {}, null, 2));
      
      // Parse existing auth config
      const config = server.auth_config || {};
      setBearerToken(config.token || config.bearer_token || '');
      setApiKey(config.api_key || config.key || '');
      setUsername(config.username || '');
      setPassword(config.password || '');
    }
  }, [server]);

  if (!isOpen || !server) return null;

  const handleSave = async () => {
    try {
      setSaving(true);
      setError('');

      let parsedAuthConfig = {};
      if (authType !== 'none') {
        // Build auth config based on type
        if (authType === 'bearer') {
          parsedAuthConfig = { token: bearerToken };
        } else if (authType === 'api_key') {
          parsedAuthConfig = { api_key: apiKey };
        } else if (authType === 'basic') {
          parsedAuthConfig = { username, password };
        } else {
          // Fallback to JSON parsing for custom types
          try {
            parsedAuthConfig = JSON.parse(authConfig);
          } catch (e) {
            setError('Invalid JSON in auth config');
            setSaving(false);
            return;
          }
        }
      }

      await onSave(server.id, {
        name,
        url,
        status,
        auth_type: authType,
        auth_config: parsedAuthConfig
      });

      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-2xl font-bold text-gray-900">Edit MCP Server</h2>
        </div>

        <div className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Server Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="My MCP Server"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Server URL
            </label>
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              placeholder="http://localhost:8080"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Status
            </label>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
              <option value="disabled">Disabled</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Authentication Type
            </label>
            <select
              value={authType}
              onChange={(e) => setAuthType(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              <option value="none">None</option>
              <option value="bearer">Bearer Token</option>
              <option value="basic">Basic Auth</option>
              <option value="api_key">API Key</option>
            </select>
          </div>

          {authType === 'bearer' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Bearer Token
              </label>
              <input
                type="password"
                value={bearerToken}
                onChange={(e) => setBearerToken(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono text-sm"
                placeholder="your-bearer-token-here"
              />
              <p className="text-xs text-gray-500 mt-1">
                Format: Authorization: Bearer &lt;token&gt;
              </p>
            </div>
          )}

          {authType === 'api_key' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                API Key
              </label>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent font-mono text-sm"
                placeholder="your-api-key-here"
              />
              <p className="text-xs text-gray-500 mt-1">
                API key for authentication
              </p>
            </div>
          )}

          {authType === 'basic' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Username
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="username"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Password
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                  placeholder="password"
                />
              </div>
              <p className="text-xs text-gray-500">
                Format: Authorization: Basic &lt;base64(username:password)&gt;
              </p>
            </div>
          )}
        </div>

        <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={saving}
            className="px-4 py-2 text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}
