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
          {columns.map((c) => {
            if (c.getActions) {
              return (
                <span key={c.field}>
                  {c.getActions({ row, id: row.id }).map((item: any, i: number) => (
                    <button
                      key={item.key || i}
                      type="button"
                      onClick={item.props?.onClick}
                    >
                      {item.props?.label || 'action'}
                    </button>
                  ))}
                </span>
              );
            }
            if (c.renderCell) {
              return <span key={c.field}>{c.renderCell({ value: row[c.field], row })}</span>;
            }
            return <span key={c.field}>{String(row[c.field] ?? '')}</span>;
          })}
        </div>
      ))}
    </div>
  ),
  GridActionsCellItem: ({ label, onClick }: { label?: string; onClick?: () => void }) => (
    <button type="button" onClick={onClick}>
      {label}
    </button>
  ),
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
    getInstrumentMaintenanceEvents: jest.fn(),
    createInstrumentMaintenanceEvent: jest.fn(),
    updateInstrumentMaintenanceEvent: jest.fn(),
    getInstrumentDowntime: jest.fn(),
    getVendors: jest.fn(),
    getClients: jest.fn(),
    getListEntries: jest.fn(),
    createInstrument: jest.fn(),
    updateInstrument: jest.fn(),
    updateInstrumentType: jest.fn(),
    setInstrumentScheduleFirstDue: jest.fn(),
  },
}));

const userState = {
  user: { id: '1', username: 'admin', role: 'Administrator', permissions: ['config:edit', 'experiment:manage'] } as {
    id: string;
    username: string;
    role: string;
    permissions: string[];
  },
  hasPermission: (_perm?: string) => true,
};

jest.mock('../contexts/UserContext', () => ({
  useUser: () => ({
    user: userState.user,
    hasPermission: userState.hasPermission,
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
  api.getInstrumentMaintenanceEvents.mockResolvedValue([]);
  api.getInstrumentDowntime.mockResolvedValue([]);
  userState.user = {
    id: '1',
    username: 'admin',
    role: 'Administrator',
    permissions: ['config:edit', 'experiment:manage'],
  };
  userState.hasPermission = () => true;
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
    expect(screen.getByRole('tab', { name: 'Events' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Downtime' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Add Instrument/i }));
    expect(await screen.findByLabelText('Vendor')).toBeInTheDocument();
    expect(screen.getByLabelText('Status')).toBeInTheDocument();
    expect(screen.getByLabelText('Track maintenance')).toBeInTheDocument();
    expect(screen.queryByLabelText('Track maintenance by default')).not.toBeInTheDocument();
  });

  test('Configuration Editor cannot send maintenance_tracked', async () => {
    userState.user = {
      id: '2',
      username: 'config-editor',
      role: 'Configuration Editor',
      permissions: ['config:edit'],
    };
    wrap(<InstrumentCatalogManagement />);
    fireEvent.click(await screen.findByRole('tab', { name: 'Instruments' }));
    fireEvent.click(screen.getByRole('button', { name: /Add Instrument/i }));
    expect(await screen.findByLabelText('Track maintenance')).toBeDisabled();
    expect(
      screen.getByText('An Administrator can turn on maintenance tracking.'),
    ).toBeInTheDocument();
  });

  test('Save turns maintenance tracking off with no extra prompt', async () => {
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
        maintenance_tracked: true,
      },
    ]);
    api.updateInstrument.mockResolvedValue({ id: 'i1', maintenance_tracked: false });
    wrap(<InstrumentCatalogManagement />);
    fireEvent.click(await screen.findByRole('tab', { name: 'Instruments' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Edit' }));
    const track = await screen.findByLabelText('Track maintenance');
    expect(track).toBeChecked();
    fireEvent.click(track);
    expect(screen.queryByRole('dialog', { name: /confirm/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await screen.findByText('Instrument updated');
    expect(api.updateInstrument).toHaveBeenCalledWith(
      'i1',
      expect.objectContaining({ maintenance_tracked: false }),
    );
    expect(screen.queryByText(/are you sure/i)).not.toBeInTheDocument();
  });

  test('maintenance-only view hides catalog tabs and shows the first-due empty state', async () => {
    api.getInstrumentMaintenanceSchedules.mockResolvedValue([
      {
        id: 's1',
        instrument_id: 'i1',
        instrument_name: 'PR-1',
        kind_id: 'k1',
        kind_name: 'PM',
        interval_days: 365,
        last_done: null,
        next_due: null,
        active: true,
      },
    ]);
    wrap(<InstrumentCatalogManagement maintenanceOnly />);
    expect(await screen.findByText('Instrument maintenance')).toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: 'Types' })).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: 'Instruments' })).not.toBeInTheDocument();
    expect(await screen.findByText('PR-1')).toBeInTheDocument();
    expect(screen.getByText('Awaiting first due date')).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Events' })).toBeInTheDocument();
  });

  test('tech can log an event and does not see edit or void', async () => {
    userState.user = {
      id: 'tech-1',
      username: 'lab-tech',
      role: 'Lab Technician',
      permissions: ['experiment:manage'],
    };
    userState.hasPermission = (perm?: string) => perm === 'experiment:manage';
    api.getInstrumentMaintenanceEvents.mockResolvedValue([
      {
        id: 'e1',
        instrument_id: 'i1',
        performed_on: '2026-10-26',
        passed: true,
        note: 'PM done',
        active: true,
      },
    ]);
    wrap(<InstrumentCatalogManagement eventsOnly />);
    expect(await screen.findByText('Maintenance events')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Log event' })).toBeInTheDocument();
    expect(await screen.findByText('PM done')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Void' })).not.toBeInTheDocument();
  });

  test('manager can void an event from the events grid', async () => {
    api.updateInstrumentMaintenanceEvent.mockResolvedValue({ id: 'e1', active: false });
    api.getInstrumentMaintenanceEvents.mockResolvedValue([
      {
        id: 'e1',
        instrument_id: 'i1',
        performed_on: '2026-10-26',
        passed: true,
        note: 'PM done',
        active: true,
      },
    ]);
    wrap(<InstrumentCatalogManagement eventsOnly />);
    expect(await screen.findByRole('button', { name: 'Void' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Void' }));
    expect(await screen.findByText('Void maintenance event')).toBeInTheDocument();
    expect(api.updateInstrumentMaintenanceEvent).not.toHaveBeenCalled();
    fireEvent.change(screen.getByTestId('void-event-reason'), { target: { value: 'wrong date' } });
    fireEvent.click(screen.getByTestId('void-event-confirm'));
    expect(await screen.findByText('Event voided')).toBeInTheDocument();
    expect(api.updateInstrumentMaintenanceEvent).toHaveBeenCalledWith('e1', {
      active: false,
      reason: 'wrong date',
    });
  });

  test('kind and downtime reason pickers omit removed entries', async () => {
    api.getListEntries.mockImplementation(async (name: string) => {
      if (name === 'maintenance_types') {
        return [
          { id: 'k1', name: 'PM', active: true },
          { id: 'k-retired', name: 'Retired kind', active: false },
        ];
      }
      if (name === 'downtime_reasons') {
        return [
          { id: 'r1', name: 'Breakdown', active: true },
          { id: 'r-retired', name: 'Retired reason', active: false },
        ];
      }
      return [];
    });
    const first = wrap(<InstrumentCatalogManagement />);
    fireEvent.click(await screen.findByRole('tab', { name: 'Maintenance' }));
    fireEvent.click(screen.getByRole('button', { name: /Add Maintenance/i }));
    fireEvent.mouseDown(await screen.findByLabelText('Kind'));
    expect(await screen.findByRole('option', { name: 'PM' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Retired kind' })).not.toBeInTheDocument();
    first.unmount();
    wrap(<InstrumentCatalogManagement />);
    fireEvent.click(await screen.findByRole('tab', { name: 'Downtime' }));
    fireEvent.click(screen.getByRole('button', { name: /Add Downtime/i }));
    fireEvent.mouseDown(await screen.findByLabelText('Reason'));
    expect(await screen.findByRole('option', { name: 'Breakdown' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Retired reason' })).not.toBeInTheDocument();
  });
});
