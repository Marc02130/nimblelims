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
import PublishPromotionDialog from '../components/runs/PublishPromotionDialog';
import DoseResponseTab from './DoseResponse/DoseResponseTab';

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

const isAnalysisAckError = (err: any): boolean => {
  const detail = err?.response?.data?.detail;
  return (
    err?.response?.status === 400 &&
    detail &&
    typeof detail === 'object' &&
    detail.code === 'analysis_required_ack'
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
  started_at?: string;
  completed_at?: string;
  published_at?: string;
  canceled_at?: string;
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
    if (!runId) return;
    setSavingAnalysis(true);
    setError(null);
    try {
      const data =
        analysisId === ''
          ? { clear_analysis: true }
          : { analysis_id: analysisId };
      const updated = await apiService.updateLimsRun(runId, data);
      setRun(updated);
    } catch (err: any) {
      setError(apiErrorMsg(err, 'Failed to update analysis'));
    } finally {
      setSavingAnalysis(false);
    }
  };

  const doStart = async (acknowledgeNoAnalysis: boolean) => {
    if (!runId) return;
    setTransitioning(true);
    setError(null);
    try {
      await apiService.startLimsRun(runId, {
        acknowledge_no_analysis: acknowledgeNoAnalysis,
      });
      setNoAnalysisDialog(false);
      await loadRun();
    } catch (err: any) {
      if (isAnalysisAckError(err)) {
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
      if (run?.analysis_id) {
        setSuccessMsg(
          `Published. Results: ${created} created, ${updated} updated.`,
        );
      } else {
        setSuccessMsg('Published (no analysis — no Tests/Results written).');
      }
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

  const handleTransition = async (
    action: 'order' | 'start' | 'results-received' | 'review' | 'publish' | 'cancel',
  ) => {
    if (!runId) return;
    if (action === 'start') {
      await doStart(false);
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
          <Chip size="small" variant="outlined" label="No analysis (non-reportable)" />
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
        {!TERMINAL_STATUSES.has(run.status) && (
          <Button
            variant="outlined"
            color="error"
            size="small"
            disabled={transitioning}
            onClick={() => handleTransition('cancel')}
          >
            Cancel Run
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
              Analysis (reportable results)
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              When an analysis is set and the run is published, imported data is written to Tests and
              Results for each sample. Leave empty only for non-reportable runs (e.g. pure plate QC).
            </Typography>
            <FormControl fullWidth size="small" sx={{ maxWidth: 400, mb: 2 }} disabled={!canEditAnalysis || savingAnalysis}>
              <InputLabel>Analysis</InputLabel>
              <Select
                label="Analysis"
                value={run.analysis_id || ''}
                onChange={(e) => handleAnalysisChange(e.target.value as string)}
              >
                <MenuItem value="">
                  <em>None (non-reportable)</em>
                </MenuItem>
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
                  secondary={run.started_at ? new Date(run.started_at).toLocaleString() : '—'}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Completed"
                  secondary={run.completed_at ? new Date(run.completed_at).toLocaleString() : '—'}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Published"
                  secondary={run.published_at ? new Date(run.published_at).toLocaleString() : '—'}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Created"
                  secondary={new Date(run.created_at).toLocaleString()}
                />
              </ListItem>
            </List>
          </CardContent>
        </Card>
      )}

      {activeTab === 1 && (
        <Card variant="outlined" sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Imported Data ({dataRows.length} rows)
            </Typography>
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
                      <TableCell>Sample ID</TableCell>
                      <TableCell>Row Data</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {dataRows.map((row: any) => (
                      <TableRow key={row.id}>
                        <TableCell>{row.well_position ?? '—'}</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                          {row.sample_id ?? '—'}
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
        <DialogTitle>No analysis associated</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Data imported on this run will <strong>not</strong> be written to Tests and Results when
            published, because no Analysis is associated.
          </DialogContentText>
          <DialogContentText sx={{ mt: 2 }}>
            Associate an existing analysis, create one (and analytes) under Admin, or continue
            without analysis for a non-reportable run.
          </DialogContentText>
          <FormControl fullWidth size="small" sx={{ mt: 2 }}>
            <InputLabel>Associate analysis</InputLabel>
            <Select
              label="Associate analysis"
              value={run.analysis_id || ''}
              onChange={async (e) => {
                await handleAnalysisChange(e.target.value as string);
              }}
            >
              <MenuItem value="">
                <em>None</em>
              </MenuItem>
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
          <Button onClick={() => navigate('/admin/analytes')}>Manage analytes</Button>
          {run.analysis_id ? (
            <Button variant="contained" disabled={transitioning} onClick={() => doStart(false)}>
              Start with analysis
            </Button>
          ) : (
            <Button
              variant="contained"
              color="warning"
              disabled={transitioning}
              onClick={() => doStart(true)}
            >
              Continue without analysis
            </Button>
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LimsRunDetail;
