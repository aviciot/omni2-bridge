"use client";

import { useState, useEffect } from 'react';
import { IAMUser } from '@/types/iam';
import { API_CONFIG } from '@/lib/config';

interface Token {
  id: number;
  name: string;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
}

interface Props {
  user: IAMUser;
  onClose: () => void;
}

export default function GenerateMCPTokenModal({ user, onClose }: Props) {
  const [loading, setLoading] = useState(false);
  const [tokens, setTokens] = useState<Token[]>([]);
  const [generatedToken, setGeneratedToken] = useState<string | null>(null);
  const [showGenerateForm, setShowGenerateForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    expires_days: 90
  });

  useEffect(() => {
    loadTokens();
  }, []);

  const loadTokens = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_CONFIG.AUTH_SERVICE_URL}/mcp/tokens`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'X-User-Id': user.id.toString()
        }
      });
      const data = await response.json();
      setTokens(data.tokens || []);
    } catch (error) {
      console.error('Failed to load tokens:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!formData.name.trim()) {
      alert('Token name is required');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_CONFIG.AUTH_SERVICE_URL}/mcp/tokens/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'X-User-Id': user.id.toString()
        },
        body: JSON.stringify({
          name: formData.name,
          expires_days: formData.expires_days || null
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to generate token');
      }

      const data = await response.json();
      setGeneratedToken(data.token);
      setShowGenerateForm(false);
      setFormData({ name: '', expires_days: 90 });
    } catch (error: any) {
      alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (tokenId: number) => {
    if (!confirm('Revoke this token? It will stop working immediately.')) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_CONFIG.AUTH_SERVICE_URL}/mcp/tokens/${tokenId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
          'X-User-Id': user.id.toString()
        }
      });

      if (!response.ok) throw new Error('Failed to revoke token');
      
      await loadTokens();
    } catch (error: any) {
      alert(error.message);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (generatedToken) {
      navigator.clipboard.writeText(generatedToken);
      alert('Token copied to clipboard!');
    }
  };

  const formatDate = (date: string | null) => {
    if (!date) return 'Never';
    return new Date(date).toLocaleDateString();
  };

  if (generatedToken) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white rounded-xl p-6 max-w-lg w-full mx-4">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Token Generated!</h3>

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-4">
            <p className="text-sm text-yellow-800 font-semibold mb-2">
              ⚠️ Save this token now - you won't see it again!
            </p>
            <p className="text-xs text-yellow-700">
              Copy and paste this token into your Claude Desktop or Cursor configuration.
            </p>
          </div>

          <label className="block text-sm font-medium text-gray-700 mb-2">
            MCP Access Token
          </label>
          <div className="relative mb-6">
            <input
              type="text"
              value={generatedToken}
              readOnly
              className="w-full px-3 py-2 pr-20 border border-gray-300 rounded-lg bg-gray-50 font-mono text-sm"
            />
            <button
              onClick={copyToClipboard}
              className="absolute right-2 top-1/2 -translate-y-1/2 px-3 py-1 bg-purple-600 text-white text-sm rounded hover:bg-purple-700"
            >
              Copy
            </button>
          </div>

          <button
            onClick={() => {
              setGeneratedToken(null);
              loadTokens();
            }}
            className="w-full px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
          >
            Done
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <h3 className="text-xl font-bold text-gray-900 mb-4">
          MCP Tokens for {user.name}
        </h3>

        {!showGenerateForm ? (
          <>
            <div className="mb-6">
              {loading ? (
                <div className="text-center py-8 text-gray-500">Loading tokens...</div>
              ) : tokens.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-500 mb-4">No MCP tokens yet</p>
                  <p className="text-sm text-gray-400">Generate a token to allow this user to connect Claude Desktop or Cursor</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {tokens.map((token) => (
                    <div key={token.id} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <h4 className="font-semibold text-gray-900">{token.name}</h4>
                          <div className="text-sm text-gray-500 mt-1 space-y-1">
                            <div>Created: {formatDate(token.created_at)}</div>
                            <div>Last used: {formatDate(token.last_used_at)}</div>
                            <div>Expires: {formatDate(token.expires_at)}</div>
                          </div>
                        </div>
                        <button
                          onClick={() => handleRevoke(token.id)}
                          disabled={loading}
                          className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded disabled:opacity-50"
                        >
                          Revoke
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Close
              </button>
              <button
                onClick={() => setShowGenerateForm(true)}
                className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
              >
                + Generate New Token
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="space-y-4 mb-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Token Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Claude Desktop, Cursor IDE"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Expiration
                </label>
                <select
                  value={formData.expires_days}
                  onChange={(e) => setFormData({ ...formData, expires_days: parseInt(e.target.value) })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
                >
                  <option value={7}>7 days</option>
                  <option value={30}>30 days</option>
                  <option value={90}>90 days</option>
                  <option value={180}>180 days</option>
                  <option value={365}>1 year</option>
                  <option value={0}>Never expires</option>
                </select>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowGenerateForm(false)}
                disabled={loading}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
              >
                Back
              </button>
              <button
                onClick={handleGenerate}
                disabled={loading}
                className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
              >
                {loading ? 'Generating...' : 'Generate Token'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
