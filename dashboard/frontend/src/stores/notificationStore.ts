import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface StoredNotification {
  id: string;
  type: string;
  severity: 'critical' | 'warning' | 'info';
  title: string;
  message: string;
  mcpName?: string;
  timestamp: number;
  read: boolean;
  dismissed: boolean;
}

interface NotificationStore {
  notifications: StoredNotification[];
  addNotification: (notification: Omit<StoredNotification, 'read' | 'dismissed'>) => void;
  markAsRead: (id: string) => void;
  dismissNotification: (id: string) => void;
  clearAll: () => void;
  getUnreadCount: () => number;
}

export const useNotificationStore = create<NotificationStore>()(
  persist(
    (set, get) => ({
      notifications: [],
      
      addNotification: (notification) => {
        set((state) => ({
          notifications: [
            { ...notification, read: false, dismissed: false },
            ...state.notifications
          ].slice(0, 100) // Keep max 100 notifications
        }));
      },
      
      markAsRead: (id) => {
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, read: true } : n
          )
        }));
      },
      
      dismissNotification: (id) => {
        set((state) => ({
          notifications: state.notifications.map((n) =>
            n.id === id ? { ...n, dismissed: true } : n
          )
        }));
      },
      
      clearAll: () => {
        set({ notifications: [] });
      },
      
      getUnreadCount: () => {
        return get().notifications.filter((n) => !n.read && !n.dismissed).length;
      }
    }),
    {
      name: 'omni2-notifications',
      version: 1
    }
  )
);
