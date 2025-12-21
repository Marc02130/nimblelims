import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import AliquotForm from '../components/aliquots/AliquotForm';
import { apiService } from '../services/apiService';

// Mock the API service
jest.mock('../services/apiService');
const mockApiService = apiService as jest.Mocked<typeof apiService>;

const mockParentSampleId = 'parent-sample-123';

const defaultProps = {
  parentSampleId: mockParentSampleId,
  onSuccess: jest.fn(),
  onCancel: jest.fn(),
};

const mockListEntries = {
  sample_types: [
    { id: 'type1', name: 'Blood' },
    { id: 'type2', name: 'Urine' },
  ],
  matrices: [
    { id: 'matrix1', name: 'Serum' },
    { id: 'matrix2', name: 'Plasma' },
  ],
};

const mockUnits = [
  { id: 'unit1', name: 'mg/L', type: 'concentration' },
  { id: 'unit2', name: 'g', type: 'mass' },
  { id: 'unit3', name: 'mL', type: 'volume' },
];

const mockContainerTypes = [
  { id: 'container1', name: 'Tube' },
  { id: 'container2', name: 'Plate' },
];

const renderWithProviders = (component: React.ReactElement) => {
  return render(
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      {component}
    </LocalizationProvider>
  );
};

describe('AliquotForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock API calls
    mockApiService.getListEntries.mockImplementation((listName: string) => {
      if (listName === 'sample_types') return Promise.resolve(mockListEntries.sample_types);
      if (listName === 'matrices') return Promise.resolve(mockListEntries.matrices);
      return Promise.resolve([]);
    });
    
    mockApiService.getUnits.mockResolvedValue(mockUnits);
    mockApiService.getContainerTypes.mockResolvedValue(mockContainerTypes);
  });

  it('renders the form with all required fields', async () => {
    renderWithProviders(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Create Aliquot')).toBeInTheDocument();
    });

    expect(screen.getByLabelText('Aliquot Name')).toBeInTheDocument();
    expect(screen.getByLabelText('Description')).toBeInTheDocument();
    expect(screen.getByLabelText('Sample Type')).toBeInTheDocument();
    expect(screen.getByLabelText('Matrix')).toBeInTheDocument();
    expect(screen.getByLabelText('Temperature')).toBeInTheDocument();
    expect(screen.getByLabelText('Due Date')).toBeInTheDocument();
    expect(screen.getByLabelText('Container Type')).toBeInTheDocument();
  });

  it('loads and populates dropdown options', async () => {
    renderWithProviders(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(mockApiService.getListEntries).toHaveBeenCalledWith('sample_types');
      expect(mockApiService.getListEntries).toHaveBeenCalledWith('matrices');
      expect(mockApiService.getUnits).toHaveBeenCalled();
      expect(mockApiService.getContainerTypes).toHaveBeenCalled();
    });
  });

  it('handles form input changes', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByLabelText('Aliquot Name')).toBeInTheDocument();
    });

    const nameInput = screen.getByLabelText('Aliquot Name');
    await user.type(nameInput, 'Test Aliquot');

    expect(nameInput).toHaveValue('Test Aliquot');
  });

  it('submits the form with correct data', async () => {
    const user = userEvent.setup();
    mockApiService.createAliquot.mockResolvedValue({ id: 'new-aliquot-123' });

    renderWithProviders(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByLabelText('Aliquot Name')).toBeInTheDocument();
    });

    // Fill in required fields
    await user.type(screen.getByLabelText('Aliquot Name'), 'Test Aliquot');
    await user.type(screen.getByLabelText('Description'), 'Test Description');
    await user.type(screen.getByLabelText('Temperature'), '25');

    // Select dropdowns
    await user.click(screen.getByLabelText('Sample Type'));
    await user.click(screen.getByText('Blood'));

    await user.click(screen.getByLabelText('Matrix'));
    await user.click(screen.getByText('Serum'));

    await user.click(screen.getByLabelText('Container Type'));
    await user.click(screen.getByText('Tube'));

    // Submit form
    await user.click(screen.getByText('Create Aliquot'));

    await waitFor(() => {
      expect(mockApiService.createAliquot).toHaveBeenCalledWith(
        expect.objectContaining({
          parent_sample_id: mockParentSampleId,
          name: 'Test Aliquot',
          description: 'Test Description',
          temperature: 25,
        })
      );
    });

    expect(defaultProps.onSuccess).toHaveBeenCalledWith({ id: 'new-aliquot-123' });
  });

  it('handles API errors gracefully', async () => {
    const user = userEvent.setup();
    mockApiService.createAliquot.mockRejectedValue(new Error('API Error'));

    renderWithProviders(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByLabelText('Aliquot Name')).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText('Aliquot Name'), 'Test Aliquot');
    await user.click(screen.getByText('Create Aliquot'));

    await waitFor(() => {
      expect(screen.getByText('API Error')).toBeInTheDocument();
    });
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    renderWithProviders(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Cancel'));

    expect(defaultProps.onCancel).toHaveBeenCalled();
  });

  it('shows loading state during submission', async () => {
    const user = userEvent.setup();
    mockApiService.createAliquot.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

    renderWithProviders(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByLabelText('Aliquot Name')).toBeInTheDocument();
    });

    await user.type(screen.getByLabelText('Aliquot Name'), 'Test Aliquot');
    await user.click(screen.getByText('Create Aliquot'));

    expect(screen.getByText('Create Aliquot')).toBeDisabled();
  });
});
