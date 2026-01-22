import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiService } from '../services/apiService';

export interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  client_id?: string;
  permissions: string[];
}

// System client ID constant (matches backend)
const SYSTEM_CLIENT_ID = '00000000-0000-0000-0000-000000000001';

interface UserContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
  isSystemClient: () => boolean;
  isAdmin: () => boolean;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const useUser = () => {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
};

interface UserProviderProps {
  children: ReactNode;
}

export const UserProvider: React.FC<UserProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      apiService.setAuthToken(token);
      // Verify token and get user info
      apiService.getCurrentUser()
        .then((userData) => {
          setUser({
            id: userData.id,
            username: userData.username,
            email: userData.email,
            role: userData.role,
            permissions: userData.permissions,
            client_id: userData.client_id,
          });
        })
        .catch(() => {
          localStorage.removeItem('token');
          apiService.setAuthToken(null);
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (username: string, password: string) => {
    try {
      const response = await apiService.login(username, password);
      const { access_token, user_id, username: username_resp, email, role, permissions } = response;
      
      if (!access_token) {
        throw new Error('No access token received from server');
      }
      
      localStorage.setItem('token', access_token);
      apiService.setAuthToken(access_token);
      
      // Fetch full user data including client_id
      const userData = await apiService.getCurrentUser();
      setUser({
        id: userData.id,
        username: userData.username,
        email: userData.email,
        role: userData.role,
        permissions: userData.permissions,
        client_id: userData.client_id,
      });
    } catch (error: any) {
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    apiService.setAuthToken(null);
    setUser(null);
  };

  const hasPermission = (permission: string): boolean => {
    if (!user) return false;
    return user.permissions.includes(permission) || user.role === 'Administrator';
  };

  const isSystemClient = (): boolean => {
    if (!user) return false;
    return user.client_id === SYSTEM_CLIENT_ID;
  };

  const isAdmin = (): boolean => {
    if (!user) return false;
    return user.role === 'Administrator';
  };

  const value: UserContextType = {
    user,
    loading,
    login,
    logout,
    hasPermission,
    isSystemClient,
    isAdmin,
  };

  return (
    <UserContext.Provider value={value}>
      {children}
    </UserContext.Provider>
  );
};
