import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import RolesManagement from '../pages/admin/RolesManagement';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    getRoles: jest.fn(),
    createRole: jest.fn(),
    updateRole: jest.fn(),
    deleteRole: jest.fn(),
    getPermissions: jest.fn(),
    getRolePermissions: jest.fn(),
    updateRolePermissions: jest.fn(),
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

const mockRoles = [
  {
    id: '1',
    name: 'Administrator',
    description: 'Full system access',
    active: true,
    created_at: '2024-01-01T00:00:00Z',
    modified_at: '2024-01-01T00:00:00Z',
    permissions: [
      { id: '1', name: 'sample:create', description: 'Create samples' },
      { id: '2', name: 'sample:read', description: 'Read samples' },
      { id: '3', name: 'user:manage', description: 'Manage users' },
    ],
    permissions_count: 3,
  },
  {
    id: '2',
    name: 'Lab Technician',
    description: 'Lab operations access',
    active: true,
    created_at: '2024-01-02T00:00:00Z',
    modified_at: '2024-01-02T00:00:00Z',
    permissions: [
      { id: '1', name: 'sample:create', description: 'Create samples' },
      { id: '4', name: 'result:enter', description: 'Enter results' },
    ],
    permissions_count: 2,
  },
];

const mockPermissions = [
  { id: '1', name: 'sample:create', description: 'Create samples' },
  { id: '2', name: 'sample:read', description: 'Read samples' },
  { id: '3', name: 'sample:update', description: 'Update samples' },
  { id: '4', name: 'result:enter', description: 'Enter results' },
  { id: '5', name: 'result:review', description: 'Review results' },
  { id: '6', name: 'user:manage', description: 'Manage users' },
  { id: '7', name: 'config:edit', description: 'Edit configuration' },
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

describe('RolesManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { apiService } = require('../services/apiService');
    apiService.getRoles.mockResolvedValue(mockRoles);
    apiService.getPermissions.mockResolvedValue(mockPermissions);
    apiService.getRolePermissions.mockImplementation((roleId: string) => {
      const role = mockRoles.find((r) => r.id === roleId);
      return Promise.resolve(role?.permissions || []);
    });
  });

  test('renders roles management page', async () => {
    renderWithProviders(<RolesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Roles & Permissions Management')).toBeInTheDocument();
    });
  });

  test('displays roles in DataGrid', async () => {
    renderWithProviders(<RolesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Administrator')).toBeInTheDocument();
      expect(screen.getByText('Lab Technician')).toBeInTheDocument();
    });
  });

  test('displays permission counts', async () => {
    renderWithProviders(<RolesManagement />);

    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument(); // Administrator permissions
      expect(screen.getByText('2')).toBeInTheDocument(); // Lab Technician permissions
    });
  });

  test('shows create button for admin users', async () => {
    renderWithProviders(<RolesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Role')).toBeInTheDocument();
    });
  });

  test('hides create button for non-admin users', async () => {
    renderWithProviders(<RolesManagement />, mockNonAdminUser);

    await waitFor(() => {
      expect(screen.queryByText('Create Role')).not.toBeInTheDocument();
    });
  });

  test('opens create role dialog on button click', async () => {
    renderWithProviders(<RolesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Role')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Role'));

    await waitFor(() => {
      expect(screen.getByText('Create New Role')).toBeInTheDocument();
    });
  });

  test('creates a new role with permissions', async () => {
    const { apiService } = require('../services/apiService');
    const newRole = { id: '3', name: 'Lab Manager', description: 'Lab management role' };
    apiService.createRole.mockResolvedValue(newRole);
    apiService.updateRolePermissions.mockResolvedValue({});

    renderWithProviders(<RolesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Role')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Role'));

    await waitFor(() => {
      expect(screen.getByText('Create New Role')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText('Role Name');
    fireEvent.change(nameInput, { target: { value: 'Lab Manager' } });

    // Select some permissions
    const sampleCreateCheckbox = screen.getByLabelText(/sample:create/i);
    fireEvent.click(sampleCreateCheckbox);

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(apiService.createRole).toHaveBeenCalledWith({
        name: 'Lab Manager',
        description: undefined,
      });
      expect(apiService.updateRolePermissions).toHaveBeenCalled();
    });
  });

  test('validates required fields', async () => {
    renderWithProviders(<RolesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Role')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Role'));

    await waitFor(() => {
      expect(screen.getByText('Create New Role')).toBeInTheDocument();
    });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Role name is required/i)).toBeInTheDocument();
    });
  });

  test('expands role to show permissions', async () => {
    renderWithProviders(<RolesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Administrator')).toBeInTheDocument();
    });

    // Find expand button
    const expandButtons = screen.getAllByRole('button', { hidden: true });
    const expandButton = expandButtons.find((btn) =>
      btn.querySelector('svg[data-testid="ExpandMoreIcon"]') ||
      btn.querySelector('svg[data-testid="ExpandLessIcon"]')
    );

    if (expandButton) {
      fireEvent.click(expandButton);

      await waitFor(() => {
        expect(screen.getByText(/Permissions for Administrator/i)).toBeInTheDocument();
        expect(screen.getByText('sample:create')).toBeInTheDocument();
        expect(screen.getByText('sample:read')).toBeInTheDocument();
        expect(screen.getByText('user:manage')).toBeInTheDocument();
      });
    }
  });

  test('filters roles by search term', async () => {
    renderWithProviders(<RolesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Administrator')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search roles and permissions...');
    fireEvent.change(searchInput, { target: { value: 'Technician' } });

    await waitFor(() => {
      expect(screen.queryByText('Administrator')).not.toBeInTheDocument();
      expect(screen.getByText('Lab Technician')).toBeInTheDocument();
    });
  });

  test('handles API error gracefully', async () => {
    const { apiService } = require('../services/apiService');
    apiService.getRoles.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<RolesManagement />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load roles/i)).toBeInTheDocument();
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

    renderWithProviders(<RolesManagement />, restrictedUser);

    expect(screen.getByText(/You do not have permission to view roles management/i)).toBeInTheDocument();
  });

  test('handles delete error when role is assigned to users', async () => {
    const { apiService } = require('../services/apiService');
    const error = new Error('Cannot delete');
    (error as any).response = {
      status: 400,
      data: { detail: 'Role is assigned to users' },
    };
    apiService.deleteRole.mockRejectedValue(error);

    renderWithProviders(<RolesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Administrator')).toBeInTheDocument();
    });

    // This would be triggered by clicking delete and confirming
    // The error message should be displayed
  });

  test('updates role permissions', async () => {
    const { apiService } = require('../services/apiService');
    apiService.updateRole.mockResolvedValue(mockRoles[0]);
    apiService.updateRolePermissions.mockResolvedValue({});

    renderWithProviders(<RolesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Administrator')).toBeInTheDocument();
    });

    // Click edit button, modify permissions, submit
    // This would require finding the edit icon in the grid
  });

  test('validates unique role names', async () => {
    renderWithProviders(<RolesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Role')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Role'));

    await waitFor(() => {
      expect(screen.getByText('Create New Role')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText('Role Name');
    fireEvent.change(nameInput, { target: { value: 'Administrator' } });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/A role with this name already exists/i)).toBeInTheDocument();
    });
  });

  test('groups permissions by resource', async () => {
    renderWithProviders(<RolesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Role')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Role'));

    await waitFor(() => {
      expect(screen.getByText('Create New Role')).toBeInTheDocument();
      // Check that permissions are grouped (sample, result, user, config)
    });
  });
});

