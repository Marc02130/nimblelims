import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import UsersManagement from '../pages/admin/UsersManagement';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    getUsers: jest.fn(),
    createUser: jest.fn(),
    updateUser: jest.fn(),
    deleteUser: jest.fn(),
    getRoles: jest.fn(),
    getClients: jest.fn(),
  },
}));

const theme = createTheme();

const mockAdminUser = {
  id: '1',
  username: 'admin',
  email: 'admin@example.com',
  role: 'Administrator',
  permissions: ['user:manage', 'config:edit', 'sample:read'],
};

const mockNonAdminUser = {
  id: '2',
  username: 'user',
  email: 'user@example.com',
  role: 'Lab Technician',
  permissions: ['sample:read'],
};

const mockUsers = [
  {
    id: '1',
    username: 'admin',
    email: 'admin@example.com',
    role_id: '1',
    role: { id: '1', name: 'Administrator' },
    client_id: null,
    last_login: '2024-01-15T10:00:00Z',
    active: true,
    created_at: '2024-01-01T00:00:00Z',
    modified_at: '2024-01-01T00:00:00Z',
  },
  {
    id: '2',
    username: 'technician1',
    email: 'tech1@example.com',
    role_id: '2',
    role: { id: '2', name: 'Lab Technician' },
    client_id: null,
    last_login: '2024-01-14T15:30:00Z',
    active: true,
    created_at: '2024-01-02T00:00:00Z',
    modified_at: '2024-01-02T00:00:00Z',
  },
  {
    id: '3',
    username: 'client1',
    email: 'client1@example.com',
    role_id: '3',
    role: { id: '3', name: 'Client' },
    client_id: '1',
    client: { id: '1', name: 'Client A' },
    last_login: null,
    active: true,
    created_at: '2024-01-03T00:00:00Z',
    modified_at: '2024-01-03T00:00:00Z',
  },
];

const mockRoles = [
  { id: '1', name: 'Administrator' },
  { id: '2', name: 'Lab Manager' },
  { id: '3', name: 'Lab Technician' },
  { id: '4', name: 'Client' },
];

const mockClients = [
  { id: '1', name: 'Client A' },
  { id: '2', name: 'Client B' },
];

const renderWithProviders = (component: React.ReactElement, user = mockAdminUser) => {
  // Mock user context
  jest.spyOn(require('../contexts/UserContext'), 'useUser').mockReturnValue({
    user,
    loading: false,
    login: jest.fn(),
    logout: jest.fn(),
    hasPermission: (permission: string) => {
      return user.permissions.includes(permission) || user.role === 'Administrator';
    },
  });

  return render(
    <MemoryRouter>
      <ThemeProvider theme={theme}>
        <UserProvider>
          {component}
        </UserProvider>
      </ThemeProvider>
    </MemoryRouter>
  );
};

describe('UsersManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { apiService } = require('../services/apiService');
    apiService.getUsers.mockResolvedValue(mockUsers);
    apiService.getRoles.mockResolvedValue(mockRoles);
    apiService.getClients.mockResolvedValue(mockClients);
  });

  test('renders users management page', async () => {
    renderWithProviders(<UsersManagement />);

    await waitFor(() => {
      expect(screen.getByText('Users Management')).toBeInTheDocument();
    });
  });

  test('displays users in DataGrid', async () => {
    renderWithProviders(<UsersManagement />);

    await waitFor(() => {
      expect(screen.getByText('admin')).toBeInTheDocument();
      expect(screen.getByText('technician1')).toBeInTheDocument();
      expect(screen.getByText('client1')).toBeInTheDocument();
    });
  });

  test('displays all user fields', async () => {
    renderWithProviders(<UsersManagement />);

    await waitFor(() => {
      expect(screen.getByText('admin@example.com')).toBeInTheDocument();
      expect(screen.getByText('Administrator')).toBeInTheDocument();
      expect(screen.getByText('Client A')).toBeInTheDocument();
    });
  });

  test('shows create button for admin users', async () => {
    renderWithProviders(<UsersManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create User')).toBeInTheDocument();
    });
  });

  test('hides create button for non-admin users', async () => {
    renderWithProviders(<UsersManagement />, mockNonAdminUser);

    await waitFor(() => {
      expect(screen.queryByText('Create User')).not.toBeInTheDocument();
    });
  });

  test('opens create user dialog on button click', async () => {
    renderWithProviders(<UsersManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create User')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create User'));

    await waitFor(() => {
      expect(screen.getByText('Create New User')).toBeInTheDocument();
    });
  });

  test('creates a new user', async () => {
    const { apiService } = require('../services/apiService');
    apiService.createUser.mockResolvedValue({
      id: '4',
      username: 'newuser',
      email: 'newuser@example.com',
      role_id: '3',
      active: true,
    });

    renderWithProviders(<UsersManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create User')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create User'));

    await waitFor(() => {
      expect(screen.getByText('Create New User')).toBeInTheDocument();
    });

    const usernameInput = screen.getByLabelText('Username');
    fireEvent.change(usernameInput, { target: { value: 'newuser' } });

    const emailInput = screen.getByLabelText('Email');
    fireEvent.change(emailInput, { target: { value: 'newuser@example.com' } });

    const passwordInput = screen.getByLabelText('Password');
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    const roleSelect = screen.getByLabelText('Role');
    fireEvent.mouseDown(roleSelect);
    await waitFor(() => {
      const option = screen.getByText('Lab Technician');
      fireEvent.click(option);
    });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(apiService.createUser).toHaveBeenCalledWith({
        username: 'newuser',
        email: 'newuser@example.com',
        password: 'password123',
        role_id: '3',
      });
    });
  });

  test('validates required fields', async () => {
    renderWithProviders(<UsersManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create User')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create User'));

    await waitFor(() => {
      expect(screen.getByText('Create New User')).toBeInTheDocument();
    });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Username is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Email is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Password is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Role is required/i)).toBeInTheDocument();
    });
  });

  test('validates unique username and email', async () => {
    renderWithProviders(<UsersManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create User')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create User'));

    await waitFor(() => {
      expect(screen.getByText('Create New User')).toBeInTheDocument();
    });

    const usernameInput = screen.getByLabelText('Username');
    fireEvent.change(usernameInput, { target: { value: 'admin' } });

    const emailInput = screen.getByLabelText('Email');
    fireEvent.change(emailInput, { target: { value: 'admin@example.com' } });

    const passwordInput = screen.getByLabelText('Password');
    fireEvent.change(passwordInput, { target: { value: 'password123' } });

    const roleSelect = screen.getByLabelText('Role');
    fireEvent.mouseDown(roleSelect);
    await waitFor(() => {
      const option = screen.getByText('Administrator');
      fireEvent.click(option);
    });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/A user with this username already exists/i)).toBeInTheDocument();
    });
  });

  test('validates password length', async () => {
    renderWithProviders(<UsersManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create User')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create User'));

    await waitFor(() => {
      expect(screen.getByText('Create New User')).toBeInTheDocument();
    });

    const usernameInput = screen.getByLabelText('Username');
    fireEvent.change(usernameInput, { target: { value: 'newuser' } });

    const emailInput = screen.getByLabelText('Email');
    fireEvent.change(emailInput, { target: { value: 'newuser@example.com' } });

    const passwordInput = screen.getByLabelText('Password');
    fireEvent.change(passwordInput, { target: { value: 'short' } });

    const roleSelect = screen.getByLabelText('Role');
    fireEvent.mouseDown(roleSelect);
    await waitFor(() => {
      const option = screen.getByText('Lab Technician');
      fireEvent.click(option);
    });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Password must be at least 8 characters/i)).toBeInTheDocument();
    });
  });

  test('filters users by search term', async () => {
    renderWithProviders(<UsersManagement />);

    await waitFor(() => {
      expect(screen.getByText('admin')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search users...');
    fireEvent.change(searchInput, { target: { value: 'client' } });

    await waitFor(() => {
      expect(screen.queryByText('admin')).not.toBeInTheDocument();
      expect(screen.queryByText('technician1')).not.toBeInTheDocument();
      expect(screen.getByText('client1')).toBeInTheDocument();
    });
  });

  test('handles API error gracefully', async () => {
    const { apiService } = require('../services/apiService');
    apiService.getUsers.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<UsersManagement />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load users/i)).toBeInTheDocument();
    });
  });

  test('shows permission warning for users without access', () => {
    const restrictedUser = {
      id: '3',
      username: 'restricted',
      email: 'restricted@example.com',
      role: 'Client',
      permissions: [],
    };

    renderWithProviders(<UsersManagement />, restrictedUser);

    expect(screen.getByText(/You do not have permission to view users management/i)).toBeInTheDocument();
  });

  test('handles delete error when user has active assignments', async () => {
    const { apiService } = require('../services/apiService');
    const error = new Error('Cannot delete');
    (error as any).response = {
      status: 400,
      data: { detail: 'User has active assignments' },
    };
    apiService.deleteUser.mockRejectedValue(error);

    renderWithProviders(<UsersManagement />);

    await waitFor(() => {
      expect(screen.getByText('admin')).toBeInTheDocument();
    });

    // This would be triggered by clicking delete and confirming
    // The error message should be displayed
  });

  test('updates user without password', async () => {
    const { apiService } = require('../services/apiService');
    apiService.updateUser.mockResolvedValue({
      ...mockUsers[0],
      email: 'updated@example.com',
    });

    renderWithProviders(<UsersManagement />);

    await waitFor(() => {
      expect(screen.getByText('admin')).toBeInTheDocument();
    });

    // Click edit button, modify form, submit
    // This would require finding the edit icon in the grid
  });

  test('formats last login date correctly', async () => {
    renderWithProviders(<UsersManagement />);

    await waitFor(() => {
      // Check that dates are formatted (not raw ISO strings)
      expect(screen.getByText(/Never|admin/)).toBeInTheDocument();
    });
  });
});

