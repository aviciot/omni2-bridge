'use client';

import { useCallback, useMemo, useState, useEffect } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  BackgroundVariant,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { useGraphConfig } from '@/stores/graphConfigStore';

interface Activity {
  activity_id: string;
  sequence_num: number;
  activity_type: string;
  activity_data: any;
  duration_ms: number | null;
  created_at: string;
}

interface ConversationFlowGraphProps {
  activities: Activity[];
  onNodeClick: (activity: Activity) => void;
  isMinimized?: boolean;
  onToggleMinimize?: () => void;
}

export default function ConversationFlowGraph({ activities, onNodeClick, isMinimized, onToggleMinimize }: ConversationFlowGraphProps) {
  const { activityStyles, layout, background, setLayout } = useGraphConfig();
  const [key, setKey] = useState(0);

  useEffect(() => {
    const handleRefresh = () => setKey(prev => prev + 1);
    window.addEventListener('graph-refresh', handleRefresh);
    return () => window.removeEventListener('graph-refresh', handleRefresh);
  }, []);

  // Auto-refresh when config changes
  useEffect(() => {
    setKey(prev => prev + 1);
  }, [activityStyles, background, layout]);

  const backgroundVariant = {
    dots: BackgroundVariant.Dots,
    lines: BackgroundVariant.Lines,
    none: undefined,
  }[background];
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    
    activities.forEach((activity, idx) => {
      const nodeType = activity.activity_type;
      const style = activityStyles[nodeType] || { bgColor: '#e5e7eb', icon: '📝', label: nodeType };
      
      let label = style.label;
      if (nodeType === 'user_message') {
        label = activity.activity_data.message?.substring(0, 30) || 'User Message';
      } else if (nodeType === 'mcp_tool_call') {
        label = `${activity.activity_data.mcp_server}: ${activity.activity_data.tool_name}`;
      } else if (nodeType === 'mcp_tool_response') {
        label = `Response: ${activity.activity_data.mcp_server}`;
      }
      
      const position = layout === 'vertical' 
        ? { x: 250, y: idx * 120 }
        : { x: idx * 250, y: 100 };
      
      nodes.push({
        id: activity.activity_id,
        type: 'default',
        position,
        data: { 
          label: (
            <div className="text-center">
              <div className="text-2xl mb-1">{style.icon}</div>
              <div className="text-xs font-semibold">{label}</div>
              {activity.duration_ms && (
                <div className="text-xs text-gray-500 mt-1">⏱️ {activity.duration_ms}ms</div>
              )}
            </div>
          ),
          activity
        },
        style: {
          background: style.bgColor,
          border: '2px solid #9ca3af',
          borderRadius: '12px',
          padding: '12px',
          width: 200,
          cursor: 'pointer',
        },
      });
      
      if (idx > 0) {
        edges.push({
          id: `e${activities[idx - 1].activity_id}-${activity.activity_id}`,
          source: activities[idx - 1].activity_id,
          target: activity.activity_id,
          type: 'smoothstep',
          animated: true,
          style: { stroke: '#9ca3af', strokeWidth: 2 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#9ca3af',
          },
        });
      }
    });
    
    return { nodes, edges };
  }, [activities, activityStyles, layout, key, background]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Force update nodes and edges when config changes
  useEffect(() => {
    setNodes(initialNodes);
    setEdges(initialEdges);
  }, [initialNodes, initialEdges, setNodes, setEdges]);

  const onNodeClickHandler = useCallback((event: React.MouseEvent, node: Node) => {
    if (node.data.activity) {
      onNodeClick(node.data.activity);
    }
  }, [onNodeClick]);

  const resetLayout = () => setKey(prev => prev + 1);

  if (isMinimized) {
    return (
      <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200">
        <span className="text-sm text-gray-600">Graph minimized</span>
        <button onClick={onToggleMinimize} className="text-purple-600 hover:text-purple-700">
          ↗️ Expand
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex gap-2 mb-3">
        <button
          onClick={() => setLayout('vertical')}
          className={`px-3 py-1 text-xs rounded ${
            layout === 'vertical' ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-700'
          }`}
        >
          ⬇️ Vertical
        </button>
        <button
          onClick={() => setLayout('horizontal')}
          className={`px-3 py-1 text-xs rounded ${
            layout === 'horizontal' ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-700'
          }`}
        >
          ➡️ Horizontal
        </button>
        <button
          onClick={resetLayout}
          className="px-3 py-1 text-xs rounded bg-gray-100 text-gray-700 hover:bg-gray-200"
        >
          🔄 Reset
        </button>
        {onToggleMinimize && (
          <button
            onClick={onToggleMinimize}
            className="px-3 py-1 text-xs rounded bg-gray-100 text-gray-700 hover:bg-gray-200 ml-auto"
          >
            ↙️ Minimize
          </button>
        )}
      </div>
      <div style={{ width: '100%', height: '600px' }} key={key}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClickHandler}
          fitView
          attributionPosition="bottom-left"
        >
          {backgroundVariant && <Background variant={backgroundVariant} />}
          <Controls />
          <MiniMap 
            nodeColor={(node) => {
              const type = node.data.activity?.activity_type;
              return activityStyles[type]?.bgColor || '#6b7280';
            }}
            maskColor="rgba(0, 0, 0, 0.1)"
          />
        </ReactFlow>
      </div>
    </div>
  );
}
