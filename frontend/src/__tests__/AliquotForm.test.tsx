import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AliquotForm from '../components/aliquots/AliquotForm';
import { apiService } from '../services/apiService';

jest.mock('../services/apiService');
const mockApiService = apiService as jest.Mocked<typeof apiService>;

const mockParentSampleId = 'parent-sample-123';

const defaultProps = {
  parentSampleId: mockParentSampleId,
  onSuccess: jest.fn(),
  onCancel: jest.fn(),
};

const mockUnits = [
  { id: 'unit1', name: 'mg/L', type_name: 'concentration' },
  { id: 'unit2', name: 'g', type_name: 'mass' },
  { id: 'unit3', name: 'mL', type_name: 'volume' },
];

const mockContainers = [
  { id: 'container-dest', name: 'Tube A' },
  { id: 'container-source', name: 'Tube B' },
];

describe('AliquotForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApiService.getUnits.mockResolvedValue(mockUnits);
    mockApiService.getContainers.mockResolvedValue(mockContainers);
  });

  it('renders the form with all required fields', async () => {
    render(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Create Aliquot' })).toBeInTheDocument();
    });

    expect(screen.getByText(/same sample in another container/i)).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /^Destination container/ })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /^Source container/ })).toBeInTheDocument();
    expect(screen.getByRole('spinbutton', { name: /^Amount/ })).toBeInTheDocument();
  });

  it('loads and populates dropdown options', async () => {
    render(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(mockApiService.getUnits).toHaveBeenCalled();
      expect(mockApiService.getContainers).toHaveBeenCalled();
    });
  });

  it('handles form input changes', async () => {
    const user = userEvent.setup();
    render(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByRole('spinbutton', { name: /^Amount/ })).toBeInTheDocument();
    });

    const amountInput = screen.getByRole('spinbutton', { name: /^Amount/ });
    await user.clear(amountInput);
    await user.type(amountInput, '4');

    expect(amountInput).toHaveValue(4);
  });

  it('submits the form with correct data', async () => {
    const user = userEvent.setup();
    mockApiService.createAliquot.mockResolvedValue({ id: mockParentSampleId });

    render(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByRole('spinbutton', { name: /^Amount/ })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('combobox', { name: /^Destination container/ }));
    await user.click(await screen.findByRole('option', { name: 'Tube A' }));

    const amountInput = screen.getByRole('spinbutton', { name: /^Amount/ });
    await user.clear(amountInput);
    await user.type(amountInput, '2');

    await user.click(screen.getByRole('button', { name: 'Create Aliquot' }));

    await waitFor(() => {
      expect(mockApiService.createAliquot).toHaveBeenCalledWith(
        expect.objectContaining({
          parent_sample_id: mockParentSampleId,
          container_id: 'container-dest',
          amount: 2,
        })
      );
    });

    expect(mockApiService.createAliquot).toHaveBeenCalledWith(
      expect.not.objectContaining({ sample_type: expect.anything() })
    );
    expect(mockApiService.createAliquot).toHaveBeenCalledWith(
      expect.not.objectContaining({ concentration: expect.anything() })
    );
    expect(defaultProps.onSuccess).toHaveBeenCalledWith({ id: mockParentSampleId });
  });

  it('sends a concentration of 0', async () => {
    const user = userEvent.setup();
    mockApiService.createAliquot.mockResolvedValue({ id: mockParentSampleId });

    render(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByRole('spinbutton', { name: /^Amount/ })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('combobox', { name: /^Destination container/ }));
    await user.click(await screen.findByRole('option', { name: 'Tube A' }));
    const amountInput = screen.getByRole('spinbutton', { name: /^Amount/ });
    await user.clear(amountInput);
    await user.type(amountInput, '2');
    await user.type(screen.getByRole('spinbutton', { name: /^Concentration/ }), '0');
    await user.click(screen.getByRole('button', { name: 'Create Aliquot' }));

    await waitFor(() => {
      expect(mockApiService.createAliquot).toHaveBeenCalledWith(
        expect.objectContaining({ amount: 2, concentration: 0 })
      );
    });
  });

  it('handles API errors gracefully', async () => {
    const user = userEvent.setup();
    mockApiService.createAliquot.mockRejectedValue({ response: { data: { detail: 'API Error' } } });

    render(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByRole('spinbutton', { name: /^Amount/ })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('combobox', { name: /^Destination container/ }));
    await user.click(await screen.findByRole('option', { name: 'Tube A' }));
    const amountInput = screen.getByRole('spinbutton', { name: /^Amount/ });
    await user.clear(amountInput);
    await user.type(amountInput, '2');
    await user.click(screen.getByRole('button', { name: 'Create Aliquot' }));

    await waitFor(() => {
      expect(screen.getByText('API Error')).toBeInTheDocument();
    });
  });

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup();
    render(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('Cancel')).toBeInTheDocument();
    });

    await user.click(screen.getByText('Cancel'));

    expect(defaultProps.onCancel).toHaveBeenCalled();
  });

  it('shows loading state during submission', async () => {
    const user = userEvent.setup();
    mockApiService.createAliquot.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

    render(<AliquotForm {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByRole('spinbutton', { name: /^Amount/ })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('combobox', { name: /^Destination container/ }));
    await user.click(await screen.findByRole('option', { name: 'Tube A' }));
    const amountInput = screen.getByRole('spinbutton', { name: /^Amount/ });
    await user.clear(amountInput);
    await user.type(amountInput, '2');
    await user.click(screen.getByRole('button', { name: 'Create Aliquot' }));

    expect(screen.getByRole('button', { name: 'Create Aliquot' })).toBeDisabled();
  });
});
