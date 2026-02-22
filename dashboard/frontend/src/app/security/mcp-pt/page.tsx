'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useAuthStore } from '@/stores/authStore';
import { useRouter } from 'next/navigation';
import MCPPTDashboardV2 from "@/components/MCPPTDashboardV2";

export default function MCPPTPage() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading: authLoading, fetchUser, logout } = useAuthStore();

  useEffect(() => {
    const initAuth = async () => {
      await fetchUser();
    };
    initAuth();
  }, [fetchUser]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    // Do NOT return null — Next.js App Router interprets null as 404.
    // Show spinner while router.push('/login') completes.
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Redirecting...</p>
        </div>
      </div>
    );
  }

  return (
    <main>
      <MCPPTDashboardV2 />
    </main>
  );
}
