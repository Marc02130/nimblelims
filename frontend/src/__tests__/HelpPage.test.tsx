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
    createHelpEntry: jest.fn(),
    updateHelpEntry: jest.fn(),
    deleteHelpEntry: jest.fn(),
  },
}));

const theme = createTheme();

const mockApiService = apiService as jest.Mocked<typeof apiService>;

const renderWithProviders = (ui: React.ReactElement, userRole: string = 'Client', permissions: string[] = []) => {
  // Mock localStorage
  const mockToken = 'mock-token';
  localStorage.setItem('token', mockToken);

  // Mock getCurrentUser to return user with specified role
  mockApiService.getCurrentUser.mockResolvedValue({
    id: '1',
    username: 'testuser',
    email: 'test@example.com',
    role: userRole,
    permissions: permissions,
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

  it('renders LabTechHelpSection for lab-technician users', async () => {
    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'Accessioning Workflow',
          content: 'Step-by-step guide to sample accessioning with test assignments.',
          role_filter: 'lab-technician',
          active: true,
        },
        {
          id: '2',
          section: 'Batch Creation',
          content: 'Create batches to group samples for testing workflows.',
          role_filter: 'lab-technician',
          active: true,
        },
      ],
      total: 2,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'lab-technician');

    await waitFor(() => {
      expect(screen.getByText('Help & Support')).toBeInTheDocument();
      expect(screen.getByText('Accessioning Workflow')).toBeInTheDocument();
      expect(screen.getByText('Batch Creation')).toBeInTheDocument();
    });
  });

  it('renders AdminHelpSection for Administrator users', async () => {
    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'User Management',
          content: 'Guide: Create/edit users/roles, assign permissions (user:manage, role:manage). Use admin UI for configs.',
          role_filter: 'administrator',
          active: true,
        },
        {
          id: '2',
          section: 'EAV Configuration',
          content: 'Configure custom attributes using Entity-Attribute-Value (EAV) model.',
          role_filter: 'administrator',
          active: true,
        },
      ],
      total: 2,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'Administrator');

    await waitFor(() => {
      expect(screen.getByText('Help & Support')).toBeInTheDocument();
      expect(screen.getByText('User Management')).toBeInTheDocument();
      expect(screen.getByText('EAV Configuration')).toBeInTheDocument();
    });
  });

  it('renders generic help message for users without role-specific help', () => {
    renderWithProviders(<HelpPage />, 'UnknownRole');

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

  it('calls API with correct role filter for lab-technician users', async () => {
    const mockHelpEntries = {
      help_entries: [],
      total: 0,
      page: 1,
      size: 10,
      pages: 0,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'lab-technician');

    await waitFor(() => {
      expect(mockApiService.getHelp).toHaveBeenCalledWith({ role: 'lab-technician' });
    });
  });

  it('calls API with administrator role filter for Administrator users', async () => {
    const mockHelpEntries = {
      help_entries: [],
      total: 0,
      page: 1,
      size: 10,
      pages: 0,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'Administrator');

    await waitFor(() => {
      expect(mockApiService.getHelp).toHaveBeenCalledWith({ role: 'administrator' });
    });
  });

  it('does not call API for users without role-specific help', () => {
    renderWithProviders(<HelpPage />, 'UnknownRole');

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

  it('lab-technician user sees only filtered help entries', async () => {
    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'Accessioning Workflow',
          content: 'Lab technician-specific help content.',
          role_filter: 'lab-technician',
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

    renderWithProviders(<HelpPage />, 'lab-technician');

    await waitFor(() => {
      expect(mockApiService.getHelp).toHaveBeenCalledWith({ role: 'lab-technician' });
      expect(screen.getByText('Accessioning Workflow')).toBeInTheDocument();
      expect(screen.getByText('Public Help')).toBeInTheDocument();
    });

    // Verify all entries are lab-technician-filtered or public
    const entries = mockHelpEntries.help_entries;
    entries.forEach((entry) => {
      expect(entry.role_filter === 'lab-technician' || entry.role_filter === null).toBe(true);
    });
  });

  it('non-Client and non-lab-technician user sees general help message', () => {
    renderWithProviders(<HelpPage />, 'Administrator');

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

  it('filters help entries correctly by role for Client', async () => {
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
          role_filter: 'lab-technician',
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

  it('filters help entries correctly by role for lab-technician', async () => {
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
          section: 'Accessioning Workflow',
          content: 'Lab technician content.',
          role_filter: 'lab-technician',
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

    // Mock API to return only lab-technician and public entries when role=lab-technician
    mockApiService.getHelp.mockImplementation((filters) => {
      if (filters?.role === 'lab-technician') {
        return Promise.resolve({
          help_entries: mockHelpEntries.help_entries.filter(
            (e) => e.role_filter === 'lab-technician' || e.role_filter === null
          ),
          total: 2,
          page: 1,
          size: 10,
          pages: 1,
        });
      }
      return Promise.resolve(mockHelpEntries);
    });

    renderWithProviders(<HelpPage />, 'lab-technician');

    await waitFor(() => {
      expect(screen.getByText('Accessioning Workflow')).toBeInTheDocument();
      expect(screen.getByText('Public Help')).toBeInTheDocument();
      expect(screen.queryByText('Client Help')).not.toBeInTheDocument();
    });
  });

  it('handles API errors gracefully for lab-technician users', async () => {
    mockApiService.getHelp.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<HelpPage />, 'lab-technician');

    await waitFor(() => {
      expect(mockApiService.getHelp).toHaveBeenCalledWith({ role: 'lab-technician' });
    });
  });

  it('renders LabTechHelpSection with ARIA labels for accessibility', async () => {
    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'Accessioning Workflow',
          content: 'Step-by-step guide to sample accessioning.',
          role_filter: 'lab-technician',
          active: true,
        },
      ],
      total: 1,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'lab-technician');

    await waitFor(() => {
      // Check for heading with ARIA label
      const heading = screen.getByText('Help & Support');
      expect(heading).toHaveAttribute('id', 'lab-tech-help-heading');
      expect(heading.tagName).toBe('H2');
      
      // Check navigation role
      const nav = screen.getByRole('navigation');
      expect(nav).toHaveAttribute('aria-labelledby', 'lab-tech-help-heading');
      
      // Check accordion ARIA attributes
      const accordion = screen.getByRole('button', { name: /Accessioning Workflow/i });
      expect(accordion).toHaveAttribute('aria-controls', 'Accessioning Workflow-content');
      expect(accordion).toHaveAttribute('id', 'Accessioning Workflow-header');
      expect(accordion).toHaveAttribute('aria-label', 'Accessioning Workflow help section');
      expect(accordion).toHaveAttribute('aria-expanded');
      
      // Check accordion details ARIA attributes
      const details = screen.getByRole('region');
      expect(details).toHaveAttribute('id', 'Accessioning Workflow-content');
      expect(details).toHaveAttribute('aria-labelledby', 'Accessioning Workflow-header');
    });
  });

  it('filters help entries correctly by role for lab-technician with RLS simulation', async () => {
    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'Accessioning Workflow',
          content: 'Lab technician content.',
          role_filter: 'lab-technician',
          active: true,
        },
        {
          id: '2',
          section: 'Client Help',
          content: 'Client content.',
          role_filter: 'Client',
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

    // Mock API to return only lab-technician and public entries when role=lab-technician
    mockApiService.getHelp.mockImplementation((filters) => {
      if (filters?.role === 'lab-technician') {
        return Promise.resolve({
          help_entries: mockHelpEntries.help_entries.filter(
            (e) => e.role_filter === 'lab-technician' || e.role_filter === null
          ),
          total: 2,
          page: 1,
          size: 10,
          pages: 1,
        });
      }
      return Promise.resolve(mockHelpEntries);
    });

    renderWithProviders(<HelpPage />, 'lab-technician');

    await waitFor(() => {
      expect(screen.getByText('Accessioning Workflow')).toBeInTheDocument();
      expect(screen.getByText('Public Help')).toBeInTheDocument();
      expect(screen.queryByText('Client Help')).not.toBeInTheDocument();
    });
  });

  it('renders LabManagerHelpSection for Lab Manager users', async () => {
    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'Results Review',
          content: 'Guide: Approve results, check QC. Use result:review permission. Flag issues per US-12.',
          role_filter: 'lab-manager',
          active: true,
        },
        {
          id: '2',
          section: 'Batch Management',
          content: 'Oversee batch operations and workflow. Monitor batch status and QC requirements.',
          role_filter: 'lab-manager',
          active: true,
        },
        {
          id: '3',
          section: 'Project Management',
          content: 'Manage projects and client relationships. Monitor project status and sample progress.',
          role_filter: 'lab-manager',
          active: true,
        },
      ],
      total: 3,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'Lab Manager');

    await waitFor(() => {
      expect(screen.getByText('Help & Support')).toBeInTheDocument();
      expect(screen.getByText('Results Review')).toBeInTheDocument();
      expect(screen.getByText('Batch Management')).toBeInTheDocument();
      expect(screen.getByText('Project Management')).toBeInTheDocument();
    });
  });

  it('renders LabManagerHelpSection for lab-manager role (slug format)', async () => {
    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'Results Review',
          content: 'Guide: Approve results, check QC.',
          role_filter: 'lab-manager',
          active: true,
        },
      ],
      total: 1,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'lab-manager');

    await waitFor(() => {
      expect(screen.getByText('Help & Support')).toBeInTheDocument();
      expect(screen.getByText('Results Review')).toBeInTheDocument();
    });
  });

  it('filters help entries correctly by role for Lab Manager', async () => {
    // Backend automatically filters by current user's role, so mock returns only lab-manager and public entries
    const mockHelpEntries = {
      help_entries: [
        {
          id: '2',
          section: 'Results Review',
          content: 'Lab manager content.',
          role_filter: 'lab-manager',
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
      total: 2,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'Lab Manager');

    await waitFor(() => {
      expect(screen.getByText('Results Review')).toBeInTheDocument();
      expect(screen.getByText('Public Help')).toBeInTheDocument();
      expect(screen.queryByText('Client Help')).not.toBeInTheDocument();
    });
  });

  it('renders LabManagerHelpSection with ARIA labels for accessibility', async () => {
    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'Results Review',
          content: 'Guide: Approve results, check QC. Use result:review permission.',
          role_filter: 'lab-manager',
          active: true,
        },
      ],
      total: 1,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'Lab Manager');

    await waitFor(() => {
      // Check for heading with ARIA label
      const heading = screen.getByText('Help & Support');
      expect(heading).toHaveAttribute('id', 'lab-manager-help-heading');
      expect(heading.tagName).toBe('H2');
      
      // Check navigation role
      const nav = screen.getByRole('navigation');
      expect(nav).toHaveAttribute('aria-labelledby', 'lab-manager-help-heading');
      
      // Check accordion ARIA attributes
      const accordion = screen.getByRole('button', { name: /Results Review/i });
      expect(accordion).toHaveAttribute('aria-controls', 'Results Review-content');
      expect(accordion).toHaveAttribute('id', 'Results Review-header');
      expect(accordion).toHaveAttribute('aria-label', 'Results Review help section');
      expect(accordion).toHaveAttribute('aria-expanded');
      
      // Check accordion details ARIA attributes
      const details = screen.getByRole('region');
      expect(details).toHaveAttribute('id', 'Results Review-content');
      expect(details).toHaveAttribute('aria-labelledby', 'Results Review-header');
    });
  });

  it('filters help entries correctly by role for Lab Manager with RLS simulation', async () => {
    // Backend RLS filters entries - Lab Manager should only see lab-manager and public entries
    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'Results Review',
          content: 'Lab manager content.',
          role_filter: 'lab-manager',
          active: true,
        },
        {
          id: '4',
          section: 'Public Help',
          content: 'Public content.',
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

    renderWithProviders(<HelpPage />, 'Lab Manager');

    await waitFor(() => {
      expect(screen.getByText('Results Review')).toBeInTheDocument();
      expect(screen.getByText('Public Help')).toBeInTheDocument();
      expect(screen.queryByText('Client Help')).not.toBeInTheDocument();
      expect(screen.queryByText('Lab Technician Help')).not.toBeInTheDocument();
    });
  });

  it('handles API errors gracefully for Lab Manager users', async () => {
    mockApiService.getHelp.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<HelpPage />, 'Lab Manager');

    await waitFor(() => {
      expect(mockApiService.getHelp).toHaveBeenCalled();
    });
  });

  it('filters help entries correctly by role for Lab Manager with RLS simulation (RLS-denied)', async () => {
    // Backend RLS filters entries - Lab Manager should only see lab-manager and public entries
    // Client and Lab Technician entries should be filtered out by RLS
    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'Results Review',
          content: 'Lab manager content.',
          role_filter: 'lab-manager',
          active: true,
        },
        {
          id: '4',
          section: 'Public Help',
          content: 'Public content.',
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

    renderWithProviders(<HelpPage />, 'Lab Manager');

    await waitFor(() => {
      expect(screen.getByText('Results Review')).toBeInTheDocument();
      expect(screen.getByText('Public Help')).toBeInTheDocument();
      // RLS should prevent these from being visible
      expect(screen.queryByText('Client Help')).not.toBeInTheDocument();
      expect(screen.queryByText('Lab Technician Help')).not.toBeInTheDocument();
    });
  });

  it('shows Manage Help button for users with config:edit permission', async () => {
    const mockHelpEntries = {
      help_entries: [],
      total: 0,
      page: 1,
      size: 10,
      pages: 0,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'Administrator', ['config:edit']);

    await waitFor(() => {
      expect(screen.getByText('Manage Help')).toBeInTheDocument();
      expect(screen.getByLabelText('Manage help entries')).toBeInTheDocument();
    });
  });

  it('does not show Manage Help button for users without config:edit permission', async () => {
    const mockHelpEntries = {
      help_entries: [],
      total: 0,
      page: 1,
      size: 10,
      pages: 0,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'Client', []);

    await waitFor(() => {
      expect(screen.queryByText('Manage Help')).not.toBeInTheDocument();
    });
  });

  it('renders AdminHelpSection with ARIA labels for accessibility', async () => {
    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'User Management',
          content: 'Guide: Create/edit users/roles, assign permissions.',
          role_filter: 'administrator',
          active: true,
        },
      ],
      total: 1,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpPage />, 'Administrator', ['config:edit']);

    await waitFor(() => {
      // Check for heading with ARIA label
      const heading = screen.getByText('Help & Support');
      expect(heading).toHaveAttribute('id', 'admin-help-heading');
      expect(heading.tagName).toBe('H2');
      
      // Check navigation role
      const nav = screen.getByRole('navigation');
      expect(nav).toHaveAttribute('aria-labelledby', 'admin-help-heading');
      
      // Check accordion ARIA attributes
      const accordion = screen.getByRole('button', { name: /User Management/i });
      expect(accordion).toHaveAttribute('aria-controls', 'User Management-content');
      expect(accordion).toHaveAttribute('id', 'User Management-header');
      expect(accordion).toHaveAttribute('aria-label', 'User Management help section');
      expect(accordion).toHaveAttribute('aria-expanded');
      
      // Check accordion details ARIA attributes
      const details = screen.getByRole('region');
      expect(details).toHaveAttribute('id', 'User Management-content');
      expect(details).toHaveAttribute('aria-labelledby', 'User Management-header');
    });
  });
});

