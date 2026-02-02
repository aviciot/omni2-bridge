import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ActivityStyle {
  bgColor: string;
  icon: string;
  label: string;
}

interface GraphConfig {
  activityStyles: Record<string, ActivityStyle>;
  layout: 'vertical' | 'horizontal';
  background: 'dots' | 'lines' | 'none';
  updateActivityStyle: (type: string, style: Partial<ActivityStyle>) => void;
  setLayout: (layout: 'vertical' | 'horizontal') => void;
  setBackground: (background: 'dots' | 'lines' | 'none') => void;
  resetToDefaults: () => void;
}

const defaultStyles: Record<string, ActivityStyle> = {
  user_message: { bgColor: '#dbeafe', icon: '👤', label: 'User Message' },
  mcp_tool_call: { bgColor: '#fef3c7', icon: '🔧', label: 'Tool Call' },
  mcp_tool_response: { bgColor: '#d1fae5', icon: '✅', label: 'Tool Response' },
  assistant_response: { bgColor: '#e9d5ff', icon: '🤖', label: 'AI Response' },
};

export const useGraphConfig = create<GraphConfig>()(
  persist(
    (set) => ({
      activityStyles: defaultStyles,
      layout: 'vertical',
      background: 'dots',
      updateActivityStyle: (type, style) =>
        set((state) => ({
          activityStyles: {
            ...state.activityStyles,
            [type]: { ...state.activityStyles[type], ...style },
          },
        })),
      setLayout: (layout) => set({ layout }),
      setBackground: (background) => set({ background }),
      resetToDefaults: () =>
        set({ activityStyles: defaultStyles, layout: 'vertical', background: 'dots' }),
    }),
    {
      name: 'graph-config',
    }
  )
);
