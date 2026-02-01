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

export default function FlowTracker({ userId }: { userId: number }) {
  const [flows, setFlows] = useState<FlowEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8500/api/v1/ws/flows/${userId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log('[FLOW-TRACKER] Connected');
    };

    ws.onmessage = (event) => {
      const flowEvent: FlowEvent = JSON.parse(event.data);
      console.log('[FLOW-TRACKER] Event received:', flowEvent);
      // Ensure timestamp is valid
      if (!flowEvent.timestamp) {
        flowEvent.timestamp = new Date().toISOString();
      }
      setFlows((prev) => [...prev, flowEvent]);
    };

    ws.onclose = () => {
      setConnected(false);
      console.log('[FLOW-TRACKER] Disconnected');
    };

    return () => {
      ws.close();
    };
  }, [userId]);

  const buildTrees = (flows: FlowEvent[]): Map<string, FlowNode | null> => {
    // Group flows by session_id
    const sessionFlows = new Map<string, FlowEvent[]>();
    flows.forEach((f) => {
      if (!sessionFlows.has(f.session_id)) {
        sessionFlows.set(f.session_id, []);
      }
      sessionFlows.get(f.session_id)!.push(f);
    });

    // Build tree for each session
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
        block_check: 'text-yellow-600 bg-yellow-50',
        usage_check: 'text-purple-600 bg-purple-50',
        llm_thinking: 'text-green-600 bg-green-50',
        tool_call: 'text-orange-600 bg-orange-50',
        llm_complete: 'text-gray-600 bg-gray-50',
      };
      return colors[checkpoint] || 'text-gray-400 bg-gray-50';
    };

    const formatTimestamp = (ts: string) => {
      // Handle Unix timestamp (seconds)
      const timestamp = parseFloat(ts);
      if (!isNaN(timestamp)) {
        return new Date(timestamp * 1000).toLocaleTimeString();
      }
      // Handle ISO string
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
        </div>
        {node.children.map((child) => renderTree(child, depth + 1))}
      </div>
    );
  };

  const trees = buildTrees(flows);
  // Get sessions sorted by most recent event timestamp
  const sessionTimestamps = new Map<string, number>();
  flows.forEach(f => {
    const ts = parseFloat(f.timestamp);
    const current = sessionTimestamps.get(f.session_id) || 0;
    if (ts > current) {
      sessionTimestamps.set(f.session_id, ts);
    }
  });
  const sortedSessions = Array.from(trees.keys()).sort((a, b) => {
    const tsA = sessionTimestamps.get(a) || 0;
    const tsB = sessionTimestamps.get(b) || 0;
    return tsB - tsA; // Most recent first
  });
  const latestSession = sortedSessions[0];

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">🔍 Flow Tracker (Real-time)</h3>
          <div className={`flex items-center gap-2 px-3 py-1 rounded-lg text-sm font-medium ${
            connected ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}>
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
            {connected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
        <p className="text-sm text-gray-500 mt-1">User ID: {userId} • Current Session</p>
      </div>
      <div className="p-4">
        {flows.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-2">🌊</div>
            <p className="text-sm">No flow events yet. Make a chat request to see tracking.</p>
          </div>
        ) : latestSession ? (
          <div className="border-2 border-purple-300 rounded-lg p-3 bg-gradient-to-r from-purple-50 to-blue-50 animate-pulse-slow">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-2 h-2 rounded-full bg-purple-500 animate-ping"></span>
              <div className="text-xs text-purple-700 font-semibold">ACTIVE SESSION: {latestSession.substring(0, 8)}...</div>
            </div>
            <div className="space-y-1">{renderTree(trees.get(latestSession)!)}</div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
