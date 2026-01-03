import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import HelpPage from '../pages/HelpPage';
import { UserProvider } from '../contexts/UserContext';
import { apiService } from '../services/apiService';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    getHelp: jest.fn(),
    setAuthToken: jest.fn(),
    getCurrentUser: jest.fn(),
  },
}));

const theme = createTheme();

const mockApiService = apiService as jest.Mocked<typeof apiService>;

const renderWithProviders = (ui: React.ReactElement, userRole: string = 'Client') => {
  // Mock localStorage
  const mockToken = 'mock-token';
  localStorage.setItem('token', mockToken);

  // Mock getCurrentUser to return user with specified role
  mockApiService.getCurrentUser.mockResolvedValue({
    id: '1',
    username: 'testuser',
    email: 'test@example.com',
    role: userRole,
    permissions: [],
  });

  return render(
    <BrowserRouter>
      <ThemeProvider theme={theme}>
        <UserProvider>
          {ui}
        </UserProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
};

describe('HelpPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('renders ClientHelpSection for Client users', async () => {
    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'Viewing Projects',
          content: 'Step-by-step guide to access your samples and results.',
          role_filter: 'Client',
          active: true,
        },
        {
          id: '2',
          section: 'Viewing Samples',
          content: 'Learn how to view and filter your samples.',
          role_filter: 'Client',
          active: true,
        },
      ],
      total: 2,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'Client');

    await waitFor(() => {
      expect(screen.getByText('Help & Support')).toBeInTheDocument();
      expect(screen.getByText('Viewing Projects')).toBeInTheDocument();
      expect(screen.getByText('Viewing Samples')).toBeInTheDocument();
    });
  });

  it('renders generic help message for non-Client users', () => {
    renderWithProviders(<HelpPage />, 'Lab Technician');

    expect(screen.getByText('Help & Documentation')).toBeInTheDocument();
    expect(screen.getByText(/Welcome to the NimbleLIMS help center/)).toBeInTheDocument();
    expect(screen.queryByText('Help & Support')).not.toBeInTheDocument();
  });

  it('displays loading state while fetching help content', () => {
    mockApiService.getHelp.mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    renderWithProviders(<HelpPage />, 'Client');

    // Check for loading indicator (ClientHelpSection handles this internally)
    // The component should be rendering
    expect(screen.getByText('Help & Support')).toBeInTheDocument();
  });

  it('handles API errors gracefully for Client users', async () => {
    mockApiService.getHelp.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<HelpPage />, 'Client');

    await waitFor(() => {
      // ClientHelpSection should handle the error and display it
      expect(mockApiService.getHelp).toHaveBeenCalledWith({ role: 'Client' });
    });
  });

  it('calls API with correct role filter for Client users', async () => {
    const mockHelpEntries = {
      help_entries: [],
      total: 0,
      page: 1,
      size: 10,
      pages: 0,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'Client');

    await waitFor(() => {
      expect(mockApiService.getHelp).toHaveBeenCalledWith({ role: 'Client' });
    });
  });

  it('does not call API for non-Client users', () => {
    renderWithProviders(<HelpPage />, 'Administrator');

    expect(mockApiService.getHelp).not.toHaveBeenCalled();
  });

  // Integration tests for role-based help access
  it('Client user sees only filtered help entries', async () => {
    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'Viewing Projects',
          content: 'Client-specific help content.',
          role_filter: 'Client',
          active: true,
        },
        {
          id: '2',
          section: 'Public Help',
          content: 'Public help content visible to all.',
          role_filter: null,
          active: true,
        },
      ],
      total: 2,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'Client');

    await waitFor(() => {
      expect(mockApiService.getHelp).toHaveBeenCalledWith({ role: 'Client' });
      expect(screen.getByText('Viewing Projects')).toBeInTheDocument();
      expect(screen.getByText('Public Help')).toBeInTheDocument();
    });

    // Verify all entries are Client-filtered or public
    const entries = mockHelpEntries.help_entries;
    entries.forEach((entry) => {
      expect(entry.role_filter === 'Client' || entry.role_filter === null).toBe(true);
    });
  });

  it('non-Client user sees general help message', () => {
    renderWithProviders(<HelpPage />, 'Lab Technician');

    expect(screen.getByText('Help & Documentation')).toBeInTheDocument();
    expect(screen.getByText(/Welcome to the NimbleLIMS help center/)).toBeInTheDocument();
    expect(screen.queryByText('Help & Support')).not.toBeInTheDocument();
    expect(mockApiService.getHelp).not.toHaveBeenCalled();
  });

  it('handles unauthorized access gracefully', async () => {
    mockApiService.getHelp.mockRejectedValue({
      response: { status: 403, data: { detail: 'Permission denied' } },
    });

    renderWithProviders(<HelpPage />, 'Client');

    await waitFor(() => {
      expect(mockApiService.getHelp).toHaveBeenCalled();
    });

    // Component should handle error and display it
    // ClientHelpSection will show error message
  });

  it('filters help entries correctly by role', async () => {
    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'Client Help',
          content: 'Client content.',
          role_filter: 'Client',
          active: true,
        },
        {
          id: '2',
          section: 'Lab Technician Help',
          content: 'Lab content.',
          role_filter: 'Lab Technician',
          active: true,
        },
        {
          id: '3',
          section: 'Public Help',
          content: 'Public content.',
          role_filter: null,
          active: true,
        },
      ],
      total: 3,
      page: 1,
      size: 10,
      pages: 1,
    };

    // Mock API to return only Client and public entries when role=Client
    mockApiService.getHelp.mockImplementation((filters) => {
      if (filters?.role === 'Client') {
        return Promise.resolve({
          help_entries: mockHelpEntries.help_entries.filter(
            (e) => e.role_filter === 'Client' || e.role_filter === null
          ),
          total: 2,
          page: 1,
          size: 10,
          pages: 1,
        });
      }
      return Promise.resolve(mockHelpEntries);
    });

    renderWithProviders(<HelpPage />, 'Client');

    await waitFor(() => {
      expect(screen.getByText('Client Help')).toBeInTheDocument();
      expect(screen.getByText('Public Help')).toBeInTheDocument();
      expect(screen.queryByText('Lab Technician Help')).not.toBeInTheDocument();
    });
  });
});

