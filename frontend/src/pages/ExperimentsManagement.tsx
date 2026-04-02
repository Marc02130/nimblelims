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
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Collapse,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ExpandLess from '@mui/icons-material/ExpandLess';
import ExpandMore from '@mui/icons-material/ExpandMore';
import ScienceIcon from '@mui/icons-material/Science';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import PlaylistPlayIcon from '@mui/icons-material/PlaylistPlay';
import LinkIcon from '@mui/icons-material/Link';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { apiService } from '../services/apiService';
import { useUser } from '../contexts/UserContext';

interface ExperimentListItem {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  experiment_template_id?: string;
  status_id?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  modified_at?: string;
  custom_attributes?: Record<string, unknown>;
}

interface ExperimentDetail {
  id: string;
  experiment_id: string;
  detail_type: string;
  content: Record<string, unknown>;
  sort_order: number;
}

interface SampleExecution {
  id: string;
  experiment_id: string;
  sample_id: string;
  role_in_experiment_id?: string;
  processing_conditions: Record<string, unknown>;
  replicate_number: number;
  test_id?: string;
  result_id?: string;
}

interface ExperimentFull extends ExperimentListItem {
  details?: ExperimentDetail[];
  sample_executions?: SampleExecution[];
}

interface LineageResponse {
  experiment: ExperimentFull;
  template?: { id: string; name: string; description?: string };
  linked_experiment_ids: string[];
}

const RunsTab: React.FC<{ experimentId: string }> = ({ experimentId }) => {
  const navigate = useNavigate();
  const [runs, setRuns] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    setLoading(true);
    // Experiment runs are not yet filterable by experiment_id in the API,
    // so list all and the user navigates to specific runs
    apiService
      .getExperimentRuns({ page: 1, size: 100 })
      .then((res: any) => setRuns(res?.runs ?? []))
      .catch((e: any) => setError(e.response?.data?.detail || 'Failed to load runs'))
      .finally(() => setLoading(false));
  }, [experimentId]);

  const statusColor = (s: string) => {
    if (s === 'published') return 'success';
    if (s === 'running') return 'warning';
    if (s === 'complete') return 'info';
    return 'default';
  };

  if (loading) return <Box sx={{ py: 4, display: 'flex', justifyContent: 'center' }}><CircularProgress /></Box>;
  if (error) return <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>;

  return (
    <Card variant="outlined" sx={{ mt: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Experiment Runs</Typography>
          <Button variant="contained" size="small" onClick={() => navigate('/runs')}>
            Manage Runs
          </Button>
        </Box>
        {runs.length === 0 ? (
          <Typography color="text.secondary">No runs yet.</Typography>
        ) : (
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Started</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {runs.map((run: any) => (
                  <TableRow key={run.id}>
                    <TableCell>{run.name}</TableCell>
                    <TableCell>
                      <Chip size="small" label={run.status} color={statusColor(run.status) as any} />
                    </TableCell>
                    <TableCell>{run.started_at ? new Date(run.started_at).toLocaleDateString() : '—'}</TableCell>
                    <TableCell>
                      <Button size="small" startIcon={<VisibilityIcon />} onClick={() => navigate(`/runs/${run.id}`)}>
                        View
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </CardContent>
    </Card>
  );
};

const ExperimentsManagement: React.FC = () => {
  const { hasPermission } = useUser();
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const mineFilter = searchParams.get('mine') === 'true';
  const [view, setView] = useState<'list' | 'detail'>('list');
  const [experiments, setExperiments] = useState<ExperimentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [templateFilter, setTemplateFilter] = useState<string>('');
  const [nameSearch, setNameSearch] = useState('');
  const [templates, setTemplates] = useState<{ id: string; name: string }[]>([]);
  const [statuses, setStatuses] = useState<{ id: string; name: string }[]>([]);
  const [selectedExperiment, setSelectedExperiment] = useState<ExperimentFull | null>(null);
  const [lineage, setLineage] = useState<LineageResponse | null>(null);
  const [lineageLoading, setLineageLoading] = useState(false);
  const [lineageError, setLineageError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [lineageExpanded, setLineageExpanded] = useState<Record<string, boolean>>({});
  const [pagination, setPagination] = useState({ page: 1, size: 25, total: 0, pages: 0 });
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [createTemplateId, setCreateTemplateId] = useState('');
  const [createStatusId, setCreateStatusId] = useState('');
  const [createLoading, setCreateLoading] = useState(false);

  const canManage = hasPermission('experiment:manage');

  useEffect(() => {
    if (id && id !== 'new') {
      setView('detail');
      loadExperimentDetail(id);
      loadLineage(id);
    } else {
      setView('list');
      setSelectedExperiment(null);
      setLineage(null);
      if (!id || id !== 'new') loadExperiments();
    }
  }, [id]);

  useEffect(() => {
    if (view === 'list') {
      loadExperiments();
    }
  }, [statusFilter, templateFilter, mineFilter, pagination.page, pagination.size]);

  useEffect(() => {
    loadTemplatesAndStatuses();
  }, []);

  const loadTemplatesAndStatuses = async () => {
    try {
      const [tplRes, statusList] = await Promise.all([
        apiService.getExperimentTemplates({ page: 1, size: 500 }),
        apiService.getListEntries('experiment_status').catch(() => []),
      ]);
      const tplList = Array.isArray(tplRes?.templates) ? tplRes.templates : [];
      setTemplates(tplList.map((t: { id: string; name: string }) => ({ id: t.id, name: t.name })));
      setStatuses(Array.isArray(statusList) ? statusList : []);
    } catch {
      // non-blocking
    }
  };

  const loadExperiments = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: Record<string, unknown> = {
        page: pagination.page,
        size: pagination.size,
        active: true,
      };
      if (statusFilter) params.status_id = statusFilter;
      if (templateFilter) params.experiment_template_id = templateFilter;
      if (mineFilter) params.mine = true;
      const res = await apiService.getExperiments(params);
      const list = res?.experiments ?? [];
      setExperiments(list);
      setPagination((p) => ({
        ...p,
        total: res?.total ?? list.length,
        pages: res?.pages ?? 1,
      }));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load experiments');
      setExperiments([]);
    } finally {
      setLoading(false);
    }
  };

  const loadExperimentDetail = async (experimentId: string) => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getExperiment(experimentId);
      setSelectedExperiment(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load experiment');
    } finally {
      setLoading(false);
    }
  };

  const loadLineage = async (experimentId: string) => {
    setLineageLoading(true);
    setLineageError(null);
    try {
      const data = await apiService.getExperimentLineage(experimentId);
      setLineage(data);
    } catch (err: any) {
      setLineageError(err.response?.data?.detail || 'Failed to load lineage');
      setLineage(null);
    } finally {
      setLineageLoading(false);
    }
  };

  const getStatusName = (statusId?: string) =>
    statusId ? statuses.find((s) => s.id === statusId)?.name ?? statusId : '—';
  const getTemplateName = (templateId?: string) =>
    templateId ? templates.find((t) => t.id === templateId)?.name ?? templateId : '—';

  const filteredExperiments = nameSearch.trim()
    ? experiments.filter((e) =>
        e.name.toLowerCase().includes(nameSearch.trim().toLowerCase())
      )
    : experiments;

  const handleCreateExperiment = async () => {
    if (!createName.trim()) return;
    setCreateLoading(true);
    setError(null);
    try {
      const created = await apiService.createExperiment({
        name: createName.trim(),
        description: createDescription.trim() || undefined,
        experiment_template_id: createTemplateId || undefined,
        status_id: createStatusId || undefined,
      });
      setShowCreateDialog(false);
      setCreateName('');
      setCreateDescription('');
      setCreateTemplateId('');
      setCreateStatusId('');
      navigate(`/experiments/${created.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create experiment');
    } finally {
      setCreateLoading(false);
    }
  };

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', width: 220, flex: 1 },
    {
      field: 'status_id',
      headerName: 'Status',
      width: 140,
      valueGetter: (_, row) => getStatusName(row.status_id),
    },
    {
      field: 'experiment_template_id',
      headerName: 'Type (Template)',
      width: 160,
      valueGetter: (_, row) => getTemplateName(row.experiment_template_id),
    },
    {
      field: 'started_at',
      headerName: 'Started',
      width: 120,
      valueGetter: (v) => (v ? new Date(v as string).toLocaleDateString() : '—'),
    },
    {
      field: 'completed_at',
      headerName: 'Completed',
      width: 120,
      valueGetter: (v) => (v ? new Date(v as string).toLocaleDateString() : '—'),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 120,
      getActions: (params) => [
        <GridActionsCellItem
          key="view"
          icon={<VisibilityIcon />}
          label="View"
          onClick={() => navigate(`/experiments/${params.id}`)}
          aria-label={`View experiment ${params.row.name}`}
        />,
        <GridActionsCellItem
          key="edit"
          icon={<EditIcon />}
          label="Edit"
          onClick={() => navigate(`/experiments/${params.id}`)}
          disabled={!canManage}
          aria-label={`Edit experiment ${params.row.name}`}
        />,
      ],
    },
  ];

  if (loading && view === 'detail' && !selectedExperiment) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (view === 'detail' && selectedExperiment) {
    return (
      <Box sx={{ p: 3 }}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate('/experiments')}
          sx={{ mb: 2 }}
        >
          Back to List
        </Button>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        <Typography variant="h4" sx={{ mb: 1 }}>
          {selectedExperiment.name}
        </Typography>
        {selectedExperiment.description && (
          <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
            {selectedExperiment.description}
          </Typography>
        )}
        <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
          <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)}>
            <Tab label="Overview" />
            <Tab label="Sample Executions" />
            <Tab label="Details / Steps" />
            <Tab label="Lineage" />
            <Tab label="Linked Processes" />
            <Tab label="Runs" />
          </Tabs>
        </Box>

        {activeTab === 0 && (
          <Card variant="outlined" sx={{ mt: 2 }}>
            <CardContent>
              <List dense>
                <ListItem>
                  <ListItemText primary="Status" secondary={getStatusName(selectedExperiment.status_id)} />
                </ListItem>
                <ListItem>
                  <ListItemText primary="Template" secondary={getTemplateName(selectedExperiment.experiment_template_id)} />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Started"
                    secondary={selectedExperiment.started_at ? new Date(selectedExperiment.started_at).toLocaleString() : '—'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Completed"
                    secondary={selectedExperiment.completed_at ? new Date(selectedExperiment.completed_at).toLocaleString() : '—'}
                  />
                </ListItem>
                {selectedExperiment.custom_attributes && Object.keys(selectedExperiment.custom_attributes).length > 0 && (
                  <ListItem>
                    <ListItemText
                      primary="Custom attributes"
                      secondary={JSON.stringify(selectedExperiment.custom_attributes)}
                    />
                  </ListItem>
                )}
              </List>
            </CardContent>
          </Card>
        )}

        {activeTab === 1 && (
          <Card variant="outlined" sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Sample Executions
              </Typography>
              {selectedExperiment.sample_executions && selectedExperiment.sample_executions.length > 0 ? (
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Sample ID</TableCell>
                        <TableCell>Role</TableCell>
                        <TableCell>Replicate</TableCell>
                        <TableCell>Processing conditions</TableCell>
                        <TableCell>Test / Result</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {selectedExperiment.sample_executions.map((ex) => (
                        <TableRow key={ex.id}>
                          <TableCell>
                            <Button
                              size="small"
                              onClick={() => navigate(`/samples?highlight=${ex.sample_id}`)}
                              startIcon={<ScienceIcon />}
                            >
                              {ex.sample_id}
                            </Button>
                          </TableCell>
                          <TableCell>{ex.role_in_experiment_id ?? '—'}</TableCell>
                          <TableCell>{ex.replicate_number}</TableCell>
                          <TableCell>
                            <Box component="pre" sx={{ m: 0, fontSize: '0.75rem', maxWidth: 280, overflow: 'auto' }}>
                              {JSON.stringify(ex.processing_conditions || {}, null, 2)}
                            </Box>
                          </TableCell>
                          <TableCell>
                            {ex.test_id && <Chip size="small" label={`Test ${ex.test_id}`} sx={{ mr: 0.5 }} />}
                            {ex.result_id && <Chip size="small" label={`Result ${ex.result_id}`} />}
                            {!ex.test_id && !ex.result_id && '—'}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography color="text.secondary">No sample executions linked yet.</Typography>
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === 2 && (
          <Card variant="outlined" sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Details / Steps
              </Typography>
              {selectedExperiment.details && selectedExperiment.details.length > 0 ? (
                <List dense>
                  {selectedExperiment.details
                    .sort((a, b) => a.sort_order - b.sort_order)
                    .map((d) => (
                      <ListItem key={d.id}>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <PlaylistPlayIcon fontSize="small" />
                              {d.detail_type}
                              <Chip size="small" label={`Order ${d.sort_order}`} />
                            </Box>
                          }
                          secondary={
                            <Box component="pre" sx={{ mt: 0.5, fontSize: '0.75rem', overflow: 'auto' }}>
                              {JSON.stringify(d.content, null, 2)}
                            </Box>
                          }
                        />
                      </ListItem>
                    ))}
                </List>
              ) : (
                <Typography color="text.secondary">No detail steps.</Typography>
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === 3 && (
          <Card variant="outlined" sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Lineage
              </Typography>
              {lineageLoading && (
                <Box display="flex" alignItems="center" gap={1} sx={{ py: 2 }}>
                  <CircularProgress size={24} />
                  <Typography color="text.secondary">Loading lineage…</Typography>
                </Box>
              )}
              {lineageError && (
                <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setLineageError(null)}>
                  {lineageError}
                </Alert>
              )}
              {!lineageLoading && lineage && (
                <List dense>
                  {lineage.template && (
                    <ListItem>
                      <ListItemText
                        primary="Template"
                        secondary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <AccountTreeIcon fontSize="small" />
                            {lineage.template.name}
                          </Box>
                        }
                      />
                    </ListItem>
                  )}
                  {lineage.linked_experiment_ids && lineage.linked_experiment_ids.length > 0 && (
                    <ListItem>
                      <ListItemButton
                        onClick={() =>
                          setLineageExpanded((p) => ({ ...p, [selectedExperiment.id]: !p[selectedExperiment.id] }))
                        }
                      >
                        <ListItemText primary="Linked experiments" secondary={`${lineage.linked_experiment_ids.length} link(s)`} />
                        {lineageExpanded[selectedExperiment.id] ? <ExpandLess /> : <ExpandMore />}
                      </ListItemButton>
                    </ListItem>
                  )}
                  {lineage.linked_experiment_ids?.length > 0 && (
                    <Collapse in={!!lineageExpanded[selectedExperiment.id]} timeout="auto" unmountOnExit>
                      <List component="div" disablePadding>
                        {lineage.linked_experiment_ids.map((linkedId) => (
                          <ListItem key={linkedId} sx={{ pl: 4 }}>
                            <Button
                              size="small"
                              startIcon={<LinkIcon />}
                              onClick={() => navigate(`/experiments/${linkedId}`)}
                            >
                              {linkedId}
                            </Button>
                          </ListItem>
                        ))}
                      </List>
                    </Collapse>
                  )}
                  {(!lineage.template && (!lineage.linked_experiment_ids || lineage.linked_experiment_ids.length === 0)) && (
                    <Typography color="text.secondary">No template or linked experiments.</Typography>
                  )}
                </List>
              )}
              {!lineageLoading && !lineage && !lineageError && (
                <Typography color="text.secondary">No lineage data.</Typography>
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === 4 && (
          <Card variant="outlined" sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Linked Workflow Instances / Processes
              </Typography>
              <Typography color="text.secondary">
                Workflow runs that used this experiment (via context.experiment_id) can be listed here when the API supports filtering by experiment.
              </Typography>
            </CardContent>
          </Card>
        )}

        {activeTab === 5 && (
          <RunsTab experimentId={selectedExperiment.id} />
        )}
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={2} mb={3}>
        <Typography variant="h4">Experiments</Typography>
        {canManage && (
          <Button
            variant="contained"
            onClick={() => setShowCreateDialog(true)}
            aria-label="New experiment"
          >
            New Experiment
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
            <TextField
              size="small"
              label="Search by name"
              value={nameSearch}
              onChange={(e) => setNameSearch(e.target.value)}
              sx={{ minWidth: 200 }}
            />
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel>Status</InputLabel>
              <Select
                value={statusFilter}
                label="Status"
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <MenuItem value="">All</MenuItem>
                {statuses.map((s) => (
                  <MenuItem key={s.id} value={s.id}>
                    {s.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>Type (Template)</InputLabel>
              <Select
                value={templateFilter}
                label="Type (Template)"
                onChange={(e) => setTemplateFilter(e.target.value)}
              >
                <MenuItem value="">All</MenuItem>
                {templates.map((t) => (
                  <MenuItem key={t.id} value={t.id}>
                    {t.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Chip
              label="My Experiments"
              color={mineFilter ? 'primary' : 'default'}
              variant={mineFilter ? 'filled' : 'outlined'}
              onClick={() => {
                const next = new URLSearchParams(searchParams);
                if (mineFilter) next.delete('mine');
                else next.set('mine', 'true');
                setSearchParams(next);
                setPagination((p) => ({ ...p, page: 1 }));
              }}
              sx={{ alignSelf: 'center' }}
              aria-pressed={mineFilter}
              aria-label={mineFilter ? 'Filter: my experiments (click to clear)' : 'Show only my experiments'}
            />
          </Box>
          {loading ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress />
            </Box>
          ) : (
            <DataGrid
              rows={filteredExperiments}
              columns={columns}
              pageSizeOptions={[10, 25, 50, 100]}
              initialState={{
                pagination: { paginationModel: { pageSize: pagination.size } },
              }}
              paginationMode="server"
              rowCount={pagination.total}
              paginationModel={{
                page: pagination.page - 1,
                pageSize: pagination.size,
              }}
              onPaginationModelChange={(model) =>
                setPagination((p) => ({ ...p, page: model.page + 1, size: model.pageSize }))
              }
              autoHeight
              disableRowSelectionOnClick
            />
          )}
        </CardContent>
      </Card>

      <Dialog open={showCreateDialog} onClose={() => !createLoading && setShowCreateDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>New Experiment</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Name"
            fullWidth
            required
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
          />
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={2}
            value={createDescription}
            onChange={(e) => setCreateDescription(e.target.value)}
          />
          <FormControl fullWidth size="small" sx={{ mt: 1 }}>
            <InputLabel>Template</InputLabel>
            <Select
              value={createTemplateId}
              label="Template"
              onChange={(e) => setCreateTemplateId(e.target.value)}
            >
              <MenuItem value="">None</MenuItem>
              {templates.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth size="small" sx={{ mt: 1 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={createStatusId}
              label="Status"
              onChange={(e) => setCreateStatusId(e.target.value)}
            >
              <MenuItem value="">None</MenuItem>
              {statuses.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {s.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCreateDialog(false)} disabled={createLoading}>
            Cancel
          </Button>
          <Button variant="contained" onClick={handleCreateExperiment} disabled={!createName.trim() || createLoading}>
            {createLoading ? 'Creating…' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ExperimentsManagement;
