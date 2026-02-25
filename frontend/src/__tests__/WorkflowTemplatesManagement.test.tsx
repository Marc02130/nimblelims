import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import WorkflowTemplatesManagement from '../pages/admin/WorkflowTemplatesManagement';

jest.mock('../services/apiService', () => ({
  apiService: {
    getWorkflowTemplates: jest.fn(),
    createWorkflowTemplate: jest.fn(),
    updateWorkflowTemplate: jest.fn(),
    deleteWorkflowTemplate: jest.fn(),
    executeWorkflow: jest.fn(),
  },
}));

const theme = createTheme();

const mockAdminUser = {
  id: '1',
  username: 'admin',
  email: 'admin@example.com',
  role: 'Administrator',
  permissions: ['config:edit', 'workflow:execute'],
};

const mockConfigEditOnlyUser = {
  id: '2',
  username: 'configuser',
  email: 'config@example.com',
  role: 'Lab Manager',
  permissions: ['config:edit'],
};

const mockExecuteOnlyUser = {
  id: '3',
  username: 'executeuser',
  email: 'execute@example.com',
  role: 'Lab Technician',
  permissions: ['workflow:execute'],
};

const mockNoPermUser = {
  id: '4',
  username: 'noperm',
  email: 'noperm@example.com',
  role: 'Client',
  permissions: ['sample:read'],
};

const mockTemplates = [
  {
    id: 't1',
    name: 'Sample Receipt Workflow',
    description: 'On sample receipt',
    active: true,
    template_definition: { steps: [{ action: 'update_status', params: {} }] },
    created_at: '2024-01-01T00:00:00Z',
    modified_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 't2',
    name: 'QC Creation',
    description: 'Create QC samples',
    active: false,
    template_definition: { steps: [{ action: 'create_qc', params: {} }] },
    created_at: '2024-01-02T00:00:00Z',
    modified_at: '2024-01-02T00:00:00Z',
  },
];

const renderWithProviders = (
  component: React.ReactElement,
  user: typeof mockAdminUser = mockAdminUser
) => {
  jest.spyOn(require('../contexts/UserContext'), 'useUser').mockReturnValue({
    user,
    loading: false,
    login: jest.fn(),
    logout: jest.fn(),
    hasPermission: (permission: string) =>
      user.permissions.includes(permission) || user.role === 'Administrator',
  });

  return render(
    <MemoryRouter>
      <ThemeProvider theme={theme}>{component}</ThemeProvider>
    </MemoryRouter>
  );
};

describe('WorkflowTemplatesManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { apiService } = require('../services/apiService');
    apiService.getWorkflowTemplates.mockResolvedValue(mockTemplates);
  });

  test('renders workflow templates page when user has config:edit', async () => {
    renderWithProviders(<WorkflowTemplatesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Workflow Templates')).toBeInTheDocument();
    });
  });

  test('shows permission warning when user lacks config:edit', () => {
    renderWithProviders(<WorkflowTemplatesManagement />, mockNoPermUser);

    expect(
      screen.getByText(/You do not have permission to view workflow templates management/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/config:edit/i)).toBeInTheDocument();
  });

  test('displays Add Template button when user has config:edit', async () => {
    renderWithProviders(<WorkflowTemplatesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Add Template')).toBeInTheDocument();
    });
  });

  test('loads and displays workflow templates in DataGrid', async () => {
    renderWithProviders(<WorkflowTemplatesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Sample Receipt Workflow')).toBeInTheDocument();
      expect(screen.getByText('QC Creation')).toBeInTheDocument();
    });

    const { apiService } = require('../services/apiService');
    expect(apiService.getWorkflowTemplates).toHaveBeenCalled();
  });

  test('shows loading state while fetching templates', () => {
    const { apiService } = require('../services/apiService');
    apiService.getWorkflowTemplates.mockImplementation(() => new Promise(() => {}));

    renderWithProviders(<WorkflowTemplatesManagement />);

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  test('shows error when load fails', async () => {
    const { apiService } = require('../services/apiService');
    apiService.getWorkflowTemplates.mockRejectedValue(new Error('Network error'));

    renderWithProviders(<WorkflowTemplatesManagement />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load workflow templates|Network error/i)).toBeInTheDocument();
    });
  });

  test('shows permission error when load returns 403', async () => {
    const { apiService } = require('../services/apiService');
    const err: any = new Error('Forbidden');
    err.response = { status: 403 };
    apiService.getWorkflowTemplates.mockRejectedValue(err);

    renderWithProviders(<WorkflowTemplatesManagement />);

    await waitFor(() => {
      expect(
        screen.getByText(/You do not have permission to view workflow templates/i)
      ).toBeInTheDocument();
    });
  });

  test('opens create dialog when Add Template is clicked', async () => {
    renderWithProviders(<WorkflowTemplatesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Add Template')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Add Template'));

    await waitFor(() => {
      expect(screen.getByText('Create Workflow Template')).toBeInTheDocument();
      expect(screen.getByLabelText(/Name/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/Template definition/i)).toBeInTheDocument();
    });
  });

  test('create dialog has Create and Cancel buttons', async () => {
    renderWithProviders(<WorkflowTemplatesManagement />);

    await waitFor(() => screen.getByText('Add Template'));
    fireEvent.click(screen.getByText('Add Template'));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Create/i })).toBeInTheDocument();
    });
  });

  test('create template calls api and refreshes list', async () => {
    const { apiService } = require('../services/apiService');
    const newTemplate = {
      id: 't3',
      name: 'New Workflow',
      description: 'New',
      active: true,
      template_definition: { steps: [{ action: 'update_status', params: {} }] },
      created_at: '2024-01-03T00:00:00Z',
      modified_at: '2024-01-03T00:00:00Z',
    };
    apiService.createWorkflowTemplate.mockResolvedValue(newTemplate);

    renderWithProviders(<WorkflowTemplatesManagement />);

    await waitFor(() => screen.getByText('Add Template'));
    fireEvent.click(screen.getByText('Add Template'));

    await waitFor(() => screen.getByText('Create Workflow Template'));

    const nameInput = screen.getByLabelText(/Name/i);
    fireEvent.change(nameInput, { target: { value: 'New Workflow' } });

    const createBtn = screen.getByRole('button', { name: /Create/i });
    fireEvent.click(createBtn);

    await waitFor(() => {
      expect(apiService.createWorkflowTemplate).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'New Workflow',
          active: true,
          template_definition: expect.objectContaining({ steps: expect.any(Array) }),
        })
      );
    });

    await waitFor(() => {
      expect(apiService.getWorkflowTemplates).toHaveBeenCalledTimes(2);
    });
  });

  test('delete opens confirm dialog and deactivate calls api', async () => {
    const { apiService } = require('../services/apiService');
    apiService.deleteWorkflowTemplate.mockResolvedValue(undefined);

    renderWithProviders(<WorkflowTemplatesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Sample Receipt Workflow')).toBeInTheDocument();
    });

    const deleteBtn = screen.getByRole('button', { name: 'Delete' });
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(screen.getByText('Confirm deactivate')).toBeInTheDocument();
      expect(screen.getByText(/Deactivate workflow template/)).toBeInTheDocument();
    });

    const deactivateBtn = screen.getByRole('button', { name: /Deactivate/i });
    fireEvent.click(deactivateBtn);

    await waitFor(() => {
      expect(apiService.deleteWorkflowTemplate).toHaveBeenCalledWith('t1');
      expect(apiService.getWorkflowTemplates).toHaveBeenCalledTimes(2);
    });
  });

  test('execute opens dialog and execute calls api with context', async () => {
    const { apiService } = require('../services/apiService');
    apiService.executeWorkflow.mockResolvedValue({ id: 'inst1', name: 'run1' });

    renderWithProviders(<WorkflowTemplatesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Sample Receipt Workflow')).toBeInTheDocument();
    });

    const executeRowBtn = screen.getByRole('button', { name: 'Execute on Entity' });
    fireEvent.click(executeRowBtn);

    await waitFor(() => {
      expect(screen.getByText('Execute on Entity')).toBeInTheDocument();
      expect(screen.getByText(/Run template/)).toBeInTheDocument();
    });

    const executeSubmitBtn = screen.getByRole('button', { name: /^Execute$/i });
    fireEvent.click(executeSubmitBtn);

    await waitFor(() => {
      expect(apiService.executeWorkflow).toHaveBeenCalledWith(
        't1',
        expect.objectContaining({ context: {} })
      );
    });
  });

  test('execute dialog shows context JSON field', async () => {
    renderWithProviders(<WorkflowTemplatesManagement />);

    await waitFor(() => screen.getByText('Sample Receipt Workflow'));
    const executeBtn = screen.getByRole('button', { name: 'Execute on Entity' });
    fireEvent.click(executeBtn);

    await waitFor(() => {
      expect(screen.getByLabelText(/Context \(JSON\)/i)).toBeInTheDocument();
    });
  });

  test('DataGrid shows active chip and created date', async () => {
    renderWithProviders(<WorkflowTemplatesManagement />);

    await waitFor(() => {
      expect(screen.getByText('Sample Receipt Workflow')).toBeInTheDocument();
    });

    expect(screen.getByText('Yes')).toBeInTheDocument();
    expect(screen.getByText('No')).toBeInTheDocument();
  });
});
