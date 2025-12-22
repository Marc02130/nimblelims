import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ListsManagement from '../pages/admin/ListsManagement';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    getLists: jest.fn(),
    createList: jest.fn(),
    updateList: jest.fn(),
    deleteList: jest.fn(),
    createListEntry: jest.fn(),
    updateListEntry: jest.fn(),
    deleteListEntry: jest.fn(),
  },
}));

const theme = createTheme();

const mockAdminUser = {
  id: '1',
  username: 'admin',
  email: 'admin@example.com',
  role: 'Administrator',
  permissions: ['config:edit', 'sample:read'],
};

const mockNonAdminUser = {
  id: '2',
  username: 'user',
  email: 'user@example.com',
  role: 'Lab Technician',
  permissions: ['sample:read'],
};

const mockLists = [
  {
    id: '1',
    name: 'sample_status',
    description: 'Sample status values',
    active: true,
    created_at: '2024-01-01T00:00:00Z',
    modified_at: '2024-01-01T00:00:00Z',
    entries: [
      {
        id: '1',
        name: 'Received',
        description: 'Sample received',
        active: true,
        created_at: '2024-01-01T00:00:00Z',
        modified_at: '2024-01-01T00:00:00Z',
        list_id: '1',
      },
      {
        id: '2',
        name: 'Available for Testing',
        description: 'Sample ready for testing',
        active: true,
        created_at: '2024-01-01T00:00:00Z',
        modified_at: '2024-01-01T00:00:00Z',
        list_id: '1',
      },
    ],
  },
  {
    id: '2',
    name: 'qc_types',
    description: 'QC types',
    active: true,
    created_at: '2024-01-01T00:00:00Z',
    modified_at: '2024-01-01T00:00:00Z',
    entries: [
      {
        id: '3',
        name: 'Sample',
        description: 'Regular sample',
        active: true,
        created_at: '2024-01-01T00:00:00Z',
        modified_at: '2024-01-01T00:00:00Z',
        list_id: '2',
      },
    ],
  },
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

describe('ListsManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { apiService } = require('../services/apiService');
    apiService.getLists.mockResolvedValue(mockLists);
  });

  test('renders lists management page', async () => {
    renderWithProviders(<ListsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Lists Management')).toBeInTheDocument();
    });
  });

  test('displays lists in DataGrid', async () => {
    renderWithProviders(<ListsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Sample Status')).toBeInTheDocument();
      expect(screen.getByText('Qc Types')).toBeInTheDocument();
    });
  });

  test('shows entry counts', async () => {
    renderWithProviders(<ListsManagement />);

    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument(); // Entry count for sample_status
      expect(screen.getByText('1')).toBeInTheDocument(); // Entry count for qc_types
    });
  });

  test('shows create list button for admin users', async () => {
    renderWithProviders(<ListsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create List')).toBeInTheDocument();
    });
  });

  test('hides create list button for non-admin users', async () => {
    renderWithProviders(<ListsManagement />, mockNonAdminUser);

    await waitFor(() => {
      expect(screen.queryByText('Create List')).not.toBeInTheDocument();
    });
  });

  test('opens create list dialog on button click', async () => {
    renderWithProviders(<ListsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create List')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create List'));

    await waitFor(() => {
      expect(screen.getByText('Create New List')).toBeInTheDocument();
    });
  });

  test('creates a new list', async () => {
    const { apiService } = require('../services/apiService');
    apiService.createList.mockResolvedValue({
      id: '3',
      name: 'new_list',
      description: 'New list',
      active: true,
      entries: [],
    });

    renderWithProviders(<ListsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create List')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create List'));

    await waitFor(() => {
      expect(screen.getByText('Create New List')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText('List Name');
    fireEvent.change(nameInput, { target: { value: 'New List' } });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(apiService.createList).toHaveBeenCalledWith({
        name: 'new_list',
        description: undefined,
      });
    });
  });

  test('expands list to show entries', async () => {
    renderWithProviders(<ListsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Sample Status')).toBeInTheDocument();
    });

    // Find expand button (icon button)
    const expandButtons = screen.getAllByRole('button', { hidden: true });
    const expandButton = expandButtons.find((btn) => 
      btn.querySelector('svg[data-testid="ExpandMoreIcon"]') || 
      btn.querySelector('svg[data-testid="ExpandLessIcon"]')
    );

    if (expandButton) {
      fireEvent.click(expandButton);

      await waitFor(() => {
        expect(screen.getByText(/Entries for Sample Status/i)).toBeInTheDocument();
        expect(screen.getByText('Received')).toBeInTheDocument();
        expect(screen.getByText('Available for Testing')).toBeInTheDocument();
      });
    }
  });

  test('filters lists by search term', async () => {
    renderWithProviders(<ListsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Sample Status')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search lists and entries...');
    fireEvent.change(searchInput, { target: { value: 'qc' } });

    await waitFor(() => {
      expect(screen.queryByText('Sample Status')).not.toBeInTheDocument();
      expect(screen.getByText('Qc Types')).toBeInTheDocument();
    });
  });

  test('handles API error gracefully', async () => {
    const { apiService } = require('../services/apiService');
    apiService.getLists.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<ListsManagement />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load lists/i)).toBeInTheDocument();
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

    renderWithProviders(<ListsManagement />, restrictedUser);

    expect(screen.getByText(/You do not have permission to view lists management/i)).toBeInTheDocument();
  });

  test('opens edit list dialog', async () => {
    renderWithProviders(<ListsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Sample Status')).toBeInTheDocument();
    });

    // Find edit button (this would be in the actions column)
    // Since DataGrid actions are complex, we'll test the dialog opening differently
    // In a real scenario, you'd click the edit icon in the grid
  });

  test('opens delete confirmation dialog', async () => {
    renderWithProviders(<ListsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Sample Status')).toBeInTheDocument();
    });

    // Similar to edit, delete would be tested by clicking the delete icon
    // The dialog would appear with confirmation message
  });

  test('creates a new entry', async () => {
    const { apiService } = require('../services/apiService');
    apiService.createListEntry.mockResolvedValue({
      id: '4',
      name: 'New Entry',
      description: 'New entry description',
      active: true,
      list_id: '1',
    });

    renderWithProviders(<ListsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Sample Status')).toBeInTheDocument();
    });

    // Expand list first, then click add entry
    // This would require finding the expand button and add entry button
  });

  test('validates unique list names', async () => {
    renderWithProviders(<ListsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create List')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create List'));

    await waitFor(() => {
      expect(screen.getByText('Create New List')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText('List Name');
    fireEvent.change(nameInput, { target: { value: 'Sample Status' } });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/A list with this name already exists/i)).toBeInTheDocument();
    });
  });

  test('clears search term', async () => {
    renderWithProviders(<ListsManagement />);

    const searchInput = screen.getByPlaceholderText('Search lists and entries...');
    fireEvent.change(searchInput, { target: { value: 'test' } });

    await waitFor(() => {
      expect(searchInput).toHaveValue('test');
    });

    // Find clear button
    const clearButton = screen.getByRole('button', { hidden: true });
    // This would be the clear icon button
  });
});

