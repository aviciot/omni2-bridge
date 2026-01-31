"use client";

import { useState, useEffect } from 'react';
import { iamApi, getMCPServers } from '@/lib/iamApi';
import { Role } from '@/types/iam';
import CreateRoleModal from './CreateRoleModal';
import EditRoleModal from './EditRoleModal';
import RoleDetailsModal from './RoleDetailsModal';

export default function RolesTab() {
  const [roles, setRoles] = useState<Role[]>([]);
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [rolesData, usersData] = await Promise.all([
        iamApi.getRoles(),
        iamApi.getUsers()
      ]);
      setRoles(rolesData);
      setUsers(usersData.users || usersData);
    } catch (error) {
      console.error('Failed to load roles:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (role: Role) => {
    const usersWithRole = users.filter(u => u.role_id === role.id);
    
    if (usersWithRole.length > 0) {
      alert(`Cannot delete role "${role.name}".\n\n${usersWithRole.length} user(s) are assigned to this role:\n${usersWithRole.map(u => `• ${u.name} (${u.email})`).join('\n')}\n\nPlease reassign these users to another role first.`);
      return;
    }

    if (!confirm(`Delete role "${role.name}"?`)) return;

    try {
      await iamApi.deleteRole(role.id);
      await loadData();
    } catch (error: any) {
      alert(error.response?.data?.detail || 'Failed to delete role');
    }
  };

  const getUserCount = (roleId: number) => {
    return users.filter(u => u.role_id === roleId).length;
  };

  if (loading) {
    return <div className="text-center py-12">Loading roles...</div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Roles Management</h3>
          <p className="text-sm text-gray-600 mt-1">{roles.length} roles configured</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium"
        >
          + Create Role
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {roles.map(role => {
          const userCount = getUserCount(role.id);
          return (
            <div
              key={role.id}
              className="bg-white border border-gray-200 rounded-xl p-6 hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => {
                setSelectedRole(role);
                setShowDetailsModal(true);
              }}
            >
              <div className="flex justify-between items-start mb-3">
                <h4 className="text-lg font-bold text-gray-900">{role.name}</h4>
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  role.dashboard_access === 'full' ? 'bg-green-100 text-green-700' :
                  role.dashboard_access === 'read' ? 'bg-blue-100 text-blue-700' :
                  'bg-gray-100 text-gray-700'
                }`}>
                  {role.dashboard_access || 'none'}
                </span>
              </div>
              
              <p className="text-sm text-gray-600 mb-4 line-clamp-2">
                {role.description || 'No description'}
              </p>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Users:</span>
                  <span className="font-medium text-gray-900">{userCount}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">MCPs:</span>
                  <span className="font-medium text-gray-900">{role.mcp_access?.length || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Rate Limit:</span>
                  <span className="font-medium text-gray-900">{role.rate_limit}/min</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Daily Cost:</span>
                  <span className="font-medium text-gray-900">${role.cost_limit_daily}</span>
                </div>
              </div>

              <div className="flex gap-2 mt-4 pt-4 border-t border-gray-200">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedRole(role);
                    setShowEditModal(true);
                  }}
                  className="flex-1 px-3 py-1.5 text-sm bg-purple-50 text-purple-700 rounded hover:bg-purple-100"
                >
                  Edit
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(role);
                  }}
                  className="flex-1 px-3 py-1.5 text-sm bg-red-50 text-red-700 rounded hover:bg-red-100"
                >
                  Delete
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {showCreateModal && (
        <CreateRoleModal
          onClose={() => setShowCreateModal(false)}
          onSuccess={() => {
            setShowCreateModal(false);
            loadData();
          }}
        />
      )}

      {showEditModal && selectedRole && (
        <EditRoleModal
          role={selectedRole}
          userCount={getUserCount(selectedRole.id)}
          onClose={() => {
            setShowEditModal(false);
            setSelectedRole(null);
          }}
          onSuccess={() => {
            setShowEditModal(false);
            setSelectedRole(null);
            loadData();
          }}
        />
      )}

      {showDetailsModal && selectedRole && (
        <RoleDetailsModal
          role={selectedRole}
          users={users.filter(u => u.role_id === selectedRole.id)}
          onClose={() => {
            setShowDetailsModal(false);
            setSelectedRole(null);
          }}
        />
      )}
    </div>
  );
}
