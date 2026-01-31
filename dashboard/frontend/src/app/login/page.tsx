"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const DEV_LOGIN_HELPER = process.env.NEXT_PUBLIC_DEV_LOGIN_HELPER === 'true';

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoading, error, clearError } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    clearError();

    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      // Error is handled by the store
    }
  };

  const handleDevLogin = async () => {
    setEmail("avi@omni.com");
    setPassword("avi123");
    clearError();
    
    try {
      await login("avi@omni.com", "avi123");
      router.push("/dashboard");
    } catch (err) {
      // Error is handled by the store
    }
  };

  return (
    <div className="min-h-screen flex bg-white">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 items-center justify-center p-12" style={{background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'}}>
        <div className="max-w-md text-white">
          <h1 className="text-5xl font-bold mb-6">Omni2 Admin</h1>
          <p className="text-xl opacity-90 mb-8">
            Centralized MCP Hub Management Platform
          </p>
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-white bg-opacity-20 flex items-center justify-center text-2xl">🚀</div>
              <div>
                <h3 className="font-semibold">Real-time Monitoring</h3>
                <p className="text-sm opacity-75">Track all MCP servers live</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-white bg-opacity-20 flex items-center justify-center text-2xl">📊</div>
              <div>
                <h3 className="font-semibold">Analytics Dashboard</h3>
                <p className="text-sm opacity-75">Comprehensive insights</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-white bg-opacity-20 flex items-center justify-center text-2xl">⚡</div>
              <div>
                <h3 className="font-semibold">Performance Optimization</h3>
                <p className="text-sm opacity-75">Keep your MCPs running fast</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-white">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-2xl shadow-lg p-8 space-y-6 border border-gray-200">
            {/* Mobile Logo */}
            <div className="lg:hidden text-center mb-6">
              <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-indigo-600 bg-clip-text text-transparent">
                Omni2 Admin
              </h1>
            </div>

            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Welcome back</h2>
              <p className="text-gray-600">Sign in to continue to your dashboard</p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-4 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
                <div className="flex items-center gap-2">
                  <span>⚠️</span>
                  <span>{error}</span>
                </div>
              </div>
            )}

            {/* Login Form */}
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-semibold text-gray-700">
                  Email Address
                </label>
                <Input
                  id="email"
                  type="email"
                  placeholder="admin@omni2.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-semibold text-gray-700">
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>

              <Button
                type="submit"
                className="w-full"
                disabled={isLoading}
                style={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  padding: '12px',
                  fontSize: '16px',
                  fontWeight: '600',
                  borderRadius: '8px',
                  border: 'none',
                  cursor: isLoading ? 'not-allowed' : 'pointer',
                  opacity: isLoading ? 0.7 : 1
                }}
              >
                {isLoading ? "Signing in..." : "Sign in"}
              </Button>

              {DEV_LOGIN_HELPER && (
                <Button
                  type="button"
                  onClick={handleDevLogin}
                  className="w-full"
                  disabled={isLoading}
                  style={{
                    background: '#10b981',
                    color: 'white',
                    padding: '12px',
                    fontSize: '16px',
                    fontWeight: '600',
                    borderRadius: '8px',
                    border: 'none',
                    cursor: isLoading ? 'not-allowed' : 'pointer',
                    opacity: isLoading ? 0.7 : 1
                  }}
                >
                  🚀 Dev Login (avi@omni.com)
                </Button>
              )}
            </form>

            {/* Footer */}
            <div className="text-center text-sm text-gray-500 pt-4 border-t">
              <p>Demo: admin@omni2.com / admin123</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
