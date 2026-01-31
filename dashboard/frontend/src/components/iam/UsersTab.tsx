"use client";

import { useState, useEffect } from "react";
import { iamApi } from "@/lib/iamApi";
import { IAMUser, Role } from "@/types/iam";
import UserDetailsModal from "@/components/UserDetailsModal";
import CreateUserModal from "@/components/iam/CreateUserModal";
import EditUserModal from "@/components/iam/EditUserModal";
import ConfirmDialog from "@/components/iam/ConfirmDialog";
import { API_CONFIG } from "@/lib/config";

interface UsersTabProps {
  isAdmin: boolean;
}

export default function UsersTab({ isAdmin }: UsersTabProps) {
  const [users, setUsers] = useState<IAMUser[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<boolean | null>(null);
  const [selectedUser, setSelectedUser] = useState<IAMUser | null>(null);
  const [editingUser, setEditingUser] = useState<IAMUser | null>(null);
  const [deletingUser, setDeletingUser] = useState<IAMUser | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    loadData();
  }, [search, roleFilter, statusFilter]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [usersData, rolesData] = await Promise.all([
        iamApi.getUsers({ 
          search: search || undefined, 
          role_id: roleFilter || undefined,
          active: statusFilter ?? undefined
        }),
        iamApi.getRoles()
      ]);
      setUsers(usersData.users);
      setTotal(usersData.total);
      setRoles(rolesData);
    } catch (error) {
      console.error("Failed to load data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!deletingUser) return;
    try {
      await fetch(`${API_CONFIG.AUTH_SERVICE_URL}/users/users/${deletingUser.id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          "X-User-Role": "super_admin",
        },
      });
      setDeletingUser(null);
      loadData();
    } catch (error) {
      console.error("Failed to delete user:", error);
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-2xl font-bold text-gray-900">Users Management</h3>
          <p className="text-gray-600 mt-1">{total} total users</p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white rounded-xl font-semibold shadow-lg transition-all transform hover:scale-105 flex items-center gap-2"
          >
            <span className="text-xl">➕</span>
            Create User
          </button>
        )}
      </div>

      <div className="bg-white/80 backdrop-blur-lg rounded-2xl border border-gray-200/50 p-6 mb-6 shadow-xl">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <input
              type="text"
              placeholder="Search by name, email, or username..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
          <select
            value={roleFilter || ""}
            onChange={(e) => setRoleFilter(e.target.value ? parseInt(e.target.value) : null)}
            className="px-6 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
          >
            <option value="">All Roles</option>
            {roles.map(role => (
              <option key={role.id} value={role.id}>{role.name}</option>
            ))}
          </select>
          <select
            value={statusFilter === null ? "" : statusFilter.toString()}
            onChange={(e) => setStatusFilter(e.target.value === "" ? null : e.target.value === "true")}
            className="px-6 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white"
          >
            <option value="">All Status</option>
            <option value="true">Active</option>
            <option value="false">Inactive</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="bg-white/80 backdrop-blur-lg rounded-2xl p-16 text-center border border-gray-200/50 shadow-xl">
          <div className="text-gray-600 font-medium">Loading users...</div>
        </div>
      ) : (
        <div className="bg-white/80 backdrop-blur-lg rounded-2xl border border-gray-200/50 overflow-hidden shadow-xl">
          <table className="w-full">
            <thead>
              <tr className="bg-gradient-to-r from-purple-50 to-indigo-50 border-b border-gray-200">
                <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase">User</th>
                <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase">Email</th>
                <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase">Role</th>
                <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase">Status</th>
                <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase">Last Login</th>
                {isAdmin && <th className="px-6 py-4 text-left text-xs font-bold text-gray-700 uppercase">Actions</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-purple-50/50 transition-all">
                  <td className="px-6 py-4 cursor-pointer" onClick={() => setSelectedUser(u)}>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-gradient-to-br from-purple-400 to-indigo-500 rounded-full flex items-center justify-center text-white font-bold">
                        {u.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-semibold text-gray-900">{u.name}</div>
                        <div className="text-sm text-gray-500">@{u.username}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 cursor-pointer" onClick={() => setSelectedUser(u)}>{u.email}</td>
                  <td className="px-6 py-4 cursor-pointer" onClick={() => setSelectedUser(u)}>
                    <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-semibold">
                      {u.role_name}
                    </span>
                  </td>
                  <td className="px-6 py-4 cursor-pointer" onClick={() => setSelectedUser(u)}>
                    <span className={`px-3 py-1 rounded-full text-sm font-semibold ${u.active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                      {u.active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4 cursor-pointer" onClick={() => setSelectedUser(u)}>
                    {u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : 'Never'}
                  </td>
                  {isAdmin && (
                    <td className="px-6 py-4">
                      <div className="flex gap-2">
                        <button onClick={() => setEditingUser(u)} className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg">
                          Edit
                        </button>
                        <button onClick={() => setDeletingUser(u)} className="p-2 text-red-600 hover:bg-red-50 rounded-lg">
                          Delete
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
          {users.length === 0 && (
            <div className="p-16 text-center">
              <h3 className="text-xl font-bold text-gray-900 mb-2">No users found</h3>
              <p className="text-gray-500">Try adjusting your search or filters</p>
            </div>
          )}
        </div>
      )}

      {selectedUser && <UserDetailsModal user={selectedUser} onClose={() => setSelectedUser(null)} />}
      {showCreateModal && <CreateUserModal roles={roles} onClose={() => setShowCreateModal(false)} onSuccess={loadData} />}
      {editingUser && <EditUserModal user={editingUser} roles={roles} onClose={() => setEditingUser(null)} onSuccess={loadData} />}
      {deletingUser && <ConfirmDialog title="Delete User" message={`Delete ${deletingUser.name}?`} confirmText="Delete" onConfirm={handleDelete} onCancel={() => setDeletingUser(null)} danger />}
    </div>
  );
}
