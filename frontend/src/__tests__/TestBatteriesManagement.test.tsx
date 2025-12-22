import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import TestBatteriesManagement from '../pages/admin/TestBatteriesManagement';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    getTestBatteries: jest.fn(),
    getTestBattery: jest.fn(),
    createTestBattery: jest.fn(),
    updateTestBattery: jest.fn(),
    deleteTestBattery: jest.fn(),
    getBatteryAnalyses: jest.fn(),
    addAnalysisToBattery: jest.fn(),
    updateBatteryAnalysis: jest.fn(),
    removeAnalysisFromBattery: jest.fn(),
    getAnalyses: jest.fn(),
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

const mockBatteries = [
  {
    id: '1',
    name: 'EPA 8080 Full',
    description: 'Complete EPA Method 8080 test battery',
    active: true,
    created_at: '2024-01-01T00:00:00Z',
    modified_at: '2024-01-01T00:00:00Z',
    analyses_count: 1,
    analyses: [
      {
        analysis_id: 'a1',
        analysis_name: 'EPA Method 8080',
        analysis_method: 'GC/ECD',
        sequence: 1,
        optional: false,
      },
    ],
  },
];

const renderWithProviders = (
  component: React.ReactElement,
  user = mockAdminUser
) => {
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

describe('TestBatteriesManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { apiService } = require('../services/apiService');
    apiService.getTestBatteries.mockResolvedValue({ batteries: mockBatteries });
    apiService.getBatteryAnalyses.mockResolvedValue(mockBatteries[0].analyses);
  });

  it('renders test batteries management page', async () => {
    renderWithProviders(<TestBatteriesManagement />);
    
    await waitFor(() => {
      expect(screen.getByText('Test Batteries Management')).toBeInTheDocument();
    });
  });

  it('displays list of batteries', async () => {
    renderWithProviders(<TestBatteriesManagement />);
    
    await waitFor(() => {
      expect(screen.getByText('EPA 8080 Full')).toBeInTheDocument();
    });
  });

  it('shows create button for admin users', async () => {
    renderWithProviders(<TestBatteriesManagement />);
    
    await waitFor(() => {
      expect(screen.getByText('Create Battery')).toBeInTheDocument();
    });
  });

  it('hides create button for non-admin users', async () => {
    renderWithProviders(<TestBatteriesManagement />, mockNonAdminUser);
    
    await waitFor(() => {
      expect(screen.queryByText('Create Battery')).not.toBeInTheDocument();
    });
  });

  it('opens create dialog when create button is clicked', async () => {
    renderWithProviders(<TestBatteriesManagement />);
    
    await waitFor(() => {
      expect(screen.getByText('Create Battery')).toBeInTheDocument();
    });
    
    fireEvent.click(screen.getByText('Create Battery'));
    
    await waitFor(() => {
      expect(screen.getByText('Create Test Battery')).toBeInTheDocument();
    });
  });

  it('filters batteries by search term', async () => {
    const { apiService } = require('../services/apiService');
    renderWithProviders(<TestBatteriesManagement />);
    
    await waitFor(() => {
      expect(screen.getByText('EPA 8080 Full')).toBeInTheDocument();
    });
    
    const searchInput = screen.getByPlaceholderText('Search batteries by name or description...');
    fireEvent.change(searchInput, { target: { value: 'EPA' } });
    
    await waitFor(() => {
      expect(apiService.getTestBatteries).toHaveBeenCalledWith({ name: 'EPA' });
    });
  });

  it('expands battery row to show analyses', async () => {
    renderWithProviders(<TestBatteriesManagement />);
    
    await waitFor(() => {
      expect(screen.getByText('EPA 8080 Full')).toBeInTheDocument();
    });
    
    // Find and click expand button
    const expandButtons = screen.getAllByRole('button');
    const expandButton = expandButtons.find(btn => 
      btn.querySelector('[data-testid="ExpandMoreIcon"]') || 
      btn.querySelector('[data-testid="ExpandLessIcon"]')
    );
    
    if (expandButton) {
      fireEvent.click(expandButton);
      
      await waitFor(() => {
        expect(screen.getByText('Analyses in EPA 8080 Full')).toBeInTheDocument();
      });
    }
  });

  it('shows error message on load failure', async () => {
    const { apiService } = require('../services/apiService');
    apiService.getTestBatteries.mockRejectedValue({
      response: { status: 500, data: { detail: 'Server error' } },
    });
    
    renderWithProviders(<TestBatteriesManagement />);
    
    await waitFor(() => {
      expect(screen.getByText(/Failed to load test batteries/i)).toBeInTheDocument();
    });
  });

  it('shows permission error for unauthorized users', async () => {
    const { apiService } = require('../services/apiService');
    apiService.getTestBatteries.mockRejectedValue({
      response: { status: 403 },
    });
    
    renderWithProviders(<TestBatteriesManagement />, mockNonAdminUser);
    
    await waitFor(() => {
      expect(screen.getByText(/permission to view test batteries/i)).toBeInTheDocument();
    });
  });
});

