'use client';

import { useEffect, useState, useRef } from 'react';

interface FlowEvent {
  node_id: string;
  user_id: string;
  session_id: string;
  event_type: string;
  parent_id: string | null;
  timestamp: string;
  [key: string]: any;
}

interface FlowNode extends FlowEvent {
  children: FlowNode[];
}

interface MonitoredUser {
  user_id: number;
  email: string;
}

interface UserFlowTrackerProps {
  userId: number;
  userEmail: string;
  onRemove: () => void;
}

function UserFlowTracker({ userId, userEmail, onRemove }: UserFlowTrackerProps) {
  const [flows, setFlows] = useState<FlowEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8500/api/v1/ws/flows/${userId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log(`[FLOW-TRACKER] Connected for user ${userId} (${userEmail})`);
    };

    ws.onmessage = (event) => {
      const flowEvent: FlowEvent = JSON.parse(event.data);
      console.log(`[FLOW-TRACKER] Event for ${userEmail}:`, flowEvent);
      if (!flowEvent.timestamp) {
        flowEvent.timestamp = new Date().toISOString();
      }
      setFlows((prev) => [...prev, flowEvent]);
    };

    ws.onclose = () => {
      setConnected(false);
      console.log(`[FLOW-TRACKER] Disconnected for user ${userId}`);
    };

    return () => {
      ws.close();
    };
  }, [userId, userEmail]);

  const getCheckpointColor = (checkpoint: string) => {
    const colors: Record<string, string> = {
      auth_check: 'text-blue-600 bg-blue-50',
      security_check: 'text-amber-600 bg-amber-50',
      block_check: 'text-yellow-600 bg-yellow-50',
      usage_check: 'text-purple-600 bg-purple-50',
      mcp_permission_check: 'text-green-600 bg-green-50',
      tool_filter: 'text-indigo-600 bg-indigo-50',
      llm_thinking: 'text-pink-600 bg-pink-50',
      tool_call: 'text-orange-600 bg-orange-50',
      llm_complete: 'text-gray-600 bg-gray-50',
    };
    return colors[checkpoint] || 'text-gray-400 bg-gray-50';
  };

  const formatTimestamp = (ts: string) => {
    const timestamp = parseFloat(ts);
    if (!isNaN(timestamp)) {
      return new Date(timestamp * 1000).toLocaleTimeString();
    }
    return new Date(ts).toLocaleTimeString();
  };

  const renderEvents = (flows: FlowEvent[]): JSX.Element[] => {
    const sorted = [...flows].sort((a, b) => {
      const tsA = parseFloat(a.timestamp);
      const tsB = parseFloat(b.timestamp);
      return tsA - tsB;
    });

    return sorted.map((event) => (
      <div key={event.node_id} className="my-1">
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${getCheckpointColor(event.event_type)}`}>
          <span className="font-mono text-sm font-semibold">
            {event.event_type}
          </span>
          <span className="text-xs text-gray-500">
            {formatTimestamp(event.timestamp)}
          </span>
          {event.score && (
            <span className="text-xs text-gray-600">
              (score: {parseFloat(event.score).toFixed(3)})
            </span>
          )}
          {(event.mcp || event.tool) && (
            <div className="flex gap-2 mt-2 text-xs">
              {event.source && (
                <span className={`px-2 py-1 rounded flex items-center gap-1 ${
                  event.source === 'mcp_gateway' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'
                }`}>
                  {event.source === 'mcp_gateway' ? '🔌' : '💬'}
                  <span>{event.source}</span>
                </span>
              )}
              {event.mcp && (
                <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded flex items-center gap-1">
                  <span>🔌</span>
                  <span className="font-semibold">MCP:</span>
                  <span>{event.mcp}</span>
                </span>
              )}
              {event.tool && (
                <span className="px-2 py-1 bg-green-100 text-green-800 rounded flex items-center gap-1">
                  <span>🔧</span>
                  <span className="font-semibold">TOOL:</span>
                  <span>{event.tool}</span>
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    ));
  };

  const buildTrees = (flows: FlowEvent[]): Map<string, FlowNode | null> => {
    const sessionFlows = new Map<string, FlowEvent[]>();
    flows.forEach((f) => {
      if (!sessionFlows.has(f.session_id)) {
        sessionFlows.set(f.session_id, []);
      }
      sessionFlows.get(f.session_id)!.push(f);
    });

    const trees = new Map<string, FlowNode | null>();
    sessionFlows.forEach((sessionEvents, sessionId) => {
      const flowMap = new Map<string, FlowNode>();
      sessionEvents.forEach((f) => flowMap.set(f.node_id, { ...f, children: [] }));

      let root: FlowNode | null = null;
      sessionEvents.forEach((f) => {
        const node = flowMap.get(f.node_id)!;
        if (f.parent_id) {
          const parent = flowMap.get(f.parent_id);
          if (parent) parent.children.push(node);
        } else {
          root = node;
        }
      });

      trees.set(sessionId, root);
    });

    return trees;
  };

  const renderTree = (node: FlowNode | null, depth = 0): JSX.Element | null => {
    if (!node) return null;

    const getCheckpointColor = (checkpoint: string) => {
      const colors: Record<string, string> = {
        auth_check: 'text-blue-600 bg-blue-50',
        security_check: 'text-amber-600 bg-amber-50',
        block_check: 'text-yellow-600 bg-yellow-50',
        usage_check: 'text-purple-600 bg-purple-50',
        llm_thinking: 'text-green-600 bg-green-50',
        tool_call: 'text-orange-600 bg-orange-50',
        llm_complete: 'text-gray-600 bg-gray-50',
      };
      return colors[checkpoint] || 'text-gray-400 bg-gray-50';
    };

    const formatTimestamp = (ts: string) => {
      const timestamp = parseFloat(ts);
      if (!isNaN(timestamp)) {
        return new Date(timestamp * 1000).toLocaleTimeString();
      }
      return new Date(ts).toLocaleTimeString();
    };

    return (
      <div key={node.node_id} style={{ marginLeft: `${depth * 20}px` }} className="my-1">
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${getCheckpointColor(node.event_type)}`}>
          <span className="font-mono text-sm font-semibold">
            {depth > 0 && '└─ '}
            {node.event_type}
          </span>
          <span className="text-xs text-gray-500">
            {formatTimestamp(node.timestamp)}
          </span>
          {node.metadata?.duration_ms && (
            <span className="text-xs text-gray-400">({node.metadata.duration_ms}ms)</span>
          )}
          {(node.mcp || node.tool) && (
            <div className="flex gap-2 mt-2 text-xs">
              {node.mcp && (
                <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded flex items-center gap-1">
                  <span>🔌</span>
                  <span className="font-semibold">MCP:</span>
                  <span>{node.mcp}</span>
                </span>
              )}
              {node.tool && (
                <span className="px-2 py-1 bg-green-100 text-green-800 rounded flex items-center gap-1">
                  <span>🔧</span>
                  <span className="font-semibold">TOOL:</span>
                  <span>{node.tool}</span>
                </span>
              )}
            </div>
          )}
        </div>
        {node.children.map((child) => renderTree(child, depth + 1))}
      </div>
    );
  };

  // Group flows by session
  const sessionFlows = new Map<string, FlowEvent[]>();
  flows.forEach((f) => {
    if (!sessionFlows.has(f.session_id)) {
      sessionFlows.set(f.session_id, []);
    }
    sessionFlows.get(f.session_id)!.push(f);
  });

  const sessionTimestamps = new Map<string, number>();
  flows.forEach(f => {
    const ts = parseFloat(f.timestamp);
    const current = sessionTimestamps.get(f.session_id) || 0;
    if (ts > current) {
      sessionTimestamps.set(f.session_id, ts);
    }
  });
  const sortedSessions = Array.from(sessionFlows.keys()).sort((a, b) => {
    const tsA = sessionTimestamps.get(a) || 0;
    const tsB = sessionTimestamps.get(b) || 0;
    return tsB - tsA;
  });
  const latestSession = sortedSessions[0];
  const latestSessionFlows = latestSession ? sessionFlows.get(latestSession)! : [];

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm mb-4">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h3 className="text-lg font-semibold text-gray-900">🔍 {userEmail}</h3>
            <div className={`flex items-center gap-2 px-3 py-1 rounded-lg text-sm font-medium ${
              connected ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
            }`}>
              <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
              {connected ? 'Connected' : 'Disconnected'}
            </div>
          </div>
          <button
            onClick={onRemove}
            className="px-3 py-1 text-sm bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition-colors"
          >
            Remove
          </button>
        </div>
        <p className="text-sm text-gray-500 mt-1">User ID: {userId}</p>
      </div>
      <div className="p-4">
        {flows.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-2">🌊</div>
            <p className="text-sm">No flow events yet. Waiting for activity...</p>
          </div>
        ) : latestSession ? (
          <div className="border-2 border-purple-300 rounded-lg p-3 bg-gradient-to-r from-purple-50 to-blue-50">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-2 h-2 rounded-full bg-purple-500 animate-ping"></span>
              <div className="text-xs text-purple-700 font-semibold">ACTIVE SESSION: {latestSession.substring(0, 8)}...</div>
            </div>
            <div className="space-y-1">{renderEvents(latestSessionFlows)}</div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default function MultiUserFlowTracker({ monitoredUsers }: { monitoredUsers: MonitoredUser[] }) {
  const [selectedUsers, setSelectedUsers] = useState<number[]>([]);

  // Auto-select if only one user is monitored
  useEffect(() => {
    if (monitoredUsers.length === 1 && selectedUsers.length === 0) {
      setSelectedUsers([monitoredUsers[0].user_id]);
    }
  }, [monitoredUsers]);

  const handleToggleUser = (userId: number) => {
    setSelectedUsers((prev) =>
      prev.includes(userId) ? prev.filter((id) => id !== userId) : [...prev, userId]
    );
  };

  const handleRemoveUser = (userId: number) => {
    setSelectedUsers((prev) => prev.filter((id) => id !== userId));
  };

  return (
    <div className="space-y-4">
      {/* User Selection */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Select Users to Track</h3>
        <div className="flex flex-wrap gap-2">
          {monitoredUsers.length === 0 ? (
            <p className="text-sm text-gray-500">No users are currently monitored. Use the Flow Monitoring Configuration above to enable monitoring.</p>
          ) : (
            monitoredUsers.map((user) => (
              <button
                key={user.user_id}
                onClick={() => handleToggleUser(user.user_id)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  selectedUsers.includes(user.user_id)
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {selectedUsers.includes(user.user_id) && '✓ '}
                {user.email}
              </button>
            ))
          )}
        </div>
        {selectedUsers.length > 0 && (
          <div className="mt-3 text-sm text-gray-600">
            {selectedUsers.length} user(s) selected
          </div>
        )}
      </div>

      {/* Flow Trackers */}
      {selectedUsers.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 text-center">
          <div className="text-6xl mb-4">👆</div>
          <p className="text-gray-600">Select users above to start tracking their flows</p>
        </div>
      ) : (
        selectedUsers.map((userId) => {
          const user = monitoredUsers.find((u) => u.user_id === userId);
          return (
            <UserFlowTracker
              key={userId}
              userId={userId}
              userEmail={user?.email || `User ${userId}`}
              onRemove={() => handleRemoveUser(userId)}
            />
          );
        })
      )}
    </div>
  );
}
