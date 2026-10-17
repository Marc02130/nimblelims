import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ThemeProvider, createTheme } from '@mui/material/styles';

jest.mock('@mui/x-data-grid', () => ({
  DataGrid: () => <div role="grid">experiment-templates-grid</div>,
  GridActionsCellItem: () => null,
}));

import ExperimentTemplatesManagement from '../pages/ExperimentTemplatesManagement';
import EntryCapturePanel from '../components/experiments/EntryCapturePanel';
import { apiService } from '../services/apiService';

jest.mock('../services/apiService', () => ({
  ...jest.requireActual('../services/apiService'),
  apiService: {
    getCurrentUser: () => Promise.reject(new Error('no session')),
    getExperimentTemplates: jest.fn(),
    getContainerTypes: jest.fn(),
    getSampleTypeTransitions: jest.fn(),
    getFieldDefinitions: jest.fn(),
    getReagents: jest.fn(),
    createExperimentTemplate: jest.fn(),
    updateExperimentTemplate: jest.fn(),
    getExperimentEntries: jest.fn(),
    getLists: jest.fn(),
    getReagentUses: jest.fn(),
    getReagentLots: jest.fn(),
    recordReagentUse: jest.fn(),
  },
}));

jest.mock('../contexts/UserContext', () => ({
  useUser: () => ({
    user: { id: '1', username: 'admin', permissions: ['experiment:manage'] },
    hasPermission: (permission: string) => permission === 'experiment:manage',
    loading: false,
  }),
}));

const api = apiService as jest.Mocked<typeof apiService>;
const theme = createTheme();

const wrap = (ui: React.ReactElement) => render(<ThemeProvider theme={theme}>{ui}</ThemeProvider>);

beforeEach(() => {
  api.getExperimentTemplates.mockResolvedValue([]);
  api.getContainerTypes.mockResolvedValue([]);
  api.getSampleTypeTransitions.mockResolvedValue([]);
  api.getFieldDefinitions.mockResolvedValue({ items: [] });
  api.getReagents.mockResolvedValue([
    { id: 'r1', name: 'Qubit dsDNA HS', active: true },
    { id: 'r2', name: 'Ethanol', active: true },
  ]);
  api.createExperimentTemplate.mockResolvedValue({ id: 't1' });
  api.getExperimentEntries.mockResolvedValue({ entries: [] });
  api.getLists.mockResolvedValue([]);
  api.getReagentUses.mockResolvedValue([]);
  api.getReagentLots.mockResolvedValue([]);
  api.recordReagentUse.mockResolvedValue({ id: 'u1' });
});

describe('Experiment template Reagent entry', () => {
  test('Type dropdown includes Reagent', async () => {
    wrap(<ExperimentTemplatesManagement />);
    fireEvent.click(await screen.findByRole('button', { name: /New Template/i }));
    fireEvent.click(screen.getByRole('tab', { name: /Tables & forms/i }));
    const typeSelects = screen.getAllByLabelText('Type');
    fireEvent.mouseDown(typeSelects[0]);
    expect(await screen.findByRole('option', { name: 'Reagent' })).toBeInTheDocument();
  });

  test('saves a Reagent entry with the reagents the author picked', async () => {
    wrap(<ExperimentTemplatesManagement />);
    fireEvent.click(await screen.findByRole('button', { name: /New Template/i }));
    fireEvent.change(screen.getByLabelText(/Template Name/i), { target: { value: 'Qubit run' } });
    fireEvent.change(screen.getByLabelText(/Experiment Name/i), {
      target: { value: 'Qubit experiment' },
    });
    fireEvent.click(screen.getByRole('tab', { name: /Tables & forms/i }));
    fireEvent.click(screen.getByRole('button', { name: /Add table \/ form/i }));

    const names = screen.getAllByLabelText(/Entry name/i);
    fireEvent.change(names[names.length - 1], { target: { value: 'Reagents used' } });
    const typeSelects = screen.getAllByLabelText('Type');
    fireEvent.mouseDown(typeSelects[typeSelects.length - 1]);
    fireEvent.click(await screen.findByRole('option', { name: 'Reagent' }));

    fireEvent.mouseDown(screen.getByLabelText('Default reagents'));
    fireEvent.click(await screen.findByRole('option', { name: 'Qubit dsDNA HS' }));
    fireEvent.keyDown(screen.getByRole('listbox'), { key: 'Escape' });
    fireEvent.click(screen.getByRole('button', { name: /^Create$/ }));

    await waitFor(() => expect(api.createExperimentTemplate).toHaveBeenCalled());
    const payload = api.createExperimentTemplate.mock.calls[0][0] as unknown as {
      template_definition: { entries: Array<Record<string, unknown>> };
    };
    const reagent = payload.template_definition.entries.find((entry) => entry.entry_type === 'reagent');
    expect(reagent).toMatchObject({
      name: 'Reagents used',
      predefined_entry_key: 'reagents',
      config: { allowed_reagent_ids: ['r1'] },
    });
  });

  test('refuses to save a Reagent entry with no reagents', async () => {
    wrap(<ExperimentTemplatesManagement />);
    fireEvent.click(await screen.findByRole('button', { name: /New Template/i }));
    fireEvent.change(screen.getByLabelText(/Template Name/i), { target: { value: 'Empty reagents' } });
    fireEvent.change(screen.getByLabelText(/Experiment Name/i), {
      target: { value: 'Empty experiment' },
    });
    fireEvent.click(screen.getByRole('tab', { name: /Tables & forms/i }));
    fireEvent.click(screen.getByRole('button', { name: '+ Reagents' }));
    fireEvent.click(screen.getByRole('button', { name: 'Create' }));

    expect(
      await screen.findByText(/A Reagent entry needs at least one default reagent/i),
    ).toBeInTheDocument();
    expect(api.createExperimentTemplate).not.toHaveBeenCalled();
  });
});

describe('Experiment reagent capture', () => {
  const reagentEntry = {
    id: 'e1',
    experiment_id: 'exp1',
    entry_type: 'reagent',
    name: 'Reagents',
    predefined_entry_key: 'reagents',
    sort_order: 0,
    active: true,
    config: { allowed_reagent_ids: ['r1'], status: 'draft' },
    field_definition_links: [],
    values: [],
  };

  test('offers lots of the default reagents and records the use on the experiment', async () => {
    api.getExperimentEntries.mockResolvedValue({ entries: [reagentEntry] });
    api.getReagentLots.mockResolvedValue([
      { id: 'l1', reagent_id: 'r1', reagent_name: 'Qubit dsDNA HS', lot_number: 'L-OK', unit: 'mL' },
      { id: 'l2', reagent_id: 'r2', reagent_name: 'Ethanol', lot_number: 'L-OFF', unit: 'mL' },
    ]);
    wrap(<EntryCapturePanel experimentId="exp1" />);

    expect(await screen.findByText('Reagents')).toBeInTheDocument();
    expect(screen.getByText('Reagent')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Record lot used/i }));
    await waitFor(() => expect(api.getReagentLots).toHaveBeenCalledWith({ usable: true }));
    fireEvent.mouseDown(screen.getByLabelText('Lot'));
    expect(await screen.findByRole('option', { name: /L-OK/ })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /L-OFF/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('option', { name: /L-OK/ }));
    fireEvent.change(screen.getByLabelText(/Quantity used/), { target: { value: '2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record' }));
    await waitFor(() => expect(api.recordReagentUse).toHaveBeenCalled());
    expect(api.recordReagentUse.mock.calls[0][0]).toMatchObject({
      reagent_lot_id: 'l1',
      experiment_id: 'exp1',
      quantity_used: '2',
      unit: 'mL',
    });
  });

  test('adds a reagent that was not prefilled and records its lot', async () => {
    api.getExperimentEntries.mockResolvedValue({ entries: [reagentEntry] });
    api.getReagentLots.mockResolvedValue([
      { id: 'l1', reagent_id: 'r1', reagent_name: 'Qubit dsDNA HS', lot_number: 'L-OK', unit: 'mL' },
      { id: 'l2', reagent_id: 'r2', reagent_name: 'Ethanol', lot_number: 'L-OFF', unit: 'mL' },
    ]);
    wrap(<EntryCapturePanel experimentId="exp1" />);
    expect(await screen.findByText(/On this experiment: Qubit dsDNA HS/)).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByLabelText('Add reagent'));
    fireEvent.click(await screen.findByRole('option', { name: 'Ethanol' }));
    expect(screen.getByText(/On this experiment: Qubit dsDNA HS, Ethanol/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Record lot used/i }));
    await waitFor(() => expect(api.getReagentLots).toHaveBeenCalledWith({ usable: true }));
    fireEvent.mouseDown(screen.getByLabelText('Lot'));
    fireEvent.click(await screen.findByRole('option', { name: /L-OFF/ }));
    fireEvent.change(screen.getByLabelText(/Quantity used/), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record' }));
    await waitFor(() => expect(api.recordReagentUse).toHaveBeenCalled());
    expect(api.recordReagentUse.mock.calls[0][0]).toMatchObject({
      reagent_lot_id: 'l2',
      experiment_id: 'exp1',
      quantity_used: '1',
      unit: 'mL',
    });
  });

  test('adds a reagent on an experiment with no template entry and records its lot', async () => {
    api.getExperimentEntries.mockResolvedValue({ entries: [] });
    api.getReagentLots.mockResolvedValue([
      { id: 'l2', reagent_id: 'r2', reagent_name: 'Ethanol', lot_number: 'L-OFF', unit: 'mL' },
    ]);
    wrap(<EntryCapturePanel experimentId="exp1" />);
    expect(await screen.findByText(/No reagents yet/i)).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByLabelText('Add reagent'));
    fireEvent.click(await screen.findByRole('option', { name: 'Ethanol' }));
    fireEvent.click(screen.getByRole('button', { name: /Record lot used/i }));
    fireEvent.mouseDown(screen.getByLabelText('Lot'));
    fireEvent.click(await screen.findByRole('option', { name: /L-OFF/ }));
    fireEvent.change(screen.getByLabelText(/Quantity used/), { target: { value: '4' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record' }));
    await waitFor(() => expect(api.recordReagentUse).toHaveBeenCalled());
    expect(api.recordReagentUse.mock.calls[0][0]).toMatchObject({
      reagent_lot_id: 'l2',
      experiment_id: 'exp1',
      quantity_used: '4',
    });
  });

  test('shows the API refusal when the reagent is inactive', async () => {
    api.getExperimentEntries.mockResolvedValue({ entries: [reagentEntry] });
    api.getReagentLots.mockResolvedValue([
      { id: 'l1', reagent_id: 'r1', reagent_name: 'Qubit dsDNA HS', lot_number: 'L-OK', unit: 'mL' },
    ]);
    api.recordReagentUse.mockRejectedValue({
      response: {
        data: {
          detail: {
            code: 'reagent_inactive',
            message: "Qubit dsDNA HS is inactive and can't be recorded.",
          },
        },
      },
    });
    wrap(<EntryCapturePanel experimentId="exp1" />);
    fireEvent.click(await screen.findByRole('button', { name: /Record lot used/i }));
    fireEvent.mouseDown(screen.getByLabelText('Lot'));
    fireEvent.click(await screen.findByRole('option', { name: /L-OK/ }));
    fireEvent.change(screen.getByLabelText(/Quantity used/), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record' }));
    expect(await screen.findByText(/inactive and can't be recorded/i)).toBeInTheDocument();
  });
});
