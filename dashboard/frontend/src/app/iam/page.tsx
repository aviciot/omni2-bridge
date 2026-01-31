"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/stores/authStore";
import UsersTab from "@/components/iam/UsersTab";
import RolesTab from "@/components/iam/RolesTab";
import TeamsTab from "@/components/iam/TeamsTab";

export default function IAMPage() {
  const router = useRouter();
  const { user, isAuthenticated, fetchUser, logout } = useAuthStore();
  const [activeTab, setActiveTab] = useState<'users' | 'roles' | 'teams'>('users');

  useEffect(() => {
    const initAuth = async () => {
      await fetchUser();
      if (!isAuthenticated) {
        router.push("/login");
      }
    };
    initAuth();
  }, [isAuthenticated, fetchUser, router]);

  if (!user) return null;
  const isAdmin = user.role === "super_admin";

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-purple-800 bg-clip-text text-transparent">
                Omni2 Admin
              </h1>
              <p className="text-sm text-gray-600 mt-1">MCP Hub Management Dashboard</p>
            </div>
            <div className="flex items-center gap-4">
              <span className="text-sm text-gray-600">
                Welcome, <span className="font-semibold">{user?.email}</span>
              </span>
              <button
                onClick={logout}
                className="px-4 py-2 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <Link
              href="/dashboard"
              className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              Dashboard
            </Link>
            <Link
              href="/mcps"
              className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              MCP Servers
            </Link>
            <Link
              href="/iam"
              className="border-b-2 border-purple-600 py-4 px-1 text-sm font-medium text-purple-600"
            >
              IAM
            </Link>
            <Link
              href="/analytics"
              className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              Analytics
            </Link>
            <Link
              href="/live-updates"
              className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              Live Updates
            </Link>
            <div className="border-l border-gray-300 mx-2"></div>
            <Link
              href="/admin"
              className="border-b-2 border-transparent py-4 px-1 text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
            >
              ⚙️ Admin
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg">
              <span className="text-2xl">🔐</span>
            </div>
            <div>
              <h2 className="text-4xl font-bold bg-gradient-to-r from-gray-900 via-purple-900 to-indigo-900 bg-clip-text text-transparent">
                Identity & Access Management
              </h2>
              <p className="text-gray-600 mt-1">Manage users, roles, and team permissions</p>
            </div>
          </div>
        </div>

        <div className="bg-white/80 backdrop-blur-lg rounded-2xl border border-gray-200/50 p-2 mb-6 shadow-xl">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('users')}
              className={`flex-1 px-6 py-3 rounded-xl font-semibold transition-all ${
                activeTab === 'users'
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              👥 Users
            </button>
            <button
              onClick={() => setActiveTab('roles')}
              className={`flex-1 px-6 py-3 rounded-xl font-semibold transition-all ${
                activeTab === 'roles'
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              🎭 Roles
            </button>
            <button
              onClick={() => setActiveTab('teams')}
              className={`flex-1 px-6 py-3 rounded-xl font-semibold transition-all ${
                activeTab === 'teams'
                  ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              👨👩👧👦 Teams
            </button>
            <Link
              href="/iam/chat-config"
              className="flex-1 px-6 py-3 rounded-xl font-semibold transition-all text-gray-600 hover:bg-gray-100 text-center"
            >
              💬 Chat Config
            </Link>
          </div>
        </div>

        <div>
          {activeTab === 'users' && <UsersTab isAdmin={isAdmin} />}
          {activeTab === 'roles' && <RolesTab />}
          {activeTab === 'teams' && <TeamsTab />}
        </div>
      </main>
    </div>
  );
}
