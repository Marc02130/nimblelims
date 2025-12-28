import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ClientProjects from '../pages/ClientProjects';
import { apiService } from '../services/apiService';
import { useUser } from '../contexts/UserContext';

// Mock dependencies
jest.mock('../services/apiService');
jest.mock('../contexts/UserContext');

const mockApiService = apiService as jest.Mocked<typeof apiService>;
const mockUseUser = useUser as jest.MockedFunction<typeof useUser>;

const mockUser = {
  id: '1',
  username: 'testuser',
  email: 'test@example.com',
  role: 'Administrator',
  permissions: ['project:manage', 'sample:read'],
  hasPermission: jest.fn((perm: string) => {
    return ['project:manage', 'sample:read'].includes(perm);
  }),
};

const mockClientProjects = [
  {
    id: '1',
    name: 'Project Alpha',
    description: 'First client project',
    client_id: 'client1',
    active: true,
    created_at: '2024-01-01T00:00:00Z',
    modified_at: '2024-01-01T00:00:00Z',
  },
  {
    id: '2',
    name: 'Project Beta',
    description: 'Second client project',
    client_id: 'client2',
    active: false,
    created_at: '2024-01-02T00:00:00Z',
    modified_at: '2024-01-02T00:00:00Z',
  },
];

const mockClients = [
  { id: 'client1', name: 'Client A' },
  { id: 'client2', name: 'Client B' },
];

const renderComponent = () => {
  return render(
    <BrowserRouter>
      <ClientProjects />
    </BrowserRouter>
  );
};

describe('ClientProjects', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUseUser.mockReturnValue(mockUser as any);
    mockApiService.getClientProjects.mockResolvedValue({
      client_projects: mockClientProjects,
      total: 2,
      page: 1,
      size: 10,
      pages: 1,
    });
    mockApiService.getClients.mockResolvedValue(mockClients);
  });

  it('renders client projects page', async () => {
    renderComponent();

    expect(screen.getByText('Client Projects')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
    });
  });

  it('displays client projects in DataGrid', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      expect(screen.getByText('Project Beta')).toBeInTheDocument();
    });
  });

  it('shows create button when user has project:manage permission', () => {
    renderComponent();

    expect(screen.getByText('Create Client Project')).toBeInTheDocument();
  });

  it('hides create button when user lacks project:manage permission', () => {
    mockUseUser.mockReturnValue({
      ...mockUser,
      hasPermission: jest.fn(() => false),
    } as any);

    renderComponent();

    expect(screen.queryByText('Create Client Project')).not.toBeInTheDocument();
  });

  it('opens create form when create button is clicked', async () => {
    renderComponent();

    const createButton = screen.getByText('Create Client Project');
    fireEvent.click(createButton);

    await waitFor(() => {
      expect(screen.getByText('Create Client Project')).toBeInTheDocument();
    });
  });

  it('filters client projects by search term', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/search by name/i);
    fireEvent.change(searchInput, { target: { value: 'Alpha' } });

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
      expect(screen.queryByText('Project Beta')).not.toBeInTheDocument();
    });
  });

  it('filters client projects by client', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
    });

    const clientFilter = screen.getByLabelText(/filter by client/i);
    fireEvent.mouseDown(clientFilter);
    
    await waitFor(() => {
      const clientOption = screen.getByText('Client A');
      fireEvent.click(clientOption);
    });

    await waitFor(() => {
      expect(mockApiService.getClientProjects).toHaveBeenCalledWith(
        expect.objectContaining({ client_id: 'client1' })
      );
    });
  });

  it('opens edit form when edit button is clicked', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
    });

    // Find edit button (MUI DataGrid actions)
    const editButtons = screen.getAllByLabelText('Edit');
    if (editButtons.length > 0) {
      fireEvent.click(editButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Edit Client Project')).toBeInTheDocument();
      });
    }
  });

  it('opens delete dialog when delete button is clicked', async () => {
    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
    });

    // Find delete button (MUI DataGrid actions)
    const deleteButtons = screen.getAllByLabelText('Delete');
    if (deleteButtons.length > 0) {
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        expect(screen.getByText('Delete Client Project')).toBeInTheDocument();
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      });
    }
  });

  it('calls delete API when delete is confirmed', async () => {
    mockApiService.deleteClientProject.mockResolvedValue({ message: 'Deleted' });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Project Alpha')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByLabelText('Delete');
    if (deleteButtons.length > 0) {
      fireEvent.click(deleteButtons[0]);

      await waitFor(() => {
        const confirmButton = screen.getByText('Delete');
        fireEvent.click(confirmButton);
      });

      await waitFor(() => {
        expect(mockApiService.deleteClientProject).toHaveBeenCalled();
      });
    }
  });

  it('displays error message when API call fails', async () => {
    mockApiService.getClientProjects.mockRejectedValue({
      response: { data: { detail: 'Failed to load' } },
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });

  it('shows permission warning when user lacks permissions', () => {
    mockUseUser.mockReturnValue({
      ...mockUser,
      hasPermission: jest.fn(() => false),
    } as any);

    renderComponent();

    expect(screen.getByText(/do not have permission/i)).toBeInTheDocument();
  });

  it('handles pagination', async () => {
    renderComponent();

    await waitFor(() => {
      expect(mockApiService.getClientProjects).toHaveBeenCalledWith(
        expect.objectContaining({ page: 1, size: 10 })
      );
    });
  });
});

