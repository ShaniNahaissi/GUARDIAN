import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';

import { isBackendEnabled } from '../services/apiBase';
import {
  fetchMe,
  loginRequest,
  registerRequest,
  roleCanWriteCameras,
  setStoredAccessToken,
  getStoredAccessToken,
  type AppRole,
  type AuthUser,
} from '../services/authApi';

export interface User {
  id: string;
  username: string;
  role: AppRole;
  name: string;
  roleLabel: string;
}

const ROLE_LABELS: Record<AppRole, string> = {
  admin: 'Administrator',
  operator: 'Operator',
  viewer: 'Viewer',
};

function normalizeRole(role: string): AppRole {
  if (role === 'admin' || role === 'operator' || role === 'viewer') return role;
  return 'viewer';
}

function toContextUser(u: AuthUser): User {
  const role = normalizeRole(u.role);
  return {
    id: u.id,
    username: u.username,
    role,
    name: u.fullName || u.username,
    roleLabel: ROLE_LABELS[role],
  };
}

interface AuthContextType {
  user: User | null;
  login: (username: string, pass: string) => Promise<boolean>;
  logout: () => void;
  register: (username: string, pass: string, name: string) => Promise<boolean>;
  authError: string | null;
  clearAuthError: () => void;
  canWriteCameras: boolean;
  isAdmin: boolean;
  sessionRestored: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [sessionRestored, setSessionRestored] = useState(!isBackendEnabled());

  const clearAuthError = useCallback(() => setAuthError(null), []);

  useEffect(() => {
    if (!isBackendEnabled()) {
      setSessionRestored(true);
      return;
    }
    const token = getStoredAccessToken();
    if (!token) {
      setSessionRestored(true);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const me = await fetchMe(token);
        if (!cancelled) setUser(toContextUser(me));
      } catch {
        setStoredAccessToken(null);
        if (!cancelled) setUser(null);
      } finally {
        if (!cancelled) setSessionRestored(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = async (username: string, pass: string): Promise<boolean> => {
    setAuthError(null);
    if (!isBackendEnabled()) {
      if (!username || !pass) return false;
      const role: AppRole = username.trim().toLowerCase() === 'admin' ? 'admin' : 'viewer';
      setUser({
        id: '1',
        username,
        name: role === 'admin' ? 'Israel Israeli' : username,
        role,
        roleLabel: ROLE_LABELS[role],
      });
      return true;
    }
    try {
      const res = await loginRequest(username, pass);
      setStoredAccessToken(res.access_token);
      setUser(toContextUser(res.user));
      return true;
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : 'Login failed');
      return false;
    }
  };

  const logout = () => {
    setStoredAccessToken(null);
    setUser(null);
  };

  const register = async (username: string, pass: string, name: string): Promise<boolean> => {
    setAuthError(null);
    if (!isBackendEnabled()) {
      if (!username || !pass || !name) return false;
      setUser({
        id: 'new_id',
        username,
        name,
        role: 'viewer',
        roleLabel: ROLE_LABELS.viewer,
      });
      return true;
    }
    try {
      const res = await registerRequest(username, pass, name);
      setStoredAccessToken(res.access_token);
      setUser(toContextUser(res.user));
      return true;
    } catch (e) {
      setAuthError(e instanceof Error ? e.message : 'Registration failed');
      return false;
    }
  };

  const canWriteCameras = user ? roleCanWriteCameras(user.role) : false;
  const isAdmin = user?.role === 'admin';

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        logout,
        register,
        authError,
        clearAuthError,
        canWriteCameras,
        isAdmin,
        sessionRestored,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
