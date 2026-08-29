import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

jest.mock('@mui/x-data-grid', () => ({
  DataGrid: () => <div role="grid">work-orders-grid</div>,
  GridActionsCellItem: () => null,
}));

import WorkOrders from '../pages/WorkOrders';

jest.mock('../services/apiService', () => ({
  apiService: {
    getWorkOrders: jest.fn().mockResolvedValue({ items: [], count: 0 }),
    startWorkOrder: jest.fn(),
  },
  ApiService: {
    formatError: (_err: unknown, fallback: string) => fallback,
  },
}));

jest.mock('../contexts/UserContext', () => ({
  useUser: () => ({
    user: { id: '1', username: 'mgr', permissions: ['experiment:manage'] },
    hasPermission: (p: string) => p === 'experiment:manage',
    loading: false,
  }),
}));

const theme = createTheme();

describe('WorkOrders', () => {
  test('renders work orders heading and does not mint Tests on this page', async () => {
    render(
      <MemoryRouter>
        <ThemeProvider theme={theme}>
          <WorkOrders />
        </ThemeProvider>
      </MemoryRouter>
    );
    expect(screen.getByText('Work orders')).toBeInTheDocument();
    expect(screen.queryByText(/Assign test/i)).not.toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole('grid')).toBeInTheDocument();
    });
  });
});
