"use client";

import { IAMUser } from "@/types/iam";

interface UserDetailsModalProps {
  user: IAMUser;
  onClose: () => void;
}

export default function UserDetailsModal({ user, onClose }: UserDetailsModalProps) {
  return (
    <div 
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 animate-fade-in" 
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div 
        className="bg-white/95 backdrop-blur-xl rounded-3xl p-8 max-w-3xl w-full mx-4 shadow-2xl border border-gray-200/50 animate-slide-up" 
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start mb-8">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl flex items-center justify-center text-white font-bold text-2xl shadow-lg">
              {user.name.charAt(0).toUpperCase()}
            </div>
            <div>
              <h2 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-purple-900 bg-clip-text text-transparent">
                {user.name}
              </h2>
              <p className="text-gray-500 mt-1">@{user.username}</p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="text-gray-400 hover:text-gray-600 hover:bg-gray-100 p-2 rounded-lg transition-all"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-6">
            <div className="bg-gradient-to-br from-purple-50 to-indigo-50 rounded-2xl p-5 border border-purple-100">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <label className="text-sm font-bold text-purple-900 uppercase tracking-wide">Username</label>
              </div>
              <p className="text-gray-900 font-semibold text-lg">{user.username}</p>
            </div>

            <div className="bg-gradient-to-br from-blue-50 to-cyan-50 rounded-2xl p-5 border border-blue-100">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                <label className="text-sm font-bold text-blue-900 uppercase tracking-wide">Email</label>
              </div>
              <p className="text-gray-900 font-semibold text-lg break-all">{user.email}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div className="bg-gradient-to-br from-violet-50 to-purple-50 rounded-2xl p-5 border border-violet-100">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">🎭</span>
                <label className="text-sm font-bold text-violet-900 uppercase tracking-wide">Role</label>
              </div>
              <span className="inline-flex items-center px-4 py-2 bg-gradient-to-r from-purple-500 to-indigo-600 text-white rounded-xl text-base font-bold shadow-md">
                {user.role_name}
              </span>
            </div>

            <div className="bg-gradient-to-br from-emerald-50 to-green-50 rounded-2xl p-5 border border-emerald-100">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">📊</span>
                <label className="text-sm font-bold text-emerald-900 uppercase tracking-wide">Status</label>
              </div>
              <span className={`inline-flex items-center px-4 py-2 rounded-xl text-base font-bold shadow-md ${
                user.active 
                  ? 'bg-gradient-to-r from-green-500 to-emerald-600 text-white' 
                  : 'bg-gradient-to-r from-red-500 to-rose-600 text-white'
              }`}>
                {user.active ? '✅ Active' : '❌ Inactive'}
              </span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-2xl p-5 border border-amber-100">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                <label className="text-sm font-bold text-amber-900 uppercase tracking-wide">Created At</label>
              </div>
              <p className="text-gray-900 font-semibold">{new Date(user.created_at).toLocaleString()}</p>
            </div>

            <div className="bg-gradient-to-br from-teal-50 to-cyan-50 rounded-2xl p-5 border border-teal-100">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-5 h-5 text-teal-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <label className="text-sm font-bold text-teal-900 uppercase tracking-wide">Last Login</label>
              </div>
              <p className="text-gray-900 font-semibold">
                {user.last_login_at ? new Date(user.last_login_at).toLocaleString() : '🚫 Never'}
              </p>
            </div>
          </div>

          <div className="bg-gradient-to-br from-slate-50 to-gray-50 rounded-2xl p-5 border border-slate-200">
            <div className="flex items-center gap-2 mb-2">
              <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
              <label className="text-sm font-bold text-slate-900 uppercase tracking-wide">User ID</label>
            </div>
            <p className="text-gray-900 font-mono font-semibold text-lg">#{user.id}</p>
          </div>
        </div>

        <div className="mt-8 flex justify-end gap-3">
          <button 
            onClick={onClose} 
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white rounded-xl font-semibold shadow-lg transition-all transform hover:scale-105"
          >
            Close
          </button>
        </div>
      </div>

      <style jsx>{`
        @keyframes slide-up {
          from {
            opacity: 0;
            transform: translateY(20px) scale(0.95);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
        .animate-slide-up {
          animation: slide-up 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}
