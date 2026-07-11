/**
 * ELN Processes management (Phase 2 UI).
 * Ordered multi-experiment workflows: list, create, detail with steps + samples.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  Checkbox,
  InputLabel,
  MenuItem,
  Select,
  Tab,
  Tabs,
  TextField,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  IconButton,
} from '@mui/material';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import VisibilityIcon from '@mui/icons-material/Visibility';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import { useNavigate, useParams } from 'react-router-dom';
import { apiService } from '../services/apiService';

const apiErrorMsg = (err: any, fallback: string): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) return detail[0]?.msg || fallback;
  return fallback;
};

interface ProcessListItem {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  created_at: string;
  step_count: number;
  sample_count: number;
}

interface ProcessStep {
  id: string;
  process_id: string;
  experiment_template_id: string;
  experiment_id?: string;
  name?: string;
  sort_order: number;
}

interface ProcessSample {
  id: string;
  process_id: string;
  sample_id: string;
  status: string;
  current_step_id?: string;
}

interface ProcessDetail {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  steps: ProcessStep[];
  process_samples: ProcessSample[];
}

const ProcessesManagement: React.FC = () => {
  const navigate = useNavigate();
  const { id: routeId } = useParams<{ id?: string }>();
  const isDetail = Boolean(routeId);

  const [processes, setProcesses] = useState<ProcessListItem[]>([]);
  const [detail, setDetail] = useState<ProcessDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState(0);
  const [templates, setTemplates] = useState<{ id: string; name: string }[]>([]);

  // Create process dialog
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDesc, setCreateDesc] = useState('');
  const [createTemplateIds, setCreateTemplateIds] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);

  // Add step
  const [showAddStep, setShowAddStep] = useState(false);
  const [stepTemplateId, setStepTemplateId] = useState('');
  const [stepName, setStepName] = useState('');

  // Assign samples
  const [showAssign, setShowAssign] = useState(false);
  const [sampleIdsText, setSampleIdsText] = useState('');
  const [setToFirst, setSetToFirst] = useState(true);

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res: any = await apiService.getElnProcesses({ page: 1, size: 100, active: true });
      setProcesses(res?.processes ?? []);
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to load processes'));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDetail = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const res: any = await apiService.getElnProcess(id);
      setDetail(res);
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to load process'));
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    apiService
      .getExperimentTemplates({ page: 1, size: 500, active: true })
      .then((res: any) => setTemplates(res?.templates ?? []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (routeId) loadDetail(routeId);
    else loadList();
  }, [routeId, loadList, loadDetail]);

  const handleCreate = async () => {
    if (!createName.trim()) return;
    setCreating(true);
    try {
      const steps = createTemplateIds.map((tid, i) => ({
        experiment_template_id: tid,
        sort_order: i,
        name: templates.find((t) => t.id === tid)?.name,
      }));
      const res: any = await apiService.createElnProcess({
        name: createName.trim(),
        description: createDesc || undefined,
        steps: steps.length ? steps : undefined,
      });
      setShowCreate(false);
      setCreateName('');
      setCreateDesc('');
      setCreateTemplateIds([]);
      navigate(`/experiments/processes/${res.id}`);
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to create process'));
    } finally {
      setCreating(false);
    }
  };

  const handleAddStep = async () => {
    if (!routeId || !stepTemplateId) return;
    try {
      await apiService.addElnProcessStep(routeId, {
        experiment_template_id: stepTemplateId,
        name: stepName || undefined,
      });
      setShowAddStep(false);
      setStepTemplateId('');
      setStepName('');
      await loadDetail(routeId);
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to add step'));
    }
  };

  const handleInstantiate = async (stepId: string) => {
    if (!routeId) return;
    try {
      await apiService.instantiateElnProcessStep(routeId, stepId);
      await loadDetail(routeId);
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to instantiate step'));
    }
  };

  const handleRemoveStep = async (stepId: string) => {
    if (!routeId) return;
    try {
      await apiService.removeElnProcessStep(routeId, stepId);
      await loadDetail(routeId);
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to remove step'));
    }
  };

  const handleAssign = async () => {
    if (!routeId) return;
    const ids = sampleIdsText
      .split(/[\s,]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    if (!ids.length) return;
    try {
      await apiService.assignElnProcessSamples(routeId, {
        sample_ids: ids,
        set_to_first_step: setToFirst,
      });
      setShowAssign(false);
      setSampleIdsText('');
      await loadDetail(routeId);
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to assign samples'));
    }
  };

  const handleAdvance = async (sampleId: string) => {
    if (!routeId) return;
    try {
      await apiService.advanceElnProcessSample(routeId, sampleId);
      await loadDetail(routeId);
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to advance sample'));
    }
  };

  const handleRemoveSample = async (sampleId: string) => {
    if (!routeId) return;
    try {
      await apiService.removeElnProcessSample(routeId, sampleId);
      await loadDetail(routeId);
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to remove sample'));
    }
  };

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 160 },
    { field: 'description', headerName: 'Description', flex: 1, minWidth: 160 },
    {
      field: 'step_count',
      headerName: 'Steps',
      width: 90,
      type: 'number',
    },
    {
      field: 'sample_count',
      headerName: 'Samples',
      width: 100,
      type: 'number',
    },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 160,
      valueGetter: (_v, row) =>
        row.created_at ? new Date(row.created_at).toLocaleString() : '',
    },
    {
      field: 'actions',
      type: 'actions',
      width: 80,
      getActions: (params) => [
        <GridActionsCellItem
          key="view"
          icon={<VisibilityIcon />}
          label="View"
          onClick={() => navigate(`/experiments/processes/${params.id}`)}
        />,
      ],
    },
  ];

  if (loading && !detail && isDetail) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  // ── Detail view ──────────────────────────────────────────────────────────
  if (isDetail && detail) {
    const templateName = (tid: string) =>
      templates.find((t) => t.id === tid)?.name || tid.slice(0, 8);

    return (
      <Box p={2}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate('/experiments/processes')}
          sx={{ mb: 2 }}
        >
          All Processes
        </Button>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        <Typography variant="h5" gutterBottom>
          {detail.name}
        </Typography>
        {detail.description && (
          <Typography color="text.secondary" gutterBottom>
            {detail.description}
          </Typography>
        )}
        <Chip
          size="small"
          label={detail.active ? 'Active' : 'Inactive'}
          color={detail.active ? 'success' : 'default'}
          sx={{ mb: 2 }}
        />

        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
          <Tab label={`Steps (${detail.steps?.length ?? 0})`} />
          <Tab label={`Samples (${detail.process_samples?.length ?? 0})`} />
        </Tabs>

        {tab === 0 && (
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" mb={2}>
                <Typography variant="h6">Process steps</Typography>
                <Button
                  size="small"
                  startIcon={<AddIcon />}
                  variant="outlined"
                  onClick={() => setShowAddStep(true)}
                >
                  Add step
                </Button>
              </Box>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell width={60}>#</TableCell>
                    <TableCell>Name</TableCell>
                    <TableCell>Template</TableCell>
                    <TableCell>Experiment</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(detail.steps || [])
                    .slice()
                    .sort((a, b) => a.sort_order - b.sort_order)
                    .map((s) => (
                      <TableRow key={s.id}>
                        <TableCell>{s.sort_order}</TableCell>
                        <TableCell>{s.name || '—'}</TableCell>
                        <TableCell>{templateName(s.experiment_template_id)}</TableCell>
                        <TableCell>
                          {s.experiment_id ? (
                            <Button
                              size="small"
                              onClick={() => navigate(`/experiments/${s.experiment_id}`)}
                            >
                              Open
                            </Button>
                          ) : (
                            <Typography variant="body2" color="text.secondary">
                              Not created
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell align="right">
                          {!s.experiment_id && (
                            <Button size="small" onClick={() => handleInstantiate(s.id)}>
                              Instantiate
                            </Button>
                          )}
                          <IconButton
                            size="small"
                            aria-label="remove step"
                            onClick={() => handleRemoveStep(s.id)}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  {!detail.steps?.length && (
                    <TableRow>
                      <TableCell colSpan={5}>
                        <Typography color="text.secondary">No steps yet.</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {tab === 1 && (
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" mb={2}>
                <Typography variant="h6">Assigned samples</Typography>
                <Button
                  size="small"
                  startIcon={<AddIcon />}
                  variant="outlined"
                  onClick={() => setShowAssign(true)}
                >
                  Assign samples
                </Button>
              </Box>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Sample ID</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Current step</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(detail.process_samples || []).map((ps) => {
                    const step = detail.steps?.find((s) => s.id === ps.current_step_id);
                    return (
                      <TableRow key={ps.id}>
                        <TableCell>
                          <Button
                            size="small"
                            onClick={() => navigate(`/samples?highlight=${ps.sample_id}`)}
                          >
                            {ps.sample_id.slice(0, 8)}…
                          </Button>
                        </TableCell>
                        <TableCell>
                          <Chip size="small" label={ps.status} />
                        </TableCell>
                        <TableCell>
                          {step
                            ? `${step.sort_order}: ${step.name || templateName(step.experiment_template_id)}`
                            : '—'}
                        </TableCell>
                        <TableCell align="right">
                          {ps.status !== 'completed' && (
                            <Button size="small" onClick={() => handleAdvance(ps.sample_id)}>
                              Advance
                            </Button>
                          )}
                          <IconButton
                            size="small"
                            onClick={() => handleRemoveSample(ps.sample_id)}
                          >
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                  {!detail.process_samples?.length && (
                    <TableRow>
                      <TableCell colSpan={4}>
                        <Typography color="text.secondary">No samples assigned.</Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        <Dialog open={showAddStep} onClose={() => setShowAddStep(false)} fullWidth maxWidth="sm">
          <DialogTitle>Add step</DialogTitle>
          <DialogContent>
            <FormControl fullWidth margin="normal">
              <InputLabel>Experiment template</InputLabel>
              <Select
                label="Experiment template"
                value={stepTemplateId}
                onChange={(e) => setStepTemplateId(e.target.value)}
              >
                {templates.map((t) => (
                  <MenuItem key={t.id} value={t.id}>
                    {t.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              fullWidth
              margin="normal"
              label="Step label (optional)"
              value={stepName}
              onChange={(e) => setStepName(e.target.value)}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowAddStep(false)}>Cancel</Button>
            <Button variant="contained" onClick={handleAddStep} disabled={!stepTemplateId}>
              Add
            </Button>
          </DialogActions>
        </Dialog>

        <Dialog open={showAssign} onClose={() => setShowAssign(false)} fullWidth maxWidth="sm">
          <DialogTitle>Assign samples</DialogTitle>
          <DialogContent>
            <TextField
              fullWidth
              margin="normal"
              multiline
              minRows={3}
              label="Sample UUIDs (comma or whitespace separated)"
              value={sampleIdsText}
              onChange={(e) => setSampleIdsText(e.target.value)}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={setToFirst}
                  onChange={(e) => setSetToFirst(e.target.checked)}
                />
              }
              label="Set to first step"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setShowAssign(false)}>Cancel</Button>
            <Button variant="contained" onClick={handleAssign}>
              Assign
            </Button>
          </DialogActions>
        </Dialog>
      </Box>
    );
  }

  // ── List view ────────────────────────────────────────────────────────────
  return (
    <Box p={2}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h5">ELN Processes</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setShowCreate(true)}>
          New process
        </Button>
      </Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Ordered multi-step experimental workflows (ELN). Distinct from instrument experiment runs.
      </Typography>
      <Card>
        <CardContent>
          <DataGrid
            autoHeight
            rows={processes}
            columns={columns}
            loading={loading}
            pageSizeOptions={[25, 50]}
            initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
            disableRowSelectionOnClick
            onRowDoubleClick={(p) => navigate(`/experiments/processes/${p.id}`)}
          />
        </CardContent>
      </Card>

      <Dialog open={showCreate} onClose={() => setShowCreate(false)} fullWidth maxWidth="sm">
        <DialogTitle>Create ELN process</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            margin="normal"
            required
            label="Name"
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
          />
          <TextField
            fullWidth
            margin="normal"
            label="Description"
            value={createDesc}
            onChange={(e) => setCreateDesc(e.target.value)}
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Initial templates (optional)</InputLabel>
            <Select
              multiple
              label="Initial templates (optional)"
              value={createTemplateIds}
              onChange={(e) =>
                setCreateTemplateIds(
                  typeof e.target.value === 'string'
                    ? e.target.value.split(',')
                    : (e.target.value as string[]),
                )
              }
              renderValue={(selected) =>
                (selected as string[])
                  .map((id) => templates.find((t) => t.id === id)?.name || id)
                  .join(', ')
              }
            >
              {templates.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCreate(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={!createName.trim() || creating}
          >
            {creating ? 'Creating…' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ProcessesManagement;
