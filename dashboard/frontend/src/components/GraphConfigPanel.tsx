'use client';

import { useGraphConfig } from '@/stores/graphConfigStore';
import { useState } from 'react';

const shapes = ['circle', 'square', 'diamond', 'hexagon'];

export default function GraphConfigPanel() {
  const { activityStyles, background, updateActivityStyle, setBackground, resetToDefaults } = useGraphConfig();
  const [isOpen, setIsOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
    window.dispatchEvent(new CustomEvent('graph-refresh', { detail: refreshKey }));
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-gray-900">⚙️ Graph Configuration</h3>
        <div className="flex gap-2">
          <button
            onClick={handleRefresh}
            className="px-3 py-1 text-sm bg-purple-600 text-white rounded hover:bg-purple-700"
          >
            🔄 Refresh Graph
          </button>
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="text-sm text-purple-600 hover:text-purple-700"
          >
            {isOpen ? '▲ Collapse' : '▼ Expand'}
          </button>
        </div>
      </div>

      {isOpen && (
        <div className="space-y-6">
          <div>
            <h4 className="font-semibold text-sm mb-3">Activity Colors</h4>
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(activityStyles).map(([type, style]) => (
                <div key={type} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                  <input
                    type="color"
                    value={style.bgColor}
                    onChange={(e) => updateActivityStyle(type, { bgColor: e.target.value })}
                    className="w-10 h-10 border border-gray-300 rounded cursor-pointer"
                  />
                  <div className="flex-1">
                    <div className="text-sm font-medium">{style.label}</div>
                    <div className="text-xs text-gray-500">{type}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-sm mb-3">Background Pattern</h4>
            <div className="flex gap-2">
              {(['dots', 'lines', 'none'] as const).map((bg) => (
                <button
                  key={bg}
                  onClick={() => setBackground(bg)}
                  className={`px-3 py-2 text-xs rounded capitalize ${
                    background === bg ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {bg}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={resetToDefaults}
            className="w-full px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 text-sm font-medium"
          >
            🔄 Reset to Defaults
          </button>
        </div>
      )}
    </div>
  );
}
