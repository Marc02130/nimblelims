import React, { useState, useEffect, useCallback, useMemo } from 'react';
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
  Checkbox,
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

interface CustomAttributeConfig {
  id: string;
  entity_type: string;
  attr_name: string;
  data_type: 'text' | 'number' | 'date' | 'boolean' | 'select';
  validation_rules: Record<string, unknown>;
  description?: string;
  active: boolean;
  created_at?: string;
  modified_at?: string;
}

const ENTITY_TYPES = ['samples', 'tests', 'results', 'projects', 'client_projects', 'batches'];
const DATA_TYPES = ['text', 'number', 'date', 'boolean', 'select'];

const AlertComponent = React.forwardRef<HTMLDivElement, AlertProps>(function Alert(props, ref) {
  return <MuiAlert elevation={6} ref={ref} variant="filled" {...props} />;
});

function formatValidationRules(rules: Record<string, unknown> | null | undefined): string {
  if (!rules || Object.keys(rules).length === 0) return '{}';
  try {
    return JSON.stringify(rules, null, 2);
  } catch {
    return '{}';
  }
}

function getIsRequired(rules: Record<string, unknown> | null | undefined): boolean {
  if (!rules || typeof rules !== 'object') return false;
  return rules.required === true;
}

const CustomAttributesAdmin: React.FC = () => {
  const { hasPermission } = useUser();
  const [configs, setConfigs] = useState<CustomAttributeConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('');
  const [formOpen, setFormOpen] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<CustomAttributeConfig | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<CustomAttributeConfig | null>(null);
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
    attr_name: '',
    data_type: 'text' as CustomAttributeConfig['data_type'],
    validation_rules: '{}',
    is_required: false,
    is_active: true,
    description: '',
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);

  const canEdit = hasPermission('config:edit');
  const isAdmin = hasPermission('config:edit');

  const loadConfigs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const filters: { entity_type?: string; page?: number; size?: number } = {
        page: page + 1,
        size: pageSize,
      };
      if (entityTypeFilter) filters.entity_type = entityTypeFilter;
      const response = await apiService.getCustomAttributeConfigs(filters);
      setConfigs(response.configs || []);
      setTotal(response.total ?? 0);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to load custom attribute configs';
      setError(msg);
      setSnackbar({ open: true, message: msg, severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, entityTypeFilter]);

  useEffect(() => {
    loadConfigs();
  }, [loadConfigs]);

  const handleSnackbarClose = () => {
    setSnackbar((prev) => ({ ...prev, open: false }));
  };

  const openForm = (config: CustomAttributeConfig | null) => {
    setSelectedConfig(config);
    const rules = config?.validation_rules ?? {};
    const rulesStr = formatValidationRules(rules);
    setFormValues({
      entity_type: config?.entity_type ?? '',
      attr_name: config?.attr_name ?? '',
      data_type: config?.data_type ?? 'text',
      validation_rules: rulesStr,
      is_required: getIsRequired(rules),
      is_active: config?.active ?? true,
      description: config?.description ?? '',
    });
    setFormErrors({});
    setFormOpen(true);
  };

  const parseValidationRules = (str: string): Record<string, unknown> => {
    const trimmed = str.trim();
    if (!trimmed) return {};
    try {
      const parsed = JSON.parse(trimmed);
      if (typeof parsed !== 'object' || parsed === null) return {};
      return parsed as Record<string, unknown>;
    } catch {
      return {};
    }
  };

  const validateForm = (): boolean => {
    const err: Record<string, string> = {};
    if (!formValues.entity_type) err.entity_type = 'Entity type is required';
    if (!formValues.attr_name?.trim()) err.attr_name = 'Attribute name is required';
    if (!/^[a-zA-Z0-9_-]+$/.test(formValues.attr_name.trim())) {
      err.attr_name = 'Attribute name can only contain letters, numbers, underscores, and hyphens';
    }
    if (!formValues.data_type) err.data_type = 'Data type is required';
    const rules = parseValidationRules(formValues.validation_rules);
    if (formValues.validation_rules.trim()) {
      try {
        JSON.parse(formValues.validation_rules);
      } catch {
        err.validation_rules = 'Validation rules must be valid JSON';
      }
    }
    if (formValues.data_type === 'select' && (!rules.options || !Array.isArray(rules.options))) {
      err.validation_rules = err.validation_rules || 'Select type requires an "options" array in validation rules';
    }
    setFormErrors(err);
    return Object.keys(err).length === 0;
  };

  const buildValidationRules = (): Record<string, unknown> => {
    const rules = parseValidationRules(formValues.validation_rules);
    if (formValues.is_required) {
      rules.required = true;
    } else if ('required' in rules) {
      delete rules.required;
    }
    return rules;
  };

  const handleCreate = async () => {
    if (!validateForm()) return;
    const duplicate = configs.some(
      (c) => c.entity_type === formValues.entity_type && c.attr_name === formValues.attr_name.trim()
    );
    if (duplicate) {
      setSnackbar({
        open: true,
        severity: 'error',
        message: `Attribute "${formValues.attr_name}" already exists for entity type "${formValues.entity_type}".`,
      });
      return;
    }
    setSubmitting(true);
    try {
      await apiService.createCustomAttributeConfig({
        entity_type: formValues.entity_type,
        attr_name: formValues.attr_name.trim(),
        data_type: formValues.data_type,
        validation_rules: buildValidationRules(),
        description: formValues.description.trim() || undefined,
        active: formValues.is_active,
      });
      setSnackbar({ open: true, message: 'Custom attribute created', severity: 'success' });
      setFormOpen(false);
      setSelectedConfig(null);
      await loadConfigs();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to create custom attribute';
      setSnackbar({ open: true, message: msg, severity: 'error' });
      setFormErrors({ attr_name: msg });
    } finally {
      setSubmitting(false);
    }
  };

  const handleUpdate = async () => {
    if (!selectedConfig || !validateForm()) return;
    const duplicate = configs.some(
      (c) =>
        c.entity_type === formValues.entity_type &&
        c.attr_name === formValues.attr_name.trim() &&
        c.id !== selectedConfig.id
    );
    if (duplicate) {
      setSnackbar({
        open: true,
        severity: 'error',
        message: `Attribute "${formValues.attr_name}" already exists for entity type "${formValues.entity_type}".`,
      });
      return;
    }
    setSubmitting(true);
    try {
      await apiService.updateCustomAttributeConfig(selectedConfig.id, {
        entity_type: formValues.entity_type,
        attr_name: formValues.attr_name.trim(),
        data_type: formValues.data_type,
        validation_rules: buildValidationRules(),
        description: formValues.description.trim() || undefined,
        active: formValues.is_active,
      });
      setSnackbar({ open: true, message: 'Custom attribute updated', severity: 'success' });
      setFormOpen(false);
      setSelectedConfig(null);
      await loadConfigs();
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to update custom attribute';
      setSnackbar({ open: true, message: msg, severity: 'error' });
      setFormErrors({ attr_name: msg });
    } finally {
      setSubmitting(false);
    }
  };

  const handleFormSubmit = () => {
    if (selectedConfig) handleUpdate();
    else handleCreate();
  };

  const handleActivate = async (config: CustomAttributeConfig) => {
    try {
      await apiService.updateCustomAttributeConfig(config.id, { active: true });
      setSnackbar({ open: true, message: 'Attribute activated', severity: 'success' });
      await loadConfigs();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to activate',
        severity: 'error',
      });
    }
  };

  const handleDeactivate = async (config: CustomAttributeConfig) => {
    try {
      await apiService.updateCustomAttributeConfig(config.id, { active: false });
      setSnackbar({ open: true, message: 'Attribute deactivated', severity: 'success' });
      await loadConfigs();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to deactivate',
        severity: 'error',
      });
    }
  };

  const handleDeleteClick = (config: CustomAttributeConfig) => {
    setDeleteTarget(config);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteCustomAttributeConfig(deleteTarget.id);
      setSnackbar({ open: true, message: 'Custom attribute deleted', severity: 'success' });
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      await loadConfigs();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to delete',
        severity: 'error',
      });
      setDeleteDialogOpen(false);
    }
  };

  const columns: GridColDef[] = useMemo(
    () => [
      {
        field: 'entity_type',
        headerName: 'Entity Type',
        width: 140,
        renderCell: (params) => (
          <Chip label={params.value} size="small" color="primary" variant="outlined" />
        ),
      },
      { field: 'attr_name', headerName: 'Attr Name', flex: 1, minWidth: 140 },
      {
        field: 'data_type',
        headerName: 'Data Type',
        width: 110,
        renderCell: (params) => (
          <Chip label={params.value} size="small" color="secondary" variant="outlined" />
        ),
      },
      {
        field: 'validation_rules',
        headerName: 'Validation Rules',
        flex: 1,
        minWidth: 160,
        valueGetter: (value) => formatValidationRules(value as Record<string, unknown>),
        renderCell: (params) => (
          <Box
            sx={{
              maxWidth: 220,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              fontFamily: 'monospace',
              fontSize: '0.75rem',
            }}
            title={params.value}
          >
            {params.value}
          </Box>
        ),
      },
      {
        field: 'is_required',
        headerName: 'Is Required',
        width: 110,
        valueGetter: (_, row) => getIsRequired(row.validation_rules),
        renderCell: (params) => (
          <Chip
            label={params.value ? 'Yes' : 'No'}
            size="small"
            color={params.value ? 'warning' : 'default'}
            variant="outlined"
          />
        ),
      },
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
        field: 'actions',
        type: 'actions',
        headerName: 'Actions',
        width: 180,
        getActions: (params: GridRowParams) => {
          const config = params.row as CustomAttributeConfig;
          const actions = [];
          if (canEdit) {
            actions.push(
              <GridActionsCellItem
                key="edit"
                icon={<Edit />}
                label="Edit"
                onClick={() => openForm(config)}
              />,
              config.active ? (
                <GridActionsCellItem
                  key="deactivate"
                  icon={<Cancel />}
                  label="Deactivate"
                  onClick={() => handleDeactivate(config)}
                />
              ) : (
                <GridActionsCellItem
                  key="activate"
                  icon={<CheckCircle />}
                  label="Activate"
                  onClick={() => handleActivate(config)}
                />
              )
            );
            actions.push(
              <GridActionsCellItem
                key="delete"
                icon={<Delete />}
                label="Delete"
                onClick={() => handleDeleteClick(config)}
              />
            );
          }
          return actions;
        },
      },
    ],
    [canEdit, configs]
  );

  if (!isAdmin) {
    return (
      <Box>
        <Alert severity="warning">
          You do not have permission to view custom attribute configs. Admin access is required.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4">Custom Attributes (Config)</Typography>
        {canEdit && (
          <Button variant="contained" startIcon={<Add />} onClick={() => openForm(null)}>
            Create Attribute
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
            rows={configs}
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
                  <Typography>No custom attribute configs found</Typography>
                </Box>
              ),
            }}
          />
        </Box>
      )}

      {/* Create/Edit Modal */}
      <Dialog open={formOpen} onClose={() => setFormOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {selectedConfig ? 'Edit Custom Attribute' : 'Create Custom Attribute'}
        </DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="normal" required error={!!formErrors.entity_type}>
            <InputLabel>Entity Type</InputLabel>
            <Select
              value={formValues.entity_type}
              label="Entity Type"
              onChange={(e) => setFormValues((v) => ({ ...v, entity_type: e.target.value }))}
              disabled={!!selectedConfig}
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
            label="Attribute Name"
            value={formValues.attr_name}
            onChange={(e) => setFormValues((v) => ({ ...v, attr_name: e.target.value }))}
            error={!!formErrors.attr_name}
            helperText={formErrors.attr_name || 'Letters, numbers, underscores, hyphens only'}
            placeholder="e.g. ph_level"
          />

          <FormControl fullWidth margin="normal" required error={!!formErrors.data_type}>
            <InputLabel>Data Type</InputLabel>
            <Select
              value={formValues.data_type}
              label="Data Type"
              onChange={(e) =>
                setFormValues((v) => ({ ...v, data_type: e.target.value as CustomAttributeConfig['data_type'] }))
              }
            >
              {DATA_TYPES.map((type) => (
                <MenuItem key={type} value={type}>
                  {type}
                </MenuItem>
              ))}
            </Select>
            {formErrors.data_type && (
              <Typography variant="caption" color="error" sx={{ mt: 0.5 }}>
                {formErrors.data_type}
              </Typography>
            )}
          </FormControl>

          <TextField
            fullWidth
            margin="normal"
            label="Validation Rules (JSON)"
            value={formValues.validation_rules}
            onChange={(e) => setFormValues((v) => ({ ...v, validation_rules: e.target.value }))}
            error={!!formErrors.validation_rules}
            helperText={
              formErrors.validation_rules ||
              'e.g. {"min": 0, "max": 14} or {"options": ["A","B"]} for select'
            }
            multiline
            rows={5}
            placeholder='{"min": 0, "max": 100}'
            sx={{ fontFamily: 'monospace' }}
          />

          <TextField
            fullWidth
            margin="normal"
            label="Description"
            value={formValues.description}
            onChange={(e) => setFormValues((v) => ({ ...v, description: e.target.value }))}
            multiline
            rows={2}
            placeholder="Optional"
          />

          <FormControlLabel
            control={
              <Checkbox
                checked={formValues.is_required}
                onChange={(e) => setFormValues((v) => ({ ...v, is_required: e.target.checked }))}
                color="primary"
              />
            }
            label="Is Required"
            sx={{ mt: 1 }}
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={formValues.is_active}
                onChange={(e) => setFormValues((v) => ({ ...v, is_active: e.target.checked }))}
                color="primary"
              />
            }
            label="Is Active"
            sx={{ mt: 0.5, display: 'block' }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFormOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button variant="contained" onClick={handleFormSubmit} disabled={submitting}>
            {submitting ? 'Saving...' : selectedConfig ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Delete custom attribute <strong>{deleteTarget?.attr_name}</strong> for entity type{' '}
            <strong>{deleteTarget?.entity_type}</strong>? This cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button color="error" variant="contained" onClick={handleDeleteConfirm}>
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

export default CustomAttributesAdmin;
