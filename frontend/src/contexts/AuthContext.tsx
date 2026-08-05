import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { getCurrentUser, loginUser, registerUser, logoutUser } from '../services/api';

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  company_name?: string;
  plan?: string;
  organization_id?: string;
  is_verified?: boolean;
}

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string, companyName?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchUser = async () => {
    try {
      const userData = await getCurrentUser();
      setUser(userData);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const login = async (email: string, password: string) => {
    setIsLoading(true);
    try {
      const data = await loginUser({ email, password });
      if (data.user) {
        setUser(data.user);
      } else {
        await fetchUser();
      }
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string, fullName?: string, companyName?: string) => {
    setIsLoading(true);
    try {
      const data = await registerUser({ email, password, full_name: fullName, company_name: companyName });
      if (data.user) {
        setUser(data.user);
      } else {
        await fetchUser();
      }
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await logoutUser();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshUser = async () => {
    await fetchUser();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
