import React, { createContext, useState, useContext } from 'react';
import type { ReactNode } from 'react';

export interface User {
  id: string;
  username: string;
  role: string;
  name: string;
}

interface AuthContextType {
  user: User | null;
  login: (username: string, pass: string) => boolean;
  logout: () => void;
  register: (username: string, pass: string, name: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);

  const login = (username: string, pass: string) => {
    // Mock login logic
    if (username && pass) {
      setUser({
        id: '1',
        username: username,
        name: username === 'admin' ? 'Israel Israeli' : username,
        role: username === 'admin' ? 'Security Admin' : 'Guard'
      });
      return true;
    }
    return false;
  };

  const logout = () => {
    setUser(null);
  };

  const register = (username: string, pass: string, name: string) => {
    // Mock register logic
    if (username && pass && name) {
      setUser({
        id: 'new_id',
        username,
        name,
        role: 'Guard'
      });
      return true;
    }
    return false;
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, register }}>
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
