'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';

interface Activity {
  activity_id: string;
  sequence_num: number;
  activity_type: string;
  activity_data: any;
  duration_ms: number | null;
  created_at: string;
}

interface ConversationDetail {
  conversation_id: string;
  user_id: number;
  started_at: string;
  ended_at: string;
  duration_seconds: number;
  total_activities: number;
  tool_calls: number;
  activities: Activity[];
}

export default function ConversationDetailPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const conversationId = searchParams.get('id');
  const { isAuthenticated, fetchUser } = useAuthStore();
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedActivity, setSelectedActivity] = useState<Activity | null>(null);

  useEffect(() => {
    const initAuth = async () => {
      await fetchUser();
      if (!isAuthenticated) {
        router.push('/login');
      }
    };
    initAuth();
  }, [isAuthenticated, fetchUser, router]);

  useEffect(() => {
    if (isAuthenticated && conversationId) {
      loadConversation();
    }
  }, [isAuthenticated, conversationId]);

  const loadConversation = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`http://localhost:8500/api/v1/activities/conversation/${conversationId}`);
      setConversation(response.data);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    } finally {
      setLoading(false);
    }
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'user_message': return '👤';
      case 'mcp_tool_call': return '🔧';
      case 'mcp_tool_response': return '✅';
      case 'assistant_response': return '🤖';
      default: return '📝';
    }
  };

  const getActivityColor = (type: string) => {
    switch (type) {
      case 'user_message': return 'bg-blue-100 border-blue-300 text-blue-900';
      case 'mcp_tool_call': return 'bg-amber-100 border-amber-300 text-amber-900';
      case 'mcp_tool_response': return 'bg-green-100 border-green-300 text-green-900';
      case 'assistant_response': return 'bg-purple-100 border-purple-300 text-purple-900';
      default: return 'bg-gray-100 border-gray-300 text-gray-900';
    }
  };

  const getActivityLabel = (type: string) => {
    return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading conversation...</p>
        </div>
      </div>
    );
  }

  if (!conversation) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">❌</div>
          <p className="text-gray-600">Conversation not found</p>
          <Link href="/analytics/conversations" className="text-purple-600 hover:underline mt-4 inline-block">
            ← Back to conversations
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-purple-800 bg-clip-text text-transparent">
              Omni2 Dashboard
            </h1>
            <Link href="/analytics/conversations" className="text-sm text-purple-600 hover:underline">
              ← Back to list
            </Link>
          </div>
        </div>
      </header>

      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <Link href="/dashboard" className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">
              Dashboard
            </Link>
            <Link href="/mcps" className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">
              MCP Servers
            </Link>
            <Link href="/iam" className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">
              IAM
            </Link>
            <Link href="/analytics" className="border-b-2 border-purple-600 py-4 px-1 text-sm font-medium text-purple-600">
              Analytics
            </Link>
            <Link href="/live-updates" className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300">
              Live Updates
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-900">Conversation Summary</h2>
            <span className="text-xs text-gray-500">ID: {conversation.conversation_id}</span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-600">User</div>
              <div className="text-lg font-semibold">👤 User {conversation.user_id}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Duration</div>
              <div className="text-lg font-semibold">⏱️ {conversation.duration_seconds.toFixed(1)}s</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Activities</div>
              <div className="text-lg font-semibold">📊 {conversation.total_activities}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Tool Calls</div>
              <div className="text-lg font-semibold">🔧 {conversation.tool_calls}</div>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Activity Flow</h3>
          
          <div className="relative">
            {conversation.activities.map((activity, idx) => (
              <div key={activity.activity_id} className="relative mb-4">
                {idx < conversation.activities.length - 1 && (
                  <div className="absolute left-6 top-16 w-0.5 h-8 bg-gray-300 z-0" />
                )}
                
                <div
                  onClick={() => setSelectedActivity(activity)}
                  className={`relative z-10 flex items-start gap-4 p-4 rounded-lg border-2 cursor-pointer transition-all ${
                    selectedActivity?.activity_id === activity.activity_id
                      ? 'ring-2 ring-purple-500 shadow-lg'
                      : 'hover:shadow-md'
                  } ${getActivityColor(activity.activity_type)}`}
                >
                  <div className="flex-shrink-0 w-12 h-12 rounded-full bg-white flex items-center justify-center text-2xl shadow-md">
                    {getActivityIcon(activity.activity_type)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="font-semibold text-sm">
                        {getActivityLabel(activity.activity_type)}
                      </h4>
                      <span className="text-xs opacity-75">
                        #{activity.sequence_num}
                      </span>
                    </div>
                    
                    {activity.activity_type === 'user_message' && (
                      <p className="text-sm">{activity.activity_data.message}</p>
                    )}
                    
                    {activity.activity_type === 'mcp_tool_call' && (
                      <div className="text-sm">
                        <span className="font-medium">{activity.activity_data.mcp_server}</span>
                        <span className="mx-1">→</span>
                        <span>{activity.activity_data.tool_name}</span>
                      </div>
                    )}
                    
                    {activity.activity_type === 'mcp_tool_response' && (
                      <div className="text-sm">
                        <span className="font-medium">{activity.activity_data.mcp_server}</span>
                        {activity.duration_ms && (
                          <span className="ml-2 text-xs">⏱️ {activity.duration_ms}ms</span>
                        )}
                      </div>
                    )}
                    
                    {activity.activity_type === 'assistant_response' && (
                      <div className="text-sm">
                        <p className="line-clamp-2">{activity.activity_data.message}</p>
                        {activity.activity_data.tokens_used && (
                          <span className="text-xs mt-1 inline-block">💰 {activity.activity_data.tokens_used} tokens</span>
                        )}
                      </div>
                    )}
                    
                    <div className="text-xs opacity-75 mt-1">
                      {new Date(activity.created_at).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {selectedActivity && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-bold">Activity Details</h3>
                <button
                  onClick={() => setSelectedActivity(null)}
                  className="text-gray-500 hover:text-gray-700"
                >
                  ✕
                </button>
              </div>
              
              <div className="space-y-4">
                <div>
                  <div className="text-sm text-gray-600">Type</div>
                  <div className="font-semibold">{getActivityLabel(selectedActivity.activity_type)}</div>
                </div>
                
                <div>
                  <div className="text-sm text-gray-600">Sequence</div>
                  <div className="font-semibold">#{selectedActivity.sequence_num}</div>
                </div>
                
                <div>
                  <div className="text-sm text-gray-600">Timestamp</div>
                  <div className="font-semibold">{new Date(selectedActivity.created_at).toLocaleString()}</div>
                </div>
                
                {selectedActivity.duration_ms && (
                  <div>
                    <div className="text-sm text-gray-600">Duration</div>
                    <div className="font-semibold">{selectedActivity.duration_ms}ms</div>
                  </div>
                )}
                
                <div>
                  <div className="text-sm text-gray-600 mb-2">Data</div>
                  <pre className="bg-gray-50 p-4 rounded text-xs overflow-x-auto">
                    {JSON.stringify(selectedActivity.activity_data, null, 2)}
                  </pre>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
