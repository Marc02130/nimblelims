/**
 * ELN Processes management (Phase 2–3 UI).
 * Definitions (reusable SOPs) + process instances with typed steps (eln_experiment | lims_run).
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
  Autocomplete,
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
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import { useNavigate, useParams } from 'react-router-dom';
import { apiService, ApiService } from '../services/apiService';
import { FillHeightPage, FillHeightTable } from '../components/common/FillHeightPage';
import StartExperimentDialog from '../components/experiments/StartExperimentDialog';

const apiErrorMsg = (err: any, fallback: string): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) return detail[0]?.msg || fallback;
  if (detail && typeof detail === 'object' && typeof detail.message === 'string') {
    return detail.message;
  }
  return fallback;
};

type StepKind = 'eln_experiment' | 'lims_run';

interface ProcessListItem {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  process_definition_id?: string;
  created_at: string;
  step_count: number;
  sample_count: number;
}

interface ProcessStep {
  id: string;
  process_id: string;
  step_kind?: StepKind;
  execution_mode?: StepKind;
  experiment_template_id?: string;
  analysis_id?: string;
  experiment_id?: string;
  current_lims_run_id?: string;
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
  process_definition_id?: string;
  steps: ProcessStep[];
  process_samples: ProcessSample[];
}

interface DefinitionListItem {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  created_at: string;
  step_count: number;
}

interface DefinitionStep {
  id: string;
  process_definition_id: string;
  step_kind: StepKind;
  execution_mode: StepKind;
  experiment_template_id?: string;
  analysis_id?: string;
  name?: string;
  sort_order: number;
}

interface DefinitionDetail {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  steps: DefinitionStep[];
}

interface DraftStep {
  experiment_template_id: string;
  analysis_id: string;
  step_kind: StepKind;
  name: string;
  sample_type_ids: string[];
}

const kindLabel = (k?: string) =>
  k === 'lims_run' ? 'LIMS Run' : 'ELN Experiment';

const kindColor = (k?: string): 'primary' | 'secondary' | 'default' =>
  k === 'lims_run' ? 'secondary' : 'primary';

const emptyDraftStep = (): DraftStep => ({
  experiment_template_id: '',
  analysis_id: '',
  step_kind: 'eln_experiment',
  name: '',
  sample_type_ids: [],
});

const ProcessesManagement: React.FC = () => {
  const navigate = useNavigate();
  const { id: routeId } = useParams<{ id?: string }>();
  const isDetail = Boolean(routeId);

  const [listTab, setListTab] = useState(0); // 0 instances, 1 definitions
  const [processes, setProcesses] = useState<ProcessListItem[]>([]);
  const [definitions, setDefinitions] = useState<DefinitionListItem[]>([]);
  const [detail, setDetail] = useState<ProcessDetail | null>(null);
  const [defDetail, setDefDetail] = useState<DefinitionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [tab, setTab] = useState(0);
  const [templates, setTemplates] = useState<{ id: string; name: string }[]>([]);
  const [analyses, setAnalyses] = useState<{ id: string; name: string }[]>([]);
  const [sampleTypes, setSampleTypes] = useState<{ id: string; name: string }[]>([]);

  // Create instance (from definition or free-form)
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDesc, setCreateDesc] = useState('');
  const [createDefinitionId, setCreateDefinitionId] = useState('');
  const [createSteps, setCreateSteps] = useState<DraftStep[]>([]);
  const [creating, setCreating] = useState(false);

  // Create definition
  const [showCreateDef, setShowCreateDef] = useState(false);
  const [defName, setDefName] = useState('');
  const [defDesc, setDefDesc] = useState('');
  const [defSteps, setDefSteps] = useState<DraftStep[]>([emptyDraftStep()]);

  // Add step to instance
  const [showAddStep, setShowAddStep] = useState(false);
  const [stepTemplateId, setStepTemplateId] = useState('');
  const [stepName, setStepName] = useState('');
  const [stepKind, setStepKind] = useState<StepKind>('eln_experiment');

  // Assign samples
  const [showAssign, setShowAssign] = useState(false);
  const [sampleIdsText, setSampleIdsText] = useState('');
  const [setToFirst, setSetToFirst] = useState(true);

  // Start instance from definition (detail or list)
  const [showStartFromDef, setShowStartFromDef] = useState(false);
  const [startDefId, setStartDefId] = useState('');
  const [startInstanceName, setStartInstanceName] = useState('');

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [procRes, defRes]: any[] = await Promise.all([
        apiService.getElnProcesses({ page: 1, size: 100, active: true }),
        apiService.getElnProcessDefinitions({ page: 1, size: 100, active: true }),
      ]);
      setProcesses(procRes?.processes ?? []);
      setDefinitions(defRes?.definitions ?? []);
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
      setDefDetail(null);
      if (res.process_definition_id) {
        try {
          const d: any = await apiService.getElnProcessDefinition(res.process_definition_id);
          setDefDetail(d);
        } catch {
          /* definition may be inaccessible */
        }
      }
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
    apiService
      .getAnalyses({ size: 200, active: true })
      .then((res: any) => setAnalyses(ApiService.unwrapAnalysesList(res)))
      .catch(() => {});
    apiService
      .getListEntries('sample_types')
      .then((res: any) => setSampleTypes(Array.isArray(res) ? res : []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (routeId) loadDetail(routeId);
    else loadList();
  }, [routeId, loadList, loadDetail]);

  const templateName = (tid?: string | null) => {
    if (!tid) return '—';
    return templates.find((t) => t.id === tid)?.name || tid.slice(0, 8);
  };

  const handleCreate = async () => {
    if (!createName.trim()) return;
    setCreating(true);
    try {
      let res: any;
      if (createDefinitionId) {
        res = await apiService.instantiateFromElnProcessDefinition(createDefinitionId, {
          name: createName.trim(),
          description: createDesc || undefined,
        });
      } else {
        const steps = createSteps
          .filter((s) => s.experiment_template_id)
          .map((s, i) => ({
            experiment_template_id: s.experiment_template_id,
            step_kind: s.step_kind,
            execution_mode: s.step_kind,
            sort_order: i,
            name: s.name || templates.find((t) => t.id === s.experiment_template_id)?.name,
          }));
        res = await apiService.createElnProcess({
          name: createName.trim(),
          description: createDesc || undefined,
          steps: steps.length ? steps : undefined,
        });
      }
      setShowCreate(false);
      setCreateName('');
      setCreateDesc('');
      setCreateDefinitionId('');
      setCreateSteps([]);
      navigate(`/experiments/processes/${res.id}`);
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to create process'));
    } finally {
      setCreating(false);
    }
  };

  const handleCreateDefinition = async () => {
    if (!defName.trim()) return;
    setCreating(true);
    try {
      const draft = defSteps.filter((s) =>
        s.step_kind === 'lims_run' ? Boolean(s.analysis_id) : Boolean(s.experiment_template_id)
      );
      const steps = draft.map((s, i) => ({
        experiment_template_id: s.experiment_template_id || undefined,
        analysis_id: s.analysis_id || undefined,
        step_kind: s.step_kind,
        execution_mode: s.step_kind,
        sort_order: i,
        name:
          s.name ||
          (s.step_kind === 'lims_run'
            ? analyses.find((a) => a.id === s.analysis_id)?.name
            : templates.find((t) => t.id === s.experiment_template_id)?.name),
      }));
      const created: any = await apiService.createElnProcessDefinition({
        name: defName.trim(),
        description: defDesc || undefined,
        steps: steps.length ? steps : undefined,
      });
      const createdSteps = created?.steps || [];
      for (let i = 0; i < createdSteps.length; i += 1) {
        const types = draft[i]?.sample_type_ids || [];
        if (types.length) {
          await apiService.putStepAcceptedSampleTypes(created.id, createdSteps[i].id, types);
        }
      }
      setShowCreateDef(false);
      setDefName('');
      setDefDesc('');
      setDefSteps([emptyDraftStep()]);
      setListTab(1);
      await loadList();
      setInfo('Process definition created');
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to create definition'));
    } finally {
      setCreating(false);
    }
  };

  const handleStartFromDefinition = async () => {
    if (!startDefId) return;
    setCreating(true);
    try {
      const res: any = await apiService.instantiateFromElnProcessDefinition(startDefId, {
        name: startInstanceName.trim() || undefined,
      });
      setShowStartFromDef(false);
      setStartDefId('');
      setStartInstanceName('');
      navigate(`/experiments/processes/${res.id}`);
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to start process from definition'));
    } finally {
      setCreating(false);
    }
  };

  const handleAddStep = async () => {
    if (!routeId || !stepTemplateId) return;
    try {
      await apiService.addElnProcessStep(routeId, {
        experiment_template_id: stepTemplateId,
        step_kind: stepKind,
        execution_mode: stepKind,
        name: stepName || undefined,
      });
      setShowAddStep(false);
      setStepTemplateId('');
      setStepName('');
      setStepKind('eln_experiment');
      await loadDetail(routeId);
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to add step'));
    }
  };

  const [startDialogStep, setStartDialogStep] = useState<ProcessStep | null>(null);

  const handleStartStep = async (step: ProcessStep, forceNew = false) => {
    if (!routeId) return;
    const kind = step.step_kind || 'eln_experiment';
    // Decision #24: eln_experiment opens dual-list start dialog (not immediate empty start)
    if (kind === 'eln_experiment' && !forceNew) {
      setStartDialogStep(step);
      return;
    }
    try {
      const res: any = await apiService.startElnProcessStep(routeId, step.id, {
        force_new: forceNew,
      });
      if (res.warning) setInfo(res.warning);
      else setInfo(step.step_kind === 'lims_run' ? 'LimsRun started' : 'Experiment created');
      await loadDetail(routeId);
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to start step'));
    }
  };

  const handleStartDialogDone = async (result: {
    experimentId?: string;
    linkedCount?: number;
    processSamplesUpdated?: number;
  }) => {
    setStartDialogStep(null);
    if (routeId) await loadDetail(routeId);
    const n = result.linkedCount ?? 0;
    const p = result.processSamplesUpdated ?? 0;
    setInfo(
      `Experiment started with ${n} sample(s)` +
        (p ? `; ${p} process sample(s) set to in_progress` : '') +
        (result.experimentId ? `. Open from Steps when ready.` : ''),
    );
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
      const res: any = await apiService.advanceElnProcessSample(routeId, sampleId);
      if (res.warning) {
        setInfo(res.warning);
      }
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

  const processColumns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 160 },
    { field: 'description', headerName: 'Description', flex: 1, minWidth: 140 },
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

  const definitionColumns: GridColDef[] = [
    { field: 'name', headerName: 'Definition', flex: 1, minWidth: 180 },
    { field: 'description', headerName: 'Description', flex: 1, minWidth: 160 },
    {
      field: 'step_count',
      headerName: 'Steps',
      width: 90,
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
      width: 120,
      getActions: (params) => [
        <GridActionsCellItem
          key="start"
          icon={<PlayArrowIcon />}
          label="Start process"
          onClick={() => {
            setStartDefId(String(params.id));
            setStartInstanceName('');
            setShowStartFromDef(true);
          }}
        />,
      ],
    },
  ];

  const draftStepEditor = (
    steps: DraftStep[],
    setSteps: React.Dispatch<React.SetStateAction<DraftStep[]>>,
  ) => (
    <Box sx={{ mt: 1 }}>
      <Typography variant="subtitle2" gutterBottom>
        Steps
      </Typography>
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
        Steps run in this order (1, 2, 3…). ELN Experiment steps pick a template; LIMS Run
        steps pick an analysis. A later step may accept a different sample type after dest-type
        change. Route assignment uses accepted types of the first experiment/LIMS Run only.
      </Typography>
      {steps.map((s, idx) => (
        <Box key={idx} display="flex" gap={1} alignItems="flex-start" mb={1.5} flexWrap="wrap">
          <Chip size="small" label={`Step ${idx + 1}`} sx={{ mt: 1 }} />
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Kind</InputLabel>
            <Select
              label="Kind"
              value={s.step_kind}
              onChange={(e) => {
                const next = [...steps];
                next[idx] = { ...next[idx], step_kind: e.target.value as StepKind };
                setSteps(next);
              }}
            >
              <MenuItem value="eln_experiment">ELN Experiment</MenuItem>
              <MenuItem value="lims_run">LIMS Run</MenuItem>
            </Select>
          </FormControl>
          {s.step_kind === 'lims_run' ? (
            <FormControl size="small" sx={{ minWidth: 200, flex: 1 }}>
              <InputLabel>Analysis</InputLabel>
              <Select
                label="Analysis"
                value={s.analysis_id}
                onChange={(e) => {
                  const next = [...steps];
                  next[idx] = { ...next[idx], analysis_id: e.target.value };
                  setSteps(next);
                }}
              >
                {analyses.map((a) => (
                  <MenuItem key={a.id} value={a.id}>
                    {a.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          ) : (
            <FormControl size="small" sx={{ minWidth: 200, flex: 1 }}>
              <InputLabel>Experiment template</InputLabel>
              <Select
                label="Experiment template"
                value={s.experiment_template_id}
                onChange={(e) => {
                  const next = [...steps];
                  next[idx] = { ...next[idx], experiment_template_id: e.target.value };
                  setSteps(next);
                }}
              >
                {templates.length === 0 ? (
                  <MenuItem value="" disabled>
                    No active experiment templates
                  </MenuItem>
                ) : (
                  templates.map((t) => (
                    <MenuItem key={t.id} value={t.id}>
                      {t.name}
                    </MenuItem>
                  ))
                )}
              </Select>
            </FormControl>
          )}
          <Autocomplete
            multiple
            size="small"
            sx={{ minWidth: 220, flex: 1 }}
            options={sampleTypes}
            getOptionLabel={(o) => o.name}
            value={sampleTypes.filter((t) => s.sample_type_ids.includes(t.id))}
            onChange={(_e, value) => {
              const next = [...steps];
              next[idx] = { ...next[idx], sample_type_ids: value.map((v) => v.id) };
              setSteps(next);
            }}
            renderInput={(params) => <TextField {...params} label="Accepted sample types" />}
          />
          <TextField
            size="small"
            label="Label"
            value={s.name}
            onChange={(e) => {
              const next = [...steps];
              next[idx] = { ...next[idx], name: e.target.value };
              setSteps(next);
            }}
            sx={{ minWidth: 100 }}
          />
          <IconButton
            size="small"
            aria-label={`move step ${idx + 1} up`}
            onClick={() => {
              if (idx === 0) return;
              const next = [...steps];
              [next[idx - 1], next[idx]] = [next[idx], next[idx - 1]];
              setSteps(next);
            }}
            disabled={idx === 0}
            sx={{ mt: 0.5 }}
          >
            <ArrowUpwardIcon fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            aria-label={`move step ${idx + 1} down`}
            onClick={() => {
              if (idx >= steps.length - 1) return;
              const next = [...steps];
              [next[idx], next[idx + 1]] = [next[idx + 1], next[idx]];
              setSteps(next);
            }}
            disabled={idx >= steps.length - 1}
            sx={{ mt: 0.5 }}
          >
            <ArrowDownwardIcon fontSize="small" />
          </IconButton>
          <IconButton
            size="small"
            aria-label={`remove step ${idx + 1}`}
            onClick={() => setSteps(steps.filter((_, i) => i !== idx))}
            disabled={steps.length <= 1}
            sx={{ mt: 0.5 }}
          >
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Box>
      ))}
      <Button
        size="small"
        startIcon={<AddIcon />}
        onClick={() => setSteps([...steps, emptyDraftStep()])}
      >
        Add step row
      </Button>
    </Box>
  );

  if (loading && !detail && isDetail) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  // ── Detail view ──────────────────────────────────────────────────────────
  if (isDetail && detail) {
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
        {info && (
          <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setInfo(null)}>
            {info}
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
        <Box display="flex" gap={1} flexWrap="wrap" mb={2}>
          <Chip
            size="small"
            label={detail.active ? 'Active' : 'Inactive'}
            color={detail.active ? 'success' : 'default'}
          />
          {detail.process_definition_id && (
            <Chip
              size="small"
              variant="outlined"
              label={
                defDetail
                  ? `From: ${defDetail.name}`
                  : `Definition ${detail.process_definition_id.slice(0, 8)}…`
              }
            />
          )}
        </Box>

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
                    <TableCell width={70}>Order</TableCell>
                    <TableCell>Name</TableCell>
                    <TableCell>Kind</TableCell>
                    <TableCell>Template</TableCell>
                    <TableCell>Work item</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(detail.steps || [])
                    .slice()
                    .sort((a, b) => a.sort_order - b.sort_order)
                    .map((s, idx) => {
                      const kind = s.step_kind || 'eln_experiment';
                      const hasWork =
                        kind === 'lims_run' ? Boolean(s.current_lims_run_id) : Boolean(s.experiment_id);
                      return (
                        <TableRow key={s.id}>
                          <TableCell>{idx + 1}</TableCell>
                          <TableCell>{s.name || '—'}</TableCell>
                          <TableCell>
                            <Chip size="small" color={kindColor(kind)} label={kindLabel(kind)} />
                          </TableCell>
                          <TableCell>{templateName(s.experiment_template_id)}</TableCell>
                          <TableCell>
                            {kind === 'lims_run' ? (
                              s.current_lims_run_id ? (
                                <Button
                                  size="small"
                                  onClick={() => navigate(`/runs/${s.current_lims_run_id}`)}
                                >
                                  Open run
                                </Button>
                              ) : (
                                <Typography variant="body2" color="text.secondary">
                                  Not started
                                </Typography>
                              )
                            ) : s.experiment_id ? (
                              <Button
                                size="small"
                                onClick={() => navigate(`/experiments/${s.experiment_id}`)}
                              >
                                Open experiment
                              </Button>
                            ) : (
                              <Typography variant="body2" color="text.secondary">
                                Not created
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell align="right">
                            {!hasWork && (
                              <Button
                                size="small"
                                startIcon={<PlayArrowIcon />}
                                onClick={() => handleStartStep(s)}
                              >
                                Start
                              </Button>
                            )}
                            {kind === 'eln_experiment' && hasWork && (
                              <Button
                                size="small"
                                onClick={() => setStartDialogStep(s)}
                              >
                                Start cohort
                              </Button>
                            )}
                            {kind === 'lims_run' && hasWork && (
                              <Button size="small" onClick={() => handleStartStep(s, true)}>
                                Retest
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
                      );
                    })}
                  {!detail.steps?.length && (
                    <TableRow>
                      <TableCell colSpan={6}>
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
                          <Chip
                            size="small"
                            color={
                              ps.status === 'completed'
                                ? 'success'
                                : ps.status === 'in_progress'
                                  ? 'warning'
                                  : 'default'
                            }
                            label={
                              ps.status === 'assigned'
                                ? 'queued'
                                : ps.status === 'in_progress'
                                  ? 'in progress'
                                  : ps.status
                            }
                          />
                        </TableCell>
                        <TableCell>
                          {step ? (
                            <Box display="flex" alignItems="center" gap={0.5}>
                              <span>
                                {(() => {
                                  const ordered = [...(detail.steps || [])].sort(
                                    (a, b) => a.sort_order - b.sort_order
                                  );
                                  const n = ordered.findIndex((x) => x.id === step.id);
                                  return n >= 0 ? n + 1 : step.sort_order + 1;
                                })()}
                                : {step.name || templateName(step.experiment_template_id)}
                              </span>
                              <Chip
                                size="small"
                                color={kindColor(step.step_kind)}
                                label={kindLabel(step.step_kind)}
                              />
                            </Box>
                          ) : (
                            '—'
                          )}
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
              <InputLabel>Step kind</InputLabel>
              <Select
                label="Step kind"
                value={stepKind}
                onChange={(e) => setStepKind(e.target.value as StepKind)}
              >
                <MenuItem value="eln_experiment">ELN Experiment</MenuItem>
                <MenuItem value="lims_run">LIMS Run (instrument / plate)</MenuItem>
              </Select>
            </FormControl>
            <FormControl fullWidth margin="normal">
              <InputLabel>
                {stepKind === 'lims_run' ? 'Run template (optional)' : 'Experiment template'}
              </InputLabel>
              <Select
                label={
                  stepKind === 'lims_run' ? 'Run template (optional)' : 'Experiment template'
                }
                value={stepTemplateId}
                onChange={(e) => setStepTemplateId(e.target.value)}
              >
                {templates.length === 0 ? (
                  <MenuItem value="" disabled>
                    No active experiment templates
                  </MenuItem>
                ) : (
                  templates.map((t) => (
                    <MenuItem key={t.id} value={t.id}>
                      {t.name}
                    </MenuItem>
                  ))
                )}
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

        <StartExperimentDialog
          open={Boolean(startDialogStep && routeId)}
          onClose={() => setStartDialogStep(null)}
          processId={routeId}
          stepId={startDialogStep?.id}
          stepLabel={
            startDialogStep
              ? startDialogStep.name ||
                templateName(startDialogStep.experiment_template_id) ||
                `Step ${
                  [...(detail.steps || [])]
                    .sort((a, b) => a.sort_order - b.sort_order)
                    .findIndex((x) => x.id === startDialogStep.id) + 1 ||
                  startDialogStep.sort_order + 1
                }`
              : undefined
          }
          onStarted={handleStartDialogDone}
        />
      </Box>
    );
  }

  // ── List view ────────────────────────────────────────────────────────────
  return (
    <FillHeightPage
      header={
        <>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h5">ELN Processes</Typography>
            <Box display="flex" gap={1}>
              {listTab === 1 ? (
                <Button variant="contained" startIcon={<AddIcon />} onClick={() => setShowCreateDef(true)}>
                  New definition
                </Button>
              ) : (
                <>
                  <Button
                    variant="outlined"
                    startIcon={<PlayArrowIcon />}
                    onClick={() => {
                      setStartDefId(definitions[0]?.id || '');
                      setShowStartFromDef(true);
                    }}
                    disabled={!definitions.length}
                  >
                    Start from definition
                  </Button>
                  <Button
                    variant="contained"
                    startIcon={<AddIcon />}
                    onClick={() => {
                      if (!createSteps.length) {
                        setCreateSteps([emptyDraftStep()]);
                      }
                      setShowCreate(true);
                    }}
                  >
                    New process
                  </Button>
                </>
              )}
            </Box>
          </Box>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          {info && (
            <Alert severity="info" sx={{ mb: 2 }} onClose={() => setInfo(null)}>
              {info}
            </Alert>
          )}
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Definitions are reusable multi-step SOPs. Instances snapshot a definition and track
            samples. Steps are typed as ELN Experiment or LIMS Run.
          </Typography>

          <Tabs value={listTab} onChange={(_, v) => setListTab(v)}>
            <Tab label={`Instances (${processes.length})`} />
            <Tab label={`Definitions (${definitions.length})`} />
          </Tabs>
        </>
      }
    >
      <FillHeightTable>
        {listTab === 0 ? (
          <DataGrid
            rows={processes}
            columns={processColumns}
            loading={loading}
            pageSizeOptions={[25, 50]}
            initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
            disableRowSelectionOnClick
            onRowDoubleClick={(p) => navigate(`/experiments/processes/${p.id}`)}
          />
        ) : (
          <DataGrid
            rows={definitions}
            columns={definitionColumns}
            loading={loading}
            pageSizeOptions={[25, 50]}
            initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
            disableRowSelectionOnClick
          />
        )}
      </FillHeightTable>

      {/* Create free-form instance or from definition */}
      <Dialog open={showCreate} onClose={() => setShowCreate(false)} fullWidth maxWidth="md">
        <DialogTitle>Create process instance</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            margin="normal"
            required
            label="Instance name"
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
            <InputLabel>From definition (recommended)</InputLabel>
            <Select
              label="From definition (recommended)"
              value={createDefinitionId}
              onChange={(e) => setCreateDefinitionId(e.target.value)}
            >
              <MenuItem value="">
                <em>Free-form (auto-creates definition snapshot)</em>
              </MenuItem>
              {definitions.map((d) => (
                <MenuItem key={d.id} value={d.id}>
                  {d.name} ({d.step_count} steps)
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {!createDefinitionId && (
            <>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                Free-form steps will also create a definition snapshot (Decision #6).
              </Typography>
              {draftStepEditor(
                createSteps.length
                  ? createSteps
                  : [emptyDraftStep()],
                setCreateSteps,
              )}
            </>
          )}
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

      {/* Create definition */}
      <Dialog open={showCreateDef} onClose={() => setShowCreateDef(false)} fullWidth maxWidth="md">
        <DialogTitle>New process definition</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            margin="normal"
            required
            label="Definition name"
            value={defName}
            onChange={(e) => setDefName(e.target.value)}
          />
          <TextField
            fullWidth
            margin="normal"
            label="Description"
            value={defDesc}
            onChange={(e) => setDefDesc(e.target.value)}
          />
          {draftStepEditor(defSteps, setDefSteps)}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCreateDef(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreateDefinition}
            disabled={!defName.trim() || creating}
          >
            {creating ? 'Saving…' : 'Save definition'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Start from definition */}
      <Dialog
        open={showStartFromDef}
        onClose={() => setShowStartFromDef(false)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Start process from definition</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="normal">
            <InputLabel>Definition</InputLabel>
            <Select
              label="Definition"
              value={startDefId}
              onChange={(e) => setStartDefId(e.target.value)}
            >
              {definitions.map((d) => (
                <MenuItem key={d.id} value={d.id}>
                  {d.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            fullWidth
            margin="normal"
            label="Instance name (optional)"
            value={startInstanceName}
            onChange={(e) => setStartInstanceName(e.target.value)}
            helperText="Defaults to definition name + short id"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowStartFromDef(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleStartFromDefinition}
            disabled={!startDefId || creating}
          >
            {creating ? 'Starting…' : 'Start'}
          </Button>
        </DialogActions>
      </Dialog>
    </FillHeightPage>
  );
};

export default ProcessesManagement;
