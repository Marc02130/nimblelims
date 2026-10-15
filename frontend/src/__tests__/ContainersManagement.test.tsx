import React from 'react';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ContainerManagement from '../pages/ContainerManagement';
import { apiService } from '../services/apiService';
import { UserContext } from '../contexts/UserContext';

// Mock apiService
jest.mock('../services/apiService');
const mockedApiService = apiService as jest.Mocked<typeof apiService>;

// Mock user context
const mockUser = {
  id: '1',
  username: 'testuser',
  role: 'Lab Manager',
  permissions: ['sample:update'],
};

const mockHasPermission = (permission: string) => {
  return mockUser.permissions.includes(permission);
};

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      <UserContext.Provider
        value={{
          user: mockUser,
          loading: false,
          hasPermission: mockHasPermission,
        } as any}
      >
        {component}
      </UserContext.Provider>
    </BrowserRouter>
  );
};

describe('ContainerManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders container management page', async () => {
    mockedApiService.getContainers.mockResolvedValue([
      {
        id: '1',
        name: 'CONTAINER-001',
        type_id: 'type-id',
        created_at: '2025-01-01T00:00:00Z',
        type: { name: 'Test Tube' },
      },
    ]);

    mockedApiService.getContainerTypes.mockResolvedValue([]);
    mockedApiService.getUnits.mockResolvedValue([]);
    mockedApiService.getSamples.mockResolvedValue([]);

    renderWithProviders(<ContainerManagement />);

    await waitFor(() => {
      expect(screen.getByText('Container Management')).toBeInTheDocument();
    });
  });

  it('displays error message when loading fails', async () => {
    mockedApiService.getContainers.mockRejectedValue(new Error('Failed to load'));

    renderWithProviders(<ContainerManagement />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load/i)).toBeInTheDocument();
    });
  });

  it('opens edit dialog when edit button is clicked', async () => {
    const containerData = {
      id: '1',
      name: 'CONTAINER-001',
      type_id: 'type-id',
      created_at: '2025-01-01T00:00:00Z',
      type: { name: 'Test Tube' },
    };

    mockedApiService.getContainers.mockResolvedValue([containerData]);
    mockedApiService.getContainer.mockResolvedValue(containerData);
    mockedApiService.getContainerTypes.mockResolvedValue([
      { id: 'type-id', name: 'Test Tube' },
    ]);
    mockedApiService.getUnits.mockResolvedValue([]);
    mockedApiService.getSamples.mockResolvedValue([]);

    renderWithProviders(<ContainerManagement />);

    await waitFor(() => {
      expect(screen.getByText('Container Management')).toBeInTheDocument();
    });

    // Find and click edit button (the grid renders once loading finishes)
    const editButtons = await screen.findAllByLabelText(/Edit container CONTAINER-001/i);
    fireEvent.click(editButtons[0]);

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('Edit Container: CONTAINER-001')).toBeInTheDocument();
  });

  it('renders DataGrid with correct columns', async () => {
    mockedApiService.getContainers.mockResolvedValue([
      {
        id: '1',
        name: 'CONTAINER-001',
        type_id: 'type-id',
        created_at: '2025-01-01T00:00:00Z',
        type: { name: 'Test Tube' },
      },
    ]);

    mockedApiService.getContainerTypes.mockResolvedValue([]);
    mockedApiService.getUnits.mockResolvedValue([]);
    mockedApiService.getSamples.mockResolvedValue([]);

    renderWithProviders(<ContainerManagement />);

    await waitFor(() => {
      expect(screen.getByText('Container Management')).toBeInTheDocument();
    });

    // Verify DataGrid is rendered once loading finishes
    expect(await screen.findByText('CONTAINER-001')).toBeInTheDocument();
    expect(document.querySelector('.MuiDataGrid-root')).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Name' })).toBeInTheDocument();
  });

  it('shows create container button', async () => {
    mockedApiService.getContainers.mockResolvedValue([]);
    mockedApiService.getContainerTypes.mockResolvedValue([]);
    mockedApiService.getUnits.mockResolvedValue([]);
    mockedApiService.getSamples.mockResolvedValue([]);

    renderWithProviders(<ContainerManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Container')).toBeInTheDocument();
    });
  });

  it('handles form mode correctly (create vs edit)', async () => {
    mockedApiService.getContainers.mockResolvedValue([]);
    mockedApiService.getContainerTypes.mockResolvedValue([]);
    mockedApiService.getUnits.mockResolvedValue([]);
    mockedApiService.getSamples.mockResolvedValue([]);

    renderWithProviders(<ContainerManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Container')).toBeInTheDocument();
    });

    // Click create button: the dialog opens in create mode (no "Edit Container:" title)
    fireEvent.click(screen.getByRole('button', { name: 'Create Container' }));

    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('Create Container')).toBeInTheDocument();
    expect(within(dialog).queryByText(/Edit Container:/)).not.toBeInTheDocument();
  });
});

