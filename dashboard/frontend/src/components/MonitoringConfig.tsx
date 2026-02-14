import React, { useState, useEffect } from 'react';

interface User {
  id: number;
  email: string;
  full_name: string;
}

interface MonitoredUser {
  user_id: number;
  expires_at: number;
}

interface MonitoringConfigProps {
  onUpdate?: () => void;
}

const MonitoringConfig: React.FC<MonitoringConfigProps> = ({ onUpdate }) => {
  const [users, setUsers] = useState<User[]>([]);
  const [monitored, setMonitored] = useState<MonitoredUser[]>([]);
  const [userEmail, setUserEmail] = useState('');
  const [ttlHours, setTtlHours] = useState<number>(24);
  const [loading, setLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  useEffect(() => {
    loadUsers();
    loadMonitored();
  }, []);

  const loadUsers = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:8500/api/v1/monitoring/users', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setUsers(data.users || []);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const loadMonitored = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:8500/api/v1/monitoring/list', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await response.json();
      setMonitored(data.monitored_users || []);
    } catch (error) {
      console.error('Failed to load monitored users:', error);
    }
  };

  const handleEnable = async () => {
    const user = users.find(u => u.email === userEmail);
    if (!user) return;

    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:8500/api/v1/monitoring/enable', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify([user.id])
      });
      await loadMonitored();
      setUserEmail('');
      if (onUpdate) onUpdate();
    } catch (error) {
      console.error('Failed to enable monitoring:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDisable = async (userId: number) => {
    setLoading(true);
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch('http://localhost:8500/api/v1/monitoring/disable', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify([userId])
      });
      await loadMonitored();
      if (onUpdate) onUpdate();
    } catch (error) {
      console.error('Failed to disable monitoring:', error);
    } finally {
      setLoading(false);
    }
  };

  const getUserEmail = (userId: number) => {
    const user = users.find(u => u.id === userId);
    return user?.email || `User ${userId}`;
  };

  const getExpiryTime = (userId: number) => {
    const user = monitored.find(m => m.user_id === userId);
    if (!user) return null;
    return new Date(user.expires_at * 1000).toLocaleString();
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div 
        className="p-4 flex items-center justify-between cursor-pointer hover:bg-gray-50"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">🔍</span>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Flow Monitoring Configuration</h3>
            <p className="text-sm text-gray-500">{monitored.length} user(s) monitored</p>
          </div>
        </div>
        <svg 
          className={`w-5 h-5 text-gray-400 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {isExpanded && (
        <div className="p-4 pt-0 border-t border-gray-200">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-2">User Email</label>
              <input
                type="text"
                list="user-emails"
                value={userEmail}
                onChange={(e) => setUserEmail(e.target.value)}
                placeholder="Select or type user email..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
              <datalist id="user-emails">
                {users.map(user => (
                  <option key={user.id} value={user.email} />
                ))}
              </datalist>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">TTL (hours)</label>
              <input
                type="number"
                value={ttlHours}
                onChange={(e) => setTtlHours(Number(e.target.value))}
                min={1}
                max={8760}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              />
            </div>
          </div>

          <button
            onClick={handleEnable}
            disabled={loading || !userEmail}
            className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? 'Processing...' : 'Enable Monitoring'}
          </button>

          {monitored.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Currently Monitored Users</h4>
              <div className="space-y-2">
                {monitored.map(m => (
                  <div
                    key={m.user_id}
                    className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded-lg"
                  >
                    <div>
                      <div className="text-sm font-medium text-gray-900">{getUserEmail(m.user_id)}</div>
                      <div className="text-xs text-green-600">Expires: {getExpiryTime(m.user_id)}</div>
                    </div>
                    <button
                      onClick={() => handleDisable(m.user_id)}
                      disabled={loading}
                      className="px-3 py-1 text-sm bg-red-100 hover:bg-red-200 text-red-700 rounded border border-red-300 disabled:opacity-50 transition-colors"
                    >
                      Disable
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default MonitoringConfig;
