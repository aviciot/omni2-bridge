'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/authStore';
import NotificationCenter from '@/components/notifications/NotificationCenter';

export default function MainNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();

  return (
    <>
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex justify-between items-center">
            <button 
              onClick={() => router.push('/dashboard')}
              className="hover:opacity-80 transition-opacity cursor-pointer"
            >
              <h1 className="text-3xl font-bold bg-gradient-to-r from-sky-500 to-blue-600 bg-clip-text text-transparent">
                Omni2 Dashboard
              </h1>
              <p className="text-sm text-gray-600 mt-1">MCP Hub Management</p>
            </button>
            <div className="flex items-center gap-4">
              <NotificationCenter />
              <span className="text-sm text-gray-600">
                Welcome, <span className="font-semibold">{user?.email}</span>
              </span>
              <button
                onClick={logout}
                className="px-4 py-2 text-sm font-medium text-white bg-sky-600 hover:bg-sky-700 rounded-lg transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            <Link href="/dashboard" className={`border-b-2 py-4 px-1 text-sm font-medium ${pathname === '/dashboard' ? 'border-sky-600 text-sky-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}>
              Dashboard
            </Link>
            <Link href="/mcps" className={`border-b-2 py-4 px-1 text-sm font-medium ${pathname === '/mcps' ? 'border-sky-600 text-sky-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}>
              MCP Servers
            </Link>
            <Link href="/iam" className={`border-b-2 py-4 px-1 text-sm font-medium ${pathname?.startsWith('/iam') ? 'border-sky-600 text-sky-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}>
              IAM
            </Link>
            <Link href="/analytics" className={`border-b-2 py-4 px-1 text-sm font-medium ${pathname?.startsWith('/analytics') ? 'border-sky-600 text-sky-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}>
              Analytics
            </Link>
            <Link href="/security" className={`border-b-2 py-4 px-1 text-sm font-medium ${pathname?.startsWith('/security') ? 'border-sky-600 text-sky-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}>
              🛡️ Security
            </Link>
            <Link href="/live-updates" className={`border-b-2 py-4 px-1 text-sm font-medium ${pathname === '/live-updates' ? 'border-sky-600 text-sky-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}>
              Live Updates
            </Link>
            <Link href="/admin" className={`border-b-2 py-4 px-1 text-sm font-medium ${pathname?.startsWith('/admin') ? 'border-sky-600 text-sky-600' : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}>
              Admin
            </Link>
          </div>
        </div>
      </nav>
    </>
  );
}
