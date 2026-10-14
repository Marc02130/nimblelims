import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import ReagentsManagement from '../pages/admin/ReagentsManagement';
import ReagentUsePanel from '../components/reagents/ReagentUsePanel';
import { apiService } from '../services/apiService';

jest.mock('../services/apiService', () => ({
  apiService: {
    getVendors: jest.fn(),
    getReagents: jest.fn(),
    getReagentLots: jest.fn(),
    getReagentVendors: jest.fn(),
    createReagentVendor: jest.fn(),
    updateReagentVendor: jest.fn(),
    createVendor: jest.fn(),
    updateVendor: jest.fn(),
    createReagent: jest.fn(),
    updateReagent: jest.fn(),
    createReagentLot: jest.fn(),
    updateReagentLot: jest.fn(),
    getReagentUses: jest.fn(),
    recordReagentUse: jest.fn(),
    voidReagentUse: jest.fn(),
  },
}));

jest.mock('../contexts/UserContext', () => ({
  useUser: () => ({
    user: { id: '1', username: 'admin', permissions: ['config:edit', 'experiment:manage'] },
    hasPermission: (p: string) => p === 'config:edit' || p === 'experiment:manage',
    loading: false,
  }),
}));

const api = apiService as jest.Mocked<typeof apiService>;
const theme = createTheme();
const wrap = (ui: React.ReactElement) => render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);

class StubResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

beforeEach(() => {
  jest.clearAllMocks();
  (window as any).ResizeObserver = StubResizeObserver;
  api.getVendors.mockResolvedValue([{ id: 'v1', name: 'Thermo Fisher', contact: 'orders', active: true }]);
  api.getReagents.mockResolvedValue([
    { id: 'r1', name: 'Qubit dsDNA HS', vendor_names: ['Thermo Fisher'], storage_condition: '4C', quantity_on_hand: 50, below_reorder_point: true, active: true },
  ]);
  api.getReagentVendors.mockResolvedValue([
    { id: 's1', reagent_id: 'r1', reagent_name: 'Qubit dsDNA HS', vendor_name: 'Thermo Fisher', catalog_number: 'Q32851', is_preferred: true, active: true },
  ]);
  api.getReagentLots.mockResolvedValue([
    { id: 'l1', reagent_id: 'r1', reagent_name: 'Qubit dsDNA HS', lot_number: 'L-2291', effective_expiration_date: '2020-01-01', qc_status: 'released', active: true, expired: true },
    { id: 'l3', reagent_id: 'r1', reagent_name: 'Qubit dsDNA HS', lot_number: 'L-3000', qc_status: 'rejected', active: true, expired: false },
    { id: 'l4', reagent_id: 'r1', reagent_name: 'Qubit dsDNA HS', lot_number: 'L-4000', qc_status: 'pending', released: false, active: true, expired: false },
  ]);
  api.getReagentUses.mockResolvedValue([]);
});

describe('ReagentsManagement', () => {
  test('lists vendors, reagents and lots, flags an expired lot, and has no delete', async () => {
    wrap(<ReagentsManagement />);
    expect(await screen.findByText('Thermo Fisher')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: 'Reagents' }));
    expect(await screen.findByText('4C')).toBeInTheDocument();
    expect(screen.getByText('Reorder')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: 'Reagent vendors' }));
    expect(await screen.findByText('Q32851')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: 'Lots' }));
    expect(await screen.findByText('L-2291')).toBeInTheDocument();
    expect(screen.getByText('Expired')).toBeInTheDocument();
    expect(screen.getByText('QC rejected')).toBeInTheDocument();
    expect(screen.getByText('Not released')).toBeInTheDocument();
  });

  test('adds a vendor', async () => {
    api.createVendor.mockResolvedValue({ id: 'v2' });
    wrap(<ReagentsManagement />);
    await screen.findByText('Thermo Fisher');
    fireEvent.click(screen.getByRole('button', { name: /Add vendor/i }));
    fireEvent.change(screen.getByLabelText(/Name/), { target: { value: 'Qiagen' } });
    fireEvent.click(screen.getByRole('button', { name: 'Save' }));
    await waitFor(() => expect(api.createVendor).toHaveBeenCalled());
    expect(api.createVendor.mock.calls[0][0]).toMatchObject({ name: 'Qiagen', active: true });
  });
});

describe('ReagentUsePanel', () => {
  test('shows the lot and expiry recorded on the run and voids instead of deleting', async () => {
    api.getReagentUses.mockResolvedValue([
      { id: 'u1', reagent_name: 'Qubit dsDNA HS', lot_number: 'L-2291', expiration_date: '2027-01-01', used_on: '2026-10-14', quantity_used: 8, unit: 'assays' },
    ]);
    api.voidReagentUse.mockResolvedValue({});
    wrap(<ReagentUsePanel limsRunId="run1" />);
    expect(await screen.findByText('L-2291')).toBeInTheDocument();
    expect(screen.getByText('2027-01-01')).toBeInTheDocument();
    expect(screen.getByText('8 assays')).toBeInTheDocument();
    expect(api.getReagentUses).toHaveBeenCalledWith({ lims_run_id: 'run1' });
    fireEvent.click(screen.getByRole('button', { name: 'Void' }));
    await waitFor(() => expect(api.voidReagentUse).toHaveBeenCalledWith('u1'));
  });

  test('shows the API refusal for an expired lot', async () => {
    api.getReagentLots.mockResolvedValue([{ id: 'l2', reagent_name: 'Kit', lot_number: 'L9', unit: 'assays', active: true }]);
    api.recordReagentUse.mockRejectedValue({ response: { data: { detail: 'Lot L9 expired on 2026-01-01 and can\'t be used' } } });
    wrap(<ReagentUsePanel limsRunId="run1" />);
    fireEvent.click(await screen.findByRole('button', { name: /Record lot used/i }));
    await waitFor(() => expect(api.getReagentLots).toHaveBeenCalledWith({ usable: true }));
    fireEvent.mouseDown(screen.getByLabelText('Lot'));
    fireEvent.click(await screen.findByRole('option', { name: /L9/ }));
    expect(screen.getByRole('button', { name: 'Record' })).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/Quantity used/), { target: { value: '3' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record' }));
    await waitFor(() => expect(api.recordReagentUse).toHaveBeenCalled());
    expect(api.recordReagentUse.mock.calls[0][0]).toMatchObject({ reagent_lot_id: 'l2', lims_run_id: 'run1', quantity_used: '3', unit: 'assays' });
    expect(await screen.findByText(/expired on 2026-01-01/)).toBeInTheDocument();
  });
});
