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
    getInstruments: jest.fn(),
    getInstrumentEligibility: jest.fn(),
    getInstrumentUses: jest.fn(),
    recordInstrumentUse: jest.fn(),
    addExperimentInstrument: jest.fn(),
    setExperimentInstrumentActive: jest.fn(),
    createExperimentTemplate: jest.fn(),
    getExperimentEntries: jest.fn(),
    getLists: jest.fn(),
    getReagentUses: jest.fn(),
    getReagentLots: jest.fn(),
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
  api.getReagents.mockResolvedValue([]);
  api.getInstruments.mockResolvedValue([{ id: 'i1', name: 'PR-1', active: true }]);
  api.getInstrumentEligibility.mockResolvedValue({ allowed: true, instrument_id: 'i1' });
  api.getInstrumentUses.mockResolvedValue([]);
  api.recordInstrumentUse.mockResolvedValue({ id: 'u1' });
  api.getLists.mockResolvedValue([]);
  api.getReagentUses.mockResolvedValue([]);
  api.getReagentLots.mockResolvedValue([]);
});

describe('Experiment template Instruments entry', () => {
  test('Type dropdown includes Instruments', async () => {
    wrap(<ExperimentTemplatesManagement />);
    fireEvent.click(await screen.findByRole('button', { name: /New Template/i }));
    fireEvent.click(screen.getByRole('tab', { name: /Tables & forms/i }));
    const typeSelects = screen.getAllByLabelText('Type');
    fireEvent.mouseDown(typeSelects[0]);
    expect(await screen.findByRole('option', { name: 'Instruments' })).toBeInTheDocument();
  });
});

describe('Experiment instrument capture', () => {
  test('records use for a saved instrument', async () => {
    api.getExperimentEntries.mockResolvedValue({
      entries: [
        {
          id: 'e1',
          experiment_id: 'exp1',
          entry_type: 'instrument',
          name: 'Instruments',
          predefined_entry_key: 'instruments',
          sort_order: 0,
          active: true,
          config: { allowed_instrument_ids: ['i1'], status: 'draft' },
          field_definition_links: [],
          values: [],
        },
      ],
    });
    wrap(<EntryCapturePanel experimentId="exp1" />);
    expect(await screen.findByRole('button', { name: /Record use/i })).toBeInTheDocument();
    await waitFor(() => expect(api.getInstruments).toHaveBeenCalled());
    fireEvent.click(screen.getByRole('button', { name: /Record use/i }));
    await waitFor(() => expect(api.recordInstrumentUse).toHaveBeenCalled());
    expect(api.recordInstrumentUse.mock.calls[0][0]).toMatchObject({
      instrument_id: 'i1',
      experiment_id: 'exp1',
    });
  });
});
