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
    <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-12 h-12 bg-gradient-to-br from-sky-400 to-blue-500 rounded-2xl flex items-center justify-center shadow-lg">
              <span className="text-2xl">🔐</span>
            </div>
            <div>
              <h2 className="text-4xl font-bold bg-gradient-to-r from-gray-900 via-sky-800 to-blue-800 bg-clip-text text-transparent">
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
                  ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-md'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              👥 Users
            </button>
            <button
              onClick={() => setActiveTab('roles')}
              className={`flex-1 px-6 py-3 rounded-xl font-semibold transition-all ${
                activeTab === 'roles'
                  ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-md'
                  : 'text-gray-600 hover:bg-gray-100'
              }`}
            >
              🎭 Roles
            </button>
            <button
              onClick={() => setActiveTab('teams')}
              className={`flex-1 px-6 py-3 rounded-xl font-semibold transition-all ${
                activeTab === 'teams'
                  ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-md'
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
  );
}
