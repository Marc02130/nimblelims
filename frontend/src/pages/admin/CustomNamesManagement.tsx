import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  TextField,
  InputAdornment,
  IconButton,
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
  useMediaQuery,
  useTheme,
  FormControlLabel,
  Switch,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Search,
  Clear,
} from '@mui/icons-material';
import Tooltip from '@mui/material/Tooltip';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';

interface NameTemplate {
  id: string;
  entity_type: string;
  template: string;
  description?: string;
  active: boolean;
  created_at: string;
  modified_at: string;
  created_by?: string;
  modified_by?: string;
}

const ENTITY_TYPES = ['sample', 'project', 'batch', 'analysis', 'container'];
const VALID_PLACEHOLDERS = ['{SEQ}', '{YYYY}', '{MM}', '{DD}', '{YYYYMMDD}', '{CLIENT}'];

const validationSchema = Yup.object({
  entity_type: Yup.string()
    .required('Entity type is required')
    .oneOf(ENTITY_TYPES, 'Invalid entity type'),
  template: Yup.string()
    .required('Template is required')
    .min(1, 'Template must be at least 1 character')
    .max(500, 'Template must be less than 500 characters')
    .test(
      'contains-seq',
      'Template must include {SEQ} placeholder for uniqueness',
      (value) => {
        if (!value) return false;
        return value.includes('{SEQ}');
      }
    )
    .test(
      'valid-placeholders',
      'Template contains invalid placeholders. Valid placeholders: {SEQ}, {YYYY}, {MM}, {DD}, {YYYYMMDD}, {CLIENT}',
      (value) => {
        if (!value) return true;
        const matches = value.match(/\{[^}]+\}/g);
        if (!matches) return true;
        return matches.every((match) => VALID_PLACEHOLDERS.includes(match));
      }
    ),
  description: Yup.string().max(1000, 'Description must be less than 1000 characters'),
  active: Yup.boolean(),
});

const CustomNamesManagement: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const { user, hasPermission } = useUser();
  const [templates, setTemplates] = useState<NameTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('');
  const [formOpen, setFormOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<NameTemplate | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<NameTemplate | null>(null);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);

  const canEdit = hasPermission('config:edit');

  useEffect(() => {
    loadTemplates();
  }, [page, pageSize, entityTypeFilter]);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      const filters: { entity_type?: string; page?: number; size?: number } = {
        page: page + 1,
        size: pageSize,
      };
      if (entityTypeFilter) {
        filters.entity_type = entityTypeFilter;
      }
      const response = await apiService.getNameTemplates(filters);
      setTemplates(response.templates || []);
      setTotal(response.total || 0);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view name templates management');
      } else {
        setError(err.response?.data?.detail || 'Failed to load name templates');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredTemplates = useMemo(() => {
    if (!searchTerm) return templates;
    const term = searchTerm.toLowerCase();
    return templates.filter(
      (template) =>
        template.template.toLowerCase().includes(term) ||
        template.description?.toLowerCase().includes(term) ||
        template.entity_type.toLowerCase().includes(term)
    );
  }, [templates, searchTerm]);

  const handleCreate = async (data: {
    entity_type?: string;
    template?: string;
    description?: string;
    active?: boolean;
  }) => {
    if (!data.entity_type || !data.template) {
      throw new Error('Missing required fields: entity_type and template are required');
    }
    await apiService.createNameTemplate({
      entity_type: data.entity_type,
      template: data.template,
      description: data.description,
      active: data.active ?? true,
    });
    await loadTemplates();
  };

  const handleUpdate = async (data: {
    entity_type?: string;
    template?: string;
    description?: string;
    active?: boolean;
  }) => {
    if (!selectedTemplate) return;
    await apiService.updateNameTemplate(selectedTemplate.id, data);
    await loadTemplates();
    setSelectedTemplate(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteNameTemplate(deleteTarget.id);
      await loadTemplates();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete name template');
      setDeleteDialogOpen(false);
    }
  };

  const columns: GridColDef[] = [
    {
      field: 'entity_type',
      headerName: 'Entity Type',
      width: 150,
      flex: isMobile ? 0 : 1,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color="primary"
          variant="outlined"
        />
      ),
    },
    {
      field: 'template',
      headerName: 'Template',
      width: 300,
      flex: isMobile ? 0 : 2,
    },
    {
      field: 'description',
      headerName: 'Description',
      width: 250,
      flex: isMobile ? 0 : 2,
      valueGetter: (value) => value || 'N/A',
    },
    {
      field: 'active',
      headerName: 'Status',
      width: 100,
      flex: isMobile ? 0 : 0.5,
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
      width: 120,
      getActions: (params: GridRowParams) => {
        const template = params.row as NameTemplate;
        const actions = [];

        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedTemplate(template);
                setFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget(template);
                setDeleteDialogOpen(true);
              }}
            />
          );
        }

        return actions;
      },
    },
  ];

  if (!canEdit) {
    return (
      <Box>
        <Alert severity="warning">
          You do not have permission to view name templates management.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 3,
          flexDirection: isMobile ? 'column' : 'row',
          gap: 2,
        }}
      >
        <Typography variant="h4">Custom Names Management</Typography>
        {canEdit && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setSelectedTemplate(null);
              setFormOpen(true);
            }}
          >
            Create Template
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box
        sx={{
          mb: 2,
          display: 'flex',
          gap: 2,
          flexDirection: isMobile ? 'column' : 'row',
        }}
      >
        <TextField
          fullWidth={isMobile}
          sx={{ flex: isMobile ? 1 : 2 }}
          placeholder="Search by template or description..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
            endAdornment: searchTerm && (
              <InputAdornment position="end">
                <IconButton size="small" onClick={() => setSearchTerm('')}>
                  <Clear />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
        <FormControl sx={{ minWidth: isMobile ? '100%' : 200 }}>
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
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <CircularProgress />
        </Box>
      ) : (
        <Box sx={{ height: 600, width: '100%', mb: 2 }}>
          <DataGrid
            rows={filteredTemplates}
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
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    height: '100%',
                  }}
                >
                  <Typography>No name templates found</Typography>
                </Box>
              ),
            }}
          />
        </Box>
      )}

      {/* Template Form Dialog */}
      <Dialog open={formOpen} onClose={() => setFormOpen(false)} maxWidth="md" fullWidth>
        <Formik
          initialValues={{
            entity_type: selectedTemplate?.entity_type || '',
            template: selectedTemplate?.template || '',
            description: selectedTemplate?.description || '',
            active: selectedTemplate?.active !== undefined ? selectedTemplate.active : true,
          }}
          validationSchema={validationSchema}
          onSubmit={async (values, { setSubmitting, setFieldError }) => {
            try {
              if (selectedTemplate) {
                await handleUpdate(values);
              } else {
                await handleCreate(values);
              }
              setFormOpen(false);
              setSelectedTemplate(null);
            } catch (err: any) {
              const errorMsg = err.response?.data?.detail || err.message || 'Failed to save template';
              setFieldError('template', errorMsg);
            } finally {
              setSubmitting(false);
            }
          }}
          enableReinitialize
        >
          {({ values, errors, touched, isValid, isSubmitting, setFieldValue }) => (
            <Form>
              <DialogTitle>
                {selectedTemplate ? 'Edit Name Template' : 'Create Name Template'}
              </DialogTitle>
              <DialogContent>
                <Box sx={{ pt: 2 }}>
                  <FormControl fullWidth margin="normal" required>
                    <InputLabel>Entity Type</InputLabel>
                    <Select
                      value={values.entity_type}
                      label="Entity Type"
                      onChange={(e) => setFieldValue('entity_type', e.target.value)}
                      error={touched.entity_type && !!errors.entity_type}
                      disabled={!!selectedTemplate}
                    >
                      {ENTITY_TYPES.map((type) => (
                        <MenuItem key={type} value={type}>
                          {type}
                        </MenuItem>
                      ))}
                    </Select>
                    {touched.entity_type && errors.entity_type && (
                      <Typography variant="caption" color="error" sx={{ mt: 0.5 }}>
                        {errors.entity_type}
                      </Typography>
                    )}
                  </FormControl>

                  <TextField
                    fullWidth
                    margin="normal"
                    required
                    label="Template"
                    name="template"
                    value={values.template}
                    onChange={(e) => setFieldValue('template', e.target.value)}
                    error={touched.template && !!errors.template}
                    helperText={
                      touched.template && errors.template
                        ? errors.template
                        : 'Use placeholders: {SEQ}, {YYYY}, {MM}, {DD}, {YYYYMMDD}, {CLIENT}. Example: SAMPLE-{YYYY}-{SEQ}'
                    }
                    placeholder="SAMPLE-{YYYY}-{SEQ}"
                  />

                  <Box
                    sx={{
                      mt: 1,
                      p: 1.5,
                      bgcolor: 'info.light',
                      borderRadius: 1,
                      border: '1px solid',
                      borderColor: 'info.main',
                    }}
                  >
                    <Typography variant="caption" component="div" sx={{ whiteSpace: 'pre-line' }}>
                      <strong>Available Placeholders:</strong>
                      <br />
                      • {'{SEQ}'} - Auto-incrementing sequence (required for uniqueness)
                      <br />
                      • {'{YYYY}'} - 4-digit year
                      <br />
                      • {'{MM}'} - 2-digit month
                      <br />
                      • {'{DD}'} - 2-digit day
                      <br />
                      • {'{YYYYMMDD}'} - Date in YYYYMMDD format
                      <br />
                      • {'{CLIENT}'} - Client name/code (from linked client)
                    </Typography>
                  </Box>

                  <TextField
                    fullWidth
                    margin="normal"
                    label="Description"
                    name="description"
                    value={values.description}
                    onChange={(e) => setFieldValue('description', e.target.value)}
                    error={touched.description && !!errors.description}
                    helperText={touched.description && errors.description ? errors.description : 'Optional description'}
                    multiline
                    rows={3}
                  />

                  <FormControlLabel
                    control={
                      <Switch
                        checked={values.active}
                        onChange={(e) => setFieldValue('active', e.target.checked)}
                        color="primary"
                      />
                    }
                    label="Active"
                    sx={{ mt: 2 }}
                  />
                </Box>
              </DialogContent>
              <DialogActions>
                <Button onClick={() => setFormOpen(false)} disabled={isSubmitting}>
                  Cancel
                </Button>
                <Button type="submit" variant="contained" disabled={isSubmitting || !isValid}>
                  {isSubmitting ? 'Saving...' : selectedTemplate ? 'Update' : 'Create'}
                </Button>
              </DialogActions>
            </Form>
          )}
        </Formik>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete the name template for entity type{' '}
            <strong>{deleteTarget?.entity_type}</strong>?
            <Box component="span" sx={{ display: 'block', mt: 1, color: 'warning.main' }}>
              This will set the template to inactive. Existing entities will not be affected, but new entities
              will not be able to use this template.
            </Box>
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CustomNamesManagement;

