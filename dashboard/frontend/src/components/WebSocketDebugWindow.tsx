'use client';

import { useState, useEffect, useRef } from 'react';

interface WebSocketMessage {
  timestamp: string;
  type: string;
  data: any;
}

export default function WebSocketDebugWindow() {
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [isVisible, setIsVisible] = useState(true);
  const [position, setPosition] = useState({ x: 20, y: 20 });
  const [size, setSize] = useState({ width: 500, height: 600 });
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionError, setConnectionError] = useState<string>('');
  const [filter, setFilter] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const dragRef = useRef<{ startX: number; startY: number } | null>(null);
  const resizeRef = useRef<{ startX: number; startY: number; startWidth: number; startHeight: number } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const connectWebSocket = () => {
    const token = localStorage.getItem('access_token');
    console.log('Token from localStorage:', token ? 'Found' : 'Not found');
    
    if (!token) {
      setConnectionError('No token found. Please login first.');
      return;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setConnectionError('');
    // Browser WebSocket doesn't support custom headers
    // Token must be passed via query parameter or use a proxy
    const wsUrl = `ws://localhost:8500/ws?token=${token}`;
    console.log('Connecting to:', wsUrl.replace(token, '***'));
    
    try {
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('WebSocket connected to OMNI2');
        setIsConnected(true);
        setConnectionError('');
        setMessages(prev => [...prev, {
          timestamp: new Date().toISOString(),
          type: 'system',
          data: { message: '✅ Connected to OMNI2 WebSocket', status: 'connected' }
        }]);
        
        // Auto-subscribe to all MCP events
        ws.send(JSON.stringify({
          action: 'subscribe',
          event_types: ['mcp_status_change', 'circuit_breaker_state', 'mcp_auto_disabled', 'mcp_health_check'],
          filters: {}
        }));
      };
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setMessages(prev => [...prev.slice(-49), {
            timestamp: new Date().toISOString(),
            type: data.type || 'unknown',
            data: data
          }]);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };
      
      ws.onerror = (error) => {
        setIsConnected(false);
        setConnectionError('Connection failed. Check console for details.');
      };
      
      ws.onclose = (event) => {
        console.log('WebSocket disconnected. Code:', event.code, 'Reason:', event.reason);
        setIsConnected(false);
        setConnectionError(`Disconnected (code: ${event.code})`);
        setMessages(prev => [...prev, {
          timestamp: new Date().toISOString(),
          type: 'system',
          data: { message: '❌ Disconnected from OMNI2', status: 'disconnected', code: event.code }
        }]);
      };
      
      wsRef.current = ws;
    } catch (error: any) {
      console.error('WebSocket connection error:', error);
      setConnectionError(`Failed to connect: ${error.message}`);
    }
  };

  const disconnectWebSocket = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
      setIsConnected(false);
      setMessages(prev => [...prev, {
        timestamp: new Date().toISOString(),
        type: 'system',
        data: { message: '🔌 Manually disconnected', status: 'disconnected' }
      }]);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      connectWebSocket();
    }
    
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    dragRef.current = {
      startX: e.clientX - position.x,
      startY: e.clientY - position.y
    };
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (isDragging && dragRef.current) {
      setPosition({
        x: e.clientX - dragRef.current.startX,
        y: e.clientY - dragRef.current.startY
      });
    }
    if (isResizing && resizeRef.current) {
      setSize({
        width: Math.max(300, resizeRef.current.startWidth + (e.clientX - resizeRef.current.startX)),
        height: Math.max(200, resizeRef.current.startHeight + (e.clientY - resizeRef.current.startY))
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setIsResizing(false);
  };

  const handleResizeStart = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsResizing(true);
    resizeRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      startWidth: size.width,
      startHeight: size.height
    };
  };

  useEffect(() => {
    if (isDragging || isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, isResizing]);

  const filteredMessages = messages.filter(msg => {
    // Type filter
    if (typeFilter !== 'all' && msg.type !== typeFilter) return false;
    
    // Text filter
    if (filter) {
      const searchText = filter.toLowerCase();
      const msgText = JSON.stringify(msg.data).toLowerCase();
      return msgText.includes(searchText);
    }
    
    return true;
  });

  const messageTypes = ['all', ...Array.from(new Set(messages.map(m => m.type)))];

  if (!isVisible) {
    return (
      <button
        onClick={() => setIsVisible(true)}
        className="fixed bottom-4 right-4 bg-blue-600 text-white px-4 py-2 rounded shadow-lg hover:bg-blue-700 z-50"
      >
        Show WS Debug
      </button>
    );
  }

  return (
    <div
      style={{ left: position.x, top: position.y, width: size.width, height: size.height }}
      className="fixed bg-gray-900 border border-gray-700 rounded-lg shadow-2xl z-50 flex flex-col"
    >
      <div
        onMouseDown={handleMouseDown}
        className="bg-gradient-to-r from-gray-800 to-gray-900 px-4 py-3 rounded-t-lg cursor-move flex justify-between items-center border-b border-gray-700"
      >
        <div className="flex items-center gap-3">
          <span className="text-white font-bold text-sm">WebSocket Monitor (ws://localhost:8500/ws)</span>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full animate-pulse ${isConnected ? 'bg-green-400' : 'bg-red-400'}`}></span>
            <span className="text-xs text-gray-400">{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
          {isConnected ? (
            <button
              onClick={disconnectWebSocket}
              className="text-xs bg-red-600 hover:bg-red-700 text-white px-2 py-1 rounded"
            >
              Disconnect
            </button>
          ) : (
            <button
              onClick={connectWebSocket}
              className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1 rounded"
            >
              Reconnect
            </button>
          )}
        </div>
        <button
          onClick={() => setIsVisible(false)}
          className="text-gray-400 hover:text-white transition-colors"
        >
          ✕
        </button>
      </div>
      
      {connectionError && (
        <div className="bg-red-900 border-b border-red-700 px-4 py-2 text-red-200 text-xs">
          ⚠️ {connectionError}
        </div>
      )}
      
      {/* Filters */}
      <div className="bg-gray-800 px-4 py-2 border-b border-gray-700 space-y-2">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Filter messages..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="flex-1 bg-gray-900 text-white text-xs px-3 py-1.5 rounded border border-gray-700 focus:border-blue-500 focus:outline-none"
          />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="bg-gray-900 text-white text-xs px-3 py-1.5 rounded border border-gray-700 focus:border-blue-500 focus:outline-none"
          >
            {messageTypes.map(type => (
              <option key={type} value={type}>{type}</option>
            ))}
          </select>
        </div>
      </div>
      
      <div className="p-3 flex-1 overflow-y-auto bg-gray-950" style={{ maxHeight: size.height - 140 }}>
        {filteredMessages.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-8">
            {filter || typeFilter !== 'all' ? 'No messages match filter' : 'Waiting for messages...'}
          </p>
        ) : (
          <div className="space-y-2">
            {filteredMessages.map((msg, idx) => (
              <div key={idx} className="bg-gray-900 p-3 rounded-lg border border-gray-800 hover:border-gray-700 transition-colors">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-mono text-xs px-2 py-1 rounded bg-blue-900 text-blue-200">{msg.type}</span>
                  <span className="text-xs text-gray-500">{new Date(msg.timestamp).toLocaleTimeString()}</span>
                </div>
                <pre className="text-green-400 text-xs overflow-x-auto whitespace-pre-wrap break-words">
                  {JSON.stringify(msg.data, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>
      
      <div className="bg-gray-800 px-4 py-2 rounded-b-lg flex justify-between items-center text-xs text-gray-400 border-t border-gray-700 relative">
        <div className="flex gap-4">
          <span>{filteredMessages.length} / {messages.length} messages</span>
          {filter && <span className="text-blue-400">Filtered</span>}
        </div>
        <button
          onClick={() => { setMessages([]); setFilter(''); setTypeFilter('all'); }}
          className="text-red-400 hover:text-red-300 transition-colors font-medium"
        >
          Clear All
        </button>
        <div
          onMouseDown={handleResizeStart}
          className="absolute bottom-0 right-0 w-5 h-5 cursor-se-resize flex items-center justify-center"
        >
          <svg className="w-3 h-3 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8l4 4 4-4M4 16l4-4 4 4" />
          </svg>
        </div>
      </div>
    </div>
  );
}
