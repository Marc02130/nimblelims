import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';

jest.mock('@mui/x-data-grid', () => ({
  DataGrid: () => <div role="grid">asked-for-grid</div>,
  GridActionsCellItem: () => null,
}));

import AskedFor from '../pages/AskedFor';

jest.mock('../services/apiService', () => ({
  apiService: {
    getAskedFor: jest.fn().mockResolvedValue({ items: [], count: 0 }),
    getSamples: jest.fn().mockResolvedValue([]),
    getListEntries: jest.fn().mockResolvedValue([]),
    getAnalyses: jest.fn().mockResolvedValue({ analyses: [] }),
    getAnalysisParamDefs: jest.fn().mockResolvedValue({ items: [], count: 0 }),
    createAskedFor: jest.fn(),
    cancelAskedFor: jest.fn(),
  },
  ApiService: {
    unwrapAnalysesList: () => [],
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
    expect(screen.getByText(/Record requested analysis/i)).toBeInTheDocument();
    expect(screen.queryByText(/Assign test/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Start$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Execute/i)).not.toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole('grid')).toBeInTheDocument();
    });
  });
});
