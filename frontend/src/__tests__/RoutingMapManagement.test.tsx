import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

jest.mock('@mui/x-data-grid', () => ({
  DataGrid: () => <div role="grid">routing-map-grid</div>,
  GridActionsCellItem: () => null,
}));

import RoutingMapManagement from '../pages/admin/RoutingMapManagement';

jest.mock('../services/apiService', () => ({
  apiService: {
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
});
