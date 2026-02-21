'use client';

import React from 'react';
import { Shield, AlertTriangle, Database, Lock, TrendingUp, FileText } from 'lucide-react';

interface SecurityProfileProps {
  runId: number;
}

interface AttackVector {
  vector: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  affected_tools: string[];
  description: string;
}

interface SecurityProfile {
  overview: string;
  tool_summary: {
    total: number;
    high_risk: number;
    medium_risk: number;
    low_risk: number;
    high_risk_tools?: string[];
  };
  risk_surface: string[];
  data_sensitivity: {
    handles_pii: boolean;
    handles_credentials: boolean;
    handles_financial: boolean;
    evidence: string[];
  };
  attack_vectors: AttackVector[];
  recommended_focus: string[];
  risk_score: number;
}

const SecurityProfile: React.FC<SecurityProfileProps> = ({ runId }) => {
  const [profile, setProfile] = React.useState<SecurityProfile | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const fetchProfile = async () => {
      try {
        const response = await fetch(`/api/v1/mcp-pt/runs/${runId}/security-profile`);
        const data = await response.json();
        setProfile(data);
      } catch (error) {
        console.error('Failed to fetch security profile:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [runId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (!profile || Object.keys(profile).length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-6xl mb-4">🔍</div>
        <h3 className="text-xl font-bold text-gray-700 mb-2">No Security Profile Available</h3>
        <p className="text-gray-500 mb-4">This run was created before the security profile feature was added.</p>
        <p className="text-sm text-gray-400">Start a new PT run to generate an AI-powered security analysis.</p>
      </div>
    );
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'bg-red-500/20 text-red-400 border-red-500/50';
      case 'high': return 'bg-orange-500/20 text-orange-400 border-orange-500/50';
      case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50';
      case 'low': return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/50';
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 8) return 'text-red-500';
    if (score >= 6) return 'text-orange-500';
    if (score >= 4) return 'text-yellow-500';
    return 'text-green-500';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-900/30 via-pink-900/30 to-red-900/30 rounded-lg p-6 border border-purple-500/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-purple-400" />
            <div>
              <h2 className="text-2xl font-bold text-white">MCP Security Profile</h2>
              <p className="text-gray-400 text-sm">AI-Powered Security Analysis</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-400">Risk Score</div>
            <div className={`text-4xl font-bold ${getRiskColor(profile.risk_score)}`}>
              {profile.risk_score}/10
            </div>
          </div>
        </div>
      </div>

      {/* Overview */}
      <div className="bg-gray-800/50 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center gap-2 mb-3">
          <FileText className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Overview</h3>
        </div>
        <p className="text-gray-300 leading-relaxed">{profile.overview}</p>
      </div>

      {/* Tool Summary */}
      <div className="bg-gray-800/50 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Tool Inventory</h3>
        </div>
        
        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-white">{profile.tool_summary.total}</div>
            <div className="text-sm text-gray-400">Total Tools</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-red-400">{profile.tool_summary.high_risk}</div>
            <div className="text-sm text-gray-400">High Risk</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-yellow-400">{profile.tool_summary.medium_risk}</div>
            <div className="text-sm text-gray-400">Medium Risk</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-green-400">{profile.tool_summary.low_risk}</div>
            <div className="text-sm text-gray-400">Low Risk</div>
          </div>
        </div>

        {profile.tool_summary.high_risk_tools && profile.tool_summary.high_risk_tools.length > 0 && (
          <div className="mt-4 p-4 bg-red-500/10 rounded border border-red-500/30">
            <div className="text-sm font-semibold text-red-400 mb-2">High Risk Tools:</div>
            <ul className="space-y-1">
              {profile.tool_summary.high_risk_tools.map((tool, idx) => (
                <li key={idx} className="text-sm text-gray-300">• {tool}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Attack Vectors */}
      <div className="bg-gray-800/50 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <AlertTriangle className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Attack Surface</h3>
        </div>
        
        <div className="space-y-3">
          {profile.attack_vectors.map((vector, idx) => (
            <div
              key={idx}
              className={`p-4 rounded-lg border ${getSeverityColor(vector.severity)}`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-white">{vector.vector}</span>
                  <span className={`text-xs px-2 py-1 rounded uppercase font-bold ${getSeverityColor(vector.severity)}`}>
                    {vector.severity}
                  </span>
                </div>
              </div>
              <p className="text-sm text-gray-300 mb-2">{vector.description}</p>
              <div className="text-xs text-gray-400">
                <span className="font-semibold">Affected Tools:</span> {vector.affected_tools.join(', ')}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Data Sensitivity */}
      <div className="bg-gray-800/50 rounded-lg p-6 border border-gray-700">
        <div className="flex items-center gap-2 mb-4">
          <Lock className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Data Sensitivity</h3>
        </div>
        
        <div className="grid grid-cols-3 gap-4 mb-4">
          <div className={`p-3 rounded text-center ${profile.data_sensitivity.handles_pii ? 'bg-red-500/20 border border-red-500/50' : 'bg-gray-700/50 border border-gray-600'}`}>
            <div className="text-sm font-semibold text-white">PII Data</div>
            <div className={`text-2xl ${profile.data_sensitivity.handles_pii ? 'text-red-400' : 'text-gray-500'}`}>
              {profile.data_sensitivity.handles_pii ? '✓' : '✗'}
            </div>
          </div>
          <div className={`p-3 rounded text-center ${profile.data_sensitivity.handles_credentials ? 'bg-red-500/20 border border-red-500/50' : 'bg-gray-700/50 border border-gray-600'}`}>
            <div className="text-sm font-semibold text-white">Credentials</div>
            <div className={`text-2xl ${profile.data_sensitivity.handles_credentials ? 'text-red-400' : 'text-gray-500'}`}>
              {profile.data_sensitivity.handles_credentials ? '✓' : '✗'}
            </div>
          </div>
          <div className={`p-3 rounded text-center ${profile.data_sensitivity.handles_financial ? 'bg-red-500/20 border border-red-500/50' : 'bg-gray-700/50 border border-gray-600'}`}>
            <div className="text-sm font-semibold text-white">Financial</div>
            <div className={`text-2xl ${profile.data_sensitivity.handles_financial ? 'text-red-400' : 'text-gray-500'}`}>
              {profile.data_sensitivity.handles_financial ? '✓' : '✗'}
            </div>
          </div>
        </div>

        {profile.data_sensitivity.evidence.length > 0 && (
          <div className="p-3 bg-gray-700/50 rounded">
            <div className="text-sm font-semibold text-gray-300 mb-2">Evidence:</div>
            <ul className="space-y-1">
              {profile.data_sensitivity.evidence.map((evidence, idx) => (
                <li key={idx} className="text-sm text-gray-400">• {evidence}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Recommended Focus */}
      <div className="bg-gradient-to-r from-purple-900/20 to-pink-900/20 rounded-lg p-6 border border-purple-500/30">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Recommended Test Focus</h3>
        </div>
        <p className="text-gray-300 mb-3">Based on this analysis, prioritize testing in these categories:</p>
        <div className="flex flex-wrap gap-2">
          {profile.recommended_focus.map((category, idx) => (
            <span
              key={idx}
              className="px-4 py-2 bg-purple-500/20 text-purple-300 rounded-full border border-purple-500/50 font-medium"
            >
              {category.replace(/_/g, ' ').toUpperCase()}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SecurityProfile;
