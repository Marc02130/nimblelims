import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import AtomicReceive from '../pages/AtomicReceive';

const mockReceiveSample = jest.fn();
const mockGetListEntries = jest.fn();
const mockGetProjects = jest.fn();
const mockGetContainerTypes = jest.fn();

jest.mock('../services/apiService', () => ({
  apiService: {
    getListEntries: (...args: any[]) => mockGetListEntries(...args),
    getProjects: (...args: any[]) => mockGetProjects(...args),
    getContainerTypes: (...args: any[]) => mockGetContainerTypes(...args),
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
    mockGetListEntries.mockResolvedValue([{ id: 'type-1', name: 'Blood' }]);
    mockGetProjects.mockImplementation(async (filters?: { size?: number }) => {
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
    mockGetContainerTypes.mockResolvedValue([
      { id: 'ct-cryo', name: 'Cryovial (2mL)', rows: 1, columns: 1 },
      { id: 'ct-plate', name: '96-Well Plate', rows: 8, columns: 12 },
      { id: 'ct-conical', name: '15mL Conical Tube', rows: 1, columns: 1 },
    ]);
    mockReceiveSample.mockResolvedValue({
      sample_id: 's1',
      sample_name: 'S-100',
      containers: [{ id: 'c1', barcode: 'NBIO-1' }],
      tests: [],
    });
  });

  test('renders receive loop with sticky 1x1 container type, no sample-ID/status', async () => {
    renderPage();
    expect(await screen.findByRole('heading', { name: 'Receive' })).toBeInTheDocument();
    expect(screen.getByTestId('primary-barcode')).toBeInTheDocument();
    expect(screen.getByTestId('container-type')).toBeInTheDocument();
    expect(screen.queryByLabelText(/lab sample id/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^status$/i)).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox', { name: /^matrix$/i })).not.toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: /sample type/i })).toBeInTheDocument();
    // Plate must not appear in options
    fireEvent.mouseDown(screen.getByRole('combobox', { name: /container type/i }));
    expect(screen.queryByRole('option', { name: /96-Well Plate/i })).not.toBeInTheDocument();
    expect(screen.getByRole('option', { name: /Cryovial/i })).toBeInTheDocument();
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

  test('submits receive with container_type_id and clears barcodes', async () => {
    renderPage();
    const primary = await screen.findByTestId('primary-barcode');

    fireEvent.mouseDown(screen.getByRole('combobox', { name: /sample type/i }));
    fireEvent.click(await screen.findByRole('option', { name: 'Blood' }));
    fireEvent.mouseDown(screen.getByRole('combobox', { name: /^project$/i }));
    fireEvent.click(await screen.findByRole('option', { name: 'Study A' }));
    // Cryovial auto-selected as sticky default among 1×1 types

    fireEvent.change(primary, { target: { value: 'NBIO-1' } });
    fireEvent.click(screen.getByTestId('receive-submit'));

    await waitFor(() => {
      expect(mockReceiveSample).toHaveBeenCalledWith(
        expect.objectContaining({
          container_barcode: 'NBIO-1',
          sample_type: 'type-1',
          project_id: 'proj-1',
          container_type_id: 'ct-cryo',
        })
      );
      expect(mockReceiveSample.mock.calls[0][0].matrix).toBeUndefined();
    });

    await waitFor(() => {
      expect((screen.getByTestId('primary-barcode') as HTMLInputElement).value).toBe('');
    });
    expect(await screen.findByText(/Received S-100/i)).toBeInTheDocument();
  });
});
