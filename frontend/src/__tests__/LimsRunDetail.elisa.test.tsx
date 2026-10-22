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
const mockRejectLimsRun = jest.fn();
const mockCreateLimsRunRerun = jest.fn();
const mockGetLimsRunValueChoices = jest.fn();

jest.mock('../services/apiService', () => ({
  apiService: {
    getLimsRun: (...args: any[]) => mockGetLimsRun(...args),
    getAnalyses: (...args: any[]) => mockGetAnalyses(...args),
    getLimsRunData: (...args: any[]) => mockGetLimsRunData(...args),
    getDataParsers: (...args: any[]) => mockGetDataParsers(...args),
    importLimsRunFile: (...args: any[]) => mockImportLimsRunFile(...args),
    rejectLimsRun: (...args: any[]) => mockRejectLimsRun(...args),
    createLimsRunRerun: (...args: any[]) => mockCreateLimsRunRerun(...args),
    getLimsRunValueChoices: (...args: any[]) => mockGetLimsRunValueChoices(...args),
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
    mockRejectLimsRun.mockResolvedValue({ ...runningRun, status: 'failed', status_reason: 'QC-H out of range' });
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

  test('reject requires a reason and create rerun opens the new run', async () => {
    renderRun();
    fireEvent.click(await screen.findByTestId('reject-plate-button'));
    expect(screen.getByTestId('reject-confirm')).toBeDisabled();
    fireEvent.change(screen.getByTestId('reject-reason'), {
      target: { value: 'QC-H out of range' },
    });
    fireEvent.click(screen.getByTestId('reject-confirm'));
    await waitFor(() => {
      expect(mockRejectLimsRun).toHaveBeenCalledWith('run-1', 'QC-H out of range');
    });

    fireEvent.click(screen.getByTestId('create-rerun-button'));
    await waitFor(() => {
      expect(mockCreateLimsRunRerun).toHaveBeenCalledWith('run-1');
    });
    expect(await screen.findByRole('heading', { name: 'IL6 plate rerun' })).toBeInTheDocument();
  });

  test('a draft run has no import button', async () => {
    mockGetLimsRun.mockResolvedValue({ ...runningRun, status: 'draft', cohort: { sample_ids: [] } });
    renderRun();
    expect(await screen.findByRole('heading', { name: 'IL6 plate' })).toBeInTheDocument();
    expect(screen.queryByTestId('run-import-button')).not.toBeInTheDocument();
    expect(screen.queryByTestId('reject-plate-button')).not.toBeInTheDocument();
    expect(screen.queryByTestId('create-rerun-button')).not.toBeInTheDocument();
  });
});
