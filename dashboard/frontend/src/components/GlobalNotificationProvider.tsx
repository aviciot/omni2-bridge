'use client';

import { useEffect, useState, useRef } from 'react';
import { usePathname } from 'next/navigation';
import NotificationFeed, { Notification } from '@/components/notifications/NotificationFeed';

export default function GlobalNotificationProvider() {
  const pathname = usePathname();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [notificationConfig, setNotificationConfig] = useState({
    enabled: true,
    sound_enabled: false,
    auto_dismiss: { critical: 15, warning: 8, info: 5 },
    critical_always_show: true,
    max_visible: 5
  });
  const wsRef = useRef<WebSocket | null>(null);
  const isConnectingRef = useRef(false);
  const seenEventsRef = useRef<Set<string>>(new Set());

  // Only show on authenticated pages (not login)
  const isAuthPage = pathname === '/login' || pathname === '/';

  useEffect(() => {
    if (isAuthPage) return;

    loadNotificationConfig();
    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [isAuthPage]);

  const loadNotificationConfig = async () => {
    try {
      const response = await fetch('http://localhost:8500/api/v1/config');
      const data = await response.json();
      if (Array.isArray(data)) {
        const notifConfig = data.find((c: any) => c.key === 'notifications');
        if (notifConfig?.value) {
          setNotificationConfig(notifConfig.value);
        }
      } else if (data.notifications) {
        setNotificationConfig(data.notifications);
      }
    } catch (err) {
      console.error('Failed to load notification config:', err);
    }
  };

  const connectWebSocket = () => {
    if (isConnectingRef.current || wsRef.current?.readyState === WebSocket.OPEN) return;
    isConnectingRef.current = true;

    const token = localStorage.getItem('access_token') || localStorage.getItem('token');
    if (!token) {
      isConnectingRef.current = false;
      return;
    }

    const ws = new WebSocket(`ws://localhost:8500/ws?token=${token}`);
    wsRef.current = ws;

    ws.onopen = () => {
      isConnectingRef.current = false;
      ws.send(JSON.stringify({
        action: 'subscribe',
        event_types: ['mcp_auto_disabled', 'circuit_breaker_state', 'mcp_status_change']
      }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'mcp_auto_disabled' || data.type === 'circuit_breaker_state') {
          addNotification(data);
        } else if (data.type === 'mcp_status_change') {
          if (data.data.old_status === 'not_loaded' && data.data.new_status === 'loading') {
            addNotification(data);
          }
        }
      } catch (err) {
        console.error('WebSocket error:', err);
      }
    };

    ws.onerror = (err) => {
      console.error('WebSocket connection error:', err);
      isConnectingRef.current = false;
    };

    ws.onclose = () => {
      isConnectingRef.current = false;
      wsRef.current = null;
      setTimeout(() => {
        if (!isAuthPage) connectWebSocket();
      }, 5000);
    };
  };

  const addNotification = (event: any) => {
    // Create unique key for deduplication
    const eventKey = `${event.type}-${event.data.mcp_name}-${event.data.old_status}-${event.data.new_status}`;
    
    // Skip if we've seen this exact event in the last 30 seconds
    if (seenEventsRef.current.has(eventKey)) {
      return;
    }
    
    // Mark as seen and auto-remove after 30 seconds
    seenEventsRef.current.add(eventKey);
    setTimeout(() => {
      seenEventsRef.current.delete(eventKey);
    }, 30000);
    
    const notification: Notification = {
      id: `${Date.now()}-${Math.random()}`,
      type: event.type,
      severity: event.type === 'mcp_auto_disabled' ? 'critical' : 
                event.data.old_status === 'not_loaded' ? 'info' :
                event.data.state === 'open' ? 'warning' : 'info',
      title: event.type === 'mcp_auto_disabled' ? 'MCP Auto-Disabled' : 
             event.data.old_status === 'not_loaded' ? 'New MCP Detected' :
             'Circuit Breaker Alert',
      message: event.type === 'mcp_auto_disabled' 
        ? `${event.data.mcp_name} has been automatically disabled after ${event.data.failure_count} failures`
        : event.data.old_status === 'not_loaded'
        ? `New MCP server ${event.data.mcp_name} detected and loading`
        : `Circuit breaker ${event.data.state} for ${event.data.mcp_name}`,
      mcpName: event.data.mcp_name,
      timestamp: Date.now()
    };
    setNotifications(prev => [notification, ...prev]);
  };

  const handleDismissNotification = (id: string) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const handleClearAllNotifications = () => {
    setNotifications([]);
  };

  const handleNotificationClick = (notification: Notification) => {
    // Navigate to MCP page if not already there
    if (pathname !== '/mcps') {
      window.location.href = '/mcps';
    }
    // Scroll to MCP row after navigation
    setTimeout(() => {
      const element = document.getElementById(`mcp-${notification.mcpName}`);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        element.classList.add('ring-4', 'ring-purple-500');
        setTimeout(() => element.classList.remove('ring-4', 'ring-purple-500'), 2000);
      }
    }, 100);
  };

  if (isAuthPage) return null;

  return (
    <NotificationFeed
      notifications={notifications}
      onDismiss={handleDismissNotification}
      onClearAll={handleClearAllNotifications}
      onNotificationClick={handleNotificationClick}
      config={notificationConfig}
    />
  );
}
