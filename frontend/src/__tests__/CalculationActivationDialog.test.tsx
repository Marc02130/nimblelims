import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import CalculationActivationDialog from '../components/analyses/CalculationActivationDialog';

jest.mock('../services/apiService', () => ({
  apiService: {
    getCalculationActivationReview: jest.fn(),
    issueCalculationConfirmToken: jest.fn(),
    activateCalculationConfig: jest.fn(),
  },
}));

const { apiService } = require('../services/apiService');

const reviewDocument = (overrides: Record<string, unknown> = {}) => ({
  analysis: { id: 'a1', name: 'Metals panel' },
  analyte: { id: 'b1', name: 'Lead' },
  configuration: { name: 'Lead recovery', version: 2, calculation_order: 1 },
  lock_hash: 'd3cea84a',
  function_versions: [{ function: 'recovery_percent', version: 1 }],
  validation_state: 'no_test_cases',
  test_cases: {
    total: 0,
    notice: 'No test cases recorded',
    summary: 'No test cases recorded, no dry run',
    cases: [],
  },
  dry_run: { done: false, run_at: null },
  plain_language: {
    stages: [{ stage: 's1', text: 'Takes the spiked and unspiked readings.' }],
    result_pointer: 'The calculated value of s1 output recovery will be published as the result.',
  },
  formulas: [{ stage: 's2', kind: 'ad_hoc_formula', name: null, version: 1, text: 'a * 2' }],
  stage_declarations: [
    {
      stage: 's1',
      outcome: 'pass_fail',
      verdict: 'pass_fail',
      flag: null,
      missing_limit_flag: null,
      gates: [],
      precedence_place: 1,
      reads_limit: false,
    },
  ],
  diff: {
    previous_version: 1,
    summary: '1 change',
    changes: [{ stage: 's2', category: 'formula', field: 'formula_text', old: 'a * 1', new: 'a * 2' }],
  },
  confirm_label: 'Activate with no test cases recorded',
  ...overrides,
});

const renderDialog = (onActivated = jest.fn()) =>
  render(
    <CalculationActivationDialog
      open
      analysisId="a1"
      analyteId="b1"
      analyteName="Lead"
      onClose={jest.fn()}
      onActivated={onActivated}
    />
  );

describe('CalculationActivationDialog', () => {
  beforeEach(() => {
    apiService.getCalculationActivationReview.mockReset();
    apiService.issueCalculationConfirmToken.mockReset();
    apiService.activateCalculationConfig.mockReset();
  });

  test('renders the review document and the no-test-cases confirm label', async () => {
    apiService.getCalculationActivationReview.mockResolvedValue({
      document: reviewDocument(),
      review_hash: 'hash-1',
    });
    renderDialog();

    expect(await screen.findByText('Test cases and dry run')).toBeInTheDocument();
    expect(screen.getAllByText('No test cases recorded')).toHaveLength(2);
    expect(screen.getByText('a * 2', { selector: 'pre' })).toBeInTheDocument();
    expect(screen.getByText('a * 1')).toBeInTheDocument();
    expect(screen.getByText('Declarations of every stage')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Activate with no test cases recorded' })).toBeInTheDocument();
    expect(screen.queryByText(/configuration is validated/i)).not.toBeInTheDocument();
  });

  test('flags a test case whose expected value came from system output', async () => {
    apiService.getCalculationActivationReview.mockResolvedValue({
      document: reviewDocument({
        validation_state: 'tests_none_passed',
        test_cases: {
          total: 1,
          notice: null,
          summary: '1 test case, 0 passed, 1 from system output, no dry run',
          cases: [
            {
              name: 'agent case',
              expected_source: 'system_output',
              from_system_output: true,
              passed_on_current_lock: null,
            },
          ],
        },
        confirm_label: 'Activate',
      }),
      review_hash: 'hash-2',
    });
    renderDialog();

    expect(await screen.findByText('From system output')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Activate' })).toBeInTheDocument();
  });

  test('issues a token for the shown review hash, then activates with it', async () => {
    apiService.getCalculationActivationReview.mockResolvedValue({
      document: reviewDocument(),
      review_hash: 'hash-1',
    });
    apiService.issueCalculationConfirmToken.mockResolvedValue({ confirm_token: 'tok', review_hash: 'hash-1' });
    apiService.activateCalculationConfig.mockResolvedValue({ id: 'x' });
    const onActivated = jest.fn();
    renderDialog(onActivated);

    fireEvent.click(await screen.findByRole('button', { name: 'Activate with no test cases recorded' }));

    await waitFor(() => expect(apiService.activateCalculationConfig).toHaveBeenCalledWith('a1', 'b1', 'tok'));
    expect(apiService.issueCalculationConfirmToken).toHaveBeenCalledWith('a1', 'b1', 'hash-1');
    expect(onActivated).toHaveBeenCalled();
    expect(await screen.findByText(/The configuration is active/)).toBeInTheDocument();
  });

  test('shows a refusal and keeps the dialog open', async () => {
    apiService.getCalculationActivationReview.mockResolvedValue({
      document: reviewDocument(),
      review_hash: 'hash-1',
    });
    apiService.issueCalculationConfirmToken.mockResolvedValue({ confirm_token: 'tok', review_hash: 'hash-1' });
    apiService.activateCalculationConfig.mockRejectedValue({
      response: { data: { detail: { code: 'confirm_token_review_changed', message: 'The review changed.' } } },
    });
    renderDialog();

    fireEvent.click(await screen.findByRole('button', { name: 'Activate with no test cases recorded' }));

    expect(await screen.findByText('The review changed.')).toBeInTheDocument();
    expect(screen.queryByText(/The configuration is active/)).not.toBeInTheDocument();
  });

  test('shows the reason when there is nothing to review', async () => {
    apiService.getCalculationActivationReview.mockRejectedValue({
      response: { data: { detail: { code: 'already_active', message: 'This configuration version is already active.' } } },
    });
    renderDialog();

    expect(await screen.findByText('This configuration version is already active.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Activate/ })).not.toBeInTheDocument();
  });
});
