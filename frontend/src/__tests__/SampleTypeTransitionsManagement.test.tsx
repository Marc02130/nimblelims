import React from 'react';
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react';
import SampleTypeTransitionsManagement from '../pages/admin/SampleTypeTransitionsManagement';
import { apiService } from '../services/apiService';
import * as UserContext from '../contexts/UserContext';

jest.mock('../services/apiService', () => ({
  ...jest.requireActual('../services/apiService'),
  apiService: {
    getCurrentUser: () => Promise.reject(new Error('no session')),
    getSampleTypeTransitions: jest.fn(),
    getListEntries: jest.fn(),
    createSampleTypeTransition: jest.fn(),
    updateSampleTypeTransition: jest.fn(),
    deleteSampleTypeTransition: jest.fn(),
  },
}));

const api = apiService as jest.Mocked<typeof apiService>;

const types = [
  { id: 'blood', name: 'Blood' },
  { id: 'dna', name: 'DNA' },
];

beforeEach(() => {
  jest
    .spyOn(UserContext, 'useUser')
    .mockReturnValue({ hasPermission: () => true } as unknown as ReturnType<
      typeof UserContext.useUser
    >);
  api.getSampleTypeTransitions.mockResolvedValue([
    {
      id: 't1',
      source_sample_type: 'blood',
      source_sample_type_name: 'Blood',
      operation: 'derivative',
      allowed_dest_sample_type: 'dna',
      allowed_dest_sample_type_name: 'DNA',
      active: true,
    },
  ]);
  api.getListEntries.mockResolvedValue(types);
  api.createSampleTypeTransition.mockResolvedValue({});
});

const pick = (label: RegExp, option: RegExp) => {
  fireEvent.mouseDown(screen.getByRole('combobox', { name: label }));
  fireEvent.click(within(screen.getByRole('listbox')).getByRole('option', { name: option }));
};

describe('SampleTypeTransitionsManagement', () => {
  it('lists derivative rows and explains aliquot vs derivative', async () => {
    render(<SampleTypeTransitionsManagement />);
    expect(await screen.findByText('derivative')).toBeInTheDocument();
    expect(screen.getByText(/Aliquots keep the type and/)).toBeInTheDocument();
  });

  it('new transitions default to derivative and offer no aliquot', async () => {
    render(<SampleTypeTransitionsManagement />);
    await screen.findByText('derivative');
    fireEvent.click(screen.getByRole('button', { name: /Add transition/i }));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText(/Blood → DNA or Blood → Plasma is a derivative/)).toBeInTheDocument();

    fireEvent.mouseDown(within(dialog).getByRole('combobox', { name: /Operation/ }));
    const listbox = screen.getByRole('listbox');
    expect(within(listbox).getByRole('option', { name: /derivative/ })).toBeInTheDocument();
    expect(within(listbox).getByRole('option', { name: /pool/ })).toBeInTheDocument();
    expect(within(listbox).queryByRole('option', { name: /^aliquot/ })).toBeNull();
    fireEvent.click(within(listbox).getByRole('option', { name: /derivative/ }));

    pick(/Source sample type/, /Blood/);
    pick(/Dest sample type/, /DNA/);
    fireEvent.click(within(dialog).getByRole('button', { name: /Save|Create/i }));
    await waitFor(() =>
      expect(api.createSampleTypeTransition).toHaveBeenCalledWith(
        expect.objectContaining({
          source_sample_type: 'blood',
          operation: 'derivative',
          allowed_dest_sample_type: 'dna',
        }),
      ),
    );
  });
});
