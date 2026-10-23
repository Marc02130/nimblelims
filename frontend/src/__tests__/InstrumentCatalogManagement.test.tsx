import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';

jest.mock('@mui/x-data-grid', () => ({
  DataGrid: ({ rows, columns }: { rows: any[]; columns: any[] }) => (
    <div role="grid">
      {columns.map((c) => (
        <span key={c.field}>{c.headerName}</span>
      ))}
      {rows.map((row) => (
        <div key={row.id}>
          {Object.values(row).map((v, i) => (
            <span key={i}>{String(v ?? '')}</span>
          ))}
        </div>
      ))}
    </div>
  ),
  GridActionsCellItem: () => null,
}));

import InstrumentCatalogManagement from '../pages/admin/InstrumentCatalogManagement';
import { apiService } from '../services/apiService';

jest.mock('../services/apiService', () => ({
  ...jest.requireActual('../services/apiService'),
  apiService: {
    getInstrumentTypes: jest.fn(),
    getInstruments: jest.fn(),
    getCroSources: jest.fn(),
    getInstrumentMaintenanceSchedules: jest.fn(),
    getInstrumentDowntime: jest.fn(),
    getVendors: jest.fn(),
    getClients: jest.fn(),
    getListEntries: jest.fn(),
    createInstrument: jest.fn(),
    updateInstrument: jest.fn(),
  },
}));

jest.mock('../contexts/UserContext', () => ({
  useUser: () => ({
    user: { id: '1', username: 'admin', permissions: ['config:edit'] },
    hasPermission: () => true,
    loading: false,
  }),
}));

const api = apiService as jest.Mocked<typeof apiService>;
const theme = createTheme();
const wrap = (ui: React.ReactElement) => render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);

beforeEach(() => {
  api.getInstrumentTypes.mockResolvedValue([{ id: 't1', name: 'Plate reader', active: true }]);
  api.getInstruments.mockResolvedValue([
    {
      id: 'i1',
      name: 'PR-1',
      instrument_type_id: 't1',
      instrument_type_name: 'Plate reader',
      vendor_id: 'v1',
      vendor_name: 'Thermo',
      model: 'M1',
      status: 'in_service',
      active: true,
    },
  ]);
  api.getCroSources.mockResolvedValue([]);
  api.getInstrumentMaintenanceSchedules.mockResolvedValue([]);
  api.getInstrumentDowntime.mockResolvedValue([]);
  api.getVendors.mockResolvedValue([{ id: 'v1', name: 'Thermo' }]);
  api.getClients.mockResolvedValue([]);
  api.getListEntries.mockImplementation(async (name: string) => {
    if (name === 'maintenance_types') return [{ id: 'k1', name: 'PM' }];
    if (name === 'downtime_reasons') return [{ id: 'r1', name: 'Breakdown' }];
    return [];
  });
});

describe('InstrumentCatalogManagement', () => {
  test('shows vendor picker, status, Maintenance and Downtime tabs, and no Delete buttons', async () => {
    wrap(<InstrumentCatalogManagement />);
    expect(await screen.findByRole('tab', { name: 'Instruments' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: 'Instruments' }));
    expect(await screen.findByText('PR-1')).toBeInTheDocument();
    expect(screen.getByText('Thermo')).toBeInTheDocument();
    expect(screen.getByText('in_service')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Maintenance' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Downtime' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Add Instrument/i }));
    expect(await screen.findByLabelText('Vendor')).toBeInTheDocument();
    expect(screen.getByLabelText('Status')).toBeInTheDocument();
    expect(screen.getByLabelText('Track maintenance')).toBeInTheDocument();
  });
});
