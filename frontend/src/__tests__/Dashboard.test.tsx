import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import Dashboard from '../pages/Dashboard';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  // Real helpers (ApiService.formatError, addClientFilterIfNeeded, types); only the client is mocked.
  ...jest.requireActual('../services/apiService'),
  apiService: {
    // UserProvider probes the cookie session on mount (P4/S10). Plain fn: survives resetMocks.
    getCurrentUser: () => Promise.resolve(mockUser),
    getSamples: jest.fn(),
    getListEntries: jest.fn(),
    getProjects: jest.fn(),
  },
}));

const theme = createTheme();

const mockUser = {
  id: '1',
  username: 'testuser',
  email: 'test@example.com',
  role: 'Lab Technician',
  permissions: ['sample:read'],
};

const mockSamples = [
  {
    id: '1',
    name: 'Sample 1',
    description: 'Test sample 1',
    status: '1',
    sample_type: '1',
    matrix: '1',
    project_id: '1',
    due_date: '2024-12-31',
    received_date: '2024-01-01',
    temperature: 25,
    qc_type: null,
    created_at: '2024-01-01T00:00:00Z',
    project: { name: 'Project A' },
    status_info: { name: 'Received' },
    sample_type_info: { name: 'Blood' },
    matrix_info: { name: 'Serum' },
    tests: [],
  },
  {
    id: '2',
    name: 'Sample 2',
    description: 'Test sample 2',
    status: '2',
    sample_type: '2',
    matrix: '2',
    project_id: '2',
    due_date: '2024-12-30',
    received_date: '2024-01-02',
    temperature: 20,
    qc_type: '1',
    created_at: '2024-01-02T00:00:00Z',
    project: { name: 'Project B' },
    status_info: { name: 'Available for Testing' },
    sample_type_info: { name: 'Urine' },
    matrix_info: { name: 'Plasma' },
    tests: [
      { id: '1', status: 'In Process', analysis: { name: 'Analysis A' } },
    ],
  },
];

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <UserProvider>
          {component}
        </UserProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
};

describe('Dashboard', () => {
  beforeEach(() => {
    // Mock API responses
    const { apiService } = require('../services/apiService');
    apiService.getSamples.mockResolvedValue(mockSamples);
    apiService.getListEntries.mockResolvedValue([
      { id: '1', name: 'Received' },
      { id: '2', name: 'Available for Testing' },
    ]);
    apiService.getProjects.mockResolvedValue([
      { id: '1', name: 'Project A' },
      { id: '2', name: 'Project B' },
    ]);
  });

  test('renders dashboard with welcome message', async () => {
    renderWithProviders(<Dashboard />);
    
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(await screen.findByText(/Welcome, testuser/)).toBeInTheDocument();
  });

  test('displays summary cards', async () => {
    renderWithProviders(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Total Samples')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument(); // Total samples
      expect(screen.getByText('In Progress')).toBeInTheDocument();
      expect(screen.getByText('Completed')).toBeInTheDocument();
      expect(screen.getByText('Total Tests')).toBeInTheDocument();
    });
  });

  test('shows samples in data grid', async () => {
    renderWithProviders(<Dashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('Sample 1')).toBeInTheDocument();
      expect(screen.getByText('Sample 2')).toBeInTheDocument();
      expect(screen.getByText('Blood')).toBeInTheDocument();
      expect(screen.getByText('Urine')).toBeInTheDocument();
    });
  });

  test('filters samples by status', async () => {
    renderWithProviders(<Dashboard />);
    
    await waitFor(() => {
      const statusFilter = screen.getByLabelText('Status');
      fireEvent.mouseDown(statusFilter);
    });
    
    await waitFor(() => {
      // Options are in the open listbox (the grid's status chips use the same names).
      const options = within(screen.getByRole('listbox'));
      expect(options.getByText('All Statuses')).toBeInTheDocument();
      expect(options.getByText('Received')).toBeInTheDocument();
      expect(options.getByText('Available for Testing')).toBeInTheDocument();
    });
  });

  test('filters samples by project', async () => {
    renderWithProviders(<Dashboard />);
    
    await waitFor(() => {
      const projectFilter = screen.getByLabelText('Project');
      fireEvent.mouseDown(projectFilter);
    });
    
    await waitFor(() => {
      const options = within(screen.getByRole('listbox'));
      expect(options.getByText('All Projects')).toBeInTheDocument();
      expect(options.getByText('Project A')).toBeInTheDocument();
      expect(options.getByText('Project B')).toBeInTheDocument();
    });
  });

  test('displays status chips with correct colors', async () => {
    renderWithProviders(<Dashboard />);
    
    await waitFor(() => {
      const chip = (name: string) =>
        screen.getAllByText(name).map((el) => el.closest('.MuiChip-root')).find(Boolean);
      const received = chip('Received');
      const available = chip('Available for Testing');
      expect(received).toHaveClass('MuiChip-colorDefault');
      expect(available).toHaveClass('MuiChip-colorPrimary');
    });
  });

  test('shows type, matrix and project names when samples carry only ids', async () => {
    // The samples API returns list-entry ids, not *_info objects.
    const { apiService } = require('../services/apiService');
    apiService.getSamples.mockResolvedValue([
      {
        ...mockSamples[0],
        sample_type_info: undefined,
        matrix_info: undefined,
        project: undefined,
        sample_type: 'st-1',
        matrix: 'mx-1',
        project_id: '1',
      },
    ]);
    apiService.getListEntries.mockImplementation((name: string) =>
      Promise.resolve(
        ({
          sample_status: [{ id: '1', name: 'Received' }],
          sample_types: [{ id: 'st-1', name: 'Whole Blood' }],
          matrix_types: [{ id: 'mx-1', name: 'EDTA Plasma' }],
          qc_types: [],
        } as Record<string, any[]>)[name] || []
      )
    );

    renderWithProviders(<Dashboard />);

    expect(await screen.findByText('Whole Blood')).toBeInTheDocument();
    expect(screen.getByText('EDTA Plasma')).toBeInTheDocument();
    expect(screen.getAllByText('Project A').length).toBeGreaterThan(0);
    expect(screen.queryByText('Unknown')).not.toBeInTheDocument();
  });
});
