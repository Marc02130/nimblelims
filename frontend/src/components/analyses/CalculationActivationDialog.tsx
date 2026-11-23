import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { apiService } from '../../services/apiService';
import { apiErrorText } from '../../utils/apiErrorText';

interface ReviewTestCase {
  name: string;
  expected_source: string;
  from_system_output: boolean;
  passed_on_current_lock: boolean | null;
}

interface ReviewChange {
  stage: string;
  category: string;
  field: string;
  old: string | null;
  new: string | null;
}

interface ReviewDocument {
  analysis: { id: string; name: string };
  analyte: { id: string; name: string | null };
  configuration: { name: string; version: number; calculation_order: number };
  lock_hash: string;
  function_versions: { function: string; version: number }[];
  validation_state: string;
  test_cases: {
    total: number;
    notice: string | null;
    summary: string;
    cases: ReviewTestCase[];
  };
  dry_run: { done: boolean; run_at: string | null };
  plain_language: {
    stages: { stage: string; text: string }[];
    result_pointer: string;
  };
  formulas: { stage: string; kind: string; name: string | null; version: number | null; text: string | null }[];
  stage_declarations: {
    stage: string;
    outcome: string | null;
    verdict: string | null;
    flag: string | null;
    missing_limit_flag: string | null;
    gates: string[];
    precedence_place: number | null;
    reads_limit: boolean;
  }[];
  diff: { previous_version: number | null; summary: string; changes: ReviewChange[] };
  confirm_label: string;
}

interface ReviewResponse {
  document: ReviewDocument;
  review_hash: string;
}

export interface CalculationActivationDialogProps {
  open: boolean;
  analysisId: string;
  analyteId: string;
  analyteName?: string;
  onClose: () => void;
  onActivated?: () => void;
}

const VALIDATION_STATE_TEXT: Record<string, string> = {
  no_test_cases: 'No test cases recorded',
  tests_none_passed: 'Test cases recorded, none passed on the current calculator lock',
  tests_some_passed: 'Test cases recorded, some passed on the current calculator lock',
  tests_all_passed: 'Test cases recorded, all passed on the current calculator lock',
};

const show = (value: string | number | null | undefined): string =>
  value === null || value === undefined || value === '' ? 'none' : String(value);

const CalculationActivationDialog: React.FC<CalculationActivationDialogProps> = ({
  open,
  analysisId,
  analyteId,
  analyteName,
  onClose,
  onActivated,
}) => {
  const [loading, setLoading] = useState(false);
  const [review, setReview] = useState<ReviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activating, setActivating] = useState(false);
  const [activated, setActivated] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setReview(null);
    setActivated(false);
    try {
      const response = await apiService.getCalculationActivationReview(analysisId, analyteId);
      setReview(response as ReviewResponse);
    } catch (err: any) {
      setError(apiErrorText(err, 'The review could not be loaded.'));
    } finally {
      setLoading(false);
    }
  }, [analysisId, analyteId]);

  useEffect(() => {
    if (open) {
      load();
    }
  }, [open, load]);

  const handleActivate = async () => {
    if (!review) return;
    setActivating(true);
    setError(null);
    try {
      const issued = await apiService.issueCalculationConfirmToken(analysisId, analyteId, review.review_hash);
      await apiService.activateCalculationConfig(analysisId, analyteId, issued.confirm_token);
      setActivated(true);
      if (onActivated) onActivated();
    } catch (err: any) {
      setError(apiErrorText(err, 'The configuration was not activated.'));
    } finally {
      setActivating(false);
    }
  };

  const doc = review ? review.document : null;

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth aria-labelledby="calc-activation-title">
      <DialogTitle id="calc-activation-title">
        Review calculation configuration{analyteName ? `: ${analyteName}` : ''}
      </DialogTitle>
      <DialogContent dividers>
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress aria-label="Loading review" />
          </Box>
        )}
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        {activated && (
          <Alert severity="success" sx={{ mb: 2 }}>
            The configuration is active. The activation is recorded and cannot be changed.
          </Alert>
        )}
        {doc && !activated && (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', alignItems: 'center' }}>
              <Typography variant="subtitle1">
                {doc.analysis.name} / {doc.analyte.name}
              </Typography>
              <Chip size="small" label={`${doc.configuration.name}, version ${doc.configuration.version}`} />
              <Chip size="small" label={`Order ${doc.configuration.calculation_order}`} />
              <Chip
                size="small"
                color={doc.validation_state === 'tests_all_passed' ? 'success' : 'warning'}
                label={VALIDATION_STATE_TEXT[doc.validation_state] || doc.validation_state}
              />
            </Box>

            <Typography variant="body2">
              Only the functions listed here are validated catalog functions. This configuration is not labelled
              validated.
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Calculator lock {doc.lock_hash}. Catalog functions:{' '}
              {doc.function_versions.map((f) => `${f.function} version ${f.version}`).join(', ') || 'none'}.
            </Typography>

            <Divider />
            <Typography variant="h6">Test cases and dry run</Typography>
            {doc.test_cases.notice && <Alert severity="warning">{doc.test_cases.notice}</Alert>}
            <Typography variant="body2">{doc.test_cases.summary}</Typography>
            {doc.test_cases.cases.length > 0 && (
              <Table size="small" aria-label="Test cases">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Expected value source</TableCell>
                    <TableCell>Passed on current lock</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {doc.test_cases.cases.map((c) => (
                    <TableRow key={c.name}>
                      <TableCell>{c.name}</TableCell>
                      <TableCell>
                        {c.from_system_output ? (
                          <Chip size="small" color="warning" label="From system output" />
                        ) : (
                          'Independent'
                        )}
                      </TableCell>
                      <TableCell>
                        {c.passed_on_current_lock === null ? 'Not run' : c.passed_on_current_lock ? 'Yes' : 'No'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
            <Typography variant="body2">
              {doc.dry_run.done ? `Dry run done ${doc.dry_run.run_at}` : 'No dry run done'}
            </Typography>

            <Divider />
            <Typography variant="h6">Change from the previous version</Typography>
            <Typography variant="body2">{doc.diff.summary}</Typography>
            {doc.diff.changes.length > 0 && (
              <Table size="small" aria-label="Changes">
                <TableHead>
                  <TableRow>
                    <TableCell>Stage</TableCell>
                    <TableCell>Change</TableCell>
                    <TableCell>Field</TableCell>
                    <TableCell>Before</TableCell>
                    <TableCell>After</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {doc.diff.changes.map((c, index) => (
                    <TableRow key={`${c.stage}-${c.field}-${index}`}>
                      <TableCell>{c.stage}</TableCell>
                      <TableCell>{c.category}</TableCell>
                      <TableCell>{c.field}</TableCell>
                      <TableCell sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>{show(c.old)}</TableCell>
                      <TableCell sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>{show(c.new)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}

            <Divider />
            <Typography variant="h6">What it does, in plain language</Typography>
            {doc.plain_language.stages.map((s) => (
              <Typography key={s.stage} variant="body2">
                <strong>{s.stage}</strong>: {s.text}
              </Typography>
            ))}
            <Typography variant="body2">{doc.plain_language.result_pointer}</Typography>

            {doc.formulas.length > 0 && (
              <>
                <Divider />
                <Typography variant="h6">Formula text</Typography>
                {doc.formulas.map((f) => (
                  <Box key={f.stage}>
                    <Typography variant="caption" color="text.secondary">
                      {f.stage}: {f.kind === 'saved_formula' ? `saved formula ${f.name}` : 'ad hoc formula'}
                      {f.version !== null ? `, version ${f.version}` : ''}
                    </Typography>
                    <Box
                      component="pre"
                      sx={{ m: 0, p: 1, bgcolor: 'action.hover', borderRadius: 1, whiteSpace: 'pre-wrap' }}
                    >
                      {show(f.text)}
                    </Box>
                  </Box>
                ))}
              </>
            )}

            <Divider />
            <Typography variant="h6">Declarations of every stage</Typography>
            <Table size="small" aria-label="Stage declarations">
              <TableHead>
                <TableRow>
                  <TableCell>Stage</TableCell>
                  <TableCell>Outcome</TableCell>
                  <TableCell>Verdict</TableCell>
                  <TableCell>Flag</TableCell>
                  <TableCell>Missing limit flag</TableCell>
                  <TableCell>Gates</TableCell>
                  <TableCell>Precedence place</TableCell>
                  <TableCell>Reads a limit</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {doc.stage_declarations.map((d) => (
                  <TableRow key={d.stage}>
                    <TableCell>{d.stage}</TableCell>
                    <TableCell>{show(d.outcome)}</TableCell>
                    <TableCell>{show(d.verdict)}</TableCell>
                    <TableCell>{show(d.flag)}</TableCell>
                    <TableCell>{show(d.missing_limit_flag)}</TableCell>
                    <TableCell>{d.gates.length ? d.gates.join(', ') : 'none'}</TableCell>
                    <TableCell>{show(d.precedence_place)}</TableCell>
                    <TableCell>{d.reads_limit ? 'Yes' : 'No'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{activated ? 'Close' : 'Cancel'}</Button>
        {doc && !activated && (
          <Button variant="contained" color="primary" onClick={handleActivate} disabled={activating}>
            {doc.confirm_label}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default CalculationActivationDialog;
