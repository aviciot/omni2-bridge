import { create } from 'zustand';
import { api } from '@/lib/api';
import { API_CONFIG } from '@/lib/config';
import type { AuthState, TokenResponse, AdminUser } from '@/types/auth';

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,

  login: async (email: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const response = await fetch(`${API_CONFIG.AUTH_SERVICE_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: email, password: password })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
      }

      const data: TokenResponse = await response.json();

      localStorage.setItem('access_token', data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token);
      }

      // Extract user from token payload (JWT contains user info)
      const payload = JSON.parse(atob(data.access_token.split('.')[1]));
      const user: AdminUser = {
        id: parseInt(payload.sub),
        email: payload.username,
        name: payload.name,
        role: payload.role
      };
      
      set({
        user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (error: any) {
      const errorMessage = error.message || 'Login failed';
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: errorMessage,
      });
      throw error;
    }
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({
      user: null,
      isAuthenticated: false,
      error: null,
    });
  },

  fetchUser: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      set({ isAuthenticated: false, user: null, isLoading: false });
      return;
    }

    set({ isLoading: true });
    try {
      // Decode JWT to get user info
      const payload = JSON.parse(atob(token.split('.')[1]));
      const user: AdminUser = {
        id: parseInt(payload.sub),
        email: payload.username,
        name: payload.name,
        role: payload.role
      };
      
      set({
        user,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      console.error('Failed to decode token:', error);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      set({
        user: null,
        isAuthenticated: false,
        isLoading: false,
      });
    }
  },

  clearError: () => set({ error: null }),
}));
