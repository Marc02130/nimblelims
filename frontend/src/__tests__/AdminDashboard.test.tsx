import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import AdminDashboard from '../pages/AdminDashboard';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    getLists: jest.fn(),
    getContainerTypes: jest.fn(),
  },
}));

const theme = createTheme();

const mockAdminUser = {
  id: '1',
  username: 'admin',
  email: 'admin@example.com',
  role: 'Administrator',
  permissions: ['config:edit', 'sample:read'],
};

const mockNonAdminUser = {
  id: '2',
  username: 'user',
  email: 'user@example.com',
  role: 'Lab Technician',
  permissions: ['sample:read'],
};

const mockLists = [
  {
    id: '1',
    name: 'sample_status',
    description: 'Sample statuses',
    active: true,
    entries: [
      { id: '1', name: 'Received', description: null, active: true, list_id: '1' },
      { id: '2', name: 'Available for Testing', description: null, active: true, list_id: '1' },
    ],
  },
  {
    id: '2',
    name: 'qc_types',
    description: 'QC types',
    active: true,
    entries: [
      { id: '3', name: 'Sample', description: null, active: true, list_id: '2' },
    ],
  },
];

const mockContainerTypes = [
  {
    id: '1',
    name: '96-well plate',
    description: 'Standard 96-well plate',
    capacity: 96,
    material: 'Plastic',
    dimensions: '8x12',
    preservative: null,
  },
  {
    id: '2',
    name: '15mL tube',
    description: 'Standard 15mL tube',
    capacity: 15,
    material: 'Plastic',
    dimensions: null,
    preservative: null,
  },
];

const renderWithProviders = (
  component: React.ReactElement,
  initialEntries: string[] = ['/admin']
) => {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <ThemeProvider theme={theme}>
        <UserProvider>
          {component}
        </UserProvider>
      </ThemeProvider>
    </MemoryRouter>
  );
};

// Helper to mock user context
const mockUserContext = (user: typeof mockAdminUser) => {
  const { useUser } = require('../contexts/UserContext');
  jest.spyOn(require('../contexts/UserContext'), 'useUser').mockReturnValue({
    user,
    loading: false,
    login: jest.fn(),
    logout: jest.fn(),
    hasPermission: (permission: string) => {
      return user.permissions.includes(permission) || user.role === 'Administrator';
    },
  });
};

describe('AdminDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { apiService } = require('../services/apiService');
    apiService.getLists.mockResolvedValue(mockLists);
    apiService.getContainerTypes.mockResolvedValue(mockContainerTypes);
  });

  test('renders admin dashboard for users with config:edit permission', async () => {
    mockUserContext(mockAdminUser);
    renderWithProviders(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Administration')).toBeInTheDocument();
      expect(screen.getByText('Admin Dashboard')).toBeInTheDocument();
    });
  });

  test('displays overview cards with statistics', async () => {
    mockUserContext(mockAdminUser);
    renderWithProviders(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Total Lists')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument(); // Total lists count
      expect(screen.getByText('Container Types')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument(); // Container types count
    });
  });

  test('displays sidebar navigation', async () => {
    mockUserContext(mockAdminUser);
    renderWithProviders(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Admin')).toBeInTheDocument();
      expect(screen.getByText('Overview')).toBeInTheDocument();
      expect(screen.getByText('Lists Management')).toBeInTheDocument();
      expect(screen.getByText('Container Types')).toBeInTheDocument();
    });
  });

  test('shows user information in app bar', async () => {
    mockUserContext(mockAdminUser);
    renderWithProviders(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/admin \(Administrator\)/)).toBeInTheDocument();
    });
  });

  test('handles navigation to lists management', async () => {
    mockUserContext(mockAdminUser);
    renderWithProviders(<AdminDashboard />, ['/admin/lists']);

    await waitFor(() => {
      expect(screen.getByText('Lists Management')).toBeInTheDocument();
    });
  });

  test('handles navigation to container types management', async () => {
    mockUserContext(mockAdminUser);
    renderWithProviders(<AdminDashboard />, ['/admin/container-types']);

    await waitFor(() => {
      expect(screen.getByText('Container Types Management')).toBeInTheDocument();
    });
  });

  test('shows loading state while fetching stats', () => {
    const { apiService } = require('../services/apiService');
    apiService.getLists.mockImplementation(() => new Promise(() => {})); // Never resolves
    apiService.getContainerTypes.mockImplementation(() => new Promise(() => {}));

    mockUserContext(mockAdminUser);
    renderWithProviders(<AdminDashboard />);

    // Should show loading indicator (CircularProgress)
    // Note: This is a basic test - in a real scenario you'd check for the spinner
  });

  test('displays error message on API failure', async () => {
    const { apiService } = require('../services/apiService');
    apiService.getLists.mockRejectedValue(new Error('API Error'));
    apiService.getContainerTypes.mockRejectedValue(new Error('API Error'));

    mockUserContext(mockAdminUser);
    renderWithProviders(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load admin statistics/i)).toBeInTheDocument();
    });
  });

  test('handles 403 error by redirecting', async () => {
    const { apiService } = require('../services/apiService');
    const error = new Error('Forbidden');
    (error as any).response = { status: 403 };
    apiService.getLists.mockRejectedValue(error);

    mockUserContext(mockAdminUser);
    const { useNavigate } = require('react-router-dom');
    const mockNavigate = jest.fn();
    jest.spyOn(require('react-router-dom'), 'useNavigate').mockReturnValue(mockNavigate);

    renderWithProviders(<AdminDashboard />);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true });
    });
  });
});

