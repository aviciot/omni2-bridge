"use client";

import { useState, useEffect } from "react";
import { IAMUser, Role } from "@/types/iam";
import { API_CONFIG } from "@/lib/config";
import { iamApi } from "@/lib/iamApi";

interface EditUserModalProps {
  user: IAMUser;
  roles: Role[];
  onClose: () => void;
  onSuccess: () => void;
}

interface Team {
  id: number;
  name: string;
  members?: Array<{id: number}>;
}

export default function EditUserModal({ user, roles, onClose, onSuccess }: EditUserModalProps) {
  const [teams, setTeams] = useState<Team[]>([]);
  const [userTeams, setUserTeams] = useState<number[]>([]);
  const [initialTeams, setInitialTeams] = useState<number[]>([]);
  const [formData, setFormData] = useState({
    name: user.name,
    email: user.email,
    role_id: user.role_id,
    active: user.active,
    rate_limit_override: user.rate_limit_override || "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadTeamsData();
  }, []);

  const loadTeamsData = async () => {
    try {
      const allTeams = await iamApi.getTeams();
      setTeams(allTeams);
      
      // Load detailed team info to find which teams user belongs to
      const teamsWithMembers = await Promise.all(
        allTeams.map(async (team: Team) => {
          try {
            const details = await iamApi.getTeam(team.id);
            return details;
          } catch {
            return team;
          }
        })
      );
      
      const userTeamIds = teamsWithMembers
        .filter((team: Team) => team.members?.some(m => m.id === user.id))
        .map((team: Team) => team.id);
      
      setUserTeams(userTeamIds);
      setInitialTeams(userTeamIds); // Store initial state
    } catch (error) {
      console.error('Failed to load teams:', error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    console.log('=== EDIT USER SUBMIT ==');
    console.log('User ID:', user.id);
    console.log('Initial teams:', initialTeams);
    console.log('Current teams:', userTeams);

    try {
      const response = await fetch(`${API_CONFIG.AUTH_SERVICE_URL}/users/users/${user.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          "X-User-Role": "super_admin",
        },
        body: JSON.stringify({
          ...formData,
          rate_limit_override: formData.rate_limit_override || null,
        }),
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Failed to update user");
      }

      console.log('User updated successfully');

      // Update team memberships
      console.log('Initial teams:', initialTeams, 'Current teams:', userTeams);
      const teamsToAdd = userTeams.filter(id => !initialTeams.includes(id));
      const teamsToRemove = initialTeams.filter(id => !userTeams.includes(id));
      console.log('Teams to add:', teamsToAdd, 'Teams to remove:', teamsToRemove);

      if (teamsToAdd.length > 0 || teamsToRemove.length > 0) {
        const promises = [
          ...teamsToAdd.map(async teamId => {
            console.log(`Adding user ${user.id} to team ${teamId}`);
            return iamApi.addTeamMember(teamId, user.id);
          }),
          ...teamsToRemove.map(async teamId => {
            console.log(`Removing user ${user.id} from team ${teamId}`);
            return iamApi.removeTeamMember(teamId, user.id);
          })
        ];
        await Promise.all(promises);
        console.log('Team memberships updated successfully');
      } else {
        console.log('No team changes needed');
      }

      onSuccess();
      onClose();
    } catch (err: any) {
      console.error('Error updating user:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in" 
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div 
        className="bg-white/95 backdrop-blur-xl rounded-3xl p-8 max-w-2xl w-full mx-4 shadow-2xl border border-gray-200/50 animate-slide-up" 
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg">
              <span className="text-2xl">✏️</span>
            </div>
            <div>
              <h2 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-blue-900 bg-clip-text text-transparent">
                Edit User
              </h2>
              <p className="text-sm text-gray-500">@{user.username}</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-2 rounded-lg transition-all">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-xl text-red-800">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">Full Name</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">Email</label>
            <input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">Role</label>
              <select
                value={formData.role_id}
                onChange={(e) => setFormData({ ...formData, role_id: parseInt(e.target.value) })}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {roles.map((role) => (
                  <option key={role.id} value={role.id}>
                    {role.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-700 mb-2">Status</label>
              <select
                value={formData.active.toString()}
                onChange={(e) => setFormData({ ...formData, active: e.target.value === "true" })}
                className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="true">✅ Active</option>
                <option value="false">❌ Inactive</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">Rate Limit Override (optional)</label>
            <input
              type="number"
              value={formData.rate_limit_override}
              onChange={(e) => setFormData({ ...formData, rate_limit_override: e.target.value })}
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Leave empty for role default"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-700 mb-2">Teams (optional)</label>
            <div className="border border-gray-300 rounded-xl p-3 max-h-48 overflow-y-auto">
              {teams.map(team => (
                <label key={team.id} className="flex items-center gap-2 py-1 hover:bg-gray-50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={userTeams.includes(team.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setUserTeams([...userTeams, team.id]);
                      } else {
                        setUserTeams(userTeams.filter(id => id !== team.id));
                      }
                    }}
                    className="rounded"
                  />
                  <span className="text-sm">{team.name}</span>
                </label>
              ))}
              {teams.length === 0 && <p className="text-sm text-gray-500">No teams available</p>}
            </div>
            <p className="text-xs text-gray-500 mt-1">{userTeams.length} team(s) selected</p>
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-6 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-xl font-semibold transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-xl font-semibold shadow-lg transition-all transform hover:scale-105 disabled:opacity-50"
            >
              {loading ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>

      <style jsx global>{`
        @keyframes slide-up {
          from {
            opacity: 0;
            transform: translateY(20px) scale(0.95);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}
