import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

jest.mock('@mui/x-data-grid', () => ({
  DataGrid: () => <div role="grid">routing-map-grid</div>,
  GridActionsCellItem: () => null,
}));

import RoutingMapManagement from '../pages/admin/RoutingMapManagement';

jest.mock('../services/apiService', () => ({
  // Real helpers (ApiService.formatError, addClientFilterIfNeeded, types); only the client is mocked.
  ...jest.requireActual('../services/apiService'),
  apiService: {
    // UserProvider probes the cookie session on mount (P4/S10). Plain fn: survives resetMocks.
    getCurrentUser: () => Promise.reject(new Error('no session')),
    getRoutingMap: jest.fn().mockResolvedValue([]),
    getAnalyses: jest.fn().mockResolvedValue({ analyses: [] }),
    getListEntries: jest.fn().mockResolvedValue([]),
    getElnProcessDefinitions: jest.fn().mockResolvedValue({ definitions: [] }),
    getElnProcessDefinition: jest.fn().mockResolvedValue({ id: 'd1', name: 'SOP', steps: [] }),
    getStepAcceptedSampleTypes: jest.fn().mockResolvedValue({ sample_type_ids: [] }),
    createRoutingMap: jest.fn(),
    deleteRoutingMap: jest.fn(),
  },
  ApiService: {
    unwrapAnalysesList: () => [],
    formatError: (_err: unknown, fallback: string) => fallback,
  },
}));

jest.mock('../contexts/UserContext', () => ({
  useUser: () => ({
    user: { id: '1', username: 'admin', permissions: ['config:edit'] },
    hasPermission: (p: string) => p === 'config:edit',
    loading: false,
  }),
}));

const theme = createTheme();

describe('RoutingMapManagement', () => {
  test('renders routing map heading', async () => {
    render(
      <MemoryRouter>
        <ThemeProvider theme={theme}>
          <RoutingMapManagement />
        </ThemeProvider>
      </MemoryRouter>
    );
    expect(screen.getByText('Routing map')).toBeInTheDocument();
    expect(screen.getByText(/Add route/i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole('grid')).toBeInTheDocument();
    });
  });

  test('accepts TAT min of 0 and refuses a negative minimum', async () => {
    render(
      <MemoryRouter>
        <ThemeProvider theme={theme}>
          <RoutingMapManagement />
        </ThemeProvider>
      </MemoryRouter>
    );

    fireEvent.click(screen.getByRole('button', { name: /Add route/i }));
    const tatMin = await screen.findByLabelText('TAT min');
    fireEvent.change(tatMin, { target: { value: '0' } });

    expect(screen.queryByText(/TAT min must be an integer of 0 or greater/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/at least 1/i)).not.toBeInTheDocument();

    fireEvent.change(tatMin, { target: { value: '-1' } });
    expect(await screen.findByText(/TAT min must be an integer of 0 or greater/i)).toBeInTheDocument();

    fireEvent.change(tatMin, { target: { value: '5' } });
    fireEvent.change(screen.getByLabelText('TAT max'), { target: { value: '0' } });
    expect(
      await screen.findByText(/TAT max must be greater than or equal to TAT min/i)
    ).toBeInTheDocument();
  });
});
