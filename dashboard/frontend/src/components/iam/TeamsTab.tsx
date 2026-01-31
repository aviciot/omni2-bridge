"use client";

import { useState, useEffect } from 'react';
import { iamApi } from '@/lib/iamApi';

interface Team {
  id: number;
  name: string;
  description?: string;
  mcp_access?: string[];
  resource_access?: any;
  member_count?: number;
  members?: Array<{id: number; name: string; email: string; role: string}>;
}

interface User {
  id: number;
  name: string;
  email: string;
  username: string;
}

export default function TeamsTab() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingTeam, setEditingTeam] = useState<Team | null>(null);
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null);
  const [loading, setLoading] = useState(false);

  const [newTeam, setNewTeam] = useState({
    name: '',
    description: '',
    userIds: [] as number[]
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [teamsData, usersData] = await Promise.all([
        iamApi.getTeams(),
        iamApi.getUsers({})
      ]);
      setTeams(teamsData);
      setUsers(usersData.users || []);
    } catch (error) {
      console.error('Failed to load data:', error);
    }
  };

  const handleAddTeam = async () => {
    if (!newTeam.name) return;
    
    setLoading(true);
    try {
      const result = await iamApi.createTeam({
        name: newTeam.name,
        description: newTeam.description || undefined,
        mcp_access: [],
        resource_access: {}
      });
      
      // Add members if selected
      if (newTeam.userIds.length > 0 && result.team_id) {
        await Promise.all(
          newTeam.userIds.map(userId => 
            iamApi.addTeamMember(result.team_id, userId)
          )
        );
      }
      
      await loadData();
      setShowAddModal(false);
      setNewTeam({ name: '', description: '', userIds: [] });
    } catch (error) {
      console.error('Failed to add team:', error);
      alert('Failed to add team');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateTeam = async () => {
    if (!editingTeam) return;
    
    setLoading(true);
    try {
      await iamApi.updateTeam(editingTeam.id, {
        name: editingTeam.name,
        description: editingTeam.description
      });
      
      await loadData();
      setEditingTeam(null);
    } catch (error) {
      console.error('Failed to update team:', error);
      alert('Failed to update team');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTeam = async (teamId: number) => {
    const team = teams.find(t => t.id === teamId);
    if (!confirm(`Delete team "${team?.name}"? Users in this team will lose their team membership.`)) return;
    
    try {
      await iamApi.deleteTeam(teamId);
      await loadData();
    } catch (error) {
      console.error('Failed to delete team:', error);
      alert('Failed to delete team');
    }
  };

  const handleViewTeam = async (teamId: number) => {
    try {
      const teamDetails = await iamApi.getTeam(teamId);
      setSelectedTeam(teamDetails);
    } catch (error) {
      console.error('Failed to load team details:', error);
    }
  };

  const handleAddMember = async (teamId: number, userId: number) => {
    try {
      await iamApi.addTeamMember(teamId, userId);
      if (selectedTeam?.id === teamId) {
        const updated = await iamApi.getTeam(teamId);
        setSelectedTeam(updated);
      }
      await loadData();
    } catch (error) {
      console.error('Failed to add member:', error);
      alert('Failed to add member');
    }
  };

  const handleRemoveMember = async (teamId: number, userId: number) => {
    try {
      await iamApi.removeTeamMember(teamId, userId);
      if (selectedTeam?.id === teamId) {
        const updated = await iamApi.getTeam(teamId);
        setSelectedTeam(updated);
      }
      await loadData();
    } catch (error) {
      console.error('Failed to remove member:', error);
      alert('Failed to remove member');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Teams</h3>
            <p className="text-sm text-gray-600 mt-1">
              {teams.length} team{teams.length !== 1 ? 's' : ''} configured
            </p>
          </div>
          <button
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium"
          >
            + Create Team
          </button>
        </div>
      </div>

      {/* Teams Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {teams.length === 0 ? (
          <div className="col-span-full bg-white rounded-xl border border-gray-200 p-12 text-center">
            <div className="text-6xl mb-4">👨‍👩‍👧‍👦</div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">No Teams Yet</h3>
            <p className="text-gray-600 mb-4">Create your first team to organize users and assign roles</p>
            <button
              onClick={() => setShowAddModal(true)}
              className="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium"
            >
              Create First Team
            </button>
          </div>
        ) : (
          teams.map(team => (
            <div key={team.id} className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-xl flex items-center justify-center">
                    <span className="text-2xl">👥</span>
                  </div>
                  <div>
                    <h4 className="font-bold text-gray-900">{team.name}</h4>
                    <p className="text-sm text-gray-600">{team.member_count || 0} members</p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setEditingTeam(team)}
                    className="text-gray-400 hover:text-blue-600 transition-colors"
                    title="Edit team"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleViewTeam(team.id)}
                    className="text-gray-400 hover:text-purple-600 transition-colors"
                    title="View members"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleDeleteTeam(team.id)}
                    className="text-gray-400 hover:text-red-600 transition-colors"
                    title="Delete team"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>

              <div className="space-y-3">

                {team.description && (
                  <div>
                    <div className="text-xs font-medium text-gray-500 uppercase mb-1">Description</div>
                    <p className="text-sm text-gray-700">{team.description}</p>
                  </div>
                )}
              </div>


            </div>
          ))
        )}
      </div>

      {/* Add Team Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-lg w-full mx-4">
            <h3 className="text-xl font-bold text-gray-900 mb-4">Create New Team</h3>

            <div className="space-y-4">
              {/* Team Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Team Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={newTeam.name}
                  onChange={(e) => setNewTeam({ ...newTeam, name: e.target.value })}
                  placeholder="e.g., Engineering, QA, Database Team"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Description (optional)</label>
                <textarea
                  value={newTeam.description}
                  onChange={(e) => setNewTeam({ ...newTeam, description: e.target.value })}
                  placeholder="Describe the team's purpose and responsibilities"
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>

              {/* Add Users */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Add Users (optional)</label>
                <div className="border border-gray-300 rounded-lg p-3 max-h-48 overflow-y-auto">
                  {users.map(user => (
                    <label key={user.id} className="flex items-center gap-2 py-1 hover:bg-gray-50 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={newTeam.userIds.includes(user.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setNewTeam({ ...newTeam, userIds: [...newTeam.userIds, user.id] });
                          } else {
                            setNewTeam({ ...newTeam, userIds: newTeam.userIds.filter(id => id !== user.id) });
                          }
                        }}
                        className="rounded"
                      />
                      <span className="text-sm">{user.name} ({user.email})</span>
                    </label>
                  ))}
                  {users.length === 0 && <p className="text-sm text-gray-500">No users available</p>}
                </div>
                <p className="text-xs text-gray-500 mt-1">{newTeam.userIds.length} user(s) selected</p>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => {
                  setShowAddModal(false);
                  setNewTeam({ name: '', description: '', userIds: [] });
                }}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                disabled={loading}
              >
                Cancel
              </button>
              <button
                onClick={handleAddTeam}
                disabled={!newTeam.name || loading}
                className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Creating...' : 'Create Team'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit Team Modal */}
      {editingTeam && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-lg w-full mx-4">
            <h3 className="text-xl font-bold text-gray-900 mb-4">Edit Team</h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Team Name</label>
                <input
                  type="text"
                  value={editingTeam.name}
                  onChange={(e) => setEditingTeam({ ...editingTeam, name: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Description</label>
                <textarea
                  value={editingTeam.description || ''}
                  onChange={(e) => setEditingTeam({ ...editingTeam, description: e.target.value })}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                />
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setEditingTeam(null)}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                disabled={loading}
              >
                Cancel
              </button>
              <button
                onClick={handleUpdateTeam}
                disabled={!editingTeam.name || loading}
                className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* View Members Modal */}
      {selectedTeam && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-xl font-bold text-gray-900">{selectedTeam.name}</h3>
                <p className="text-sm text-gray-600">{selectedTeam.members?.length || 0} members</p>
              </div>
              <button onClick={() => setSelectedTeam(null)} className="text-gray-400 hover:text-gray-600">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Current Members */}
            <div className="mb-6">
              <h4 className="font-semibold text-gray-900 mb-3">Current Members</h4>
              {selectedTeam.members && selectedTeam.members.length > 0 ? (
                <div className="space-y-2">
                  {selectedTeam.members.map(member => (
                    <div key={member.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                      <div>
                        <div className="font-medium text-gray-900">{member.name}</div>
                        <div className="text-sm text-gray-600">{member.email} • {member.role}</div>
                      </div>
                      <button
                        onClick={() => handleRemoveMember(selectedTeam.id, member.id)}
                        className="text-red-600 hover:text-red-700 text-sm font-medium"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-500 text-sm">No members yet</p>
              )}
            </div>

            {/* Add Members */}
            <div>
              <h4 className="font-semibold text-gray-900 mb-3">Add Members</h4>
              <div className="border border-gray-300 rounded-lg p-3 max-h-48 overflow-y-auto">
                {users
                  .filter(user => !selectedTeam.members?.some(m => m.id === user.id))
                  .map(user => (
                    <div key={user.id} className="flex items-center justify-between py-2 hover:bg-gray-50">
                      <div>
                        <div className="text-sm font-medium text-gray-900">{user.name}</div>
                        <div className="text-xs text-gray-600">{user.email}</div>
                      </div>
                      <button
                        onClick={() => handleAddMember(selectedTeam.id, user.id)}
                        className="text-purple-600 hover:text-purple-700 text-sm font-medium"
                      >
                        Add
                      </button>
                    </div>
                  ))}
                {users.filter(user => !selectedTeam.members?.some(m => m.id === user.id)).length === 0 && (
                  <p className="text-sm text-gray-500">All users are already members</p>
                )}
              </div>
            </div>

            <div className="mt-6">
              <button
                onClick={() => setSelectedTeam(null)}
                className="w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
