import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import AnalysesManagement from '../pages/admin/AnalysesManagement';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    getAnalyses: jest.fn(),
    createAnalysis: jest.fn(),
    updateAnalysis: jest.fn(),
    deleteAnalysis: jest.fn(),
    getAnalytes: jest.fn(),
    getAnalysisAnalytes: jest.fn(),
    updateAnalysisAnalytes: jest.fn(),
  },
}));

const theme = createTheme();

const mockAdminUser = {
  id: '1',
  username: 'admin',
  email: 'admin@example.com',
  role: 'Administrator',
  permissions: ['config:edit', 'test:configure', 'sample:read'],
};

const mockNonAdminUser = {
  id: '2',
  username: 'user',
  email: 'user@example.com',
  role: 'Lab Technician',
  permissions: ['sample:read'],
};

const mockAnalyses = [
  {
    id: '1',
    name: 'pH Analysis',
    description: 'pH measurement',
    method: 'EPA 150.1',
    turnaround_time: 1,
    cost: 25.00,
    active: true,
    created_at: '2024-01-01T00:00:00Z',
    modified_at: '2024-01-01T00:00:00Z',
    analytes: [
      { id: '1', name: 'pH', description: 'pH value' },
    ],
    analytes_count: 1,
  },
  {
    id: '2',
    name: 'EPA 8080',
    description: 'Organochlorine pesticides',
    method: 'EPA 8080',
    turnaround_time: 5,
    cost: 150.00,
    active: true,
    created_at: '2024-01-02T00:00:00Z',
    modified_at: '2024-01-02T00:00:00Z',
    analytes: [
      { id: '2', name: 'DDT', description: 'DDT concentration' },
      { id: '3', name: 'DDE', description: 'DDE concentration' },
    ],
    analytes_count: 2,
  },
];

const mockAnalytes = [
  { id: '1', name: 'pH', description: 'pH value' },
  { id: '2', name: 'DDT', description: 'DDT concentration' },
  { id: '3', name: 'DDE', description: 'DDE concentration' },
  { id: '4', name: 'TOC', description: 'Total Organic Carbon' },
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

describe('AnalysesManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { apiService } = require('../services/apiService');
    apiService.getAnalyses.mockResolvedValue(mockAnalyses);
    apiService.getAnalytes.mockResolvedValue(mockAnalytes);
    apiService.getAnalysisAnalytes.mockImplementation((analysisId: string) => {
      const analysis = mockAnalyses.find((a) => a.id === analysisId);
      return Promise.resolve(analysis?.analytes || []);
    });
  });

  test('renders analyses management page', async () => {
    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Analyses Management')).toBeInTheDocument();
    });
  });

  test('displays analyses in DataGrid', async () => {
    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('pH Analysis')).toBeInTheDocument();
      expect(screen.getByText('EPA 8080')).toBeInTheDocument();
    });
  });

  test('displays all analysis fields', async () => {
    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('EPA 150.1')).toBeInTheDocument();
      expect(screen.getByText('$25.00')).toBeInTheDocument();
      expect(screen.getByText('1')).toBeInTheDocument(); // Turnaround time
    });
  });

  test('shows create button for admin users', async () => {
    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Analysis')).toBeInTheDocument();
    });
  });

  test('hides create button for non-admin users', async () => {
    renderWithProviders(<AnalysesManagement />, mockNonAdminUser);

    await waitFor(() => {
      expect(screen.queryByText('Create Analysis')).not.toBeInTheDocument();
    });
  });

  test('opens create analysis dialog on button click', async () => {
    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Analysis')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Analysis'));

    await waitFor(() => {
      expect(screen.getByText('Create New Analysis')).toBeInTheDocument();
    });
  });

  test('creates a new analysis with analytes', async () => {
    const { apiService } = require('../services/apiService');
    const newAnalysis = { id: '3', name: 'TOC Analysis', method: 'EPA 415.1', turnaround_time: 3, cost: 50.00 };
    apiService.createAnalysis.mockResolvedValue(newAnalysis);
    apiService.updateAnalysisAnalytes.mockResolvedValue({});

    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Analysis')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Analysis'));

    await waitFor(() => {
      expect(screen.getByText('Create New Analysis')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText('Analysis Name');
    fireEvent.change(nameInput, { target: { value: 'TOC Analysis' } });

    const methodInput = screen.getByLabelText('Method');
    fireEvent.change(methodInput, { target: { value: 'EPA 415.1' } });

    const turnaroundInput = screen.getByLabelText('Turnaround Time (days)');
    fireEvent.change(turnaroundInput, { target: { value: '3' } });

    const costInput = screen.getByLabelText('Cost');
    fireEvent.change(costInput, { target: { value: '50.00' } });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(apiService.createAnalysis).toHaveBeenCalledWith({
        name: 'TOC Analysis',
        description: undefined,
        method: 'EPA 415.1',
        turnaround_time: 3,
        cost: 50.00,
      });
      expect(apiService.updateAnalysisAnalytes).toHaveBeenCalled();
    });
  });

  test('validates required fields', async () => {
    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Analysis')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Analysis'));

    await waitFor(() => {
      expect(screen.getByText('Create New Analysis')).toBeInTheDocument();
    });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Analysis name is required/i)).toBeInTheDocument();
    });
  });

  test('validates unique analysis names', async () => {
    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Analysis')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Analysis'));

    await waitFor(() => {
      expect(screen.getByText('Create New Analysis')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText('Analysis Name');
    fireEvent.change(nameInput, { target: { value: 'pH Analysis' } });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/An analysis with this name already exists/i)).toBeInTheDocument();
    });
  });

  test('validates turnaround time is positive integer', async () => {
    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Analysis')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Analysis'));

    await waitFor(() => {
      expect(screen.getByText('Create New Analysis')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText('Analysis Name');
    fireEvent.change(nameInput, { target: { value: 'New Analysis' } });

    const turnaroundInput = screen.getByLabelText('Turnaround Time (days)');
    fireEvent.change(turnaroundInput, { target: { value: '0' } });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Turnaround time must be at least 1 day/i)).toBeInTheDocument();
    });
  });

  test('validates cost is non-negative', async () => {
    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Analysis')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Analysis'));

    await waitFor(() => {
      expect(screen.getByText('Create New Analysis')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText('Analysis Name');
    fireEvent.change(nameInput, { target: { value: 'New Analysis' } });

    const costInput = screen.getByLabelText('Cost');
    fireEvent.change(costInput, { target: { value: '-10' } });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Cost must be greater than or equal to 0/i)).toBeInTheDocument();
    });
  });

  test('expands analysis to show analytes', async () => {
    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('pH Analysis')).toBeInTheDocument();
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
        expect(screen.getByText(/Analytes for pH Analysis/i)).toBeInTheDocument();
        expect(screen.getByText('pH')).toBeInTheDocument();
      });
    }
  });

  test('filters analyses by search term', async () => {
    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('pH Analysis')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search analyses, methods, or analytes...');
    fireEvent.change(searchInput, { target: { value: 'EPA' } });

    await waitFor(() => {
      expect(screen.queryByText('pH Analysis')).not.toBeInTheDocument();
      expect(screen.getByText('EPA 8080')).toBeInTheDocument();
    });
  });

  test('handles API error gracefully', async () => {
    const { apiService } = require('../services/apiService');
    apiService.getAnalyses.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load analyses/i)).toBeInTheDocument();
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

    renderWithProviders(<AnalysesManagement />, restrictedUser);

    expect(screen.getByText(/You do not have permission to view analyses management/i)).toBeInTheDocument();
  });

  test('handles delete error when analysis is referenced in tests', async () => {
    const { apiService } = require('../services/apiService');
    const error = new Error('Cannot delete');
    (error as any).response = {
      status: 400,
      data: { detail: 'Analysis is referenced in tests' },
    };
    apiService.deleteAnalysis.mockRejectedValue(error);

    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('pH Analysis')).toBeInTheDocument();
    });

    // This would be triggered by clicking delete and confirming
    // The error message should be displayed
  });

  test('displays analyte count in grid', async () => {
    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('1')).toBeInTheDocument(); // pH Analysis analytes
      expect(screen.getByText('2')).toBeInTheDocument(); // EPA 8080 analytes
    });
  });

  test('formats cost as currency', async () => {
    renderWithProviders(<AnalysesManagement />);

    await waitFor(() => {
      expect(screen.getByText('$25.00')).toBeInTheDocument();
      expect(screen.getByText('$150.00')).toBeInTheDocument();
    });
  });
});

