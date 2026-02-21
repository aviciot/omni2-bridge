"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/stores/authStore";
import { iamApi } from "@/lib/iamApi";
import axios from "axios";

const API_BASE = 'http://localhost:8500/api/v1';

const getAuthHeaders = () => ({
  Authorization: `Bearer ${localStorage.getItem('access_token')}`
});

interface User {
  id: number;
  username: string;
  email: string;
  role_id: number;
  active: boolean;
}

interface BlockStatus {
  user_id: number;
  is_blocked: boolean;
  block_reason?: string;
  custom_block_message?: string;
  blocked_at?: string;
  blocked_by?: number;
  blocked_services?: string[];
}

interface WelcomeConfig {
  config_type: string;
  target_id?: number;
  welcome_message: string;
  show_usage_info: boolean;
}

export default function ChatConfigPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout } = useAuthStore();
  const [users, setUsers] = useState<User[]>([]);
  const [blockStatuses, setBlockStatuses] = useState<Record<number, BlockStatus>>({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"blocking" | "welcome">("blocking");
  const [welcomeTab, setWelcomeTab] = useState<"default" | "user" | "role">("default");
  
  // Block user modal
  const [showBlockModal, setShowBlockModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [blockReason, setBlockReason] = useState("");
  const [customBlockMessage, setCustomBlockMessage] = useState("");
  const [blockedServices, setBlockedServices] = useState<string[]>(["chat", "mcp"]);
  
  // Welcome message editor
  const [welcomeMessage, setWelcomeMessage] = useState("");
  const [showUsageInfo, setShowUsageInfo] = useState(true);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const response = await iamApi.getUsers();
      const data = response.users || response;
      setUsers(data);
      
      // Load block status for each user
      const statuses: Record<number, BlockStatus> = {};
      for (const user of data) {
        try {
          const { data: status } = await axios.get(`${API_BASE}/chat-config/users/${user.id}/block`, {
            headers: getAuthHeaders()
          });
          statuses[user.id] = status;
        } catch (e) {
          statuses[user.id] = { user_id: user.id, is_blocked: false };
        }
      }
      setBlockStatuses(statuses);
    } catch (error) {
      console.error("Failed to load users:", error);
    } finally {
      setLoading(false);
    }
  };

  const openBlockModal = (user: User) => {
    setSelectedUser(user);
    const status = blockStatuses[user.id];
    setBlockReason(status?.block_reason || "");
    setCustomBlockMessage(status?.custom_block_message || "");
    setBlockedServices(status?.blocked_services || ["chat", "mcp"]);
    setShowBlockModal(true);
  };

  const handleBlockUser = async () => {
    if (!selectedUser) return;
    
    try {
      await axios.put(`${API_BASE}/chat-config/users/${selectedUser.id}/block`, {
        is_blocked: true,
        block_reason: blockReason,
        custom_block_message: customBlockMessage,
        blocked_services: blockedServices
      }, {
        headers: getAuthHeaders()
      });
      
      await loadUsers();
      setShowBlockModal(false);
      setSelectedUser(null);
      setBlockReason("");
      setCustomBlockMessage("");
      setBlockedServices(["chat", "mcp"]);
    } catch (error) {
      console.error("Failed to block user:", error);
      alert("Failed to block user");
    }
  };

  const handleUnblockUser = async (userId: number) => {
    if (!confirm("Unblock this user?")) return;
    
    try {
      await axios.put(`${API_BASE}/chat-config/users/${userId}/block`, {
        is_blocked: false
      }, {
        headers: getAuthHeaders()
      });
      await loadUsers();
    } catch (error) {
      console.error("Failed to unblock user:", error);
      alert("Failed to unblock user");
    }
  };

  const loadWelcomeMessage = async (type: "default" | "user" | "role", id?: number) => {
    try {
      let response;
      if (type === "default") {
        response = await axios.get(`${API_BASE}/chat-config/welcome/default`, {
          headers: getAuthHeaders()
        });
      } else if (type === "user" && id) {
        response = await axios.get(`${API_BASE}/chat-config/users/${id}/welcome`, {
          headers: getAuthHeaders()
        });
      } else if (type === "role" && id) {
        response = await axios.get(`${API_BASE}/chat-config/roles/${id}/welcome`, {
          headers: getAuthHeaders()
        });
      }
      
      if (response?.data) {
        setWelcomeMessage(response.data.welcome_message);
        setShowUsageInfo(response.data.show_usage_info);
      }
    } catch (error: any) {
      if (error.response?.status === 404) {
        // No custom message exists, show empty
        setWelcomeMessage("");
        setShowUsageInfo(true);
      } else {
        console.error("Failed to load welcome message:", error);
        setWelcomeMessage("");
        setShowUsageInfo(true);
      }
    }
  };

  const saveWelcomeMessage = async () => {
    try {
      const payload = {
        config_type: welcomeTab,
        welcome_message: welcomeMessage,
        show_usage_info: showUsageInfo
      };
      
      if (welcomeTab === "default") {
        await axios.put(`${API_BASE}/chat-config/welcome/default`, payload, {
          headers: getAuthHeaders()
        });
      } else if (welcomeTab === "user" && selectedUserId) {
        await axios.put(`${API_BASE}/chat-config/users/${selectedUserId}/welcome`, payload, {
          headers: getAuthHeaders()
        });
      } else if (welcomeTab === "role" && selectedRoleId) {
        await axios.put(`${API_BASE}/chat-config/roles/${selectedRoleId}/welcome`, payload, {
          headers: getAuthHeaders()
        });
      }
      
      alert("Welcome message saved!");
    } catch (error) {
      console.error("Failed to save welcome message:", error);
      alert("Failed to save welcome message");
    }
  };

  useEffect(() => {
    if (welcomeTab === "default") {
      loadWelcomeMessage("default");
    }
  }, [welcomeTab]);

  if (isLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    router.push("/login");
    return null;
  }

  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h2 className="text-2xl font-bold mb-6">Chat Configuration</h2>
      
      {/* Tabs */}
      <div className="flex space-x-4 mb-6 border-b">
        <button
          onClick={() => setActiveTab("blocking")}
          className={`px-4 py-2 font-medium ${
            activeTab === "blocking"
              ? "border-b-2 border-purple-600 text-purple-600"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          User Blocking
        </button>
        <button
          onClick={() => setActiveTab("welcome")}
          className={`px-4 py-2 font-medium ${
            activeTab === "welcome"
              ? "border-b-2 border-purple-600 text-purple-600"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          Welcome Messages
        </button>
      </div>

      {/* User Blocking Section */}
      {activeTab === "blocking" && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            <h2 className="text-xl font-semibold mb-4">User Access Control</h2>
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4">User</th>
                  <th className="text-left py-3 px-4">Email</th>
                  <th className="text-left py-3 px-4">Status</th>
                  <th className="text-left py-3 px-4">Block Reason</th>
                  <th className="text-right py-3 px-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => {
                  const status = blockStatuses[user.id];
                  return (
                    <tr key={user.id} className="border-b hover:bg-gray-50">
                      <td className="py-3 px-4 font-medium">{user.username}</td>
                      <td className="py-3 px-4 text-gray-600">{user.email}</td>
                      <td className="py-3 px-4">
                        {status?.is_blocked ? (
                          <div className="flex flex-col gap-1">
                            <span className="px-2 py-1 bg-red-100 text-red-700 rounded text-sm w-fit">
                              Blocked
                            </span>
                            {status.blocked_services && status.blocked_services.length > 0 && (
                              <span className="text-xs text-gray-500">
                                {status.blocked_services.join(", ")}
                              </span>
                            )}
                          </div>
                        ) : (
                          <span className="px-2 py-1 bg-green-100 text-green-700 rounded text-sm">
                            Active
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-gray-600 text-sm">
                        {status?.custom_block_message || status?.block_reason || "-"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {status?.is_blocked ? (
                          <button
                            onClick={() => handleUnblockUser(user.id)}
                            className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
                          >
                            Unblock
                          </button>
                        ) : (
                          <button
                            onClick={() => openBlockModal(user)}
                            className="px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
                          >
                            Block
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Welcome Messages Section */}
      {activeTab === "welcome" && (
        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            <h2 className="text-xl font-semibold mb-4">Welcome Message Configuration</h2>
            
            {/* Welcome Message Tabs */}
            <div className="flex space-x-2 mb-4">
              <button
                onClick={() => setWelcomeTab("default")}
                className={`px-4 py-2 rounded ${
                  welcomeTab === "default"
                    ? "bg-purple-600 text-white"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                }`}
              >
                Default
              </button>
              <button
                onClick={() => setWelcomeTab("user")}
                className={`px-4 py-2 rounded ${
                  welcomeTab === "user"
                    ? "bg-purple-600 text-white"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                }`}
              >
                User-Specific
              </button>
              <button
                onClick={() => setWelcomeTab("role")}
                className={`px-4 py-2 rounded ${
                  welcomeTab === "role"
                    ? "bg-purple-600 text-white"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                }`}
              >
                Role-Specific
              </button>
            </div>

            {/* User/Role Selector */}
            {welcomeTab === "user" && (
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Select User</label>
                <select
                  value={selectedUserId || ""}
                  onChange={(e) => {
                    const id = parseInt(e.target.value);
                    setSelectedUserId(id);
                    loadWelcomeMessage("user", id);
                  }}
                  className="w-full px-3 py-2 border rounded"
                >
                  <option value="">-- Select User --</option>
                  {users.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.username} ({user.email})
                    </option>
                  ))}
                </select>
              </div>
            )}

            {welcomeTab === "role" && (
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Select Role</label>
                <input
                  type="number"
                  value={selectedRoleId || ""}
                  onChange={(e) => {
                    const id = parseInt(e.target.value);
                    setSelectedRoleId(id);
                    loadWelcomeMessage("role", id);
                  }}
                  placeholder="Enter role ID"
                  className="w-full px-3 py-2 border rounded"
                />
              </div>
            )}

            {/* Welcome Message Editor */}
            {(welcomeTab === "default" || (welcomeTab === "user" && selectedUserId) || (welcomeTab === "role" && selectedRoleId)) && (
              <div>
                <label className="block text-sm font-medium mb-2">Welcome Message</label>
                <textarea
                  value={welcomeMessage}
                  onChange={(e) => setWelcomeMessage(e.target.value)}
                  rows={6}
                  className="w-full px-3 py-2 border rounded font-mono text-sm"
                  placeholder="Enter welcome message..."
                />
                
                <div className="mt-4 flex items-center">
                  <input
                    type="checkbox"
                    id="showUsageInfo"
                    checked={showUsageInfo}
                    onChange={(e) => setShowUsageInfo(e.target.checked)}
                    className="mr-2"
                  />
                  <label htmlFor="showUsageInfo" className="text-sm">
                    Show usage information
                  </label>
                </div>

                <button
                  onClick={saveWelcomeMessage}
                  className="mt-4 px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700"
                >
                  Save Welcome Message
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Block User Modal */}
      {showBlockModal && selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-xl font-semibold mb-4">Block User: {selectedUser.username}</h3>
            
            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Block Reason (Internal)</label>
              <input
                type="text"
                value={blockReason}
                onChange={(e) => setBlockReason(e.target.value)}
                placeholder="e.g., Policy violation"
                className="w-full px-3 py-2 border rounded"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Custom Message (Shown to User)</label>
              <textarea
                value={customBlockMessage}
                onChange={(e) => setCustomBlockMessage(e.target.value)}
                rows={3}
                placeholder="e.g., Your account has been temporarily suspended. Please contact support."
                className="w-full px-3 py-2 border rounded"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">Block From Services</label>
              <div className="space-y-2">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={blockedServices.includes("chat")}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setBlockedServices([...blockedServices, "chat"]);
                      } else {
                        setBlockedServices(blockedServices.filter(s => s !== "chat"));
                      }
                    }}
                    className="mr-2"
                  />
                  <span className="text-sm">Chat (WebSocket)</span>
                </label>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={blockedServices.includes("mcp")}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setBlockedServices([...blockedServices, "mcp"]);
                      } else {
                        setBlockedServices(blockedServices.filter(s => s !== "mcp"));
                      }
                    }}
                    className="mr-2"
                  />
                  <span className="text-sm">MCP Gateway</span>
                </label>
              </div>
            </div>

            <div className="flex justify-end space-x-2">
              <button
                onClick={() => {
                  setShowBlockModal(false);
                  setSelectedUser(null);
                  setBlockReason("");
                  setCustomBlockMessage("");
                  setBlockedServices(["chat", "mcp"]);
                }}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={handleBlockUser}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
              >
                Block User
              </button>
            </div>
          </div>
        </div>
      )}
      </main>
  );
}
