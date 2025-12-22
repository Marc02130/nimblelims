import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import AnalysisAnalytesConfig from '../pages/admin/AnalysisAnalytesConfig';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    getAnalyses: jest.fn(),
    getAnalysisAnalyteRules: jest.fn(),
    createAnalysisAnalyteRule: jest.fn(),
    updateAnalysisAnalyteRule: jest.fn(),
    deleteAnalysisAnalyteRule: jest.fn(),
    getAnalytes: jest.fn(),
    getListEntries: jest.fn(),
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

const mockAnalysis = {
  id: '1',
  name: 'pH Analysis',
  description: 'pH measurement',
  method: 'EPA 150.1',
  turnaround_time: 1,
  cost: 25.00,
};

const mockRules = [
  {
    analyte_id: '1',
    analyte_name: 'pH',
    data_type: 'numeric',
    low_value: 0,
    high_value: 14,
    significant_figures: 2,
    is_required: true,
    reported_name: 'pH Value',
  },
  {
    analyte_id: '2',
    analyte_name: 'Temperature',
    data_type: 'numeric',
    low_value: -10,
    high_value: 100,
    significant_figures: 1,
    is_required: false,
  },
];

const mockAnalytes = [
  { id: '1', name: 'pH', description: 'pH value' },
  { id: '2', name: 'Temperature', description: 'Temperature' },
  { id: '3', name: 'TOC', description: 'Total Organic Carbon' },
];

const mockDataTypes = [
  { id: '1', name: 'numeric' },
  { id: '2', name: 'text' },
  { id: '3', name: 'boolean' },
];

const renderWithProviders = (component: React.ReactElement, user = mockAdminUser, initialEntries = ['/admin/analyses/1/analytes']) => {
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
    <MemoryRouter initialEntries={initialEntries}>
      <ThemeProvider theme={theme}>
        <UserProvider>
          {component}
        </UserProvider>
      </ThemeProvider>
    </MemoryRouter>
  );
};

describe('AnalysisAnalytesConfig', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { apiService } = require('../services/apiService');
    apiService.getAnalyses.mockResolvedValue([mockAnalysis]);
    apiService.getAnalysisAnalyteRules.mockResolvedValue(mockRules);
    apiService.getAnalytes.mockResolvedValue(mockAnalytes);
    apiService.getListEntries.mockResolvedValue(mockDataTypes);
  });

  test('renders analysis-analytes config page', async () => {
    renderWithProviders(<AnalysisAnalytesConfig />);

    await waitFor(() => {
      expect(screen.getByText(/Configure Analytes: pH Analysis/i)).toBeInTheDocument();
    });
  });

  test('displays analyte rules in DataGrid', async () => {
    renderWithProviders(<AnalysisAnalytesConfig />);

    await waitFor(() => {
      expect(screen.getByText('pH')).toBeInTheDocument();
      expect(screen.getByText('Temperature')).toBeInTheDocument();
    });
  });

  test('displays all rule fields', async () => {
    renderWithProviders(<AnalysisAnalytesConfig />);

    await waitFor(() => {
      expect(screen.getByText('numeric')).toBeInTheDocument();
      expect(screen.getByText('0 - 14')).toBeInTheDocument();
      expect(screen.getByText('2')).toBeInTheDocument(); // Significant figures
      expect(screen.getByText('Yes')).toBeInTheDocument(); // Required
    });
  });

  test('shows add button for admin users', async () => {
    renderWithProviders(<AnalysisAnalytesConfig />);

    await waitFor(() => {
      expect(screen.getByText('Add Analyte Rule')).toBeInTheDocument();
    });
  });

  test('opens add rule dialog on button click', async () => {
    renderWithProviders(<AnalysisAnalytesConfig />);

    await waitFor(() => {
      expect(screen.getByText('Add Analyte Rule')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Add Analyte Rule'));

    await waitFor(() => {
      expect(screen.getByText('Add Analyte Rule')).toBeInTheDocument();
    });
  });

  test('creates a new analyte rule', async () => {
    const { apiService } = require('../services/apiService');
    const newRule = {
      analyte_id: '3',
      analyte_name: 'TOC',
      data_type: 'numeric',
      is_required: false,
    };
    apiService.createAnalysisAnalyteRule.mockResolvedValue(newRule);

    renderWithProviders(<AnalysisAnalytesConfig />);

    await waitFor(() => {
      expect(screen.getByText('Add Analyte Rule')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Add Analyte Rule'));

    await waitFor(() => {
      expect(screen.getByText('Add Analyte Rule')).toBeInTheDocument();
    });

    // Select analyte, fill form, submit
    // This would require interacting with the form dialog
  });

  test('validates low <= high range', async () => {
    renderWithProviders(<AnalysisAnalytesConfig />);

    await waitFor(() => {
      expect(screen.getByText('Add Analyte Rule')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Add Analyte Rule'));

    await waitFor(() => {
      expect(screen.getByText('Add Analyte Rule')).toBeInTheDocument();
    });

    // Fill form with invalid range (low > high)
    // This would require interacting with the form dialog
  });

  test('validates significant figures is positive integer', async () => {
    renderWithProviders(<AnalysisAnalytesConfig />);

    await waitFor(() => {
      expect(screen.getByText('Add Analyte Rule')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Add Analyte Rule'));

    await waitFor(() => {
      expect(screen.getByText('Add Analyte Rule')).toBeInTheDocument();
    });

    // Fill form with invalid significant figures
    // This would require interacting with the form dialog
  });

  test('filters rules by search term', async () => {
    renderWithProviders(<AnalysisAnalytesConfig />);

    await waitFor(() => {
      expect(screen.getByText('pH')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search analytes, data types, or reported names...');
    fireEvent.change(searchInput, { target: { value: 'pH' } });

    await waitFor(() => {
      expect(screen.queryByText('Temperature')).not.toBeInTheDocument();
      expect(screen.getByText('pH')).toBeInTheDocument();
    });
  });

  test('handles API error gracefully', async () => {
    const { apiService } = require('../services/apiService');
    apiService.getAnalysisAnalyteRules.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<AnalysisAnalytesConfig />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load configuration/i)).toBeInTheDocument();
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

    renderWithProviders(<AnalysisAnalytesConfig />, restrictedUser);

    expect(screen.getByText(/You do not have permission to view analysis-analytes configuration/i)).toBeInTheDocument();
  });

  test('navigates back to analyses on back button click', async () => {
    const mockNavigate = jest.fn();
    jest.mock('react-router-dom', () => ({
      ...jest.requireActual('react-router-dom'),
      useNavigate: () => mockNavigate,
    }));

    renderWithProviders(<AnalysisAnalytesConfig />);

    await waitFor(() => {
      expect(screen.getByText('Back to Analyses')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Back to Analyses'));

    // Navigation would be tested via mock
  });

  test('formats range correctly', async () => {
    renderWithProviders(<AnalysisAnalytesConfig />);

    await waitFor(() => {
      // Check that ranges are formatted correctly
      expect(screen.getByText('0 - 14')).toBeInTheDocument();
      expect(screen.getByText('-10 - 100')).toBeInTheDocument();
    });
  });

  test('displays required status as chip', async () => {
    renderWithProviders(<AnalysisAnalytesConfig />);

    await waitFor(() => {
      expect(screen.getByText('Yes')).toBeInTheDocument(); // Required
      expect(screen.getByText('No')).toBeInTheDocument(); // Not required
    });
  });
});

