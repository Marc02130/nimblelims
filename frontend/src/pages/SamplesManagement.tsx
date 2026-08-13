import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  DialogContentText,
  Alert,
  CircularProgress,
  Tooltip,
  Chip,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
} from '@mui/material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowSelectionModel } from '@mui/x-data-grid';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import { useNavigate, useSearchParams } from 'react-router-dom';
import SampleForm from '../components/samples/SampleForm';
import { apiService, addClientFilterIfNeeded } from '../services/apiService';
import { useUser } from '../contexts/UserContext';
import { FillHeightPage, FillHeightTable } from '../components/common/FillHeightPage';

interface JourneyItem {
  process_id: string;
  process_name: string;
  process_sample_status: string;
  current_step_name?: string;
  current_step_kind?: string;
  current_step_sort_order?: number;
  experiment_id?: string;
  lims_run_id?: string;
  lims_run_status?: string;
}

interface Sample {
  id: string;
  name: string;
  description?: string;
  status: string;
  sample_type: string;
  matrix: string;
  project_id: string;
  due_date?: string;
  received_date?: string;
  created_at: string;
  modified_at?: string;
  status_name?: string;
  sample_type_name?: string;
  matrix_name?: string;
  project_name?: string;
}

interface LookupItem {
  id: string;
  name: string;
  [key: string]: unknown;
}

const SamplesManagement: React.FC = () => {
  const { hasPermission, user } = useUser();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [samples, setSamples] = useState<Sample[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSample, setSelectedSample] = useState<Sample | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [viewMode, setViewMode] = useState(false);
  const [journey, setJourney] = useState<JourneyItem[]>([]);
  const [journeyLoading, setJourneyLoading] = useState(false);
  const [lookupData, setLookupData] = useState<{
    sampleTypes: LookupItem[];
    statuses: LookupItem[];
    matrices: LookupItem[];
    qcTypes: LookupItem[];
    projects: LookupItem[];
  }>({
    sampleTypes: [],
    statuses: [],
    matrices: [],
    qcTypes: [],
    projects: [],
  });

  // Assign selected samples to an ELN process (MUI X v8 selection model)
  const [rowSelection, setRowSelection] = useState<GridRowSelectionModel>({
    type: 'include',
    ids: new Set(),
  });
  const [assignOpen, setAssignOpen] = useState(false);
  const [processes, setProcesses] = useState<{ id: string; name: string }[]>([]);
  const [assignProcessId, setAssignProcessId] = useState('');
  const [assignToFirstStep, setAssignToFirstStep] = useState(true);
  const [assignLoading, setAssignLoading] = useState(false);
  const [assignError, setAssignError] = useState<string | null>(null);
  const [assignSuccess, setAssignSuccess] = useState<string | null>(null);

  const canUpdate = hasPermission('sample:update');
  const canManageProcesses = hasPermission('experiment:manage');
  const selectedIds = Array.from(rowSelection.ids).map(String);
  const selectedCount = selectedIds.length;

  useEffect(() => {
    loadData();
  }, [searchParams]);

  useEffect(() => {
    if (!selectedSample?.id || !showForm) {
      setJourney([]);
      return;
    }
    let cancelled = false;
    setJourneyLoading(true);
    apiService
      .getSampleJourney(selectedSample.id)
      .then((res: any) => {
        if (!cancelled) setJourney(res?.processes ?? []);
      })
      .catch(() => {
        if (!cancelled) setJourney([]);
      })
      .finally(() => {
        if (!cancelled) setJourneyLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedSample?.id, showForm]);

  const loadData = async () => {
    try {
      setLoading(true);
      // Get project_id from URL query parameters
      const projectId = searchParams.get('project_id') || undefined;
      
      // Build filters object - supports project_id, status, qc_type, and custom.* attributes
      const filters: Record<string, string | undefined> = {};
      if (projectId) {
        filters.project_id = projectId;
      }
      
      // Pass through all custom.* parameters for JSONB filtering
      // Backend supports: ?custom.ph_level=7.5, ?custom.notes=test, etc.
      searchParams.forEach((value, key) => {
        if (key.startsWith('custom.')) {
          filters[key] = value;
        }
        // Also support status and qc_type filters
        if (key === 'status' || key === 'qc_type') {
          filters[key] = value;
        }
      });

      // Add client_id filter for non-System clients (though RLS will also enforce this)
      const filteredFilters = addClientFilterIfNeeded(
        filters,
        user?.client_id,
        user?.role
      );

      const [samplesResponse, sampleTypesRaw, statusesRaw, matricesRaw, qcTypesRaw, projectsResponse] = await Promise.all([
        apiService.getSamples(filteredFilters),
        apiService.getListEntries('sample_types'),
        apiService.getListEntries('sample_status'),
        apiService.getListEntries('matrix_types'),
        apiService.getListEntries('qc_types'),
        apiService.getProjects(),
      ]);

      // Handle paginated response - extract samples array
      const samplesData = Array.isArray(samplesResponse) ? samplesResponse : (samplesResponse?.samples ?? []);
      // Ensure all lookup data are arrays so .map() never runs on non-arrays
      const sampleTypes = Array.isArray(sampleTypesRaw) ? sampleTypesRaw : [];
      const statuses = Array.isArray(statusesRaw) ? statusesRaw : [];
      const matrices = Array.isArray(matricesRaw) ? matricesRaw : [];
      const qcTypes = Array.isArray(qcTypesRaw) ? qcTypesRaw : [];
      const projects = Array.isArray(projectsResponse?.projects)
        ? projectsResponse.projects
        : Array.isArray(projectsResponse)
          ? projectsResponse
          : [];

      // Enrich samples with names for display
      const enrichedSamples = samplesData.map((sample: any) => ({
        ...sample,
        status_name: statuses.find((s: any) => s.id === sample.status)?.name || 'Unknown',
        sample_type_name: sampleTypes.find((t: any) => t.id === sample.sample_type)?.name || 'Unknown',
        matrix_name: matrices.find((m: any) => m.id === sample.matrix)?.name || 'Unknown',
        project_name: projects.find((p: any) => p.id === sample.project_id)?.name || 'Unknown',
      }));

      setSamples(enrichedSamples);
      setLookupData({ sampleTypes, statuses, matrices, qcTypes, projects });

      // Bidirectional link from Experiments: open sample view when ?highlight=<sample_id>
      const highlightId = searchParams.get('highlight');
      if (highlightId && highlightId.trim()) {
        try {
          const sample = await apiService.getSample(highlightId.trim());
          setSelectedSample(sample);
          setViewMode(true);
          setShowForm(true);
        } catch {
          // Sample may not exist or no access; ignore
        }
      }
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('Access denied: You do not have permission to view these samples. Client users can only view samples from their own client\'s projects.');
      } else if (err.response?.status === 404) {
        setError('No samples found. This may be due to access restrictions.');
      } else {
        setError(err.response?.data?.detail || 'Failed to load samples');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleView = async (sampleId: string) => {
    try {
      setError(null);
      const sample = await apiService.getSample(sampleId);
      setSelectedSample(sample);
      setViewMode(true);
      setShowForm(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load sample');
    }
  };

  const handleEdit = async (sampleId: string) => {
    try {
      setError(null);
      const sample = await apiService.getSample(sampleId);
      setSelectedSample(sample);
      setViewMode(false);
      setShowForm(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load sample');
    }
  };

  const handleUpdateSample = async (sampleData: any) => {
    if (!selectedSample) return;
    try {
      await apiService.updateSample(selectedSample.id, sampleData);
      await loadData(); // Reload data
      setShowForm(false);
      setSelectedSample(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update sample');
      throw err;
    }
  };

  const openAssignDialog = async () => {
    if (!selectedCount) {
      setError('Select one or more samples to assign to a process');
      return;
    }
    setAssignError(null);
    setAssignProcessId('');
    setAssignToFirstStep(true);
    setAssignOpen(true);
    try {
      const res: any = await apiService.getElnProcesses({ active: true, page: 1, size: 100 });
      const items = res?.items ?? res?.processes ?? (Array.isArray(res) ? res : []);
      setProcesses(
        items.map((p: any) => ({
          id: p.id,
          name: p.name + (p.sample_count != null ? ` (${p.sample_count} samples)` : ''),
        })),
      );
    } catch (err: any) {
      setAssignError(err.response?.data?.detail || 'Failed to load processes');
      setProcesses([]);
    }
  };

  const handleAssignToProcess = async () => {
    if (!assignProcessId || !selectedCount) return;
    setAssignLoading(true);
    setAssignError(null);
    try {
      await apiService.assignElnProcessSamples(assignProcessId, {
        sample_ids: selectedIds,
        set_to_first_step: assignToFirstStep,
      });
      setAssignOpen(false);
      setRowSelection({ type: 'include', ids: new Set() });
      setAssignSuccess(
        `Assigned ${selectedIds.length} sample${selectedIds.length === 1 ? '' : 's'} to the process`,
      );
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setAssignError(
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map((d: any) => d.msg || d).join('; ')
            : 'Failed to assign samples (they may already be on this process)',
      );
    } finally {
      setAssignLoading(false);
    }
  };

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', width: 200, flex: 1 },
    { 
      field: 'status_name', 
      headerName: 'Status', 
      width: 150,
    },
    { 
      field: 'sample_type_name', 
      headerName: 'Sample Type', 
      width: 150,
    },
    { 
      field: 'matrix_name', 
      headerName: 'Matrix', 
      width: 150,
    },
    { 
      field: 'project_name', 
      headerName: 'Project', 
      width: 200,
    },
    { 
      field: 'due_date', 
      headerName: 'Due Date', 
      width: 120,
      valueGetter: (value) => value ? new Date(value).toLocaleDateString() : '',
    },
    { 
      field: 'modified_at', 
      headerName: 'Last Modified', 
      width: 150,
      valueGetter: (value) => value ? new Date(value).toLocaleDateString() : '',
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 150,
      getActions: (params) => [
        <GridActionsCellItem
          icon={
            <Tooltip title="View sample">
              <VisibilityIcon />
            </Tooltip>
          }
          label="View"
          onClick={() => handleView(params.id as string)}
          aria-label={`View sample ${params.row.name}`}
        />,
        <GridActionsCellItem
          icon={
            <Tooltip title="Edit sample">
              <EditIcon />
            </Tooltip>
          }
          label="Edit"
          onClick={() => handleEdit(params.id as string)}
          disabled={!canUpdate}
          aria-label={`Edit sample ${params.row.name}`}
        />,
      ],
    },
  ];

  return (
    <FillHeightPage
      header={
        <>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} flexWrap="wrap" gap={1}>
            <Typography variant="h4">Samples Management</Typography>
            <Box display="flex" gap={1} flexWrap="wrap">
              {canManageProcesses && (
                <Button
                  variant="outlined"
                  startIcon={<AccountTreeIcon />}
                  onClick={() => void openAssignDialog()}
                  disabled={selectedCount === 0}
                  aria-label="Assign selected samples to a process"
                >
                  Assign to process{selectedCount > 0 ? ` (${selectedCount})` : ''}
                </Button>
              )}
              <Button
                variant="contained"
                onClick={() => navigate('/accessioning')}
                aria-label="Navigate to accessioning form"
              >
                Create Sample
              </Button>
            </Box>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          {assignSuccess && (
            <Alert severity="success" sx={{ mb: 2 }} onClose={() => setAssignSuccess(null)}>
              {assignSuccess}
            </Alert>
          )}

          {!canUpdate && (
            <Alert severity="info" sx={{ mb: 2 }}>
              You have read-only access. Contact your administrator for update permissions.
            </Alert>
          )}
          {canManageProcesses && selectedCount === 0 && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Select one or more rows, then <strong>Assign to process</strong> to put samples on an ELN
              process queue.
            </Typography>
          )}
        </>
      }
    >
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" flex={1}>
          <CircularProgress />
        </Box>
      ) : (
        <FillHeightTable>
          <DataGrid
            rows={samples}
            columns={columns}
            pageSizeOptions={[10, 25, 50, 100]}
            initialState={{
              pagination: {
                paginationModel: { page: 0, pageSize: 25 },
              },
            }}
            checkboxSelection={canManageProcesses}
            rowSelectionModel={rowSelection}
            onRowSelectionModelChange={(m) => setRowSelection(m)}
            disableRowSelectionOnClick
          />
        </FillHeightTable>
      )}

      {/* Assign to process dialog */}
      <Dialog
        open={assignOpen}
        onClose={() => !assignLoading && setAssignOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Assign samples to process</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Assign <strong>{selectedCount}</strong> selected sample
            {selectedCount === 1 ? '' : 's'} to an ELN process. They become available in that
            process queue when starting experiments (status Available for Testing required at start).
          </DialogContentText>
          {assignError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setAssignError(null)}>
              {assignError}
            </Alert>
          )}
          <FormControl fullWidth margin="normal" required>
            <InputLabel>Process</InputLabel>
            <Select
              label="Process"
              value={assignProcessId}
              onChange={(e) => setAssignProcessId(e.target.value)}
              disabled={assignLoading}
            >
              {processes.length === 0 ? (
                <MenuItem value="" disabled>
                  No active processes — create one under Experiments → Processes
                </MenuItem>
              ) : (
                processes.map((p) => (
                  <MenuItem key={p.id} value={p.id}>
                    {p.name}
                  </MenuItem>
                ))
              )}
            </Select>
          </FormControl>
          <FormControlLabel
            control={
              <Checkbox
                checked={assignToFirstStep}
                onChange={(e) => setAssignToFirstStep(e.target.checked)}
                disabled={assignLoading}
              />
            }
            label="Set current step to first process step"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAssignOpen(false)} disabled={assignLoading}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={() => void handleAssignToProcess()}
            disabled={assignLoading || !assignProcessId}
          >
            {assignLoading ? 'Assigning…' : 'Assign'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Sample Form Dialog */}
      <Dialog
        open={showForm}
        onClose={() => {
          setShowForm(false);
          setSelectedSample(null);
          setViewMode(false);
        }}
        maxWidth="md"
        fullWidth
        aria-labelledby="sample-form-dialog-title"
      >
        <DialogTitle id="sample-form-dialog-title">
          {viewMode ? `View Sample: ${selectedSample?.name}` : canUpdate ? `Edit Sample: ${selectedSample?.name}` : `View Sample: ${selectedSample?.name}`}
        </DialogTitle>
        <DialogContent>
          <SampleForm
            sample={selectedSample || undefined}
            lookupData={lookupData}
            onSubmit={handleUpdateSample}
            onCancel={() => {
              setShowForm(false);
              setSelectedSample(null);
              setViewMode(false);
            }}
            readOnly={viewMode}
          />
          {/* Phase 3: sample-scoped process journey (Decision #7) */}
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle1" gutterBottom>
            Process journey
          </Typography>
          {journeyLoading ? (
            <CircularProgress size={20} />
          ) : journey.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              Not assigned to any ELN process.
            </Typography>
          ) : (
            <Box display="flex" flexDirection="column" gap={1}>
              {journey.map((j) => (
                <Box
                  key={j.process_id}
                  sx={{
                    p: 1.5,
                    border: '1px solid',
                    borderColor: 'divider',
                    borderRadius: 1,
                  }}
                >
                  <Box display="flex" alignItems="center" gap={1} flexWrap="wrap" mb={0.5}>
                    <Button
                      size="small"
                      onClick={() => navigate(`/experiments/processes/${j.process_id}`)}
                    >
                      {j.process_name}
                    </Button>
                    <Chip size="small" label={j.process_sample_status} />
                    {j.current_step_kind && (
                      <Chip
                        size="small"
                        color={j.current_step_kind === 'lims_run' ? 'secondary' : 'primary'}
                        label={
                          j.current_step_kind === 'lims_run' ? 'LIMS Run' : 'ELN Experiment'
                        }
                      />
                    )}
                  </Box>
                  <Typography variant="body2" color="text.secondary">
                    Current step:{' '}
                    {j.current_step_name
                      ? `${j.current_step_sort_order ?? ''}: ${j.current_step_name}`
                      : '—'}
                    {j.lims_run_status ? ` · Run status: ${j.lims_run_status}` : ''}
                  </Typography>
                  <Box display="flex" gap={1} mt={0.5}>
                    {j.experiment_id && (
                      <Button
                        size="small"
                        onClick={() => navigate(`/experiments/${j.experiment_id}`)}
                      >
                        Open experiment
                      </Button>
                    )}
                    {j.lims_run_id && (
                      <Button size="small" onClick={() => navigate(`/runs/${j.lims_run_id}`)}>
                        Open run
                      </Button>
                    )}
                  </Box>
                </Box>
              ))}
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </FillHeightPage>
  );
};

export default SamplesManagement;

