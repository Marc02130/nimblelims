import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import BatchForm from '../components/batches/BatchForm';
import { apiService } from '../services/apiService';

// Mock the API service
jest.mock('../services/apiService');
const mockApiService = apiService as jest.Mocked<typeof apiService>;

const defaultProps = {
  onSuccess: jest.fn(),
  onCancel: jest.fn(),
};

const mockListEntries = {
  batch_types: [
    { id: 'type1', name: 'Analysis' },
    { id: 'type2', name: 'QC' },
  ],
  batch_statuses: [
    { id: 'status1', name: 'Created' },
    { id: 'status2', name: 'In Process' },
    { id: 'status3', name: 'Completed' },
  ],
};

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      {component}
    </LocalizationProvider>
  );
};

describe('BatchForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock API calls
    mockApiService.getListEntries.mockImplementation((listName: string) => {
      if (listName === 'batch_types') return Promise.resolve(mockListEntries.batch_types);
      if (listName === 'batch_statuses') return Promise.resolve(mockListEntries.batch_statuses);
      return Promise.resolve([]);
    });
  });

  it('renders the form with all required fields', async () => {
    renderWithProviders(<BatchForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Create New Batch')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('Batch Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
    expect(screen.getByLabelText('Batch Type')).toBeInTheDocument();
    expect(screen.getByLabelText('Status')).toBeInTheDocument();
    expect(screen.getByLabelText('Start Date')).toBeInTheDocument();
    expect(screen.getByLabelText('End Date')).toBeInTheDocument();
  });

  it('loads and populates dropdown options', async () => {
    renderWithProviders(<BatchForm {...defaultProps} />);

    await waitFor(() => {
      expect(mockApiService.getListEntries).toHaveBeenCalledWith('batch_types');
      expect(mockApiService.getListEntries).toHaveBeenCalledWith('batch_statuses');
    });
  });

  it('sets default status to Created', async () => {
    renderWithProviders(<BatchForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByLabelText('Status')).toBeInTheDocument();
    });

    // The status should be set to 'Created' by default
    expect(screen.getByDisplayValue('Created')).toBeInTheDocument();
  });

  it('handles form input changes', async () => {
    const user = userEvent.setup();
    renderWithProviders(<BatchForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByLabelText('Batch Name')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText('Batch Name');
    await user.type(nameInput, 'Test Batch');

    expect(nameInput).toHaveValue('Test Batch');
  });

  it('submits the form with correct data', async () => {
    const user = userEvent.setup();
    mockApiService.createBatch.mockResolvedValue({ id: 'new-batch-123' });

    renderWithProviders(<BatchForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByLabelText('Batch Name')).toBeInTheDocument();
    });

    // Fill in required fields
    await user.type(screen.getByLabelText('Batch Name'), 'Test Batch');
    await user.type(screen.getByLabelText('Description'), 'Test Description');

    // Select batch type
    await user.click(screen.getByLabelText('Batch Type'));
    await user.click(screen.getByText('Analysis'));

    // Submit form
    await user.click(screen.getByText('Create Batch'));

    await waitFor(() => {
      expect(mockApiService.createBatch).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'Test Batch',
          description: 'Test Description',
          type: 'type1', // Analysis type ID
          status: 'status1', // Created status ID
        })
      );
    });

    expect(defaultProps.onSuccess).toHaveBeenCalledWith({ id: 'new-batch-123' });
  });

  it('handles API errors gracefully', async () => {
    const user = userEvent.setup();
    mockApiService.createBatch.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<BatchForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByLabelText('Batch Name')).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText('Batch Name'), 'Test Batch');
    await user.click(screen.getByText('Create Batch'));

    await waitFor(() => {
      expect(screen.getByText('API Error')).toBeInTheDocument();
    });
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<BatchForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Cancel'));

    expect(defaultProps.onCancel).toHaveBeenCalled();
  });

  it('shows loading state during submission', async () => {
    const user = userEvent.setup();
    mockApiService.createBatch.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

    renderWithProviders(<BatchForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByLabelText('Batch Name')).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText('Batch Name'), 'Test Batch');
    await user.click(screen.getByText('Create Batch'));

    expect(screen.getByText('Create Batch')).toBeDisabled();
  });
});
