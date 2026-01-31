"use client";

import { useState } from 'react';
import { iamApi } from '@/lib/iamApi';
import { Role } from '@/types/iam';
import PermissionBuilder from './PermissionBuilder';

interface Props {
  role: Role;
  userCount: number;
  onClose: () => void;
  onSuccess: () => void;
}

export default function EditRoleModal({ role, userCount, onClose, onSuccess }: Props) {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    description: role.description || '',
    mcp_access: role.mcp_access || [],
    tool_restrictions: role.tool_restrictions || {},
    dashboard_access: role.dashboard_access || 'none',
    rate_limit: role.rate_limit || 100,
    cost_limit_daily: role.cost_limit_daily || 10.00,
    token_expiry: role.token_expiry || 3600
  });

  const handleSubmit = async () => {
    setLoading(true);
    try {
      await iamApi.updateRole(role.id, formData);
      onSuccess();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to update role');
    } finally {
      setLoading(false);
    }
  };



  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <h3 className="text-xl font-bold text-gray-900 mb-2">Edit Role: {role.name}</h3>
        
        {userCount > 0 && (
          <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <p className="text-sm text-amber-800">
              ⚠️ <strong>{userCount} user(s)</strong> are assigned to this role. Changes will affect their permissions immediately.
            </p>
          </div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
            <textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Role description"
              rows={2}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
            />
          </div>

          <PermissionBuilder
            value={{
              mcp_access: formData.mcp_access,
              tool_restrictions: formData.tool_restrictions
            }}
            onChange={(value) => setFormData({ ...formData, ...value })}
          />

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Dashboard Access</label>
            <select
              value={formData.dashboard_access}
              onChange={(e) => setFormData({ ...formData, dashboard_access: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
            >
              <option value="none">None</option>
              <option value="read">Read Only</option>
              <option value="full">Full Access</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Rate Limit (req/min)</label>
              <input
                type="number"
                value={formData.rate_limit}
                onChange={(e) => setFormData({ ...formData, rate_limit: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Daily Cost Limit ($)</label>
              <input
                type="number"
                step="0.01"
                value={formData.cost_limit_daily}
                onChange={(e) => setFormData({ ...formData, cost_limit_daily: parseFloat(e.target.value) })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Token Expiry (seconds)</label>
            <input
              type="number"
              value={formData.token_expiry}
              onChange={(e) => setFormData({ ...formData, token_expiry: parseInt(e.target.value) })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500"
            />
          </div>
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={onClose}
            disabled={loading}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
          >
            {loading ? 'Updating...' : 'Update Role'}
          </button>
        </div>
      </div>
    </div>
  );
}
