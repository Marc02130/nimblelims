import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  TextField,
  Chip,
  FormControlLabel,
  Switch,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import { Add, Edit, Delete, PlayArrow } from '@mui/icons-material';
import Tooltip from '@mui/material/Tooltip';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';

export interface WorkflowTemplateRow {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  template_definition: Record<string, unknown>;
  created_at: string;
  modified_at: string;
  created_by?: string;
  modified_by?: string;
}

const DEFAULT_TEMPLATE_DEFINITION = {
  steps: [
    { action: 'update_status', params: {} },
  ],
};

function tryParseJson(value: string): { ok: true; data: Record<string, unknown> } | { ok: false; error: string } {
  const trimmed = value.trim();
  if (!trimmed) {
    return { ok: false, error: 'JSON is required' };
  }
  try {
    const data = JSON.parse(trimmed) as Record<string, unknown>;
    if (typeof data !== 'object' || data === null) {
      return { ok: false, error: 'Must be a JSON object' };
    }
    if (!Array.isArray(data.steps)) {
      return { ok: false, error: 'template_definition must contain a "steps" array' };
    }
    for (let i = 0; i < data.steps.length; i++) {
      const step = data.steps[i];
      if (typeof step !== 'object' || step === null || typeof (step as any).action !== 'string') {
        return { ok: false, error: `steps[${i}] must have "action" string` };
      }
    }
    return { ok: true, data };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : 'Invalid JSON' };
  }
}

const WorkflowTemplatesManagement: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const { hasPermission } = useUser();

  const [rows, setRows] = useState<WorkflowTemplateRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [formOpen, setFormOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplateRow | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<WorkflowTemplateRow | null>(null);
  const [executeDialogOpen, setExecuteDialogOpen] = useState(false);
  const [executeTarget, setExecuteTarget] = useState<WorkflowTemplateRow | null>(null);
  const [executeContextJson, setExecuteContextJson] = useState('{}');
  const [executeSubmitting, setExecuteSubmitting] = useState(false);
  const [executeError, setExecuteError] = useState<string | null>(null);

  const [formName, setFormName] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formActive, setFormActive] = useState(true);
  const [formDefinitionJson, setFormDefinitionJson] = useState(
    () => JSON.stringify(DEFAULT_TEMPLATE_DEFINITION, null, 2)
  );
  const [formJsonError, setFormJsonError] = useState<string | null>(null);
  const [formSubmitting, setFormSubmitting] = useState(false);

  const canEdit = hasPermission('config:edit');
  const canExecute = hasPermission('workflow:execute');

  const loadTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getWorkflowTemplates();
      setRows(Array.isArray(data) ? data : []);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view workflow templates.');
      } else {
        setError(err.response?.data?.detail || 'Failed to load workflow templates');
      }
      setRows([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  const handleOpenCreate = () => {
    setSelectedTemplate(null);
    setFormName('');
    setFormDescription('');
    setFormActive(true);
    setFormDefinitionJson(JSON.stringify(DEFAULT_TEMPLATE_DEFINITION, null, 2));
    setFormJsonError(null);
    setFormOpen(true);
  };

  const handleOpenEdit = (row: WorkflowTemplateRow) => {
    setSelectedTemplate(row);
    setFormName(row.name);
    setFormDescription(row.description ?? '');
    setFormActive(row.active);
    setFormDefinitionJson(
      typeof row.template_definition === 'object' && row.template_definition !== null
        ? JSON.stringify(row.template_definition, null, 2)
        : JSON.stringify(DEFAULT_TEMPLATE_DEFINITION, null, 2)
    );
    setFormJsonError(null);
    setFormOpen(true);
  };

  const handleSaveForm = async () => {
    const parsed = tryParseJson(formDefinitionJson);
    if (!parsed.ok) {
      setFormJsonError(parsed.error);
      return;
    }
    setFormJsonError(null);
    setFormSubmitting(true);
    try {
      if (selectedTemplate) {
        await apiService.updateWorkflowTemplate(selectedTemplate.id, {
          name: formName,
          description: formDescription || undefined,
          active: formActive,
          template_definition: parsed.data,
        });
      } else {
        await apiService.createWorkflowTemplate({
          name: formName,
          description: formDescription || undefined,
          active: formActive,
          template_definition: parsed.data,
        });
      }
      await loadTemplates();
      setFormOpen(false);
      setSelectedTemplate(null);
    } catch (err: any) {
      setFormJsonError(err.response?.data?.detail || err.message || 'Failed to save');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleDeleteClick = (row: WorkflowTemplateRow) => {
    setDeleteTarget(row);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteWorkflowTemplate(deleteTarget.id);
      await loadTemplates();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete template');
      setDeleteDialogOpen(false);
    }
  };

  const handleExecuteClick = (row: WorkflowTemplateRow) => {
    setExecuteTarget(row);
    setExecuteContextJson('{}');
    setExecuteError(null);
    setExecuteDialogOpen(true);
  };

  const handleExecuteConfirm = async () => {
    if (!executeTarget) return;
    let context: Record<string, unknown> = {};
    try {
      context = JSON.parse(executeContextJson.trim() || '{}') as Record<string, unknown>;
    } catch {
      setExecuteError('Context must be valid JSON');
      return;
    }
    setExecuteSubmitting(true);
    setExecuteError(null);
    try {
      await apiService.executeWorkflow(executeTarget.id, { context });
      setExecuteDialogOpen(false);
      setExecuteTarget(null);
    } catch (err: any) {
      setExecuteError(err.response?.data?.detail || err.message || 'Execute failed');
    } finally {
      setExecuteSubmitting(false);
    }
  };

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', width: 200, flex: isMobile ? 0 : 1 },
    {
      field: 'description',
      headerName: 'Description',
      width: 220,
      flex: isMobile ? 0 : 1,
      valueGetter: (_, row) => row.description ?? '—',
    },
    {
      field: 'active',
      headerName: 'Active',
      width: 90,
      renderCell: (params) => (
        <Chip
          label={params.value ? 'Yes' : 'No'}
          size="small"
          color={params.value ? 'success' : 'default'}
          variant="outlined"
        />
      ),
    },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 160,
      valueFormatter: (value) => (value ? new Date(value as string).toLocaleString() : '—'),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 160,
      getActions: (params: GridRowParams) => {
        const row = params.row as WorkflowTemplateRow;
        const actions: React.ReactNode[] = [];
        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              key="edit"
              icon={<Edit />}
              label="Edit"
              onClick={() => handleOpenEdit(row)}
            />,
            <GridActionsCellItem
              key="delete"
              icon={<Delete />}
              label="Delete"
              onClick={() => handleDeleteClick(row)}
            />
          );
        }
        if (canExecute && row.active) {
          actions.push(
            <GridActionsCellItem
              key="execute"
              icon={<PlayArrow />}
              label="Execute on Entity"
              onClick={() => handleExecuteClick(row)}
            />
          );
        }
        // Assert to expected getActions return type (readonly ReactElement[]); runtime type is correct
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        return actions as any;
      },
    },
  ];

  if (!canEdit) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="warning">
          You do not have permission to view workflow templates management. Requires <strong>config:edit</strong>{' '}
          permission.
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2, mb: 2 }}>
        <Typography variant="h5">Workflow Templates</Typography>
        {canEdit && (
          <Button variant="contained" startIcon={<Add />} onClick={handleOpenCreate}>
            Add Template
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
          <CircularProgress />
        </Box>
      ) : (
        <Box sx={{ height: rows.length === 0 ? 'auto' : 600, minHeight: 220, width: '100%', mb: 2 }}>
          <DataGrid
            rows={rows}
            columns={columns}
            getRowId={(row) => row.id}
            pageSizeOptions={[10, 25, 50]}
            initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
            disableRowSelectionOnClick
            autoHeight={rows.length === 0}
            slots={{
              noRowsOverlay: () => (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%', minHeight: 160 }}>
                  <Typography>No workflow templates. Create one to get started.</Typography>
                </Box>
              ),
            }}
            sx={{
              '& .MuiDataGrid-cell': { fontSize: theme.typography.body2.fontSize },
            }}
          />
        </Box>
      )}

      {/* Create/Edit Dialog with JSON editor (monospace TextField; can be replaced by Monaco/CodeMirror) */}
      <Dialog open={formOpen} onClose={() => setFormOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{selectedTemplate ? 'Edit Workflow Template' : 'Create Workflow Template'}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            margin="normal"
            required
            label="Name"
            value={formName}
            onChange={(e) => setFormName(e.target.value)}
            placeholder="e.g. Sample Receipt Workflow"
            disabled={!!selectedTemplate}
          />
          <TextField
            fullWidth
            margin="normal"
            label="Description"
            value={formDescription}
            onChange={(e) => setFormDescription(e.target.value)}
            placeholder="Optional description"
            multiline
            rows={2}
          />
          <TextField
            fullWidth
            margin="normal"
            required
            label="Template definition (JSON)"
            value={formDefinitionJson}
            onChange={(e) => {
              setFormDefinitionJson(e.target.value);
              setFormJsonError(null);
            }}
            error={!!formJsonError}
            helperText={
              formJsonError ||
              'Must have "steps" array. action: update_status | validate_custom | create_qc | assign_tests | create_batch | enter_results | send_notification | accession_sample | link_container | review_result | create_experiment | create_experiment_from_template | link_sample_to_experiment | add_experiment_detail_step | link_experiments | update_experiment_status. params: {} or e.g. { "name": "...", "experiment_template_id": "uuid", "sample_id": "uuid" }. Context can carry experiment_id, execution_id.'
            }
            multiline
            minRows={10}
            maxRows={24}
            sx={{
              fontFamily: 'monospace',
              '& textarea': { fontFamily: 'monospace', fontSize: '0.875rem' },
            }}
          />
          <FormControlLabel
            control={
              <Switch checked={formActive} onChange={(e) => setFormActive(e.target.checked)} color="primary" />
            }
            label="Active"
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFormOpen(false)} disabled={formSubmitting}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSaveForm}
            disabled={formSubmitting || !formName.trim()}
          >
            {formSubmitting ? 'Saving...' : selectedTemplate ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete confirmation */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm deactivate</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Deactivate workflow template <strong>{deleteTarget?.name}</strong>? It will no longer appear for execution.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained">
            Deactivate
          </Button>
        </DialogActions>
      </Dialog>

      {/* Execute on Entity dialog */}
      <Dialog open={executeDialogOpen} onClose={() => setExecuteDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Execute on Entity</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Run template <strong>{executeTarget?.name}</strong>. Pass context as JSON (e.g. sample_id, batch_id). For experiment actions use experiment_id (set by create_experiment / create_experiment_from_template) or experiment_template_id, sample_id in params.
          </DialogContentText>
          <TextField
            fullWidth
            label="Context (JSON)"
            value={executeContextJson}
            onChange={(e) => setExecuteContextJson(e.target.value)}
            multiline
            minRows={3}
            sx={{
              fontFamily: 'monospace',
              '& textarea': { fontFamily: 'monospace', fontSize: '0.875rem' },
            }}
          />
          {executeError && (
            <Alert severity="error" sx={{ mt: 2 }} onClose={() => setExecuteError(null)}>
              {executeError}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExecuteDialogOpen(false)} disabled={executeSubmitting}>
            Cancel
          </Button>
          <Tooltip title={canExecute ? '' : 'Requires workflow:execute permission'}>
            <span>
              <Button
                variant="contained"
                startIcon={<PlayArrow />}
                onClick={handleExecuteConfirm}
                disabled={executeSubmitting || !canExecute}
              >
                {executeSubmitting ? 'Running...' : 'Execute'}
              </Button>
            </span>
          </Tooltip>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default WorkflowTemplatesManagement;
