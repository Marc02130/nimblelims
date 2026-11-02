import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import LimsRunDetail from '../pages/LimsRunDetail';

const mockGetLimsRun = jest.fn();
const mockGetAnalyses = jest.fn();
const mockGetLimsRunData = jest.fn();
const mockGetDataParsers = jest.fn();
const mockImportLimsRunFile = jest.fn();
const mockFailLimsRun = jest.fn();
const mockCreateLimsRunRerun = jest.fn();
const mockGetLimsRunValueChoices = jest.fn();
const mockGetInstrumentTypes = jest.fn();
const mockSubstituteLimsRunInstrumentType = jest.fn();

jest.mock('../services/apiService', () => ({
  apiService: {
    getLimsRun: (...args: any[]) => mockGetLimsRun(...args),
    getAnalyses: (...args: any[]) => mockGetAnalyses(...args),
    getLimsRunData: (...args: any[]) => mockGetLimsRunData(...args),
    getDataParsers: (...args: any[]) => mockGetDataParsers(...args),
    importLimsRunFile: (...args: any[]) => mockImportLimsRunFile(...args),
    failLimsRun: (...args: any[]) => mockFailLimsRun(...args),
    createLimsRunRerun: (...args: any[]) => mockCreateLimsRunRerun(...args),
    getLimsRunValueChoices: (...args: any[]) => mockGetLimsRunValueChoices(...args),
    getInstrumentTypes: (...args: any[]) => mockGetInstrumentTypes(...args),
    substituteLimsRunInstrumentType: (...args: any[]) =>
      mockSubstituteLimsRunInstrumentType(...args),
    acceptLimsRunValue: jest.fn(),
    updateLimsRun: jest.fn(),
    startLimsRun: jest.fn(),
    getLimsRunPromotionPreview: jest.fn(),
    publishLimsRun: jest.fn(),
    orderLimsRun: jest.fn(),
    markResultsReceived: jest.fn(),
    reviewLimsRun: jest.fn(),
    cancelLimsRun: jest.fn(),
  },
}));

jest.mock('../components/reagents/ReagentUsePanel', () => () => null);
jest.mock('../components/instruments/InstrumentUsePanel', () => () => null);
jest.mock('../pages/DoseResponse/DoseResponseTab', () => () => null);
jest.mock('../components/experiments/StartCohortPanel', () => () => null);
jest.mock('../components/runs/PublishPromotionDialog', () => () => null);

const theme = createTheme();

const runningRun = {
  id: 'run-1',
  name: 'IL6 plate',
  experiment_template_id: 'tpl-1',
  analysis_id: 'an-1',
  status: 'running',
  lifecycle_type: 'standard',
  cohort: { sample_ids: ['s1'], locked_at: '2026-10-21T00:00:00Z' },
  created_at: '2026-10-21T12:00:00Z',
};

const renderRun = () =>
  render(
    <MemoryRouter initialEntries={['/runs/run-1']}>
      <ThemeProvider theme={theme}>
        <Routes>
          <Route path="/runs/:runId" element={<LimsRunDetail />} />
        </Routes>
      </ThemeProvider>
    </MemoryRouter>
  );

describe('LimsRunDetail ELISA gaps', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGetLimsRun.mockImplementation(async (id: string) =>
      id === 'run-2'
        ? { ...runningRun, id: 'run-2', name: 'IL6 plate rerun', replaces_run_id: 'run-1' }
        : runningRun
    );
    mockGetAnalyses.mockResolvedValue({ analyses: [{ id: 'an-1', name: 'IL-6' }] });
    mockGetLimsRunData.mockResolvedValue({ rows: [] });
    mockGetDataParsers.mockResolvedValue([
      {
        id: 'parser-1',
        name: 'Gen5 IL-6',
        version: 1,
        instrument_id: 'inst-1',
        cro_source_id: null,
      },
    ]);
    mockGetLimsRunValueChoices.mockResolvedValue([]);
    mockGetInstrumentTypes.mockResolvedValue([
      { id: 't-plate', name: 'Plate reader', active: true },
      { id: 't-qpcr', name: 'qPCR', active: true },
    ]);
    mockSubstituteLimsRunInstrumentType.mockResolvedValue({
      ...runningRun,
      instrument_type_id: 't-qpcr',
      instrument_type_name: 'qPCR',
    });
    mockImportLimsRunFile.mockResolvedValue({
      imported: 96,
      linked: 2,
      unmatched_count: 94,
      unmatched: [
        {
          row_index: 0,
          well_position: 'A1',
          sample_key: 'STD-S1',
          reason: 'No sample matches STD-S1',
        },
      ],
    });
    mockFailLimsRun.mockResolvedValue({ ...runningRun, status: 'failed', status_reason: 'QC-H out of range' });
    mockCreateLimsRunRerun.mockResolvedValue({
      ...runningRun,
      id: 'run-2',
      name: 'IL6 plate rerun',
      status: 'draft',
      replaces_run_id: 'run-1',
    });
  });

  test('import from the run page sends the parser and shows unmatched rows', async () => {
    mockGetLimsRunData.mockResolvedValue({
      rows: [
        {
          id: 'row-1',
          well_position: 'D3',
          sample_key: 'IL6-SER-0001',
          sample_id: 's1',
          link_note: null,
          row_data: { corr: 0.063 },
        },
        {
          id: 'row-2',
          well_position: 'A1',
          sample_key: 'STD-S1',
          sample_id: null,
          link_note: 'No sample matches STD-S1',
          row_data: { corr: 2.058 },
        },
      ],
    });
    renderRun();
    fireEvent.click(await screen.findByTestId('run-import-button'));
    expect(await screen.findByText('Import instrument file')).toBeInTheDocument();

    fireEvent.mouseDown(screen.getByRole('combobox', { name: /parser/i }));
    fireEvent.click(await screen.findByRole('option', { name: /Gen5 IL-6/i }));
    const file = new File(['well'], 'IL6-PLT-0001_Gen5.csv', { type: 'text/csv' });
    fireEvent.change(screen.getByTestId('import-file-input'), { target: { files: [file] } });
    fireEvent.click(screen.getByTestId('import-submit'));

    await waitFor(() => {
      expect(mockImportLimsRunFile).toHaveBeenCalledWith(
        'run-1',
        file,
        expect.objectContaining({ parser_id: 'parser-1', instrument_id: 'inst-1' })
      );
    });
    expect(await screen.findByText(/Unmatched 94/)).toBeInTheDocument();
    expect(screen.getAllByText(/No sample matches STD-S1/).length).toBeGreaterThan(0);
    expect(await screen.findByTestId('unmatched-summary')).toHaveTextContent('1 row did not match');
    expect(screen.getByText('IL6-SER-0001')).toBeInTheDocument();
  });

  test('fail requires a reason and create rerun opens the new run', async () => {
    renderRun();
    const failButton = await screen.findByTestId('fail-run-button');
    expect(failButton).toHaveTextContent('Fail run');
    fireEvent.click(failButton);
    expect(screen.getByTestId('fail-run-confirm')).toBeDisabled();
    fireEvent.change(screen.getByTestId('fail-run-reason'), {
      target: { value: 'QC-H out of range' },
    });
    fireEvent.click(screen.getByTestId('fail-run-confirm'));
    await waitFor(() => {
      expect(mockFailLimsRun).toHaveBeenCalledWith('run-1', 'QC-H out of range');
    });

    fireEvent.click(screen.getByTestId('create-rerun-button'));
    await waitFor(() => {
      expect(mockCreateLimsRunRerun).toHaveBeenCalledWith('run-1');
    });
    expect(await screen.findByRole('heading', { name: 'IL6 plate rerun' })).toBeInTheDocument();
  });

  test('a dual match stays linked and a miss stays on the data tab', async () => {
    mockGetLimsRunData.mockResolvedValue({
      rows: [
        {
          id: 'row-both',
          well_position: 'D4',
          sample_key: 'BOTH-1',
          sample_id: 's-both',
          link_note: 'Matched by client sample ID and sample name',
          row_data: { corr: 0.1 },
        },
        {
          id: 'row-off',
          well_position: 'E1',
          sample_key: 'OFF-1',
          sample_id: null,
          link_note: 'Not on this run',
          row_data: { corr: 0.2 },
        },
      ],
    });
    renderRun();
    fireEvent.click(await screen.findByRole('tab', { name: 'Data' }));
    expect(await screen.findByTestId('link-flag-summary')).toHaveTextContent(
      '1 row linked with a note'
    );
    expect(screen.getByText('Matched by client sample ID and sample name')).toBeInTheDocument();
    expect(screen.getByTestId('unmatched-summary')).toHaveTextContent('1 row did not match');
    expect(screen.getByText('Not on this run')).toBeInTheDocument();
  });

  test('a draft run has no import button', async () => {
    mockGetLimsRun.mockResolvedValue({ ...runningRun, status: 'draft', cohort: { sample_ids: [] } });
    renderRun();
    expect(await screen.findByRole('heading', { name: 'IL6 plate' })).toBeInTheDocument();
    expect(screen.queryByTestId('run-import-button')).not.toBeInTheDocument();
    expect(screen.queryByTestId('fail-run-button')).not.toBeInTheDocument();
    expect(screen.queryByTestId('create-rerun-button')).not.toBeInTheDocument();
    expect(screen.getByTestId('cancel-run-button')).toBeInTheDocument();
  });

  test('cancel is offered before import and hidden once data is imported', async () => {
    renderRun();
    expect(await screen.findByTestId('cancel-run-button')).toHaveTextContent('Cancel Run');
    expect(screen.getByTestId('fail-run-button')).toBeInTheDocument();
  });

  test('tech can substitute the instrument type on their own run', async () => {
    mockGetLimsRun.mockResolvedValue({
      ...runningRun,
      instrument_type_id: 't-plate',
      instrument_type_name: 'Plate reader',
      can_substitute_instrument_type: true,
    });
    renderRun();
    expect(await screen.findByText('Instrument type')).toBeInTheDocument();
    expect(screen.getByText('Plate reader')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('substitute-instrument-type-button'));
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByLabelText('New instrument type'));
    fireEvent.click(await screen.findByRole('option', { name: 'qPCR' }));
    fireEvent.change(screen.getByTestId('substitute-instrument-type-reason'), {
      target: { value: 'backup reader' },
    });
    fireEvent.click(screen.getByTestId('substitute-instrument-type-confirm'));
    await waitFor(() => {
      expect(mockSubstituteLimsRunInstrumentType).toHaveBeenCalledWith('run-1', {
        instrument_type_id: 't-qpcr',
        reason: 'backup reader',
      });
    });
  });

  test('substitute reason accepts 4000 characters and rejects 4001', async () => {
    mockGetLimsRun.mockResolvedValue({
      ...runningRun,
      instrument_type_id: 't-plate',
      instrument_type_name: 'Plate reader',
      can_substitute_instrument_type: true,
    });
    renderRun();
    fireEvent.click(await screen.findByTestId('substitute-instrument-type-button'));
    expect(await screen.findByRole('dialog')).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByLabelText('New instrument type'));
    fireEvent.click(await screen.findByRole('option', { name: 'qPCR' }));
    const field = screen.getByTestId('substitute-instrument-type-reason');
    expect(field).toHaveAttribute('maxLength', '4000');
    expect(screen.getByText(/1–4000/)).toBeInTheDocument();
    fireEvent.change(field, { target: { value: 'x'.repeat(4001) } });
    fireEvent.click(screen.getByTestId('substitute-instrument-type-confirm'));
    expect(await screen.findByText('Reason must be at most 4000 characters.')).toBeInTheDocument();
    expect(mockSubstituteLimsRunInstrumentType).not.toHaveBeenCalled();
    fireEvent.change(field, { target: { value: 'x'.repeat(4000) } });
    fireEvent.click(screen.getByTestId('substitute-instrument-type-confirm'));
    await waitFor(() => {
      expect(mockSubstituteLimsRunInstrumentType).toHaveBeenCalledWith('run-1', {
        instrument_type_id: 't-qpcr',
        reason: 'x'.repeat(4000),
      });
    });
  });

  test('a tech does not see substitute on another person\'s run', async () => {
    mockGetLimsRun.mockResolvedValue({
      ...runningRun,
      can_substitute_instrument_type: false,
    });
    renderRun();
    expect(await screen.findByRole('heading', { name: 'IL6 plate' })).toBeInTheDocument();
    expect(screen.queryByTestId('substitute-instrument-type-button')).not.toBeInTheDocument();
  });

  test('a run with imported data offers Fail and no Cancel', async () => {
    mockGetLimsRun.mockResolvedValue({ ...runningRun, has_imported_data: true });
    renderRun();
    expect(await screen.findByTestId('fail-run-button')).toHaveTextContent('Fail run');
    expect(screen.queryByTestId('cancel-run-button')).not.toBeInTheDocument();
    expect(screen.queryByText('Cancel Run')).not.toBeInTheDocument();
  });
});
