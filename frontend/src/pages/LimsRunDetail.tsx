import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Chip,
  List,
  ListItem,
  ListItemText,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useNavigate, useParams } from 'react-router-dom';
import { apiService, PromotionPreview } from '../services/apiService';
import { formatInstant } from '../utils/localDate';
import PublishPromotionDialog from '../components/runs/PublishPromotionDialog';
import RunImportDialog, {
  ImportFileResult,
  ParserOption,
} from '../components/runs/RunImportDialog';
import FailRunDialog from '../components/runs/FailRunDialog';
import ValueChoicesPanel from '../components/runs/ValueChoicesPanel';
import DoseResponseTab from './DoseResponse/DoseResponseTab';
import StartCohortPanel from '../components/experiments/StartCohortPanel';
import ReagentUsePanel from '../components/reagents/ReagentUsePanel';

const apiErrorMsg = (err: any, fallback: string): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') {
    if (detail.message) {
      const extra =
        Array.isArray(detail.errors) && detail.errors.length
          ? ` ${detail.errors.slice(0, 3).join('; ')}`
          : '';
      return `${detail.message}${extra}`;
    }
    if (detail.code === 'promotion_conflict') {
      return 'Publish blocked: result conflicts with another run or manual entry.';
    }
  }
  if (Array.isArray(detail) && detail.length > 0) return detail[0]?.msg || fallback;
  return fallback;
};

const isAnalysisRequiredError = (err: any): boolean => {
  const detail = err?.response?.data?.detail;
  return (
    err?.response?.status === 400 &&
    detail &&
    typeof detail === 'object' &&
    (detail.code === 'analysis_required' || detail.code === 'analysis_required_ack')
  );
};

interface RunDetail {
  id: string;
  name: string;
  description?: string;
  experiment_template_id: string;
  analysis_id?: string | null;
  status: string;
  lifecycle_type?: string;
  cohort?: { sample_ids?: string[]; locked_at?: string | null } | null;
  started_at?: string;
  completed_at?: string;
  published_at?: string;
  canceled_at?: string;
  status_reason?: string | null;
  rejected_at?: string | null;
  failed_by?: string | null;
  replaces_run_id?: string | null;
  has_imported_data?: boolean;
  created_at: string;
  modified_at?: string;
}

const TERMINAL_STATUSES = new Set(['published', 'failed', 'canceled']);

const statusColor = (s: string) => {
  if (s === 'published') return 'success';
  if (s === 'running') return 'warning';
  if (s === 'results_received') return 'warning';
  if (s === 'ordered') return 'info';
  if (s === 'complete') return 'info';
  if (s === 'failed') return 'error';
  if (s === 'canceled') return 'default';
  return 'default';
};

const statusLabel = (s: string) => {
  if (s === 'results_received') return 'Results Received';
  if (s === 'ordered') return 'Ordered';
  if (s === 'canceled') return 'Canceled';
  return s.charAt(0).toUpperCase() + s.slice(1);
};

const LimsRunDetail: React.FC = () => {
  const navigate = useNavigate();
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [dataRows, setDataRows] = useState<any[]>([]);
  const [dataLoading, setDataLoading] = useState(false);
  const [transitioning, setTransitioning] = useState(false);
  const [analyses, setAnalyses] = useState<{ id: string; name: string }[]>([]);
  const [savingAnalysis, setSavingAnalysis] = useState(false);
  const [noAnalysisDialog, setNoAnalysisDialog] = useState(false);
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);
  const [publishPreview, setPublishPreview] = useState<PromotionPreview | null>(null);
  const [publishPreviewLoading, setPublishPreviewLoading] = useState(false);
  const [publishPreviewError, setPublishPreviewError] = useState<string | null>(null);
  const [publishing, setPublishing] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [parsers, setParsers] = useState<ParserOption[]>([]);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<ImportFileResult | null>(null);
  const [failOpen, setFailOpen] = useState(false);
  const [failing, setFailing] = useState(false);
  const [failError, setFailError] = useState<string | null>(null);
  const [rerunning, setRerunning] = useState(false);

  useEffect(() => {
    if (!runId) return;
    loadRun();
  }, [runId]);

  useEffect(() => {
    (async () => {
      try {
        const res: any = await apiService.getAnalyses({
          page: 1,
          size: 500,
          active: true,
        });
        const list = res?.analyses ?? (Array.isArray(res) ? res : []);
        setAnalyses(list.map((a: any) => ({ id: a.id, name: a.name })));
      } catch {
        /* ignore */
      }
    })();
  }, []);

  const loadRun = async () => {
    if (!runId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getLimsRun(runId);
      setRun(data);
    } catch (err: any) {
      setError(apiErrorMsg(err, 'Failed to load run'));
    } finally {
      setLoading(false);
    }
  };

  const loadData = async () => {
    if (!runId) return;
    setDataLoading(true);
    try {
      const res = await apiService.getLimsRunData(runId, { page: 1, size: 200 });
      setDataRows(res?.rows ?? []);
    } catch {
      // non-fatal
    } finally {
      setDataLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 1) loadData();
  }, [activeTab, runId]);

  const handleAnalysisChange = async (analysisId: string) => {
    if (!runId || !analysisId) return;
    setSavingAnalysis(true);
    setError(null);
    try {
      const updated = await apiService.updateLimsRun(runId, { analysis_id: analysisId });
      setRun(updated);
    } catch (err: any) {
      setError(apiErrorMsg(err, 'Failed to update analysis'));
    } finally {
      setSavingAnalysis(false);
    }
  };

  const doStart = async (sampleIds?: string[]) => {
    if (!runId) return;
    if (!run?.analysis_id) {
      setNoAnalysisDialog(true);
      return;
    }
    const ids =
      sampleIds && sampleIds.length > 0
        ? sampleIds
        : (run.cohort?.sample_ids || []).map(String);
    if (ids.length === 0) {
      setError(
        'Select a sample cohort first (scan plate/tube below), then Start.',
      );
      return;
    }
    setTransitioning(true);
    setError(null);
    try {
      await apiService.startLimsRun(runId, { sample_ids: ids });
      setNoAnalysisDialog(false);
      await loadRun();
    } catch (err: any) {
      if (isAnalysisRequiredError(err)) {
        setNoAnalysisDialog(true);
      } else {
        setError(apiErrorMsg(err, 'Failed to start run'));
      }
    } finally {
      setTransitioning(false);
    }
  };

  const openPublishDialog = async () => {
    if (!runId || !run) return;
    setSuccessMsg(null);
    setError(null);
    setPublishDialogOpen(true);
    setPublishPreview(null);
    setPublishPreviewError(null);

    if (!run.analysis_id) {
      setPublishPreviewLoading(false);
      return;
    }

    setPublishPreviewLoading(true);
    try {
      const preview = await apiService.getLimsRunPromotionPreview(runId);
      setPublishPreview(preview);
    } catch (err: any) {
      setPublishPreviewError(apiErrorMsg(err, 'Failed to load promotion preview'));
    } finally {
      setPublishPreviewLoading(false);
    }
  };

  const confirmPublish = async () => {
    if (!runId) return;
    setPublishing(true);
    setError(null);
    try {
      await apiService.publishLimsRun(runId);
      setPublishDialogOpen(false);
      setPublishPreview(null);
      const created = publishPreview?.create_count ?? 0;
      const updated = publishPreview?.update_count ?? 0;
      setSuccessMsg(
        `Published. Results: ${created} created, ${updated} updated.`,
      );
      await loadRun();
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      // Surface 409 conflicts in-dialog when possible
      if (status === 409 && detail?.preview) {
        setPublishPreview(detail.preview as PromotionPreview);
        setPublishPreviewError(null);
      }
      setError(apiErrorMsg(err, 'Failed to publish run'));
    } finally {
      setPublishing(false);
    }
  };

  const openImport = async () => {
    if (!run) return;
    setImportOpen(true);
    setImportError(null);
    setImportResult(null);
    try {
      const list: any = await apiService.getDataParsers({
        active_only: true,
        analysis_id: run.analysis_id || undefined,
      });
      const arr = Array.isArray(list) ? list : [];
      setParsers(
        arr.map((p: any) => ({
          id: String(p.id),
          name: String(p.name),
          version: p.version,
          instrument_id: p.instrument_id || null,
          cro_source_id: p.cro_source_id || null,
        })),
      );
    } catch (err: any) {
      setParsers([]);
      setImportError(apiErrorMsg(err, 'Failed to load parsers'));
    }
  };

  const submitImport = async (parser: ParserOption, file: File) => {
    if (!runId) return;
    if (!parser.instrument_id && !parser.cro_source_id) {
      setImportError('This parser has no instrument or CRO source');
      return;
    }
    setImporting(true);
    setImportError(null);
    try {
      const result = await apiService.importLimsRunFile(runId, file, {
        parser_id: parser.id,
        instrument_id: parser.instrument_id || undefined,
        cro_source_id: parser.cro_source_id || undefined,
      });
      setImportResult(result);
      setActiveTab(1);
      await loadData();
      await loadRun();
    } catch (err: any) {
      setImportError(apiErrorMsg(err, 'Import failed'));
    } finally {
      setImporting(false);
    }
  };

  const confirmFail = async (reason: string) => {
    if (!runId) return;
    setFailing(true);
    setFailError(null);
    try {
      await apiService.failLimsRun(runId, reason);
      setFailOpen(false);
      setSuccessMsg(
        'Run failed. Imported rows were kept. Rerun every sample on this plate.',
      );
      await loadRun();
    } catch (err: any) {
      setFailError(apiErrorMsg(err, 'Could not fail the run'));
    } finally {
      setFailing(false);
    }
  };

  const handleRerun = async () => {
    if (!runId) return;
    setRerunning(true);
    setError(null);
    try {
      const created = await apiService.createLimsRunRerun(runId);
      navigate(`/runs/${created.id}`);
    } catch (err: any) {
      setError(apiErrorMsg(err, 'Failed to create rerun'));
    } finally {
      setRerunning(false);
    }
  };

  const handleTransition = async (
    action: 'order' | 'start' | 'results-received' | 'review' | 'publish' | 'cancel',
  ) => {
    if (!runId) return;
    if (action === 'start') {
      await doStart();
      return;
    }
    if (action === 'publish') {
      await openPublishDialog();
      return;
    }
    setTransitioning(true);
    try {
      if (action === 'order') await apiService.orderLimsRun(runId);
      else if (action === 'results-received') await apiService.markResultsReceived(runId);
      else if (action === 'review') await apiService.reviewLimsRun(runId);
      else if (action === 'cancel') await apiService.cancelLimsRun(runId);
      await loadRun();
    } catch (err: any) {
      setError(apiErrorMsg(err, `Failed to ${action} run`));
    } finally {
      setTransitioning(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!run) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error || 'Run not found'}</Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/runs')} sx={{ mt: 2 }}>
          Back to Runs
        </Button>
      </Box>
    );
  }

  const analysisName =
    analyses.find((a) => a.id === run.analysis_id)?.name ||
    (run.analysis_id ? run.analysis_id.slice(0, 8) + '…' : null);
  const canEditAnalysis = run.status === 'draft' || run.status === 'ordered';

  return (
    <Box sx={{ p: 3 }}>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/runs')} sx={{ mb: 2 }}>
        Back to Runs
      </Button>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {successMsg && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMsg(null)}>
          {successMsg}
        </Alert>
      )}

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
        <Typography variant="h4">{run.name}</Typography>
        <Chip label={statusLabel(run.status)} color={statusColor(run.status) as any} />
        {run.analysis_id ? (
          <Chip size="small" color="primary" variant="outlined" label={`Analysis: ${analysisName}`} />
        ) : (
          <Chip size="small" color="warning" variant="outlined" label="Analysis required" />
        )}
      </Box>
      {run.description && (
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          {run.description}
        </Typography>
      )}

      <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
        {run.status === 'draft' && run.lifecycle_type === 'cro' && (
          <Button
            variant="contained"
            color="primary"
            size="small"
            disabled={transitioning}
            onClick={() => handleTransition('order')}
          >
            Send to CRO
          </Button>
        )}
        {run.status === 'draft' && run.lifecycle_type !== 'cro' && (
          <Button
            variant="contained"
            color="primary"
            size="small"
            disabled={transitioning}
            onClick={() => handleTransition('start')}
          >
            Start Run
          </Button>
        )}
        {run.status === 'ordered' && (
          <Button
            variant="contained"
            color="primary"
            size="small"
            disabled={transitioning}
            onClick={() => handleTransition('start')}
          >
            Mark Running
          </Button>
        )}
        {run.status === 'running' && run.lifecycle_type === 'cro' && (
          <Button
            variant="contained"
            color="warning"
            size="small"
            disabled={transitioning}
            onClick={() => handleTransition('results-received')}
          >
            Mark Results Received
          </Button>
        )}
        {run.status === 'running' && run.lifecycle_type !== 'cro' && (
          <Button
            variant="contained"
            color="warning"
            size="small"
            disabled={transitioning}
            onClick={() => handleTransition('review')}
          >
            Mark Ready for Review
          </Button>
        )}
        {run.status === 'results_received' && (
          <Button
            variant="contained"
            color="warning"
            size="small"
            disabled={transitioning}
            onClick={() => handleTransition('review')}
          >
            Mark Ready for Review
          </Button>
        )}
        {run.status === 'complete' && (
          <Button
            variant="contained"
            color="success"
            size="small"
            disabled={transitioning}
            onClick={() => handleTransition('publish')}
          >
            Publish
          </Button>
        )}
        {!TERMINAL_STATUSES.has(run.status) && !run.has_imported_data && (
          <Button
            variant="outlined"
            color="error"
            size="small"
            disabled={transitioning}
            data-testid="cancel-run-button"
            onClick={() => handleTransition('cancel')}
          >
            Cancel Run
          </Button>
        )}
        {(run.status === 'running' || run.status === 'results_received') && (
          <Button
            variant="contained"
            size="small"
            disabled={transitioning || !run.analysis_id}
            data-testid="run-import-button"
            onClick={() => void openImport()}
          >
            Import
          </Button>
        )}
        {(run.status === 'running' ||
          run.status === 'results_received' ||
          run.status === 'complete') && (
          <Button
            variant="outlined"
            color="error"
            size="small"
            disabled={transitioning}
            data-testid="fail-run-button"
            onClick={() => {
              setFailError(null);
              setFailOpen(true);
            }}
          >
            Fail run
          </Button>
        )}
        {run.status !== 'draft' && (
          <Button
            variant="outlined"
            size="small"
            disabled={rerunning || transitioning}
            data-testid="create-rerun-button"
            onClick={() => void handleRerun()}
          >
            Create rerun
          </Button>
        )}
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} variant="scrollable" scrollButtons="auto">
          <Tab label="Overview" />
          <Tab label="Data" />
          <Tab label="Dose Response" />
        </Tabs>
      </Box>

      {activeTab === 0 && (
        <Card variant="outlined" sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>
              Analysis (required)
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Every run must have an analysis. On publish, imported data is written to Tests and
              Results for that assay. Data parsers must be linked to this analysis.
            </Typography>
            <FormControl
              fullWidth
              size="small"
              required
              sx={{ maxWidth: 400, mb: 2 }}
              disabled={!canEditAnalysis || savingAnalysis}
            >
              <InputLabel>Analysis</InputLabel>
              <Select
                label="Analysis"
                value={run.analysis_id || ''}
                displayEmpty
                onChange={(e) => handleAnalysisChange(e.target.value as string)}
              >
                {!run.analysis_id && (
                  <MenuItem value="" disabled>
                    <em>Select analysis…</em>
                  </MenuItem>
                )}
                {analyses.map((a) => (
                  <MenuItem key={a.id} value={a.id}>
                    {a.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            {!canEditAnalysis && (
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
                Analysis can only be changed while the run is in draft (or ordered).
              </Typography>
            )}
            <Button
              size="small"
              sx={{ mb: 2, mr: 1 }}
              onClick={() => navigate('/admin/analyses')}
            >
              Manage analyses
            </Button>
            <Button size="small" sx={{ mb: 2 }} onClick={() => navigate('/admin/analytes')}>
              Manage analytes / aliases
            </Button>

            {(run.status === 'draft' || run.status === 'ordered') && (
              <Box sx={{ mb: 3 }}>
                <StartCohortPanel
                  title="Run cohort (queue / scan)"
                  startedAt={run.started_at}
                  locked={Boolean(run.cohort?.locked_at)}
                  existingSampleIds={(run.cohort?.sample_ids || []).map(String)}
                  canEdit={Boolean(run.analysis_id)}
                  onStartCohort={async (ids) => {
                    if (!run.analysis_id) {
                      setNoAnalysisDialog(true);
                      throw new Error('Analysis required');
                    }
                    await apiService.startLimsRun(runId!, { sample_ids: ids });
                  }}
                  onStarted={() => void loadRun()}
                />
              </Box>
            )}
            {run.cohort?.sample_ids && run.cohort.sample_ids.length > 0 && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Cohort: {run.cohort.sample_ids.length} sample(s)
                {run.cohort.locked_at ? ' (locked)' : ''}
              </Alert>
            )}
            {run.replaces_run_id && (
              <Alert severity="info" sx={{ mb: 2 }}>
                This run replaces{' '}
                <Button
                  size="small"
                  onClick={() => navigate(`/runs/${run.replaces_run_id}`)}
                >
                  {run.replaces_run_id}
                </Button>
              </Alert>
            )}
            {run.status_reason && (
              <Alert severity={run.status === 'failed' ? 'error' : 'info'} sx={{ mb: 2 }}>
                {run.status_reason}
                {run.rejected_at ? ` (${formatInstant(run.rejected_at)})` : ''}
              </Alert>
            )}

            <List dense>
              <ListItem>
                <ListItemText primary="Status" secondary={run.status} />
              </ListItem>
              <ListItem>
                <ListItemText primary="Template ID" secondary={run.experiment_template_id} />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Started"
                  secondary={run.started_at ? formatInstant(run.started_at) : '—'}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Completed"
                  secondary={run.completed_at ? formatInstant(run.completed_at) : '—'}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Published"
                  secondary={run.published_at ? formatInstant(run.published_at) : '—'}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Created"
                  secondary={formatInstant(run.created_at)}
                />
              </ListItem>
              {run.rejected_at && (
                <ListItem>
                  <ListItemText
                    primary="Failed"
                    secondary={formatInstant(run.rejected_at)}
                  />
                </ListItem>
              )}
            </List>
            {run.replaces_run_id && runId && <ValueChoicesPanel runId={runId} />}
          </CardContent>
        </Card>
      )}

      {activeTab === 1 && (
        <Card variant="outlined" sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Imported Data ({dataRows.length} rows)
            </Typography>
            {dataRows.some((row: any) => row.link_note && !row.sample_id) && (
              <Alert severity="warning" sx={{ mb: 2 }} data-testid="unmatched-summary">
                {dataRows.filter((row: any) => row.link_note && !row.sample_id).length} row
                {dataRows.filter((row: any) => row.link_note && !row.sample_id).length === 1
                  ? ''
                  : 's'}{' '}
                did not match a sample on this run. Those rows are kept.
              </Alert>
            )}
            {dataRows.some((row: any) => row.link_note && row.sample_id) && (
              <Alert severity="info" sx={{ mb: 2 }} data-testid="link-flag-summary">
                {dataRows.filter((row: any) => row.link_note && row.sample_id).length} row
                {dataRows.filter((row: any) => row.link_note && row.sample_id).length === 1
                  ? ''
                  : 's'}{' '}
                linked with a note. Check the note on each row.
              </Alert>
            )}
            {dataLoading ? (
              <Box display="flex" justifyContent="center" py={3}>
                <CircularProgress />
              </Box>
            ) : dataRows.length === 0 ? (
              <Typography color="text.secondary">No data imported yet.</Typography>
            ) : (
              <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 400 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>Well</TableCell>
                      <TableCell>Sample</TableCell>
                      <TableCell>Row Data</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {dataRows.map((row: any) => (
                      <TableRow key={row.id}>
                        <TableCell>{row.well_position ?? '—'}</TableCell>
                        <TableCell>
                          <Typography variant="body2">
                            {row.sample_key || row.sample_id || '—'}
                          </Typography>
                          {row.link_note && (
                            <Typography variant="caption" color="warning.main" display="block">
                              {row.link_note}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Box
                            component="pre"
                            sx={{ m: 0, fontSize: '0.7rem', maxWidth: 400, overflow: 'auto' }}
                          >
                            {JSON.stringify(row.row_data, null, 2)}
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 2 && runId && (
        <DoseResponseTab runId={runId} runStatus={run.status} />
      )}

      {runId && <ReagentUsePanel limsRunId={runId} analysisId={run.analysis_id} />}

      <RunImportDialog
        open={importOpen}
        parsers={parsers}
        submitting={importing}
        error={importError}
        result={importResult}
        onClose={() => {
          if (!importing) setImportOpen(false);
        }}
        onSubmit={(parser, file) => void submitImport(parser, file)}
      />
      <FailRunDialog
        open={failOpen}
        submitting={failing}
        error={failError}
        sampleCount={run.cohort?.sample_ids?.length || 0}
        onClose={() => {
          if (!failing) setFailOpen(false);
        }}
        onConfirm={(reason) => void confirmFail(reason)}
      />

      <PublishPromotionDialog
        open={publishDialogOpen}
        onClose={() => {
          if (!publishing) {
            setPublishDialogOpen(false);
            setPublishPreview(null);
            setPublishPreviewError(null);
          }
        }}
        onConfirm={confirmPublish}
        hasAnalysis={Boolean(run.analysis_id)}
        analysisName={analysisName}
        preview={publishPreview}
        loading={publishPreviewLoading}
        loadError={publishPreviewError}
        publishing={publishing}
      />

      <Dialog open={noAnalysisDialog} onClose={() => setNoAnalysisDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Analysis required</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Every LimsRun must have an <strong>Analysis</strong> before start, import, or publish.
            There is no non-reportable path.
          </DialogContentText>
          <FormControl fullWidth size="small" sx={{ mt: 2 }} required>
            <InputLabel>Associate analysis</InputLabel>
            <Select
              label="Associate analysis"
              value={run.analysis_id || ''}
              displayEmpty
              onChange={async (e) => {
                const v = e.target.value as string;
                if (v) await handleAnalysisChange(v);
              }}
            >
              {!run.analysis_id && (
                <MenuItem value="" disabled>
                  <em>Select analysis…</em>
                </MenuItem>
              )}
              {analyses.map((a) => (
                <MenuItem key={a.id} value={a.id}>
                  {a.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions sx={{ flexWrap: 'wrap', gap: 1 }}>
          <Button onClick={() => setNoAnalysisDialog(false)}>Cancel</Button>
          <Button onClick={() => navigate('/admin/analyses')}>Create / manage analyses</Button>
          <Button
            variant="contained"
            disabled={transitioning || !run.analysis_id}
            onClick={() => doStart()}
          >
            Start run
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LimsRunDetail;
