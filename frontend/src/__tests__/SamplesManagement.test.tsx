import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

  it('renders a 422 validation list as text and keeps the form', async () => {
    const user = userEvent.setup();
    const sample = {
      id: '1',
      name: 'SAMPLE-001',
      status: 'status-id',
      sample_type: 'type-id',
      matrix: 'matrix-id',
      project_id: 'project-id',
      created_at: '2025-01-01T00:00:00Z',
    };
    mockedApiService.getSamples.mockResolvedValue([sample]);
    mockedApiService.getSample.mockResolvedValue(sample);
    mockedApiService.getListEntries.mockResolvedValue([
      { id: 'status-id', name: 'Received' },
      { id: 'type-id', name: 'Blood' },
      { id: 'matrix-id', name: 'Human' },
    ]);
    mockedApiService.getProjects.mockResolvedValue([{ id: 'project-id', name: 'Test Project' }]);
    mockedApiService.getCustomAttributeConfigs.mockResolvedValue({ configs: [] });
    mockedApiService.getSampleJourney.mockResolvedValue({ processes: [] });
    mockedApiService.getAskedFor.mockResolvedValue({ items: [] });
    mockedApiService.updateSample.mockRejectedValue({
      response: {
        data: {
          detail: [
            {
              type: 'value_error',
              loc: ['body', 'received_date'],
              msg: 'Value error, Date cannot be in the future',
              input: '2026-10-19',
              ctx: { error: {} },
            },
          ],
        },
      },
    });

    renderWithProviders(<SamplesManagement />);
    const edit = await screen.findByLabelText('Edit sample SAMPLE-001');
    await user.click(edit);
    expect(await screen.findByText('Edit Sample: SAMPLE-001')).toBeInTheDocument();
    await user.click(await screen.findByRole('button', { name: 'Update sample' }));

    expect(await screen.findAllByText('Date cannot be in the future')).toHaveLength(1);
    expect(screen.getByText('Edit Sample: SAMPLE-001')).toBeInTheDocument();
    expect(screen.queryByText(/\[object Object\]/)).not.toBeInTheDocument();
    expect(screen.queryByText(/received_date:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Value error/)).not.toBeInTheDocument();
  });
});

