import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Alert,
  CircularProgress,
  TextField,
  InputAdornment,
  IconButton,
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormControlLabel,
  Switch,
  Chip,
  Snackbar,
  Tooltip,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Autocomplete,
} from '@mui/material';
import {
  Add,
  Edit,
  Search,
  Clear,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridToolbar } from '@mui/x-data-grid';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { useUser } from '../contexts/UserContext';
import { apiService } from '../services/apiService';
import CustomAttributeField from '../components/common/CustomAttributeField';

interface Unit {
  id: string;
  name: string;
  description?: string;
}

interface Analyte {
  id: string;
  name: string;
  description?: string;
  cas_number?: string;
  units_default?: string;
  data_type?: string;
  active: boolean;
  created_at: string;
  modified_at: string;
  custom_attributes?: Record<string, any>;
}

interface CustomAttributeConfig {
  id: string;
  entity_type: string;
  attr_name: string;
  data_type: 'text' | 'number' | 'date' | 'boolean' | 'select';
  validation_rules: Record<string, any>;
  description?: string;
  active: boolean;
}

interface FormValues {
  name: string;
  cas_number: string;
  units_default: string | null;
  data_type: string;
  description: string;
  active: boolean;
  custom_attributes: Record<string, any>;
}

const DATA_TYPE_OPTIONS = [
  { value: 'numeric', label: 'Numeric' },
  { value: 'text', label: 'Text' },
  { value: 'date', label: 'Date' },
  { value: 'boolean', label: 'Boolean' },
];

const validationSchema = Yup.object({
  name: Yup.string()
    .required('Name is required')
    .min(1, 'Name is required')
    .max(255, 'Name must be less than 255 characters'),
  cas_number: Yup.string()
    .max(50, 'CAS number must be less than 50 characters')
    .nullable(),
  units_default: Yup.string().nullable(),
  data_type: Yup.string()
    .oneOf(['numeric', 'text', 'date', 'boolean', ''], 'Invalid data type')
    .nullable(),
  description: Yup.string().max(1000, 'Description must be less than 1000 characters'),
  active: Yup.boolean(),
});

const AnalytesManagement: React.FC = () => {
  const { hasPermission } = useUser();
  const [analytes, setAnalytes] = useState<Analyte[]>([]);
  const [units, setUnits] = useState<Unit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedAnalyte, setSelectedAnalyte] = useState<Analyte | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });
  const [customAttributeConfigs, setCustomAttributeConfigs] = useState<CustomAttributeConfig[]>([]);
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 25 });
  const [totalRows, setTotalRows] = useState(0);

  const canManage = hasPermission('analysis:manage');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Load analytes with pagination and search
      const [analytesResponse, unitsData] = await Promise.all([
        apiService.getAnalytes({
          search: searchTerm || undefined,
          page: paginationModel.page + 1,
          size: paginationModel.pageSize,
        }),
        apiService.getUnits(),
      ]);

      // Handle paginated response
      if (analytesResponse.analytes) {
        setAnalytes(analytesResponse.analytes);
        setTotalRows(analytesResponse.total || analytesResponse.analytes.length);
      } else if (Array.isArray(analytesResponse)) {
        setAnalytes(analytesResponse);
        setTotalRows(analytesResponse.length);
      } else {
        setAnalytes([]);
        setTotalRows(0);
      }

      // Set units for autocomplete
      setUnits(unitsData || []);

      // Load custom attribute configs for analytes
      try {
        const configsResponse = await apiService.getCustomAttributeConfigs({ entity_type: 'analytes', active: true });
        const configs = configsResponse.configs || configsResponse || [];
        setCustomAttributeConfigs(configs);
      } catch {
        // Custom attributes may not be configured
        setCustomAttributeConfigs([]);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load analytes');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, paginationModel]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      setPaginationModel(prev => ({ ...prev, page: 0 }));
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const handleOpenCreate = () => {
    setSelectedAnalyte(null);
    setDialogOpen(true);
  };

  const handleOpenEdit = async (analyteId: string) => {
    try {
      const analyte = await apiService.getAnalyte(analyteId);
      setSelectedAnalyte(analyte);
      setDialogOpen(true);
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to load analyte',
        severity: 'error',
      });
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSelectedAnalyte(null);
  };

  const handleSubmit = async (values: FormValues) => {
    setSubmitting(true);
    try {
      const payload = {
        name: values.name,
        cas_number: values.cas_number || undefined,
        units_default: values.units_default || undefined,
        data_type: values.data_type || undefined,
        description: values.description || undefined,
        active: values.active,
        custom_attributes: values.custom_attributes,
      };

      if (selectedAnalyte) {
        await apiService.updateAnalyte(selectedAnalyte.id, payload);
        setSnackbar({
          open: true,
          message: 'Analyte updated successfully',
          severity: 'success',
        });
      } else {
        await apiService.createAnalyte(payload);
        setSnackbar({
          open: true,
          message: 'Analyte created successfully',
          severity: 'success',
        });
      }

      handleCloseDialog();
      loadData();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to save analyte',
        severity: 'error',
      });
    } finally {
      setSubmitting(false);
    }
  };

  const getUnitName = (unitId?: string): string => {
    if (!unitId) return 'N/A';
    const unit = units.find(u => u.id === unitId);
    return unit?.name || 'Unknown';
  };

  const getDataTypeChip = (dataType?: string) => {
    if (!dataType) return <Chip label="N/A" size="small" variant="outlined" />;
    
    const colorMap: Record<string, 'primary' | 'secondary' | 'success' | 'info'> = {
      numeric: 'primary',
      text: 'secondary',
      date: 'success',
      boolean: 'info',
    };
    
    const labelMap: Record<string, string> = {
      numeric: 'Numeric',
      text: 'Text',
      date: 'Date',
      boolean: 'Boolean',
    };
    
    return (
      <Chip
        label={labelMap[dataType] || dataType}
        color={colorMap[dataType] || 'default'}
        size="small"
      />
    );
  };

  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Name',
      width: 200,
      flex: 1,
    },
    {
      field: 'cas_number',
      headerName: 'CAS Number',
      width: 130,
      valueGetter: (value) => value || 'N/A',
    },
    {
      field: 'units_default',
      headerName: 'Default Units',
      width: 130,
      valueGetter: (value) => getUnitName(value),
    },
    {
      field: 'data_type',
      headerName: 'Data Type',
      width: 120,
      renderCell: (params) => getDataTypeChip(params.value),
    },
    {
      field: 'active',
      headerName: 'Status',
      width: 100,
      renderCell: (params) => (
        <Chip
          label={params.value ? 'Active' : 'Inactive'}
          color={params.value ? 'success' : 'default'}
          size="small"
        />
      ),
    },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 120,
      valueGetter: (value) => value ? new Date(value).toLocaleDateString() : '',
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 80,
      getActions: (params) => {
        if (!canManage) return [];
        return [
          <GridActionsCellItem
            icon={
              <Tooltip title="Edit analyte">
                <Edit />
              </Tooltip>
            }
            label="Edit"
            onClick={() => handleOpenEdit(params.id as string)}
            aria-label={`Edit analyte ${params.row.name}`}
          />,
        ];
      },
    },
  ];

  const getInitialValues = (): FormValues => {
    if (selectedAnalyte) {
      return {
        name: selectedAnalyte.name || '',
        cas_number: selectedAnalyte.cas_number || '',
        units_default: selectedAnalyte.units_default || null,
        data_type: selectedAnalyte.data_type || '',
        description: selectedAnalyte.description || '',
        active: selectedAnalyte.active ?? true,
        custom_attributes: selectedAnalyte.custom_attributes || {},
      };
    }
    return {
      name: '',
      cas_number: '',
      units_default: null,
      data_type: '',
      description: '',
      active: true,
      custom_attributes: {},
    };
  };

  if (loading && analytes.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, position: 'relative' }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Analytes</Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {!canManage && (
        <Alert severity="info" sx={{ mb: 2 }}>
          You have read-only access. Contact your administrator for management permissions.
        </Alert>
      )}

      {/* Search */}
      <Box sx={{ mb: 2 }}>
        <TextField
          fullWidth
          placeholder="Search by name or CAS number..."
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
      </Box>

      <Card>
        <CardContent>
          <DataGrid
            rows={analytes}
            columns={columns}
            rowCount={totalRows}
            loading={loading}
            paginationMode="server"
            paginationModel={paginationModel}
            onPaginationModelChange={setPaginationModel}
            pageSizeOptions={[10, 25, 50, 100]}
            sx={{ height: 600 }}
            disableRowSelectionOnClick
            slots={{
              toolbar: GridToolbar,
            }}
            slotProps={{
              toolbar: {
                showQuickFilter: false,
                printOptions: { disableToolbarButton: true },
              },
            }}
          />
        </CardContent>
      </Card>

      {/* FAB for Create */}
      {canManage && (
        <Fab
          color="primary"
          aria-label="Create analyte"
          onClick={handleOpenCreate}
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
          }}
        >
          <Add />
        </Fab>
      )}

      {/* Create/Edit Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={handleCloseDialog}
        maxWidth="md"
        fullWidth
        aria-labelledby="analyte-form-dialog-title"
      >
        <Formik
          initialValues={getInitialValues()}
          validationSchema={validationSchema}
          onSubmit={handleSubmit}
          enableReinitialize
        >
          {({ values, errors, touched, setFieldValue, isValid, dirty }) => (
            <Form>
              <DialogTitle id="analyte-form-dialog-title">
                {selectedAnalyte ? `Edit Analyte: ${selectedAnalyte.name}` : 'Create New Analyte'}
              </DialogTitle>
              <DialogContent>
                <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <Field name="name">
                    {({ field, meta }: any) => (
                      <TextField
                        {...field}
                        label="Name"
                        fullWidth
                        required
                        error={meta.touched && !!meta.error}
                        helperText={meta.touched && meta.error ? meta.error : 'Unique name for this analyte'}
                      />
                    )}
                  </Field>

                  <Field name="cas_number">
                    {({ field, meta }: any) => (
                      <TextField
                        {...field}
                        label="CAS Number"
                        fullWidth
                        error={meta.touched && !!meta.error}
                        helperText={meta.touched && meta.error ? meta.error : 'Chemical Abstracts Service registry number'}
                      />
                    )}
                  </Field>

                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Autocomplete
                      options={units}
                      getOptionLabel={(option) => option.name}
                      value={units.find(u => u.id === values.units_default) || null}
                      onChange={(_, newValue) => {
                        setFieldValue('units_default', newValue?.id || null);
                      }}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Default Units"
                          helperText="Default measurement unit for this analyte"
                        />
                      )}
                      sx={{ flex: 1 }}
                      isOptionEqualToValue={(option, value) => option.id === value.id}
                    />

                    <FormControl sx={{ flex: 1 }}>
                      <InputLabel>Data Type</InputLabel>
                      <Select
                        value={values.data_type}
                        onChange={(e) => setFieldValue('data_type', e.target.value)}
                        label="Data Type"
                      >
                        <MenuItem value="">None</MenuItem>
                        {DATA_TYPE_OPTIONS.map((option) => (
                          <MenuItem key={option.value} value={option.value}>
                            {option.label}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Box>

                  <Field name="description">
                    {({ field, meta }: any) => (
                      <TextField
                        {...field}
                        label="Description"
                        fullWidth
                        multiline
                        rows={3}
                        error={meta.touched && !!meta.error}
                        helperText={meta.touched && meta.error ? meta.error : 'Optional description'}
                      />
                    )}
                  </Field>

                  <FormControlLabel
                    control={
                      <Switch
                        checked={values.active}
                        onChange={(e) => setFieldValue('active', e.target.checked)}
                      />
                    }
                    label="Active"
                  />

                  {/* Custom Attributes */}
                  {customAttributeConfigs.length > 0 && (
                    <>
                      <Divider sx={{ my: 2 }} />
                      <Typography variant="h6" gutterBottom>
                        Custom Attributes
                      </Typography>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        {customAttributeConfigs.map((config) => (
                          <CustomAttributeField
                            key={config.id}
                            config={config}
                            value={values.custom_attributes[config.attr_name]}
                            onChange={(value) => {
                              setFieldValue('custom_attributes', {
                                ...values.custom_attributes,
                                [config.attr_name]: value,
                              });
                            }}
                          />
                        ))}
                      </Box>
                    </>
                  )}
                </Box>
              </DialogContent>
              <DialogActions>
                <Button onClick={handleCloseDialog} disabled={submitting}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="contained"
                  disabled={submitting || !isValid || (!selectedAnalyte && !dirty)}
                >
                  {submitting ? 'Saving...' : selectedAnalyte ? 'Update' : 'Create'}
                </Button>
              </DialogActions>
            </Form>
          )}
        </Formik>
      </Dialog>

      {/* Snackbar for feedback */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbar(prev => ({ ...prev, open: false }))}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default AnalytesManagement;
