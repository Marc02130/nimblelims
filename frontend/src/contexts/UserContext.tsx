import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiService } from '../services/apiService';

export interface User {
  id: string;
  username: string;
  email: string;
  role: string;
  client_id?: string;
  permissions: string[];
  must_change_password?: boolean;
}

// System client ID constant (matches backend)
const SYSTEM_CLIENT_ID = '00000000-0000-0000-0000-000000000001';

interface UserContextType {
  user: User | null;
  loading: boolean;
  mustChangePassword: boolean;
  login: (username: string, password: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
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

const mapUser = (userData: any, mustChange?: boolean): User => ({
  id: userData.id,
  username: userData.username,
  email: userData.email,
  role: userData.role,
  permissions: userData.permissions,
  client_id: userData.client_id,
  must_change_password:
    mustChange ?? Boolean(userData.must_change_password),
});

export const UserProvider: React.FC<UserProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [mustChangePassword, setMustChangePassword] = useState(false);

  useEffect(() => {
    // P4 / S10: session lives in httpOnly cookie — probe /auth/me with credentials
    try {
      localStorage.removeItem('token');
    } catch {
      /* ignore */
    }

    apiService
      .getCurrentUser()
      .then((userData) => {
        const mapped = mapUser(userData);
        setUser(mapped);
        setMustChangePassword(Boolean(mapped.must_change_password));
      })
      .catch((err: any) => {
        const detail = err?.response?.data?.detail;
        if (detail?.code === 'password_change_required') {
          setMustChangePassword(true);
          setUser({
            id: '',
            username: '',
            email: '',
            role: '',
            permissions: [],
            must_change_password: true,
          });
          return;
        }
        setUser(null);
        setMustChangePassword(false);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const login = async (username: string, password: string) => {
    const response = await apiService.login(username, password);
    const { must_change_password } = response;

    // Cookie is set by Set-Cookie; do not store JWT in localStorage
    if (must_change_password) {
      setMustChangePassword(true);
      setUser({
        id: response.user_id,
        username: response.username,
        email: response.email,
        role: response.role,
        permissions: response.permissions || [],
        must_change_password: true,
      });
      return;
    }

    const userData = await apiService.getCurrentUser();
    const mapped = mapUser(userData, false);
    setUser(mapped);
    setMustChangePassword(false);
  };

  const changePassword = async (currentPassword: string, newPassword: string) => {
    await apiService.changePassword(currentPassword, newPassword);
    const userData = await apiService.getCurrentUser();
    setUser(mapUser(userData, false));
    setMustChangePassword(false);
  };

  const logout = () => {
    void apiService.logout().finally(() => {
      setUser(null);
      setMustChangePassword(false);
    });
  };

  /**
   * UX-only gate for showing/hiding UI. Server RBAC + RLS are AuthZ.
   * Do not treat this as a security boundary.
   */
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
    mustChangePassword,
    login,
    changePassword,
    logout,
    hasPermission,
    isSystemClient,
    isAdmin,
  };

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
};
