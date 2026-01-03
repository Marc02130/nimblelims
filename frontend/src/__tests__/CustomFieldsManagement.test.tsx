import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CustomFieldsManagement from '../pages/admin/CustomFieldsManagement';
import { UserProvider } from '../contexts/UserContext';

// Mock the API service
jest.mock('../services/apiService', () => ({
  apiService: {
    getCustomAttributeConfigs: jest.fn(),
    createCustomAttributeConfig: jest.fn(),
    updateCustomAttributeConfig: jest.fn(),
    deleteCustomAttributeConfig: jest.fn(),
  },
}));

const theme = createTheme();

const mockAdminUser = {
  id: '1',
  username: 'admin',
  email: 'admin@example.com',
  role: 'Administrator',
  permissions: ['config:edit'],
};

const mockNonAdminUser = {
  id: '2',
  username: 'user',
  email: 'user@example.com',
  role: 'Lab Technician',
  permissions: ['sample:read'],
};

const mockConfigs = [
  {
    id: '1',
    entity_type: 'samples',
    attr_name: 'ph_level',
    data_type: 'number',
    validation_rules: { min: 0, max: 14 },
    description: 'pH level of the sample',
    active: true,
    created_at: '2024-01-01T00:00:00Z',
    modified_at: '2024-01-01T00:00:00Z',
  },
  {
    id: '2',
    entity_type: 'tests',
    attr_name: 'instrument_id',
    data_type: 'text',
    validation_rules: { max_length: 50 },
    description: 'Instrument used for the test',
    active: true,
    created_at: '2024-01-02T00:00:00Z',
    modified_at: '2024-01-02T00:00:00Z',
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

describe('CustomFieldsManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    const { apiService } = require('../services/apiService');
    apiService.getCustomAttributeConfigs.mockResolvedValue({
      configs: mockConfigs,
      total: mockConfigs.length,
      page: 1,
      size: 10,
      pages: 1,
    });
  });

  test('renders custom fields management page', async () => {
    renderWithProviders(<CustomFieldsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Custom Fields Management')).toBeInTheDocument();
    });
  });

  test('displays custom fields in DataGrid', async () => {
    renderWithProviders(<CustomFieldsManagement />);

    await waitFor(() => {
      expect(screen.getByText('ph_level')).toBeInTheDocument();
      expect(screen.getByText('instrument_id')).toBeInTheDocument();
    });
  });

  test('displays all custom field columns', async () => {
    renderWithProviders(<CustomFieldsManagement />);

    await waitFor(() => {
      expect(screen.getByText('samples')).toBeInTheDocument();
      expect(screen.getByText('number')).toBeInTheDocument();
      expect(screen.getByText('pH level of the sample')).toBeInTheDocument();
    });
  });

  test('shows create button for admin users', async () => {
    renderWithProviders(<CustomFieldsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Custom Field')).toBeInTheDocument();
    });
  });

  test('hides create button for non-admin users', async () => {
    renderWithProviders(<CustomFieldsManagement />, mockNonAdminUser);

    await waitFor(() => {
      expect(screen.queryByText('Create Custom Field')).not.toBeInTheDocument();
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

    renderWithProviders(<CustomFieldsManagement />, restrictedUser);

    expect(
      screen.getByText(/You do not have permission to view custom fields management/i)
    ).toBeInTheDocument();
  });

  test('opens create custom field dialog on button click', async () => {
    renderWithProviders(<CustomFieldsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Custom Field')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Custom Field'));

    await waitFor(() => {
      expect(screen.getByText('Create New Custom Field')).toBeInTheDocument();
    });
  });

  test('filters custom fields by search term', async () => {
    renderWithProviders(<CustomFieldsManagement />);

    await waitFor(() => {
      expect(screen.getByText('ph_level')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search by attribute name or description...');
    fireEvent.change(searchInput, { target: { value: 'ph' } });

    await waitFor(() => {
      expect(screen.queryByText('instrument_id')).not.toBeInTheDocument();
      expect(screen.getByText('ph_level')).toBeInTheDocument();
    });
  });

  test('filters custom fields by entity type', async () => {
    renderWithProviders(<CustomFieldsManagement />);

    await waitFor(() => {
      expect(screen.getByText('ph_level')).toBeInTheDocument();
    });

    // Find and click the entity type filter
    const entityTypeSelect = screen.getByLabelText('Entity Type');
    fireEvent.mouseDown(entityTypeSelect);

    await waitFor(() => {
      const samplesOption = screen.getByText('samples');
      fireEvent.click(samplesOption);
    });

    // The API should be called with the filter
    await waitFor(() => {
      const { apiService } = require('../services/apiService');
      expect(apiService.getCustomAttributeConfigs).toHaveBeenCalledWith(
        expect.objectContaining({
          entity_type: 'samples',
        })
      );
    });
  });

  test('creates a new custom field', async () => {
    const { apiService } = require('../services/apiService');
    const newConfig = {
      id: '3',
      entity_type: 'samples',
      attr_name: 'temperature',
      data_type: 'number',
      validation_rules: { min: -20, max: 40 },
      active: true,
    };
    apiService.createCustomAttributeConfig.mockResolvedValue(newConfig);

    renderWithProviders(<CustomFieldsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Custom Field')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Custom Field'));

    await waitFor(() => {
      expect(screen.getByText('Create New Custom Field')).toBeInTheDocument();
    });

    // Fill in the form
    const entityTypeSelect = screen.getByLabelText('Entity Type');
    fireEvent.mouseDown(entityTypeSelect);
    await waitFor(() => {
      const samplesOption = screen.getByText('samples');
      fireEvent.click(samplesOption);
    });

    const attrNameInput = screen.getByLabelText('Attribute Name');
    fireEvent.change(attrNameInput, { target: { value: 'temperature' } });

    const dataTypeSelect = screen.getByLabelText('Data Type');
    fireEvent.mouseDown(dataTypeSelect);
    await waitFor(() => {
      const numberOption = screen.getByText('number');
      fireEvent.click(numberOption);
    });

    const validationRulesInput = screen.getByLabelText('Validation Rules');
    fireEvent.change(validationRulesInput, {
      target: { value: JSON.stringify({ min: -20, max: 40 }) },
    });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(apiService.createCustomAttributeConfig).toHaveBeenCalledWith({
        entity_type: 'samples',
        attr_name: 'temperature',
        data_type: 'number',
        validation_rules: { min: -20, max: 40 },
        description: undefined,
        active: true,
      });
    });
  });

  test('validates required fields', async () => {
    renderWithProviders(<CustomFieldsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Custom Field')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Custom Field'));

    await waitFor(() => {
      expect(screen.getByText('Create New Custom Field')).toBeInTheDocument();
    });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Entity type is required/i)).toBeInTheDocument();
      expect(screen.getByText(/Attribute name is required/i)).toBeInTheDocument();
    });
  });

  test('validates attribute name format', async () => {
    renderWithProviders(<CustomFieldsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Custom Field')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Custom Field'));

    await waitFor(() => {
      expect(screen.getByText('Create New Custom Field')).toBeInTheDocument();
    });

    const attrNameInput = screen.getByLabelText('Attribute Name');
    fireEvent.change(attrNameInput, { target: { value: 'invalid name!' } });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(
        screen.getByText(/Attribute name can only contain letters, numbers, underscores, and hyphens/i)
      ).toBeInTheDocument();
    });
  });

  test('validates JSON format for validation rules', async () => {
    renderWithProviders(<CustomFieldsManagement />);

    await waitFor(() => {
      expect(screen.getByText('Create Custom Field')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Create Custom Field'));

    await waitFor(() => {
      expect(screen.getByText('Create New Custom Field')).toBeInTheDocument();
    });

    const entityTypeSelect = screen.getByLabelText('Entity Type');
    fireEvent.mouseDown(entityTypeSelect);
    await waitFor(() => {
      const samplesOption = screen.getByText('samples');
      fireEvent.click(samplesOption);
    });

    const attrNameInput = screen.getByLabelText('Attribute Name');
    fireEvent.change(attrNameInput, { target: { value: 'test_attr' } });

    const dataTypeSelect = screen.getByLabelText('Data Type');
    fireEvent.mouseDown(dataTypeSelect);
    await waitFor(() => {
      const numberOption = screen.getByText('number');
      fireEvent.click(numberOption);
    });

    const validationRulesInput = screen.getByLabelText('Validation Rules');
    fireEvent.change(validationRulesInput, { target: { value: 'invalid json{' } });

    const submitButton = screen.getByText('Create');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(screen.getByText(/Validation rules must be valid JSON/i)).toBeInTheDocument();
    });
  });

  test('handles API error gracefully', async () => {
    const { apiService } = require('../services/apiService');
    apiService.getCustomAttributeConfigs.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<CustomFieldsManagement />);

    await waitFor(() => {
      expect(screen.getByText(/Failed to load custom fields/i)).toBeInTheDocument();
    });
  });

  test('displays validation rules in grid', async () => {
    renderWithProviders(<CustomFieldsManagement />);

    await waitFor(() => {
      // Validation rules should be displayed (formatted as JSON string)
      expect(screen.getByText(/min.*max/i)).toBeInTheDocument();
    });
  });

  test('shows active/inactive status chips', async () => {
    renderWithProviders(<CustomFieldsManagement />);

    await waitFor(() => {
      expect(screen.getAllByText('Active').length).toBeGreaterThan(0);
    });
  });
});

