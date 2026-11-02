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
import { localDateString } from '../utils/localDate';

jest.mock('../services/apiService', () => ({
  ...jest.requireActual('../services/apiService'),
  apiService: {
    getCurrentUser: () => Promise.reject(new Error('no session')),
    getExperimentTemplates: jest.fn(),
    getContainerTypes: jest.fn(),
    getSampleTypeTransitions: jest.fn(),
    getFieldDefinitions: jest.fn(),
    getReagents: jest.fn(),
    getInstruments: jest.fn(),
    getInstrumentTypes: jest.fn(),
    getInstrumentEligibility: jest.fn(),
    getInstrumentUses: jest.fn(),
    recordInstrumentUse: jest.fn(),
    addExperimentInstrument: jest.fn(),
    setExperimentInstrumentActive: jest.fn(),
    createExperimentTemplate: jest.fn(),
    updateExperimentTemplate: jest.fn(),
    getExperimentEntries: jest.fn(),
    getLists: jest.fn(),
    getReagentUses: jest.fn(),
    getReagentLots: jest.fn(),
    recordReagentUse: jest.fn(),
    addExperimentReagent: jest.fn(),
    setExperimentReagentActive: jest.fn(),
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
  api.getInstruments.mockResolvedValue([]);
  api.getInstrumentTypes.mockResolvedValue([]);
  api.getInstrumentEligibility.mockResolvedValue({ allowed: true });
  api.getInstrumentUses.mockResolvedValue([]);
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
  const reagentEntry: {
    id: string;
    experiment_id: string;
    entry_type: string;
    name: string;
    predefined_entry_key: string;
    sort_order: number;
    active: boolean;
    config: { allowed_reagent_ids: string[]; removed_reagent_ids?: string[]; status: string };
    field_definition_links: never[];
    values: never[];
  } = {
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

  const lots = [
    { id: 'l1', reagent_id: 'r1', reagent_name: 'Qubit dsDNA HS', lot_number: 'L-OK', unit: 'mL', usable: true },
    {
      id: 'l1-old',
      reagent_id: 'r1',
      reagent_name: 'Qubit dsDNA HS',
      lot_number: 'L-OLD',
      unit: 'mL',
      usable: false,
      expired: true,
      qc_status: 'rejected',
      active: false,
      released: false,
    },
    { id: 'l2', reagent_id: 'r2', reagent_name: 'Ethanol', lot_number: 'L-OFF', unit: 'mL', usable: true },
  ];

  test('offers lots of the saved reagent and records the use on the experiment', async () => {
    api.getExperimentEntries.mockResolvedValue({ entries: [reagentEntry] });
    api.getReagentLots.mockResolvedValue(lots);
    wrap(<EntryCapturePanel experimentId="exp1" />);

    expect(await screen.findByText('Reagents')).toBeInTheDocument();
    expect(screen.getByText('Reagent')).toBeInTheDocument();
    await waitFor(() => expect(api.getReagentLots).toHaveBeenCalledWith({ usable: true }));
    fireEvent.mouseDown(await screen.findByLabelText('Lot for Qubit dsDNA HS'));
    expect(await screen.findByRole('option', { name: /L-OK/ })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /L-OFF/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /L-OLD/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('option', { name: /L-OK/ }));
    fireEvent.change(screen.getByLabelText(/Quantity for Qubit dsDNA HS/), { target: { value: '2' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record' }));
    await waitFor(() => expect(api.recordReagentUse).toHaveBeenCalled());
    expect(api.recordReagentUse.mock.calls[0][0]).toMatchObject({
      reagent_lot_id: 'l1',
      experiment_id: 'exp1',
      quantity_used: '2',
      unit: 'mL',
    });
  });

  test("each reagent's lot picker lists only that reagent's usable lots", async () => {
    api.getExperimentEntries.mockResolvedValue({
      entries: [
        {
          ...reagentEntry,
          config: { allowed_reagent_ids: ['r1', 'r2'], status: 'draft' },
        },
      ],
    });
    api.getReagentLots.mockResolvedValue(lots);
    wrap(<EntryCapturePanel experimentId="exp1" />);

    fireEvent.mouseDown(await screen.findByLabelText('Lot for Qubit dsDNA HS'));
    expect(await screen.findByRole('option', { name: /L-OK/ })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /L-OFF/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /L-OLD/ })).not.toBeInTheDocument();
    fireEvent.keyDown(screen.getByRole('listbox'), { key: 'Escape' });

    fireEvent.mouseDown(screen.getByLabelText('Lot for Ethanol'));
    expect(await screen.findByRole('option', { name: /L-OFF/ })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /L-OK/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /L-OLD/ })).not.toBeInTheDocument();
  });

  test('adds a reagent through the API and then records its own lot', async () => {
    let entries = [reagentEntry];
    api.getExperimentEntries.mockImplementation(async () => ({ entries }));
    api.getReagentLots.mockResolvedValue(lots);
    api.addExperimentReagent.mockImplementation(async (_experimentId: string, reagentId: string) => {
      const ids = ['r1', reagentId];
      entries = [{ ...reagentEntry, config: { allowed_reagent_ids: ids, status: 'draft' } }];
      return { experiment_id: 'exp1', entry_id: 'e1', allowed_reagent_ids: ids };
    });
    wrap(<EntryCapturePanel experimentId="exp1" />);
    fireEvent.mouseDown(await screen.findByLabelText('Add reagent'));
    fireEvent.click(await screen.findByRole('option', { name: 'Ethanol' }));
    await waitFor(() => expect(api.addExperimentReagent).toHaveBeenCalledWith('exp1', 'r2'));
    fireEvent.mouseDown(await screen.findByLabelText('Lot for Ethanol'));
    expect(await screen.findByRole('option', { name: /L-OFF/ })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: /L-OK/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('option', { name: /L-OFF/ }));
    fireEvent.change(screen.getByLabelText(/Quantity for Ethanol/), { target: { value: '1' } });
    const recordButtons = screen.getAllByRole('button', { name: 'Record' });
    fireEvent.click(recordButtons[recordButtons.length - 1]);
    await waitFor(() => expect(api.recordReagentUse).toHaveBeenCalled());
    expect(api.recordReagentUse.mock.calls[0][0]).toMatchObject({
      reagent_lot_id: 'l2',
      experiment_id: 'exp1',
      quantity_used: '1',
      unit: 'mL',
    });
  });

  test('adds a reagent on an experiment with no template entry and records its lot', async () => {
    let entries: unknown[] = [];
    api.getExperimentEntries.mockImplementation(async () => ({ entries }));
    api.getReagentLots.mockResolvedValue(lots);
    api.addExperimentReagent.mockImplementation(async () => {
      entries = [
        {
          ...reagentEntry,
          config: { allowed_reagent_ids: ['r2'], status: 'draft' },
        },
      ];
      return { experiment_id: 'exp1', entry_id: 'e1', allowed_reagent_ids: ['r2'] };
    });
    wrap(<EntryCapturePanel experimentId="exp1" />);
    expect(await screen.findByText(/No reagents yet/i)).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByLabelText('Add reagent'));
    fireEvent.click(await screen.findByRole('option', { name: 'Ethanol' }));
    await waitFor(() => expect(api.addExperimentReagent).toHaveBeenCalledWith('exp1', 'r2'));
    fireEvent.mouseDown(await screen.findByLabelText('Lot for Ethanol'));
    fireEvent.click(await screen.findByRole('option', { name: /L-OFF/ }));
    fireEvent.change(screen.getByLabelText(/Quantity for Ethanol/), { target: { value: '4' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record' }));
    await waitFor(() => expect(api.recordReagentUse).toHaveBeenCalled());
    expect(api.recordReagentUse.mock.calls[0][0]).toMatchObject({
      reagent_lot_id: 'l2',
      experiment_id: 'exp1',
      quantity_used: '4',
    });
  });

  test('shows an inactivated reagent by name', async () => {
    api.getReagents.mockResolvedValue([
      { id: 'r1', name: 'Qubit dsDNA HS', active: false },
      { id: 'r2', name: 'Ethanol', active: true },
      { id: 'r3', name: 'Retired buffer', active: false },
    ]);
    api.getExperimentEntries.mockResolvedValue({ entries: [reagentEntry] });
    api.getReagentLots.mockResolvedValue([]);
    wrap(<EntryCapturePanel experimentId="exp1" />);

    expect(await screen.findByLabelText('Lot for Qubit dsDNA HS')).toBeInTheDocument();
    expect(screen.queryByLabelText('Lot for r1')).not.toBeInTheDocument();
    await waitFor(() => expect(api.getReagents).toHaveBeenCalledWith({ include_inactive: true }));
    fireEvent.mouseDown(screen.getByLabelText('Add reagent'));
    expect(await screen.findByRole('option', { name: 'Ethanol' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Retired buffer' })).not.toBeInTheDocument();
    expect(screen.queryByRole('option', { name: 'Qubit dsDNA HS' })).not.toBeInTheDocument();
  });

  test('removes a reagent from the picker and keeps the recorded use', async () => {
    let entries = [reagentEntry];
    api.getExperimentEntries.mockImplementation(async () => ({ entries }));
    api.getReagentLots.mockResolvedValue(lots);
    api.getReagentUses.mockResolvedValue([
      {
        id: 'u-kept',
        reagent_name: 'Qubit dsDNA HS',
        lot_number: 'L-OK',
        used_on: '2026-10-18',
        quantity_used: '2',
        unit: 'mL',
        note: 'bench note',
      },
    ]);
    api.setExperimentReagentActive.mockImplementation(async () => {
      entries = [{ ...reagentEntry, config: { allowed_reagent_ids: [], removed_reagent_ids: ['r1'], status: 'draft' } }];
      return { experiment_id: 'exp1', entry_id: 'e1', allowed_reagent_ids: [], removed_reagent_ids: ['r1'] };
    });
    wrap(<EntryCapturePanel experimentId="exp1" />);
    expect(await screen.findByText('bench note')).toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: 'Remove Qubit dsDNA HS' }));
    await waitFor(() =>
      expect(api.setExperimentReagentActive).toHaveBeenCalledWith('exp1', 'r1', false),
    );
    await waitFor(() => expect(screen.queryByLabelText('Lot for Qubit dsDNA HS')).not.toBeInTheDocument());
    expect(screen.getByText('bench note')).toBeInTheDocument();
    expect(screen.getByText('L-OK')).toBeInTheDocument();
    expect(await screen.findByText(/lots already recorded stay listed below/i)).toBeInTheDocument();
    expect(screen.queryByText(/No reagents yet/i)).not.toBeInTheDocument();
    fireEvent.mouseDown(screen.getByLabelText('Add reagent'));
    expect(await screen.findByRole('option', { name: 'Qubit dsDNA HS' })).toBeInTheDocument();
  });

  test('records a used-on date and note from the experiment lot row', async () => {
    api.getExperimentEntries.mockResolvedValue({ entries: [reagentEntry] });
    api.getReagentLots.mockResolvedValue(lots);
    wrap(<EntryCapturePanel experimentId="exp1" />);
    fireEvent.mouseDown(await screen.findByLabelText('Lot for Qubit dsDNA HS'));
    fireEvent.click(await screen.findByRole('option', { name: /L-OK/ }));
    fireEvent.change(screen.getByLabelText(/Quantity for Qubit dsDNA HS/), { target: { value: '1' } });
    fireEvent.change(screen.getAllByLabelText('Used on')[0], { target: { value: '2026-10-01' } });
    fireEvent.change(screen.getAllByLabelText('Note')[0], { target: { value: 'opened today' } });
    expect(screen.getByText('Leave empty for today')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Record' }));
    await waitFor(() => expect(api.recordReagentUse).toHaveBeenCalled());
    expect(api.recordReagentUse.mock.calls[0][0]).toMatchObject({
      reagent_lot_id: 'l1',
      experiment_id: 'exp1',
      quantity_used: '1',
      used_on: '2026-10-01',
      note: 'opened today',
    });
    await waitFor(() => expect(screen.getAllByLabelText('Used on')[0]).toHaveValue(''));
    expect(screen.getAllByLabelText('Note')[0]).toHaveValue('');
  });

  test('keeps Used on and Note when the API refuses the use', async () => {
    api.getExperimentEntries.mockResolvedValue({ entries: [reagentEntry] });
    api.getReagentLots.mockResolvedValue(lots);
    api.recordReagentUse.mockRejectedValue({
      response: { data: { detail: { code: 'insufficient_amount', message: 'Lot L-OK has 1 mL left' } } },
    });
    wrap(<EntryCapturePanel experimentId="exp1" />);
    fireEvent.mouseDown(await screen.findByLabelText('Lot for Qubit dsDNA HS'));
    fireEvent.click(await screen.findByRole('option', { name: /L-OK/ }));
    fireEvent.change(screen.getByLabelText(/Quantity for Qubit dsDNA HS/), { target: { value: '5' } });
    fireEvent.change(screen.getAllByLabelText('Used on')[0], { target: { value: '2026-10-01' } });
    fireEvent.change(screen.getAllByLabelText('Note')[0], { target: { value: 'opened today' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record' }));
    expect(await screen.findByText('Lot L-OK has 1 mL left')).toBeInTheDocument();
    expect(screen.getAllByLabelText('Used on')[0]).toHaveValue('2026-10-01');
    expect(screen.getAllByLabelText('Note')[0]).toHaveValue('opened today');
  });

  test('caps Used on at the browser today and shows a future-date refusal', async () => {
    api.getExperimentEntries.mockResolvedValue({ entries: [reagentEntry] });
    api.getReagentLots.mockResolvedValue(lots);
    api.recordReagentUse.mockRejectedValue({
      response: {
        data: {
          detail: {
            code: 'used_on_in_future',
            message: 'Used on 2026-10-19 is after today in the lab timezone (2026-10-18).',
          },
        },
      },
    });
    wrap(<EntryCapturePanel experimentId="exp1" />);
    fireEvent.mouseDown(await screen.findByLabelText('Lot for Qubit dsDNA HS'));
    fireEvent.click(await screen.findByRole('option', { name: /L-OK/ }));
    fireEvent.change(screen.getByLabelText(/Quantity for Qubit dsDNA HS/), { target: { value: '1' } });
    expect(screen.getAllByLabelText('Used on')[0]).toHaveAttribute('max', localDateString());
    fireEvent.click(screen.getByRole('button', { name: 'Record' }));
    expect(
      await screen.findByText('Used on 2026-10-19 is after today in the lab timezone (2026-10-18).'),
    ).toBeInTheDocument();
  });

  test("sends the browser's local date when Used on is left empty", async () => {
    api.getExperimentEntries.mockResolvedValue({ entries: [reagentEntry] });
    api.getReagentLots.mockResolvedValue(lots);
    wrap(<EntryCapturePanel experimentId="exp1" />);
    fireEvent.mouseDown(await screen.findByLabelText('Lot for Qubit dsDNA HS'));
    fireEvent.click(await screen.findByRole('option', { name: /L-OK/ }));
    fireEvent.change(screen.getByLabelText(/Quantity for Qubit dsDNA HS/), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record' }));
    await waitFor(() => expect(api.recordReagentUse).toHaveBeenCalled());
    expect(api.recordReagentUse.mock.calls[0][0].used_on).toBe(localDateString());
  });

  test('says no reagents yet only when nothing has been recorded', async () => {
    api.getExperimentEntries.mockResolvedValue({
      entries: [{ ...reagentEntry, config: { allowed_reagent_ids: [], status: 'draft' } }],
    });
    wrap(<EntryCapturePanel experimentId="exp1" />);
    expect(await screen.findByText(/No reagents yet/i)).toBeInTheDocument();
    expect(screen.queryByText(/lots already recorded/i)).not.toBeInTheDocument();
  });

  test('shows the API refusal when the reagent is inactive', async () => {
    api.getExperimentEntries.mockResolvedValue({ entries: [reagentEntry] });
    api.getReagentLots.mockResolvedValue(lots);
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
    fireEvent.mouseDown(await screen.findByLabelText('Lot for Qubit dsDNA HS'));
    fireEvent.click(await screen.findByRole('option', { name: /L-OK/ }));
    fireEvent.change(screen.getByLabelText(/Quantity for Qubit dsDNA HS/), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Record' }));
    expect(await screen.findByText(/inactive and can't be recorded/i)).toBeInTheDocument();
  });
});
