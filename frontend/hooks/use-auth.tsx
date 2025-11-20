'use client';

import { useState, useEffect, createContext, useContext, ReactNode } from 'react';
import { User } from '@/types';
import { authApi } from '@/lib/api';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  forgotPassword: (email: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get current user from backend cookie-based auth only
    (async () => {
      try {
        const resp = await authApi.me();
        if (resp.success && resp.data) {
          setUser(resp.data.user);
        }
      } catch (e) {
        // Cookie invalid/expired - user stays null
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  // Listen for unauthorized events (401 responses) from API calls
  useEffect(() => {
    const handleUnauthorized = () => {
      console.log('Unauthorized event received - logging out');
      setUser(null);
    };

    window.addEventListener('auth:unauthorized', handleUnauthorized);
    return () => {
      window.removeEventListener('auth:unauthorized', handleUnauthorized);
    };
  }, []);

  const login = async (email: string, password: string) => {
    const response = await authApi.login({ email, password });
    if (response.success && response.data) {
      setUser(response.data.user);
    } else {
      throw new Error(response.error || 'Login failed');
    }
  };

  const register = async (name: string, email: string, password: string) => {
    const response = await authApi.register({ name, email, password, confirmPassword: password });
    if (!response.success) {
      throw new Error(response.error || 'Registration failed');
    }
  };

  const logout = () => {
    setUser(null);
    // Cookie will be invalidated by backend or expire naturally
  };

  const forgotPassword = async (email: string) => {
    const response = await authApi.forgotPassword(email);
    if (!response.success) {
      throw new Error(response.error || 'Failed to send reset email');
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, forgotPassword }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
