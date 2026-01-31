import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Chip,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Snackbar,
  FormControlLabel,
  Switch,
} from '@mui/material';
import MuiAlert, { AlertProps } from '@mui/material/Alert';
import {
  Add,
  Edit,
  Delete,
  CheckCircle,
  Cancel,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';

interface NameTemplate {
  id: string;
  entity_type: string;
  template: string;
  description?: string;
  active: boolean;
  created_at: string;
  modified_at: string;
}

const ENTITY_TYPES = ['sample', 'project', 'batch', 'analysis', 'container'];
const VALID_PLACEHOLDERS = ['{SEQ}', '{YYYY}', '{MM}', '{DD}', '{YYYYMMDD}', '{CLIENT}'];

/** Generate example preview from template string (client-side). */
function previewFromTemplate(template: string): string {
  if (!template || !template.trim()) return '';
  const now = new Date();
  let out = template
    .replace(/\{YYYY\}/g, String(now.getFullYear()))
    .replace(/\{MM\}/g, String(now.getMonth() + 1).padStart(2, '0'))
    .replace(/\{DD\}/g, String(now.getDate()).padStart(2, '0'))
    .replace(/\{YYYYMMDD\}/g, now.toISOString().slice(0, 10).replace(/-/g, ''))
    .replace(/\{SEQ\}/g, '001')
    .replace(/\{CLIENT\}/g, 'ACME');
  const invalidPlaceholders = out.match(/\{[^}]+\}/g);
  if (invalidPlaceholders?.length) return out;
  return out;
}

const AlertComponent = React.forwardRef<HTMLDivElement, AlertProps>(function Alert(props, ref) {
  return <MuiAlert elevation={6} ref={ref} variant="filled" {...props} />;
});

const NameTemplatesAdmin: React.FC = () => {
  const { hasPermission } = useUser();
  const [templates, setTemplates] = useState<NameTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('');
  const [formOpen, setFormOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<NameTemplate | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<NameTemplate | null>(null);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning';
  }>({ open: false, message: '', severity: 'success' });
  const [formValues, setFormValues] = useState({
    entity_type: '',
    template: '',
    description: '',
    active: true,
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const canEdit = hasPermission('config:edit');
  const isAdmin = hasPermission('config:edit');

  const loadTemplates = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const filters: { entity_type?: string; page?: number; size?: number; active?: boolean } = {
        page: page + 1,
        size: pageSize,
      };
      if (entityTypeFilter) filters.entity_type = entityTypeFilter;
      const response = await apiService.getNameTemplates(filters);
      setTemplates(response.templates || []);
      setTotal(response.total ?? 0);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view name templates');
      } else {
        setError(err.response?.data?.detail || 'Failed to load name templates');
      }
      setSnackbar({ open: true, message: err.response?.data?.detail || 'Failed to load name templates', severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, entityTypeFilter]);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const handleSnackbarClose = () => {
    setSnackbar((prev) => ({ ...prev, open: false }));
  };

  const openForm = (template: NameTemplate | null) => {
    setSelectedTemplate(template);
    setFormValues({
      entity_type: template?.entity_type ?? '',
      template: template?.template ?? '',
      description: template?.description ?? '',
      active: template?.active ?? true,
    });
    setFormErrors({});
    setFormOpen(true);
  };

  const validateForm = (): boolean => {
    const err: Record<string, string> = {};
    if (!formValues.entity_type) err.entity_type = 'Entity type is required';
    if (!formValues.template?.trim()) err.template = 'Template is required';
    if (formValues.template && !formValues.template.includes('{SEQ}')) {
      err.template = 'Template must include {SEQ} for uniqueness';
    }
    if (formValues.template) {
      const matches = formValues.template.match(/\{[^}]+\}/g);
      if (matches && !matches.every((m) => VALID_PLACEHOLDERS.includes(m))) {
        err.template = `Valid placeholders: ${VALID_PLACEHOLDERS.join(', ')}`;
      }
    }
    setFormErrors(err);
    return Object.keys(err).length === 0;
  };

  const handleCreate = async () => {
    if (!validateForm()) return;
    const alreadyActive = templates.some(
      (t) => t.entity_type === formValues.entity_type && t.active
    );
    if (formValues.active && alreadyActive) {
      setSnackbar({
        open: true,
        severity: 'warning',
        message: `Only one template can be active per entity type. Activating this template will deactivate the current active "${formValues.entity_type}" template.`,
      });
    }
    setSubmitting(true);
    try {
      await apiService.createNameTemplate({
        entity_type: formValues.entity_type,
        template: formValues.template.trim(),
        description: formValues.description.trim() || undefined,
        active: formValues.active,
      });
      setSnackbar({ open: true, message: 'Template created', severity: 'success' });
      setFormOpen(false);
      setSelectedTemplate(null);
      await loadTemplates();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to create template';
      setSnackbar({ open: true, message: msg, severity: 'error' });
      setFormErrors({ template: msg });
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdate = async () => {
    if (!selectedTemplate || !validateForm()) return;
    const alreadyActive = templates.find(
      (t) => t.entity_type === formValues.entity_type && t.active && t.id !== selectedTemplate.id
    );
    if (formValues.active && alreadyActive) {
      setSnackbar({
        open: true,
        severity: 'warning',
        message: `Only one template can be active per entity type. Activating this template will deactivate the current active "${formValues.entity_type}" template.`,
      });
    }
    setSubmitting(true);
    try {
      await apiService.updateNameTemplate(selectedTemplate.id, {
        entity_type: formValues.entity_type,
        template: formValues.template.trim(),
        description: formValues.description.trim() || undefined,
        active: formValues.active,
      });
      setSnackbar({ open: true, message: 'Template updated', severity: 'success' });
      setFormOpen(false);
      setSelectedTemplate(null);
      await loadTemplates();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to update template';
      setSnackbar({ open: true, message: msg, severity: 'error' });
      setFormErrors({ template: msg });
    } finally {
      setSubmitting(false);
    }
  };

  const handleFormSubmit = () => {
    if (selectedTemplate) handleUpdate();
    else handleCreate();
  };

  const handleActivate = async (template: NameTemplate) => {
    const otherActive = templates.some(
      (t) => t.entity_type === template.entity_type && t.active && t.id !== template.id
    );
    if (otherActive) {
      setSnackbar({
        open: true,
        severity: 'warning',
        message: `Another "${template.entity_type}" template is active. It will be deactivated.`,
      });
    }
    try {
      await apiService.updateNameTemplate(template.id, { active: true });
      setSnackbar({ open: true, message: 'Template activated', severity: 'success' });
      await loadTemplates();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to activate template',
        severity: 'error',
      });
    }
  };

  const handleDeactivate = async (template: NameTemplate) => {
    try {
      await apiService.updateNameTemplate(template.id, { active: false });
      setSnackbar({ open: true, message: 'Template deactivated', severity: 'success' });
      await loadTemplates();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to deactivate template',
        severity: 'error',
      });
    }
  };

  const handleDeleteClick = (template: NameTemplate) => {
    setDeleteTarget(template);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    if (deleteTarget.active) {
      setSnackbar({
        open: true,
        message: 'Cannot delete an active template. Deactivate it first.',
        severity: 'warning',
      });
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      return;
    }
    try {
      await apiService.deleteNameTemplate(deleteTarget.id);
      setSnackbar({ open: true, message: 'Template deleted', severity: 'success' });
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      await loadTemplates();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to delete template',
        severity: 'error',
      });
      setDeleteDialogOpen(false);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleString();
  };

  const previewExample = useMemo(
    () => previewFromTemplate(formValues.template),
    [formValues.template]
  );

  const columns: GridColDef[] = useMemo(
    () => [
      {
        field: 'entity_type',
        headerName: 'Entity Type',
        width: 130,
        renderCell: (params) => (
          <Chip label={params.value} size="small" color="primary" variant="outlined" />
        ),
      },
      { field: 'template', headerName: 'Template', flex: 1, minWidth: 200 },
      {
        field: 'active',
        headerName: 'Is Active',
        width: 100,
        renderCell: (params) => (
          <Chip
            label={params.value ? 'Active' : 'Inactive'}
            size="small"
            color={params.value ? 'success' : 'default'}
          />
        ),
      },
      {
        field: 'created_at',
        headerName: 'Created At',
        width: 160,
        valueFormatter: (value) => formatDate(value as string),
      },
      {
        field: 'modified_at',
        headerName: 'Updated At',
        width: 160,
        valueFormatter: (value) => formatDate(value as string),
      },
      {
        field: 'actions',
        type: 'actions',
        headerName: 'Actions',
        width: 180,
        getActions: (params: GridRowParams) => {
          const template = params.row as NameTemplate;
          const actions = [];
          if (canEdit) {
            actions.push(
              <GridActionsCellItem
                key="edit"
                icon={<Edit />}
                label="Edit"
                onClick={() => openForm(template)}
              />,
              template.active ? (
                <GridActionsCellItem
                  key="deactivate"
                  icon={<Cancel />}
                  label="Deactivate"
                  onClick={() => handleDeactivate(template)}
                />
              ) : (
                <GridActionsCellItem
                  key="activate"
                  icon={<CheckCircle />}
                  label="Activate"
                  onClick={() => handleActivate(template)}
                />
              )
            );
            if (!template.active) {
              actions.push(
                <GridActionsCellItem
                  key="delete"
                  icon={<Delete />}
                  label="Delete"
                  onClick={() => handleDeleteClick(template)}
                />
              );
            }
          }
          return actions;
        },
      },
    ],
    [canEdit, templates]
  );

  if (!isAdmin) {
    return (
      <Box>
        <Alert severity="warning">
          You do not have permission to view name templates. Admin access is required.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4">Name Templates</Typography>
        {canEdit && (
          <Button variant="contained" startIcon={<Add />} onClick={() => openForm(null)}>
            Create Template
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ mb: 2, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Entity Type</InputLabel>
          <Select
            value={entityTypeFilter}
            label="Entity Type"
            onChange={(e) => {
              setEntityTypeFilter(e.target.value);
              setPage(0);
            }}
          >
            <MenuItem value="">All</MenuItem>
            {ENTITY_TYPES.map((type) => (
              <MenuItem key={type} value={type}>
                {type}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
          <CircularProgress />
        </Box>
      ) : (
        <Box sx={{ height: 600, width: '100%' }}>
          <DataGrid
            rows={templates}
            columns={columns}
            getRowId={(row) => row.id}
            pageSizeOptions={[10, 25, 50]}
            paginationMode="server"
            rowCount={total}
            paginationModel={{ page, pageSize }}
            onPaginationModelChange={(model) => {
              setPage(model.page);
              setPageSize(model.pageSize);
            }}
            disableRowSelectionOnClick
            slots={{
              noRowsOverlay: () => (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  <Typography>No name templates found</Typography>
                </Box>
              ),
            }}
          />
        </Box>
      )}

      {/* Create/Edit Modal */}
      <Dialog open={formOpen} onClose={() => setFormOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{selectedTemplate ? 'Edit Name Template' : 'Create Name Template'}</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="normal" required error={!!formErrors.entity_type}>
            <InputLabel>Entity Type</InputLabel>
            <Select
              value={formValues.entity_type}
              label="Entity Type"
              onChange={(e) => setFormValues((v) => ({ ...v, entity_type: e.target.value }))}
              disabled={!!selectedTemplate}
            >
              {ENTITY_TYPES.map((type) => (
                <MenuItem key={type} value={type}>
                  {type}
                </MenuItem>
              ))}
            </Select>
            {formErrors.entity_type && (
              <Typography variant="caption" color="error" sx={{ mt: 0.5 }}>
                {formErrors.entity_type}
              </Typography>
            )}
          </FormControl>

          <TextField
            fullWidth
            margin="normal"
            required
            label="Template"
            value={formValues.template}
            onChange={(e) => setFormValues((v) => ({ ...v, template: e.target.value }))}
            error={!!formErrors.template}
            helperText={formErrors.template || 'e.g. SAMPLE-{YYYY}-{SEQ}'}
            placeholder="SAMPLE-{YYYY}-{SEQ}"
          />

          <TextField
            fullWidth
            margin="normal"
            label="Description"
            value={formValues.description}
            onChange={(e) => setFormValues((v) => ({ ...v, description: e.target.value }))}
            multiline
            rows={3}
            placeholder="Optional description"
          />

          <Box sx={{ mt: 2, p: 1.5, bgcolor: 'action.hover', borderRadius: 1 }}>
            <Typography variant="subtitle2" color="text.secondary" gutterBottom>
              Preview
            </Typography>
            <Typography variant="body2" fontFamily="monospace">
              {previewExample || '—'}
            </Typography>
            {formValues.template && !previewExample && (
              <Typography variant="caption" color="text.secondary">
                Enter a template with placeholders like {'{YYYY}'}, {'{SEQ}'} to see a preview.
              </Typography>
            )}
          </Box>

          <FormControlLabel
            control={
              <Switch
                checked={formValues.active}
                onChange={(e) => setFormValues((v) => ({ ...v, active: e.target.checked }))}
                color="primary"
              />
            }
            label="Active"
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFormOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button variant="contained" onClick={handleFormSubmit} disabled={submitting}>
            {submitting ? 'Saving...' : selectedTemplate ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Delete the name template for entity type <strong>{deleteTarget?.entity_type}</strong>?
            Only inactive templates can be deleted.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button
            color="error"
            variant="contained"
            onClick={handleDeleteConfirm}
            disabled={deleteTarget?.active}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={handleSnackbarClose}>
        <AlertComponent onClose={handleSnackbarClose} severity={snackbar.severity}>
          {snackbar.message}
        </AlertComponent>
      </Snackbar>
    </Box>
  );
};

export default NameTemplatesAdmin;
