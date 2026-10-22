import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ValueChoicesPanel from '../components/runs/ValueChoicesPanel';

const mockGet = jest.fn();
const mockAccept = jest.fn();

jest.mock('../services/apiService', () => ({
  apiService: {
    getLimsRunValueChoices: (...args: any[]) => mockGet(...args),
    acceptLimsRunValue: (...args: any[]) => mockAccept(...args),
  },
}));

const theme = createTheme();

const row = {
  sample_id: 's1',
  client_sample_id: 'IL6-SER-0001',
  analyte_id: 'a1',
  analyte_name: 'IL-6',
  replicate: 1,
  options: [
    {
      lims_run_id: 'run-old',
      run_name: 'Plate 1',
      run_status: 'failed',
      raw_result: '0.063',
      source: 'result',
    },
    {
      lims_run_id: 'run-new',
      run_name: 'Plate 1 rerun',
      run_status: 'published',
      raw_result: '0.070',
      source: 'import',
    },
  ],
};

describe('ValueChoicesPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGet.mockResolvedValue([row]);
    mockAccept.mockResolvedValue({ ...row, accepted_lims_run_id: 'run-new', accepted_value: '0.070' });
  });

  test('accept sends the picked run and the reason', async () => {
    render(
      <ThemeProvider theme={theme}>
        <ValueChoicesPanel runId="run-new" />
      </ThemeProvider>
    );
    expect(await screen.findByText('IL6-SER-0001')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/Plate 1 rerun/));
    fireEvent.change(screen.getByLabelText('Reason for IL6-SER-0001'), {
      target: { value: 'Rerun within range' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Accept' }));
    await waitFor(() => {
      expect(mockAccept).toHaveBeenCalledWith('run-new', {
        sample_id: 's1',
        analyte_id: 'a1',
        replicate: 1,
        accepted_lims_run_id: 'run-new',
        reason: 'Rerun within range',
      });
    });
  });
});
