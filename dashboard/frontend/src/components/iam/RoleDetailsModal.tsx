"use client";

import { Role } from '@/types/iam';

interface Props {
  role: Role;
  users: any[];
  onClose: () => void;
}

export default function RoleDetailsModal({ role, users, onClose }: Props) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl p-6 max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex justify-between items-start mb-6">
          <div>
            <h3 className="text-2xl font-bold text-gray-900">{role.name}</h3>
            <p className="text-sm text-gray-600 mt-1">{role.description || 'No description'}</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl"
          >
            ×
          </button>
        </div>

        <div className="space-y-6">
          {/* Basic Info */}
          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="font-semibold text-gray-900 mb-3">Configuration</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Dashboard Access:</span>
                <span className="ml-2 font-medium text-gray-900">{role.dashboard_access || 'none'}</span>
              </div>
              <div>
                <span className="text-gray-600">Rate Limit:</span>
                <span className="ml-2 font-medium text-gray-900">{role.rate_limit} req/min</span>
              </div>
              <div>
                <span className="text-gray-600">Daily Cost Limit:</span>
                <span className="ml-2 font-medium text-gray-900">${role.cost_limit_daily}</span>
              </div>
              <div>
                <span className="text-gray-600">Token Expiry:</span>
                <span className="ml-2 font-medium text-gray-900">{role.token_expiry}s</span>
              </div>
            </div>
          </div>

          {/* MCP Access */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-3">MCP Access ({role.mcp_access?.length || 0})</h4>
            {role.mcp_access && role.mcp_access.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {role.mcp_access.map(mcp => (
                  <span key={mcp} className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
                    {mcp}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No MCP access configured</p>
            )}
          </div>

          {/* Tool Restrictions */}
          {role.tool_restrictions && Object.keys(role.tool_restrictions).length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-900 mb-3">Tool Restrictions</h4>
              <div className="bg-gray-50 rounded-lg p-4">
                <pre className="text-xs text-gray-700 overflow-x-auto">
                  {JSON.stringify(role.tool_restrictions, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Assigned Users */}
          <div>
            <h4 className="font-semibold text-gray-900 mb-3">Assigned Users ({users.length})</h4>
            {users.length > 0 ? (
              <div className="border border-gray-200 rounded-lg overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left font-medium text-gray-700">Name</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-700">Email</th>
                      <th className="px-4 py-2 text-left font-medium text-gray-700">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {users.map(user => (
                      <tr key={user.id} className="hover:bg-gray-50">
                        <td className="px-4 py-2 font-medium text-gray-900">{user.name}</td>
                        <td className="px-4 py-2 text-gray-600">{user.email}</td>
                        <td className="px-4 py-2">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            user.active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                          }`}>
                            {user.active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-gray-500">No users assigned to this role</p>
            )}
          </div>
        </div>

        <div className="mt-6">
          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
