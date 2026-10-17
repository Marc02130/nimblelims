import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

jest.mock('@mui/x-data-grid', () => ({
  DataGrid: () => <div role="grid">asked-for-grid</div>,
  GridActionsCellItem: () => null,
}));

import AskedFor from '../pages/AskedFor';
import AskedForForm from '../components/asked-for/AskedForForm';
import { apiService } from '../services/apiService';

jest.mock('../services/apiService', () => ({
  // Real helpers (ApiService.formatError, addClientFilterIfNeeded, types); only the client is mocked.
  ...jest.requireActual('../services/apiService'),
  apiService: {
    // UserProvider probes the cookie session on mount (P4/S10). Plain fn: survives resetMocks.
    getCurrentUser: () => Promise.reject(new Error('no session')),
    getAskedFor: jest.fn().mockResolvedValue({ items: [], count: 0 }),
    getSamples: jest.fn().mockResolvedValue([]),
    getListEntries: jest.fn().mockResolvedValue([]),
    getAnalyses: jest.fn().mockResolvedValue({ analyses: [] }),
    getAnalysisParamDefs: jest.fn().mockResolvedValue({ items: [], count: 0 }),
    createAskedFor: jest.fn(),
    cancelAskedFor: jest.fn(),
    routeAskedFor: jest.fn(),
    routeAskedForBatch: jest.fn(),
  },
  ApiService: {
    unwrapAnalysesList: (res: { analyses?: unknown[] } | unknown[] | null | undefined) =>
      Array.isArray(res) ? res : res?.analyses ?? [],
    formatError: (_err: unknown, fallback: string) => fallback,
  },
}));

jest.mock('../contexts/UserContext', () => ({
  useUser: () => ({
    user: { id: '1', username: 'tech', permissions: ['test:assign', 'sample:read'] },
    hasPermission: (p: string) => p === 'test:assign' || p === 'sample:read',
    loading: false,
  }),
}));

const theme = createTheme();

describe('AskedFor', () => {
  test('renders Asked-for heading and does not look like Test assignment', async () => {
    render(
      <MemoryRouter>
        <ThemeProvider theme={theme}>
          <AskedFor />
        </ThemeProvider>
      </MemoryRouter>
    );

    expect(screen.getByText('Asked-for')).toBeInTheDocument();
    expect(screen.getAllByText(/Record requested analysis/i).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Assign test/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Start$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Execute/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Route selected/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole('grid')).toBeInTheDocument();
    });
  });
});

describe('AskedForForm TAT', () => {
  test('accepts TAT of 0 and refuses a negative value', async () => {
    (apiService.getAnalyses as jest.Mock).mockResolvedValue({
      analyses: [{ id: 'a1', name: 'ELISA', turnaround_time: 5 }],
    });
    (apiService.getAnalysisParamDefs as jest.Mock).mockResolvedValue({
      items: [],
      count: 0,
    });
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();

    render(
      <ThemeProvider theme={theme}>
        <AskedForForm
          lockSamples
          sampleIds={['sample-1']}
          onSubmit={onSubmit}
          onCancel={jest.fn()}
        />
      </ThemeProvider>
    );

    await user.click(screen.getByRole('combobox', { name: /Requested analysis/ }));
    await user.click(await screen.findByRole('option', { name: 'ELISA' }));

    const tat = screen.getByLabelText(/TAT \(days\)/);
    fireEvent.change(tat, { target: { value: '0' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record asked-for' }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });
    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        sample_ids: ['sample-1'],
        analysis_id: 'a1',
        tat_days: 0,
      })
    );
    expect(screen.queryByText(/0 or greater/i)).not.toBeInTheDocument();

    fireEvent.change(tat, { target: { value: '-1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record asked-for' }));

    expect(await screen.findByText(/TAT must be an integer of 0 or greater/i)).toBeInTheDocument();
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });
});
