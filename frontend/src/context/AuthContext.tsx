import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

// Base API URL (backend FastAPI). If backend runs on a different host/port adjust here.
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

interface AuthState {
  token: string | null;
  role: string | null;
  userId: number | null;
}

interface AuthContextValue extends AuthState {
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('auth_token'));
  const [role, setRole] = useState<string | null>(() => localStorage.getItem('auth_role'));
  const [userId, setUserId] = useState<number | null>(() => {
    const stored = localStorage.getItem('auth_userId');
    return stored ? parseInt(stored, 10) : null;
  });

  useEffect(() => {
    if (token) localStorage.setItem('auth_token', token); else localStorage.removeItem('auth_token');
    if (role) localStorage.setItem('auth_role', role); else localStorage.removeItem('auth_role');
    if (userId) localStorage.setItem('auth_userId', String(userId)); else localStorage.removeItem('auth_userId');
  }, [token, role, userId]);

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const resp = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      if (!resp.ok) {
        let detail = '';
        try { const err = await resp.json(); detail = err.detail || JSON.stringify(err); } catch {}
        console.warn('Login failed', resp.status, detail);
        return false;
      }
      const data = await resp.json();
      setToken(data.access_token);
      setRole(data.role || null);
      setUserId(data.user_id || null);
      return true;
    } catch (e) {
      console.error('Login error', e);
      return false;
    }
  };

  const logout = () => {
    setToken(null);
    setRole(null);
    setUserId(null);
  };

  return (
    <AuthContext.Provider value={{ token, role, userId, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
