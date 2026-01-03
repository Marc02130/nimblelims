import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import HelpManagement from '../pages/admin/HelpManagement';
import { UserProvider } from '../contexts/UserContext';
import { apiService } from '../services/apiService';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    getHelp: jest.fn(),
    getRoles: jest.fn(),
    createHelpEntry: jest.fn(),
    updateHelpEntry: jest.fn(),
    deleteHelpEntry: jest.fn(),
    setAuthToken: jest.fn(),
    getCurrentUser: jest.fn(),
  },
}));

const theme = createTheme();

const mockApiService = apiService as jest.Mocked<typeof apiService>;

const renderWithProviders = (ui: React.ReactElement, permissions: string[] = ['config:edit']) => {
  // Mock localStorage
  const mockToken = 'mock-token';
  localStorage.setItem('token', mockToken);

  // Mock getCurrentUser to return admin user
  mockApiService.getCurrentUser.mockResolvedValue({
    id: '1',
    username: 'admin',
    email: 'admin@example.com',
    role: 'Administrator',
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

describe('HelpManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
  });

  it('renders Help Management page for users with config:edit permission', async () => {
    const mockRoles = [
      { id: '1', name: 'Administrator' },
      { id: '2', name: 'Lab Manager' },
      { id: '3', name: 'Lab Technician' },
      { id: '4', name: 'Client' },
    ];

    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'User Management',
          content: 'Guide: Create/edit users/roles.',
          role_filter: 'administrator',
          active: true,
          created_at: '2025-01-01T00:00:00Z',
          modified_at: '2025-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getRoles.mockResolvedValue(mockRoles);
    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpManagement />);

    await waitFor(() => {
      expect(screen.getByText('Help Management')).toBeInTheDocument();
      expect(screen.getByText('Create Help Entry')).toBeInTheDocument();
    });
  });

  it('shows permission warning for users without config:edit permission', () => {
    renderWithProviders(<HelpManagement />, []);

    expect(screen.getByText(/You do not have permission to view help management/)).toBeInTheDocument();
    expect(screen.getByText(/Requires config:edit permission/)).toBeInTheDocument();
  });

  it('loads and displays help entries', async () => {
    const mockRoles = [
      { id: '1', name: 'Administrator' },
      { id: '2', name: 'Lab Manager' },
    ];

    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'User Management',
          content: 'Guide: Create/edit users/roles.',
          role_filter: 'administrator',
          active: true,
          created_at: '2025-01-01T00:00:00Z',
          modified_at: '2025-01-01T00:00:00Z',
        },
        {
          id: '2',
          section: 'EAV Configuration',
          content: 'Configure custom attributes.',
          role_filter: 'administrator',
          active: true,
          created_at: '2025-01-01T00:00:00Z',
          modified_at: '2025-01-01T00:00:00Z',
        },
      ],
      total: 2,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getRoles.mockResolvedValue(mockRoles);
    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpManagement />);

    await waitFor(() => {
      expect(screen.getByText('User Management')).toBeInTheDocument();
      expect(screen.getByText('EAV Configuration')).toBeInTheDocument();
    });
  });

  it('filters help entries by role', async () => {
    const mockRoles = [
      { id: '1', name: 'Administrator' },
      { id: '2', name: 'Lab Manager' },
    ];

    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'User Management',
          content: 'Admin content.',
          role_filter: 'administrator',
          active: true,
          created_at: '2025-01-01T00:00:00Z',
          modified_at: '2025-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getRoles.mockResolvedValue(mockRoles);
    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpManagement />);

    await waitFor(() => {
      expect(screen.getByText('Filter by Role')).toBeInTheDocument();
    });

    // Test role filter dropdown
    const roleFilter = screen.getByLabelText('Filter by Role');
    fireEvent.mouseDown(roleFilter);

    await waitFor(() => {
      expect(screen.getByText('All Roles')).toBeInTheDocument();
      expect(screen.getByText('Administrator')).toBeInTheDocument();
      expect(screen.getByText('Lab Manager')).toBeInTheDocument();
    });
  });

  it('opens create dialog when Create Help Entry button is clicked', async () => {
    const mockRoles = [
      { id: '1', name: 'Administrator' },
    ];

    const mockHelpEntries = {
      help_entries: [],
      total: 0,
      page: 1,
      size: 10,
      pages: 0,
    };

    mockApiService.getRoles.mockResolvedValue(mockRoles);
    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Help Entry')).toBeInTheDocument();
    });

    const createButton = screen.getByText('Create Help Entry');
    fireEvent.click(createButton);

    await waitFor(() => {
      expect(screen.getByText('Create Help Entry')).toBeInTheDocument();
      expect(screen.getByLabelText('Section')).toBeInTheDocument();
      expect(screen.getByLabelText('Content')).toBeInTheDocument();
    });
  });

  it('creates a new help entry', async () => {
    const mockRoles = [
      { id: '1', name: 'Administrator' },
    ];

    const mockHelpEntries = {
      help_entries: [],
      total: 0,
      page: 1,
      size: 10,
      pages: 0,
    };

    const newEntry = {
      id: '1',
      section: 'Test Section',
      content: 'Test content',
      role_filter: 'administrator',
      active: true,
      created_at: '2025-01-01T00:00:00Z',
      modified_at: '2025-01-01T00:00:00Z',
    };

    mockApiService.getRoles.mockResolvedValue(mockRoles);
    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);
    mockApiService.createHelpEntry.mockResolvedValue(newEntry);

    renderWithProviders(<HelpManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Help Entry')).toBeInTheDocument();
    });

    const createButton = screen.getByText('Create Help Entry');
    fireEvent.click(createButton);

    await waitFor(() => {
      const sectionInput = screen.getByLabelText('Section');
      const contentInput = screen.getByLabelText('Content');
      
      fireEvent.change(sectionInput, { target: { value: 'Test Section' } });
      fireEvent.change(contentInput, { target: { value: 'Test content' } });
    });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockApiService.createHelpEntry).toHaveBeenCalledWith({
        section: 'Test Section',
        content: 'Test content',
        role_filter: '',
      });
    });
  });

  it('handles API errors gracefully', async () => {
    const mockRoles = [
      { id: '1', name: 'Administrator' },
    ];

    mockApiService.getRoles.mockResolvedValue(mockRoles);
    mockApiService.getHelp.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<HelpManagement />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load help entries/)).toBeInTheDocument();
    });
  });

  it('displays search functionality', async () => {
    const mockRoles = [
      { id: '1', name: 'Administrator' },
    ];

    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'User Management',
          content: 'Guide: Create/edit users/roles.',
          role_filter: 'administrator',
          active: true,
          created_at: '2025-01-01T00:00:00Z',
          modified_at: '2025-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getRoles.mockResolvedValue(mockRoles);
    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpManagement />);

    await waitFor(() => {
      expect(screen.getByPlaceholderText('Search by section or content...')).toBeInTheDocument();
    });
  });

  it('edits an existing help entry', async () => {
    const mockRoles = [
      { id: '1', name: 'Administrator' },
    ];

    const existingEntry = {
      id: '1',
      section: 'Original Section',
      content: 'Original content',
      role_filter: 'administrator',
      active: true,
      created_at: '2025-01-01T00:00:00Z',
      modified_at: '2025-01-01T00:00:00Z',
    };

    const mockHelpEntries = {
      help_entries: [existingEntry],
      total: 1,
      page: 1,
      size: 10,
      pages: 1,
    };

    const updatedEntry = {
      ...existingEntry,
      section: 'Updated Section',
      content: 'Updated content',
    };

    mockApiService.getRoles.mockResolvedValue(mockRoles);
    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);
    mockApiService.updateHelpEntry.mockResolvedValue(updatedEntry);

    renderWithProviders(<HelpManagement />);

    await waitFor(() => {
      expect(screen.getByText('Original Section')).toBeInTheDocument();
    });

    // Click edit button
    const editButtons = screen.getAllByLabelText('Edit');
    fireEvent.click(editButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Edit Help Entry')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Original Section')).toBeInTheDocument();
    });

    // Update fields
    const sectionInput = screen.getByLabelText('Section');
    const contentInput = screen.getByLabelText('Content');

    fireEvent.change(sectionInput, { target: { value: 'Updated Section' } });
    fireEvent.change(contentInput, { target: { value: 'Updated content' } });

    // Submit
    const updateButton = screen.getByText('Update');
    fireEvent.click(updateButton);

    await waitFor(() => {
      expect(mockApiService.updateHelpEntry).toHaveBeenCalledWith('1', {
        section: 'Updated Section',
        content: 'Updated content',
      });
    });
  });

  it('denies access to users without config:edit permission', () => {
    renderWithProviders(<HelpManagement />, []);

    expect(screen.getByText(/You do not have permission to view help management/)).toBeInTheDocument();
    expect(screen.getByText(/Requires config:edit permission/)).toBeInTheDocument();
    expect(screen.queryByText('Create Help Entry')).not.toBeInTheDocument();
  });

  it('deletes a help entry', async () => {
    const mockRoles = [
      { id: '1', name: 'Administrator' },
    ];

    const existingEntry = {
      id: '1',
      section: 'Delete Test Section',
      content: 'Content to be deleted',
      role_filter: 'administrator',
      active: true,
      created_at: '2025-01-01T00:00:00Z',
      modified_at: '2025-01-01T00:00:00Z',
    };

    const mockHelpEntries = {
      help_entries: [existingEntry],
      total: 1,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getRoles.mockResolvedValue(mockRoles);
    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);
    mockApiService.deleteHelpEntry.mockResolvedValue({});

    renderWithProviders(<HelpManagement />);

    await waitFor(() => {
      expect(screen.getByText('Delete Test Section')).toBeInTheDocument();
    });

    // Click delete button
    const deleteButtons = screen.getAllByLabelText('Delete');
    fireEvent.click(deleteButtons[0]);

    await waitFor(() => {
      expect(screen.getByText('Delete Help Entry')).toBeInTheDocument();
      expect(screen.getByText(/Are you sure you want to delete/)).toBeInTheDocument();
    });

    // Confirm delete
    const confirmButton = screen.getByText('Delete');
    fireEvent.click(confirmButton);

    await waitFor(() => {
      expect(mockApiService.deleteHelpEntry).toHaveBeenCalledWith('1');
    });
  });

  it('filters help entries by role', async () => {
    const mockRoles = [
      { id: '1', name: 'Administrator' },
      { id: '2', name: 'Lab Manager' },
    ];

    const mockHelpEntries = {
      help_entries: [
        {
          id: '1',
          section: 'Admin Section',
          content: 'Admin content',
          role_filter: 'administrator',
          active: true,
          created_at: '2025-01-01T00:00:00Z',
          modified_at: '2025-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      size: 10,
      pages: 1,
    };

    mockApiService.getRoles.mockResolvedValue(mockRoles);
    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);

    renderWithProviders(<HelpManagement />);

    await waitFor(() => {
      expect(screen.getByText('Filter by Role')).toBeInTheDocument();
    });

    // Test role filter
    const roleFilter = screen.getByLabelText('Filter by Role');
    fireEvent.mouseDown(roleFilter);

    await waitFor(() => {
      expect(screen.getByText('All Roles')).toBeInTheDocument();
      expect(screen.getByText('Administrator')).toBeInTheDocument();
      expect(screen.getByText('Lab Manager')).toBeInTheDocument();
    });
  });

  it('handles API errors during create', async () => {
    const mockRoles = [
      { id: '1', name: 'Administrator' },
    ];

    const mockHelpEntries = {
      help_entries: [],
      total: 0,
      page: 1,
      size: 10,
      pages: 0,
    };

    mockApiService.getRoles.mockResolvedValue(mockRoles);
    mockApiService.getHelp.mockResolvedValue(mockHelpEntries);
    mockApiService.createHelpEntry.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<HelpManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Help Entry')).toBeInTheDocument();
    });

    const createButton = screen.getByText('Create Help Entry');
    fireEvent.click(createButton);

    await waitFor(() => {
      const sectionInput = screen.getByLabelText('Section');
      const contentInput = screen.getByLabelText('Content');
      
      fireEvent.change(sectionInput, { target: { value: 'Test Section' } });
      fireEvent.change(contentInput, { target: { value: 'Test content' } });
    });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(mockApiService.createHelpEntry).toHaveBeenCalled();
    });
  });
});

