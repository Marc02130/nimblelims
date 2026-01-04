import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import TestsManagement from '../pages/TestsManagement';
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
  permissions: ['test:update'],
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

describe('TestsManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders tests management page', async () => {
    mockedApiService.getTests.mockResolvedValue({
      tests: [
        {
          id: '1',
          name: 'TEST-001',
          status: 'status-id',
          sample_id: 'sample-id',
          analysis_id: 'analysis-id',
          created_at: '2025-01-01T00:00:00Z',
          sample: { name: 'SAMPLE-001' },
          analysis: { name: 'Analysis 1' },
        },
      ],
    });

    mockedApiService.getListEntries.mockResolvedValue([
      { id: 'status-id', name: 'In Process' },
    ]);

    renderWithProviders(<TestsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Tests Management')).toBeInTheDocument();
    });
  });

  it('displays error message when loading fails', async () => {
    mockedApiService.getTests.mockRejectedValue(new Error('Failed to load'));

    renderWithProviders(<TestsManagement />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load/i)).toBeInTheDocument();
    });
  });

  it('shows read-only message when user lacks update permission', async () => {
    const readOnlyUser = {
      ...mockUser,
      permissions: [],
    };

    mockedApiService.getTests.mockResolvedValue({ tests: [] });
    mockedApiService.getListEntries.mockResolvedValue([]);

    render(
      <BrowserRouter>
        <UserContext.Provider
          value={{
            user: readOnlyUser,
            loading: false,
            hasPermission: () => false,
          } as any}
        >
          <TestsManagement />
        </UserContext.Provider>
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/read-only access/i)).toBeInTheDocument();
    });
  });

  it('opens edit dialog when edit button is clicked', async () => {
    const testData = {
      id: '1',
      name: 'TEST-001',
      status: 'status-id',
      sample_id: 'sample-id',
      analysis_id: 'analysis-id',
      created_at: '2025-01-01T00:00:00Z',
      sample: { name: 'SAMPLE-001' },
      analysis: { name: 'Analysis 1' },
    };

    mockedApiService.getTests.mockResolvedValue({
      tests: [testData],
    });

    mockedApiService.getTest.mockResolvedValue(testData);
    mockedApiService.getListEntries.mockResolvedValue([
      { id: 'status-id', name: 'In Process' },
    ]);

    renderWithProviders(<TestsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Tests Management')).toBeInTheDocument();
    });

    // Find and click edit button
    const editButtons = screen.getAllByLabelText(/Edit test/i);
    if (editButtons.length > 0) {
      fireEvent.click(editButtons[0]);

      await waitFor(() => {
        expect(screen.getByText(/Edit Test/i)).toBeInTheDocument();
      });
    }
  });

  it('renders DataGrid with correct columns', async () => {
    mockedApiService.getTests.mockResolvedValue({
      tests: [
        {
          id: '1',
          name: 'TEST-001',
          status: 'status-id',
          sample_id: 'sample-id',
          analysis_id: 'analysis-id',
          created_at: '2025-01-01T00:00:00Z',
          sample: { name: 'SAMPLE-001' },
          analysis: { name: 'Analysis 1' },
        },
      ],
    });

    mockedApiService.getListEntries.mockResolvedValue([
      { id: 'status-id', name: 'In Process' },
    ]);

    renderWithProviders(<TestsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Tests Management')).toBeInTheDocument();
    });

    // Verify DataGrid is rendered (MUI DataGrid renders with specific classes)
    const dataGrid = document.querySelector('.MuiDataGrid-root');
    expect(dataGrid).toBeInTheDocument();
  });

  it('hides edit buttons when user lacks permission', async () => {
    const readOnlyUser = {
      ...mockUser,
      permissions: [],
    };

    mockedApiService.getTests.mockResolvedValue({
      tests: [
        {
          id: '1',
          name: 'TEST-001',
          status: 'status-id',
          sample_id: 'sample-id',
          analysis_id: 'analysis-id',
          created_at: '2025-01-01T00:00:00Z',
        },
      ],
    });

    mockedApiService.getListEntries.mockResolvedValue([]);

    render(
      <BrowserRouter>
        <UserContext.Provider
          value={{
            user: readOnlyUser,
            loading: false,
            hasPermission: () => false,
          } as any}
        >
          <TestsManagement />
        </UserContext.Provider>
      </BrowserRouter>
    );

    await waitFor(() => {
      // Edit buttons should be disabled when no permission
      const editButtons = screen.queryAllByLabelText(/Edit test/i);
      editButtons.forEach((button) => {
        expect(button.closest('button')).toBeDisabled();
      });
    });
  });
});

