import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import SamplesManagement from '../pages/SamplesManagement';
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
  permissions: ['sample:read', 'sample:update'],
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

describe('SamplesManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders samples management page', async () => {
    mockedApiService.getSamples.mockResolvedValue([
      {
        id: '1',
        name: 'SAMPLE-001',
        status: 'status-id',
        sample_type: 'type-id',
        matrix: 'matrix-id',
        project_id: 'project-id',
        created_at: '2025-01-01T00:00:00Z',
      },
    ]);

    mockedApiService.getListEntries.mockResolvedValue([
      { id: 'status-id', name: 'Received' },
      { id: 'type-id', name: 'Blood' },
      { id: 'matrix-id', name: 'Human' },
    ]);

    mockedApiService.getProjects.mockResolvedValue([
      { id: 'project-id', name: 'Test Project' },
    ]);

    renderWithProviders(<SamplesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Samples Management')).toBeInTheDocument();
    });
  });

  it('displays error message when loading fails', async () => {
    mockedApiService.getSamples.mockRejectedValue(new Error('Failed to load'));

    renderWithProviders(<SamplesManagement />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load/i)).toBeInTheDocument();
    });
  });

  it('shows read-only message when user lacks update permission', async () => {
    const readOnlyUser = {
      ...mockUser,
      permissions: ['sample:read'],
    };

    mockedApiService.getSamples.mockResolvedValue([]);
    mockedApiService.getListEntries.mockResolvedValue([]);
    mockedApiService.getProjects.mockResolvedValue([]);

    render(
      <BrowserRouter>
        <UserContext.Provider
          value={{
            user: readOnlyUser,
            loading: false,
            hasPermission: (perm: string) => readOnlyUser.permissions.includes(perm),
          } as any}
        >
          <SamplesManagement />
        </UserContext.Provider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/read-only access/i)).toBeInTheDocument();
    });
  });
});

