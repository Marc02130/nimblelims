import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DerivativeForm from '../components/aliquots/DerivativeForm';
import { apiService } from '../services/apiService';

jest.mock('../services/apiService');
const mockApiService = apiService as jest.Mocked<typeof apiService>;

const defaultProps = {
  parentSampleId: 'parent-sample-123',
  onSuccess: jest.fn(),
  onCancel: jest.fn(),
};

describe('DerivativeForm', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockApiService.getListEntries.mockResolvedValue([{ id: 'dna', name: 'DNA' }]);
    mockApiService.getUnits.mockResolvedValue([
      { id: 'unit-mass', name: 'g', type_name: 'mass' },
    ]);
    mockApiService.getContainers.mockResolvedValue([{ id: 'tube', name: 'Tube A' }]);
    mockApiService.createDerivative.mockResolvedValue({ id: 'child' });
  });

  async function fillRequired() {
    const user = userEvent.setup();
    render(<DerivativeForm {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByRole('spinbutton', { name: /^Amount/ })).toBeInTheDocument();
    });
    await user.click(screen.getByRole('combobox', { name: /^Sample Type/ }));
    await user.click(await screen.findByRole('option', { name: 'DNA' }));
    await user.click(screen.getByRole('combobox', { name: /^Destination container/ }));
    await user.click(await screen.findByRole('option', { name: 'Tube A' }));
    const amount = screen.getByRole('spinbutton', { name: /^Amount/ });
    await user.clear(amount);
    await user.type(amount, '2');
    return user;
  }

  it('sends a temperature of 0 and omits a blank temperature', async () => {
    const user = await fillRequired();
    await user.type(screen.getByRole('spinbutton', { name: /^Temperature/ }), '0');
    await user.click(screen.getByRole('button', { name: 'Create Derivative' }));

    await waitFor(() => {
      expect(mockApiService.createDerivative).toHaveBeenCalledWith(
        expect.objectContaining({ temperature: 0, amount: 2 })
      );
    });
  });

  it('omits temperature when the field is left blank', async () => {
    const user = await fillRequired();
    await user.click(screen.getByRole('button', { name: 'Create Derivative' }));

    await waitFor(() => {
      expect(mockApiService.createDerivative).toHaveBeenCalled();
    });
    expect(mockApiService.createDerivative).toHaveBeenCalledWith(
      expect.not.objectContaining({ temperature: expect.anything() })
    );
  });
});
