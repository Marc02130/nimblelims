import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

    // Find and click edit button (the grid renders once loading finishes)
    const editButtons = await screen.findAllByLabelText(/Edit test TEST-001/i);
    fireEvent.click(editButtons[0]);

    expect(await screen.findByText('Edit Test: TEST-001')).toBeInTheDocument();
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

    // Verify DataGrid is rendered once loading finishes
    expect(await screen.findByText('TEST-001')).toBeInTheDocument();
    expect(document.querySelector('.MuiDataGrid-root')).toBeInTheDocument();
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

  it('renders a 422 validation list as text and keeps the form', async () => {
    const user = userEvent.setup();
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
    mockedApiService.getTests.mockResolvedValue({ tests: [testData] });
    mockedApiService.getTest.mockResolvedValue(testData);
    mockedApiService.getListEntries.mockResolvedValue([{ id: 'status-id', name: 'In Process' }]);
    mockedApiService.getCustomAttributeConfigs.mockResolvedValue({ configs: [] });
    mockedApiService.updateTest.mockRejectedValue({
      response: {
        data: {
          detail: [
            {
              type: 'value_error',
              loc: ['body', 'test_date'],
              msg: 'Value error, Date cannot be in the future',
              input: '2026-10-19',
              ctx: { error: {} },
            },
          ],
        },
      },
    });

    renderWithProviders(<TestsManagement />);
    const edit = await screen.findByLabelText('Edit test TEST-001');
    await user.click(edit);
    expect(await screen.findByText('Edit Test: TEST-001')).toBeInTheDocument();
    await user.click(await screen.findByRole('button', { name: 'Update test' }));

    expect((await screen.findAllByText('Date cannot be in the future')).length).toBeGreaterThan(0);
    expect(screen.getByText('Edit Test: TEST-001')).toBeInTheDocument();
    expect(screen.queryByText(/\[object Object\]/)).not.toBeInTheDocument();
    expect(screen.queryByText(/test_date:/)).not.toBeInTheDocument();
  });
});

