'use client';

import { useState, useEffect } from 'react';

export interface Notification {
  id: string;
  type: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  message: string;
  mcpName?: string;
  timestamp: number;
}

interface NotificationConfig {
  enabled: boolean;
  sound_enabled: boolean;
  auto_dismiss: {
    critical: number;
    warning: number;
    info: number;
  };
  critical_always_show: boolean;
  max_visible: number;
}

interface NotificationFeedProps {
  notifications: Notification[];
  onDismiss: (id: string) => void;
  onClearAll: () => void;
  onNotificationClick?: (notification: Notification) => void;
  config: NotificationConfig;
}

export default function NotificationFeed({
  notifications,
  onDismiss,
  onClearAll,
  onNotificationClick,
  config
}: NotificationFeedProps) {
  const [isMinimized, setIsMinimized] = useState(false);
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  // Auto-dismiss based on severity
  useEffect(() => {
    notifications.forEach(notification => {
      const dismissTime = config.auto_dismiss[notification.severity] * 1000;
      
      // Critical alerts don't auto-dismiss if config says so
      if (notification.severity === 'critical' && config.critical_always_show) {
        return;
      }
      
      const timer = setTimeout(() => {
        onDismiss(notification.id);
      }, dismissTime);
      
      return () => clearTimeout(timer);
    });
  }, [notifications, config, onDismiss]);

  if (!config.enabled) return null;

  const visibleNotifications = notifications.slice(0, config.max_visible);
  const hasNotifications = visibleNotifications.length > 0;

  const getSeverityStyles = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-gradient-to-r from-red-500 to-red-600 border-red-400';
      case 'warning':
        return 'bg-gradient-to-r from-yellow-500 to-yellow-600 border-yellow-400';
      case 'info':
        return 'bg-gradient-to-r from-green-500 to-green-600 border-green-400';
      default:
        return 'bg-gradient-to-r from-blue-500 to-blue-600 border-blue-400';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return '🔴';
      case 'warning':
        return '🟡';
      case 'info':
        return '🟢';
      default:
        return '🔵';
    }
  };

  const getTimeAgo = (timestamp: number) => {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    return `${hours}h ago`;
  };

  return (
    <div className="fixed left-6 bottom-6 z-[9999] flex flex-col gap-3 max-w-sm">
      {/* Header with controls */}
      {hasNotifications && (
        <div className="flex items-center justify-between mb-2">
          <button
            onClick={() => setIsMinimized(!isMinimized)}
            className="px-3 py-1.5 bg-white/90 backdrop-blur-lg rounded-full shadow-lg border border-gray-200 text-sm font-medium text-gray-700 hover:bg-white transition-all"
          >
            {isMinimized ? '📬' : '📭'} {visibleNotifications.length}
          </button>
          {!isMinimized && (
            <button
              onClick={onClearAll}
              className="px-3 py-1.5 bg-white/90 backdrop-blur-lg rounded-full shadow-lg border border-gray-200 text-sm font-medium text-gray-700 hover:bg-white transition-all"
            >
              Clear All
            </button>
          )}
        </div>
      )}

      {/* Notifications stack */}
      {!isMinimized && visibleNotifications.map((notification, index) => (
        <div
          key={notification.id}
          className={`
            transform transition-all duration-300 ease-out
            ${index === 0 ? 'animate-slide-in-left' : ''}
            ${hoveredId === notification.id ? 'scale-105' : 'scale-100'}
          `}
          style={{
            animation: index === 0 ? 'slideInLeft 0.3s ease-out' : 'none'
          }}
          onMouseEnter={() => setHoveredId(notification.id)}
          onMouseLeave={() => setHoveredId(null)}
        >
          <div
            className={`
              relative overflow-hidden rounded-2xl shadow-2xl border-2
              backdrop-blur-xl cursor-pointer
              ${getSeverityStyles(notification.severity)}
              hover:shadow-3xl transition-all duration-200
            `}
            onClick={() => onNotificationClick?.(notification)}
          >
            {/* Animated gradient overlay */}
            <div className="absolute inset-0 bg-gradient-to-br from-white/20 to-transparent opacity-50"></div>
            
            {/* Content */}
            <div className="relative p-4 text-white">
              {/* Header */}
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{getSeverityIcon(notification.severity)}</span>
                  <div>
                    <h3 className="font-bold text-sm leading-tight">{notification.title}</h3>
                    {notification.mcpName && (
                      <p className="text-xs opacity-90 font-medium mt-0.5">MCP: {notification.mcpName}</p>
                    )}
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onDismiss(notification.id);
                  }}
                  className="text-white/80 hover:text-white hover:bg-white/20 rounded-full p-1 transition-all"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Message */}
              <p className="text-sm opacity-95 leading-snug mb-3">{notification.message}</p>

              {/* Footer */}
              <div className="flex items-center justify-between text-xs opacity-80">
                <span>{getTimeAgo(notification.timestamp)}</span>
                {notification.severity === 'critical' && config.critical_always_show && (
                  <span className="bg-white/20 px-2 py-0.5 rounded-full font-medium">
                    Manual dismiss
                  </span>
                )}
              </div>
            </div>

            {/* Progress bar for auto-dismiss */}
            {!(notification.severity === 'critical' && config.critical_always_show) && (
              <div className="absolute bottom-0 left-0 right-0 h-1 bg-white/20">
                <div
                  className="h-full bg-white/60 transition-all"
                  style={{
                    animation: `shrink ${config.auto_dismiss[notification.severity]}s linear`,
                    transformOrigin: 'left'
                  }}
                ></div>
              </div>
            )}
          </div>
        </div>
      ))}

      {/* Inline styles for animations */}
      <style jsx>{`
        @keyframes slideInLeft {
          from {
            transform: translateX(-100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }

        @keyframes shrink {
          from {
            transform: scaleX(1);
          }
          to {
            transform: scaleX(0);
          }
        }
      `}</style>
    </div>
  );
}
