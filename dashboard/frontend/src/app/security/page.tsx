'use client';

import Link from 'next/link';

export default function SecurityPage() {
  return (
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900">🛡️ Security Services</h2>
        <p className="text-gray-600 mt-1">Manage security and protection services</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Security Incidents */}
          <Link href="/security/incidents">
            <div className="bg-white rounded-2xl shadow-xl p-8 border-2 border-gray-200 hover:border-yellow-500 hover:shadow-2xl transition-all cursor-pointer">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-16 h-16 bg-gradient-to-br from-yellow-600 to-orange-600 rounded-xl flex items-center justify-center shadow-lg">
                  <span className="text-3xl">🚨</span>
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-gray-900">Security Incidents</h3>
                  <p className="text-sm text-gray-600">Threat monitoring</p>
                </div>
              </div>
              <p className="text-gray-700 mb-4">
                Monitor prompt injections, blocked users, and policy violations in real-time.
              </p>
              <div className="flex items-center gap-2 text-yellow-600 font-semibold">
                <span>View Incidents</span>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          </Link>

          {/* Prompt Guard */}
          <Link href="/security/prompt-guard">
            <div className="bg-white rounded-2xl shadow-xl p-8 border-2 border-gray-200 hover:border-purple-500 hover:shadow-2xl transition-all cursor-pointer">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-16 h-16 bg-gradient-to-br from-purple-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg">
                  <span className="text-3xl">🛡️</span>
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-gray-900">Prompt Guard</h3>
                  <p className="text-sm text-gray-600">AI-powered injection detection</p>
                </div>
              </div>
              <p className="text-gray-700 mb-4">
                Real-time prompt injection detection using ML models. Protects against malicious prompts and jailbreak attempts.
              </p>
              <div className="flex items-center gap-2 text-purple-600 font-semibold">
                <span>Configure Settings</span>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          </Link>

          {/* MCP PT */}
          <Link href="/security/mcp-pt">
            <div className="bg-white rounded-2xl shadow-xl p-8 border-2 border-gray-200 hover:border-red-500 hover:shadow-2xl transition-all cursor-pointer">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-16 h-16 bg-gradient-to-br from-red-600 to-orange-600 rounded-xl flex items-center justify-center shadow-lg">
                  <span className="text-3xl">🔍</span>
                </div>
                <div>
                  <h3 className="text-2xl font-bold text-gray-900">MCP PT</h3>
                  <p className="text-sm text-gray-600">Penetration Testing</p>
                </div>
              </div>
              <p className="text-gray-700 mb-4">
                Security scanning for MCP servers with PII/Secrets detection. Identifies vulnerabilities and provides security scores.
              </p>
              <div className="flex items-center gap-2 text-red-600 font-semibold">
                <span>Start Scanning</span>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </div>
          </Link>
      </div>
    </main>
  );
}
