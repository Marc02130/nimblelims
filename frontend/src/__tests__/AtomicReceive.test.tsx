import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import AtomicReceive from '../pages/AtomicReceive';

const mockReceiveSample = jest.fn();
const mockGetListEntries = jest.fn();
const mockGetProjects = jest.fn();

jest.mock('../services/apiService', () => ({
  apiService: {
    getListEntries: (...args: any[]) => mockGetListEntries(...args),
    getProjects: (...args: any[]) => mockGetProjects(...args),
    receiveSample: (...args: any[]) => mockReceiveSample(...args),
    getCurrentUser: jest.fn().mockResolvedValue({
      id: '1',
      username: 'tech',
      email: 'tech@example.com',
      role: { name: 'Lab Technician' },
      permissions: ['sample:create'],
    }),
  },
}));

// Avoid UserProvider network — AtomicReceive does not require user context
jest.mock('../contexts/UserContext', () => ({
  useUser: () => ({
    user: {
      id: '1',
      username: 'tech',
      permissions: ['sample:create'],
    },
    hasPermission: (p: string) => p === 'sample:create',
    loading: false,
  }),
  UserProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

const theme = createTheme();

const renderPage = () =>
  render(
    <MemoryRouter>
      <ThemeProvider theme={theme}>
        <AtomicReceive />
      </ThemeProvider>
    </MemoryRouter>
  );

describe('AtomicReceive', () => {
  beforeEach(() => {
    sessionStorage.clear();
    jest.clearAllMocks();
    mockGetListEntries.mockImplementation(async (name: string) => {
      if (String(name).toLowerCase().includes('sample')) {
        return [{ id: 'type-1', name: 'Blood' }];
      }
      return [{ id: 'matrix-1', name: 'Serum' }];
    });
    mockGetProjects.mockImplementation(async (filters?: { size?: number }) => {
      // Guard: backend le=100 — UI must not request size > 100
      if (filters?.size != null && filters.size > 100) {
        const err: any = new Error('Unprocessable Entity');
        err.response = {
          status: 422,
          data: {
            detail: [
              {
                type: 'less_than_equal',
                loc: ['query', 'size'],
                msg: 'Input should be less than or equal to 100',
                input: filters.size,
                ctx: { le: 100 },
              },
            ],
          },
        };
        throw err;
      }
      return { projects: [{ id: 'proj-1', name: 'Study A' }] };
    });
    mockReceiveSample.mockResolvedValue({
      sample_id: 's1',
      sample_name: 'S-100',
      containers: [{ id: 'c1', barcode: 'NBIO-1' }],
      tests: [],
    });
  });

  test('renders receive loop without sample-ID or status fields', async () => {
    renderPage();
    expect(await screen.findByRole('heading', { name: 'Receive' })).toBeInTheDocument();
    expect(screen.getByTestId('primary-barcode')).toBeInTheDocument();
    expect(screen.queryByLabelText(/lab sample id/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^status$/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/container type/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/asked-for analyses/i)).not.toBeInTheDocument();
  });

  test('adds additional barcode chips', async () => {
    renderPage();
    await screen.findByTestId('primary-barcode');
    fireEvent.change(screen.getByTestId('additional-barcode-draft'), {
      target: { value: 'NBIO-EXTRA-1' },
    });
    fireEvent.click(screen.getByLabelText('Add additional barcode'));
    expect(screen.getByTestId('extra-barcode-NBIO-EXTRA-1')).toBeInTheDocument();
  });

  test('submits receive and clears barcodes', async () => {
    renderPage();
    const primary = await screen.findByTestId('primary-barcode');

    fireEvent.mouseDown(screen.getByRole('combobox', { name: /sample type/i }));
    fireEvent.click(await screen.findByRole('option', { name: 'Blood' }));
    fireEvent.mouseDown(screen.getByRole('combobox', { name: /^matrix$/i }));
    fireEvent.click(await screen.findByRole('option', { name: 'Serum' }));
    fireEvent.mouseDown(screen.getByRole('combobox', { name: /^project$/i }));
    fireEvent.click(await screen.findByRole('option', { name: 'Study A' }));

    fireEvent.change(primary, { target: { value: 'NBIO-1' } });
    fireEvent.click(screen.getByTestId('receive-submit'));

    await waitFor(() => {
      expect(mockReceiveSample).toHaveBeenCalledWith(
        expect.objectContaining({
          container_barcode: 'NBIO-1',
          sample_type: 'type-1',
          matrix: 'matrix-1',
          project_id: 'proj-1',
        })
      );
    });
    expect(mockReceiveSample.mock.calls[0][0]).not.toHaveProperty('analysis_ids');

    await waitFor(() => {
      expect((screen.getByTestId('primary-barcode') as HTMLInputElement).value).toBe('');
    });
    expect(await screen.findByText(/Received S-100/i)).toBeInTheDocument();
  });
});
