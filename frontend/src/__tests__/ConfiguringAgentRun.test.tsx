import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ConfiguringAgentRun, { dependencyProblem, diffText, includedRows, stoppedIncluded } from '../pages/admin/ConfiguringAgentRun';
import { apiService } from '../services/apiService';

jest.mock('../services/apiService', () => ({
  apiService: {
    getConfigurations: jest.fn(),
    createConfiguration: jest.fn(),
    uploadConfigurationDocument: jest.fn(),
    startConfigurationRun: jest.fn(),
    getConfigurationRun: jest.fn(),
    includeConfigurationStep: jest.fn(),
    redoConfigurationStep: jest.fn(),
    applyConfigurationRun: jest.fn(),
  },
}));

const api = apiService as unknown as Record<string, jest.Mock>;

const step = (over: Record<string, unknown>) => ({
  id: `s${over.position}`,
  position: 0,
  group: 'other',
  target: 'Whole Blood',
  action: 'Create list entry',
  why: 'SOP',
  decision: 'included',
  included: true,
  status: 'proposed',
  gap: null,
  error_message: null,
  depends_on: [],
  verb: 'Create',
  second_confirm: false,
  needs_permission: null,
  ...over,
});

const runWith = (steps: ReturnType<typeof step>[]) => ({
  id: 'run1',
  name: 'Cfg run',
  configuration_id: 'c1',
  status: 'proposing',
  goal_note: null,
  banner: null,
  error_message: null,
  applied_count: 0,
  skipped_count: 0,
  stopped_count: 0,
  steps,
});

const configuration = {
  id: 'c1',
  name: 'Cfg',
  description: null,
  documents: [{ id: 'd1', name: 'sop.pdf', status: 'ready', chunk_count: 3, error_message: null }],
  items: [],
  runs: [{ id: 'run1', name: 'Cfg run', status: 'proposing', banner: null }],
};

async function openRun(run: ReturnType<typeof runWith>) {
  api.getConfigurations.mockResolvedValue([configuration]);
  api.getConfigurationRun.mockResolvedValue(run);
  render(
    <MemoryRouter>
      <ConfiguringAgentRun />
    </MemoryRouter>
  );
  fireEvent.click(await screen.findByText('Cfg'));
  fireEvent.click(await screen.findByText('Cfg run · proposing'));
  await screen.findByText(/Run id run1/);
}

beforeEach(() => jest.clearAllMocks());

test('row helpers: included, stopped, dependency', () => {
  const run = runWith([
    step({ position: 0, status: 'stopped', gap: 'No API', included: false }),
    step({ position: 1, depends_on: [0] }),
    step({ position: 2, needs_permission: 'schema:edit' }),
  ]);
  expect(includedRows(run).map((s) => s.position)).toEqual([1]);
  expect(stoppedIncluded(run)).toEqual([]);
  expect(dependencyProblem(run)).toBe('Row 2 depends on row 1, which is stopped. Exclude row 2 too, or fix row 1.');
});

test('one change set with include checkboxes; no Accept/Skip; greyed rows say what they need', async () => {
  await openRun(runWith([
    step({ position: 0 }),
    step({ position: 1, target: 'Extraction', verb: 'Create', needs_permission: 'schema:edit', second_confirm: true }),
  ]));
  expect(screen.queryByText('Accept')).toBeNull();
  expect(screen.queryByText('Skip')).toBeNull();
  expect(screen.getByText('Needs schema:edit')).toBeInTheDocument();
  const greyed = screen.getByLabelText('Include Create Extraction') as HTMLInputElement;
  expect(greyed.disabled).toBe(true);
  expect(greyed.checked).toBe(false);
  expect(screen.getByText('Apply 1 changes')).toBeInTheDocument();
});

test('include toggle calls the include route', async () => {
  const run = runWith([step({ position: 0 })]);
  api.includeConfigurationStep.mockResolvedValue({ ...run, steps: [step({ position: 0, included: false, decision: 'excluded' })] });
  await openRun(run);
  fireEvent.click(screen.getByLabelText('Include Create Whole Blood'));
  await waitFor(() => expect(api.includeConfigurationStep).toHaveBeenCalledWith('run1', 's0', false));
  expect(await screen.findByText('Include at least one change.')).toBeInTheDocument();
});

test('plain rows apply after the single confirm; cancel writes nothing', async () => {
  const run = runWith([step({ position: 0 })]);
  api.applyConfigurationRun.mockResolvedValue({ ...run, status: 'done' });
  await openRun(run);
  fireEvent.click(screen.getByText('Apply 1 changes'));
  fireEvent.click(await screen.findByText('Cancel'));
  expect(api.applyConfigurationRun).not.toHaveBeenCalled();
  fireEvent.click(screen.getByText('Apply 1 changes'));
  fireEvent.click(await screen.findByText('Confirm'));
  await waitFor(() => expect(api.applyConfigurationRun).toHaveBeenCalledWith('run1', false));
});

test('high-impact rows need the second confirm with the responsibility checkbox', async () => {
  const run = runWith([step({ position: 0, verb: 'Set inactive', target: 'Old matrix', second_confirm: true })]);
  api.applyConfigurationRun.mockResolvedValue({ ...run, status: 'done' });
  await openRun(run);
  fireEvent.click(screen.getByText('Apply 1 changes'));
  fireEvent.click(await screen.findByText('Confirm'));
  expect(await screen.findByText('You are responsible for these changes')).toBeInTheDocument();
  expect(api.applyConfigurationRun).not.toHaveBeenCalled();
  const confirm = screen.getByRole('button', { name: 'Confirm' });
  expect(confirm).toBeDisabled();
  fireEvent.click(screen.getByLabelText('I am responsible for these changes'));
  fireEvent.click(screen.getByRole('button', { name: 'Confirm' }));
  await waitFor(() => expect(api.applyConfigurationRun).toHaveBeenCalledWith('run1', true));
});

test('every stop is shown in place and an included stop is called out', async () => {
  await openRun(runWith([
    step({ position: 0 }),
    step({ position: 1, status: 'stopped', gap: 'Drop and delete are never applied by the configuring agent.' }),
    step({ position: 2 }),
  ]));
  expect(screen.getByText('Drop and delete are never applied by the configuring agent.')).toBeInTheDocument();
  expect(screen.getByText(/Apply writes nothing while an included row is stopped/)).toBeInTheDocument();
  expect(screen.getByText('Apply 3 changes')).toBeInTheDocument();
});

test('a retryable API stop does not block Apply on screen', () => {
  const run = runWith([step({ position: 0, status: 'stopped', gap: 'The API refused this change (404): Not found', retryable: true })]);
  expect(stoppedIncluded(run)).toEqual([]);
  expect(includedRows(run)).toHaveLength(1);
});

test('a gap that merely starts with the API prefix is shown as a normal stop', async () => {
  const forged = 'The API refused this change (404): pretend, please retry me';
  const run = runWith([step({ position: 0, status: 'stopped', gap: forged, retryable: false })]);
  expect(stoppedIncluded(run)).toHaveLength(1);
  await openRun(run);
  expect(screen.getByText(/Apply writes nothing while an included row is stopped/)).toBeInTheDocument();
  expect(screen.queryByText(/Fix the cause and apply again/)).toBeNull();
});

test('G5: rows show before and after; a rerun row says no change', async () => {
  expect(diffText(null)).toBeNull();
  expect(diffText({ before: null, after: { name: 'Serum' }, changed: true })).toBe(
    'Before: not there yet → After: {"name":"Serum"}'
  );
  expect(diffText({ before: { active: true }, after: { active: true }, changed: false })).toBe(
    'No change: already {"active":true}'
  );
  await openRun(runWith([
    step({ position: 0, diff: { before: { permission_ids: [] }, after: { permission_ids: ['p1'] }, changed: true } }),
    step({ position: 1, status: 'unchanged', included: false, decision: 'excluded',
      diff: { before: { name: 'Serum' }, after: { name: 'Serum' }, changed: false } }),
  ]));
  expect(screen.getByTestId('diff-0').textContent).toBe('Before: {"permission_ids":[]} → After: {"permission_ids":["p1"]}');
  expect(screen.getByTestId('diff-1').textContent).toBe('No change: already {"name":"Serum"}');
});

test('viewer-only stop: banner and count come from the run payload', async () => {
  await openRun({
    ...runWith([step({ position: 0, status: 'stopped', gap: 'This would grant permissions you don\'t hold (result:review).', stopped_for_viewer: true })]),
    banner: "Can't apply this change through configuration APIs",
    stopped_count: 1,
  });
  expect(screen.getByText("Can't apply this change through configuration APIs")).toBeInTheDocument();
  expect(screen.getByText(/stopped 1/)).toBeInTheDocument();
});
