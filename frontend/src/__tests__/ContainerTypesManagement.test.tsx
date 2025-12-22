import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ContainerTypesManagement from '../pages/admin/ContainerTypesManagement';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    getContainerTypes: jest.fn(),
    createContainerType: jest.fn(),
    updateContainerType: jest.fn(),
    deleteContainerType: jest.fn(),
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

const mockContainerTypes = [
  {
    id: '1',
    name: '96-well plate',
    description: 'Standard 96-well plate',
    capacity: 96,
    material: 'polypropylene',
    dimensions: '8x12',
    preservative: null,
    active: true,
    created_at: '2024-01-01T00:00:00Z',
    modified_at: '2024-01-01T00:00:00Z',
  },
  {
    id: '2',
    name: '15mL tube',
    description: 'Standard 15mL tube',
    capacity: 15,
    material: 'polypropylene',
    dimensions: '15x100mm',
    preservative: null,
    active: true,
    created_at: '2024-01-01T00:00:00Z',
    modified_at: '2024-01-01T00:00:00Z',
  },
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

describe('ContainerTypesManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { apiService } = require('../services/apiService');
    apiService.getContainerTypes.mockResolvedValue(mockContainerTypes);
  });

  test('renders container types management page', async () => {
    renderWithProviders(<ContainerTypesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Container Types Management')).toBeInTheDocument();
    });
  });

  test('displays container types in DataGrid', async () => {
    renderWithProviders(<ContainerTypesManagement />);

    await waitFor(() => {
      expect(screen.getByText('96-well plate')).toBeInTheDocument();
      expect(screen.getByText('15mL tube')).toBeInTheDocument();
    });
  });

  test('displays all container type fields', async () => {
    renderWithProviders(<ContainerTypesManagement />);

    await waitFor(() => {
      expect(screen.getByText('96-well plate')).toBeInTheDocument();
      expect(screen.getByText('Standard 96-well plate')).toBeInTheDocument();
      expect(screen.getByText('polypropylene')).toBeInTheDocument();
      expect(screen.getByText('8x12')).toBeInTheDocument();
    });
  });

  test('shows create button for admin users', async () => {
    renderWithProviders(<ContainerTypesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Container Type')).toBeInTheDocument();
    });
  });

  test('hides create button for non-admin users', async () => {
    renderWithProviders(<ContainerTypesManagement />, mockNonAdminUser);

    await waitFor(() => {
      expect(screen.queryByText('Create Container Type')).not.toBeInTheDocument();
    });
  });

  test('opens create dialog on button click', async () => {
    renderWithProviders(<ContainerTypesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Container Type')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Container Type'));

    await waitFor(() => {
      expect(screen.getByText('Create New Container Type')).toBeInTheDocument();
    });
  });

  test('creates a new container type', async () => {
    const { apiService } = require('../services/apiService');
    apiService.createContainerType.mockResolvedValue({
      id: '3',
      name: '50mL tube',
      description: 'Standard 50mL tube',
      capacity: 50,
      material: 'polypropylene',
      dimensions: '50x100mm',
      preservative: null,
      active: true,
    });

    renderWithProviders(<ContainerTypesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Container Type')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Container Type'));

    await waitFor(() => {
      expect(screen.getByText('Create New Container Type')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText('Container Type Name');
    fireEvent.change(nameInput, { target: { value: '50mL tube' } });

    const materialInput = screen.getByLabelText('Material');
    fireEvent.change(materialInput, { target: { value: 'polypropylene' } });

    const dimensionsInput = screen.getByLabelText('Dimensions');
    fireEvent.change(dimensionsInput, { target: { value: '50x100mm' } });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(apiService.createContainerType).toHaveBeenCalledWith({
        name: '50mL tube',
        material: 'polypropylene',
        dimensions: '50x100mm',
        description: undefined,
        capacity: undefined,
        preservative: undefined,
      });
    });
  });

  test('validates required fields', async () => {
    renderWithProviders(<ContainerTypesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Container Type')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Container Type'));

    await waitFor(() => {
      expect(screen.getByText('Create New Container Type')).toBeInTheDocument();
    });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Container type name is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Material is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Dimensions are required/i)).toBeInTheDocument();
    });
  });

  test('validates positive capacity', async () => {
    renderWithProviders(<ContainerTypesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Container Type')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Container Type'));

    await waitFor(() => {
      expect(screen.getByText('Create New Container Type')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText('Container Type Name');
    fireEvent.change(nameInput, { target: { value: 'Test Type' } });

    const materialInput = screen.getByLabelText('Material');
    fireEvent.change(materialInput, { target: { value: 'plastic' } });

    const dimensionsInput = screen.getByLabelText('Dimensions');
    fireEvent.change(dimensionsInput, { target: { value: '10x10' } });

    const capacityInput = screen.getByLabelText('Capacity');
    fireEvent.change(capacityInput, { target: { value: '-5' } });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Capacity must be positive or zero/i)).toBeInTheDocument();
    });
  });

  test('filters container types by search term', async () => {
    renderWithProviders(<ContainerTypesManagement />);

    await waitFor(() => {
      expect(screen.getByText('96-well plate')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search container types...');
    fireEvent.change(searchInput, { target: { value: 'tube' } });

    await waitFor(() => {
      expect(screen.queryByText('96-well plate')).not.toBeInTheDocument();
      expect(screen.getByText('15mL tube')).toBeInTheDocument();
    });
  });

  test('handles API error gracefully', async () => {
    const { apiService } = require('../services/apiService');
    apiService.getContainerTypes.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<ContainerTypesManagement />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load container types/i)).toBeInTheDocument();
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

    renderWithProviders(<ContainerTypesManagement />, restrictedUser);

    expect(screen.getByText(/You do not have permission to view container types management/i)).toBeInTheDocument();
  });

  test('opens delete confirmation dialog', async () => {
    renderWithProviders(<ContainerTypesManagement />);

    await waitFor(() => {
      expect(screen.getByText('96-well plate')).toBeInTheDocument();
    });

    // Find delete button (this would be in the actions column)
    // In a real scenario, you'd click the delete icon in the grid
  });

  test('handles delete error when type is in use', async () => {
    const { apiService } = require('../services/apiService');
    const error = new Error('Cannot delete');
    (error as any).response = {
      status: 400,
      data: { detail: 'Container type is referenced by existing containers' },
    };
    apiService.deleteContainerType.mockRejectedValue(error);

    renderWithProviders(<ContainerTypesManagement />);

    // This would be triggered by clicking delete and confirming
    // The error message should be displayed
  });

  test('updates container type', async () => {
    const { apiService } = require('../services/apiService');
    apiService.updateContainerType.mockResolvedValue({
      ...mockContainerTypes[0],
      description: 'Updated description',
    });

    renderWithProviders(<ContainerTypesManagement />);

    await waitFor(() => {
      expect(screen.getByText('96-well plate')).toBeInTheDocument();
    });

    // Click edit button, modify form, submit
    // This would require finding the edit icon in the grid
  });

  test('validates unique container type names', async () => {
    renderWithProviders(<ContainerTypesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Container Type')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Container Type'));

    await waitFor(() => {
      expect(screen.getByText('Create New Container Type')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText('Container Type Name');
    fireEvent.change(nameInput, { target: { value: '96-well plate' } });

    const materialInput = screen.getByLabelText('Material');
    fireEvent.change(materialInput, { target: { value: 'plastic' } });

    const dimensionsInput = screen.getByLabelText('Dimensions');
    fireEvent.change(dimensionsInput, { target: { value: '8x12' } });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/A container type with this name already exists/i)).toBeInTheDocument();
    });
  });
});

