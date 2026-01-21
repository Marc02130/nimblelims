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
  Collapse,
  Paper,
  Autocomplete,
  Skeleton,
} from '@mui/material';
import {
  Add,
  Edit,
  Search,
  Clear,
  ExpandMore,
  ExpandLess,
  Delete,
  Link as LinkIcon,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridToolbar } from '@mui/x-data-grid';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { useUser } from '../contexts/UserContext';
import { apiService } from '../services/apiService';
import CustomAttributeField from '../components/common/CustomAttributeField';

interface Analyte {
  id: string;
  name: string;
  description?: string;
  cas_number?: string;
  data_type?: string;
}

interface Analysis {
  id: string;
  name: string;
  description?: string;
  method?: string;
  turnaround_time?: number;
  cost?: number | string;
  active: boolean;
  created_at: string;
  modified_at: string;
  custom_attributes?: Record<string, any>;
  analytes?: Analyte[];
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
  method: string;
  turnaround_time: number | null;
  cost: number | null;
  description: string;
  active: boolean;
  custom_attributes: Record<string, any>;
}

// Track expanded rows and their analytes
interface ExpandedRowData {
  loading: boolean;
  analytes: Analyte[];
  error?: string;
}

const validationSchema = Yup.object({
  name: Yup.string()
    .required('Name is required')
    .min(1, 'Name is required')
    .max(255, 'Name must be less than 255 characters'),
  method: Yup.string()
    .required('Method is required')
    .min(1, 'Method is required')
    .max(255, 'Method must be less than 255 characters'),
  turnaround_time: Yup.number()
    .nullable()
    .min(0, 'Turnaround time must be 0 or greater')
    .integer('Turnaround time must be a whole number'),
  cost: Yup.number()
    .nullable()
    .min(0, 'Cost must be 0 or greater'),
  description: Yup.string().max(1000, 'Description must be less than 1000 characters'),
  active: Yup.boolean(),
});

const AnalysesManagement: React.FC = () => {
  const { hasPermission } = useUser();
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });
  const [customAttributeConfigs, setCustomAttributeConfigs] = useState<CustomAttributeConfig[]>([]);
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 25 });
  const [totalRows, setTotalRows] = useState(0);

  // Expanded rows state - tracks which rows are expanded and their data
  const [expandedRows, setExpandedRows] = useState<Record<string, ExpandedRowData>>({});

  // All analytes for autocomplete (loaded when adding)
  const [allAnalytes, setAllAnalytes] = useState<Analyte[]>([]);
  const [analyteSearchTerm, setAnalyteSearchTerm] = useState('');
  const [selectedAnalytesToAdd, setSelectedAnalytesToAdd] = useState<Analyte[]>([]);
  const [addingAnalytes, setAddingAnalytes] = useState<string | null>(null); // analysis ID currently adding to

  const canManage = hasPermission('analysis:manage');

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Load analyses with pagination and search
      const response = await apiService.getAnalyses({
        search: searchTerm || undefined,
        page: paginationModel.page + 1,
        size: paginationModel.pageSize,
      });

      // Handle paginated response
      if (response.analyses) {
        setAnalyses(response.analyses);
        setTotalRows(response.total || response.analyses.length);
      } else if (Array.isArray(response)) {
        setAnalyses(response);
        setTotalRows(response.length);
      } else {
        setAnalyses([]);
        setTotalRows(0);
      }

      // Load custom attribute configs for analyses
      try {
        const configsResponse = await apiService.getCustomAttributeConfigs({ entity_type: 'analyses', active: true });
        const configs = configsResponse.configs || configsResponse || [];
        setCustomAttributeConfigs(configs);
      } catch {
        // Custom attributes may not be configured
        setCustomAttributeConfigs([]);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load analyses');
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

  // Load analytes for a specific analysis when expanded
  const loadAnalytesForAnalysis = useCallback(async (analysisId: string) => {
    setExpandedRows(prev => ({
      ...prev,
      [analysisId]: { loading: true, analytes: [] },
    }));

    try {
      const analytes = await apiService.getAnalysisAnalytes(analysisId);
      setExpandedRows(prev => ({
        ...prev,
        [analysisId]: { loading: false, analytes: analytes || [] },
      }));
    } catch (err: any) {
      setExpandedRows(prev => ({
        ...prev,
        [analysisId]: { loading: false, analytes: [], error: 'Failed to load analytes' },
      }));
    }
  }, []);

  // Toggle row expansion
  const handleToggleExpand = (analysisId: string) => {
    if (expandedRows[analysisId]) {
      // Collapse - remove from expanded rows
      setExpandedRows(prev => {
        const newState = { ...prev };
        delete newState[analysisId];
        return newState;
      });
    } else {
      // Expand - load analytes
      loadAnalytesForAnalysis(analysisId);
    }
  };

  // Load all analytes for autocomplete
  const loadAllAnalytes = useCallback(async (search?: string) => {
    try {
      const response = await apiService.getAnalytes({
        search: search || undefined,
        active: true,
        size: 100,
      });
      const analytes = response.analytes || response || [];
      setAllAnalytes(analytes);
    } catch (err: any) {
      console.error('Failed to load analytes:', err);
      setAllAnalytes([]);
    }
  }, []);

  // Debounce analyte search for autocomplete
  useEffect(() => {
    if (addingAnalytes === null) return;
    const timer = setTimeout(() => {
      loadAllAnalytes(analyteSearchTerm);
    }, 300);
    return () => clearTimeout(timer);
  }, [analyteSearchTerm, addingAnalytes, loadAllAnalytes]);

  const handleOpenCreate = () => {
    setSelectedAnalysis(null);
    setDialogOpen(true);
  };

  const handleOpenEdit = async (analysisId: string) => {
    try {
      const analysis = await apiService.getAnalysis(analysisId);
      setSelectedAnalysis(analysis);
      setDialogOpen(true);
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to load analysis',
        severity: 'error',
      });
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setSelectedAnalysis(null);
  };

  const handleSubmit = async (values: FormValues) => {
    setSubmitting(true);
    try {
      const payload = {
        name: values.name,
        method: values.method,
        turnaround_time: values.turnaround_time,
        cost: values.cost,
        description: values.description || undefined,
        active: values.active,
        custom_attributes: values.custom_attributes,
      };

      if (selectedAnalysis) {
        await apiService.updateAnalysis(selectedAnalysis.id, payload);
        setSnackbar({
          open: true,
          message: 'Analysis updated successfully',
          severity: 'success',
        });
      } else {
        await apiService.createAnalysis(payload);
        setSnackbar({
          open: true,
          message: 'Analysis created successfully',
          severity: 'success',
        });
      }

      handleCloseDialog();
      loadData();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to save analysis',
        severity: 'error',
      });
    } finally {
      setSubmitting(false);
    }
  };

  // Start adding analytes to an analysis
  const handleStartAddAnalytes = (analysisId: string) => {
    setAddingAnalytes(analysisId);
    setSelectedAnalytesToAdd([]);
    loadAllAnalytes();
  };

  // Cancel adding analytes
  const handleCancelAddAnalytes = () => {
    setAddingAnalytes(null);
    setSelectedAnalytesToAdd([]);
    setAnalyteSearchTerm('');
  };

  // Confirm adding analytes
  const handleConfirmAddAnalytes = async () => {
    if (!addingAnalytes || selectedAnalytesToAdd.length === 0) return;

    try {
      await apiService.linkAnalytesToAnalysis(
        addingAnalytes,
        selectedAnalytesToAdd.map(a => a.id)
      );
      setSnackbar({
        open: true,
        message: `${selectedAnalytesToAdd.length} analyte(s) linked successfully`,
        severity: 'success',
      });
      // Reload analytes for this row
      loadAnalytesForAnalysis(addingAnalytes);
      handleCancelAddAnalytes();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to link analytes',
        severity: 'error',
      });
    }
  };

  // Remove an analyte from an analysis
  const handleRemoveAnalyte = async (analysisId: string, analyteId: string) => {
    try {
      await apiService.unlinkAnalyteFromAnalysis(analysisId, analyteId);
      // Update local state
      setExpandedRows(prev => ({
        ...prev,
        [analysisId]: {
          ...prev[analysisId],
          analytes: prev[analysisId].analytes.filter(a => a.id !== analyteId),
        },
      }));
      setSnackbar({
        open: true,
        message: 'Analyte unlinked successfully',
        severity: 'success',
      });
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to unlink analyte',
        severity: 'error',
      });
    }
  };

  const formatCurrency = (value?: number | string) => {
    if (value === null || value === undefined) return 'N/A';
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(numValue)) return 'N/A';
    return `$${numValue.toFixed(2)}`;
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
      field: 'expand',
      headerName: '',
      width: 50,
      sortable: false,
      filterable: false,
      disableColumnMenu: true,
      renderCell: (params) => {
        const isExpanded = !!expandedRows[params.id as string];
        return (
          <IconButton
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              handleToggleExpand(params.id as string);
            }}
            aria-label={isExpanded ? 'Collapse analytes' : 'Expand analytes'}
          >
            {isExpanded ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
        );
      },
    },
    {
      field: 'name',
      headerName: 'Name',
      width: 200,
      flex: 1,
    },
    {
      field: 'method',
      headerName: 'Method',
      width: 150,
      flex: 1,
    },
    {
      field: 'turnaround_time',
      headerName: 'Turnaround (days)',
      width: 140,
      valueGetter: (value) => value ?? 'N/A',
    },
    {
      field: 'cost',
      headerName: 'Cost',
      width: 100,
      valueGetter: (value, row) => formatCurrency(row.cost),
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
              <Tooltip title="Edit analysis">
                <Edit />
              </Tooltip>
            }
            label="Edit"
            onClick={() => handleOpenEdit(params.id as string)}
            aria-label={`Edit analysis ${params.row.name}`}
          />,
        ];
      },
    },
  ];

  const getInitialValues = (): FormValues => {
    if (selectedAnalysis) {
      return {
        name: selectedAnalysis.name || '',
        method: selectedAnalysis.method || '',
        turnaround_time: selectedAnalysis.turnaround_time ?? null,
        cost: selectedAnalysis.cost !== undefined && selectedAnalysis.cost !== null
          ? (typeof selectedAnalysis.cost === 'string' ? parseFloat(selectedAnalysis.cost) : selectedAnalysis.cost)
          : null,
        description: selectedAnalysis.description || '',
        active: selectedAnalysis.active ?? true,
        custom_attributes: selectedAnalysis.custom_attributes || {},
      };
    }
    return {
      name: '',
      method: '',
      turnaround_time: null,
      cost: null,
      description: '',
      active: true,
      custom_attributes: {},
    };
  };

  // Render the expanded detail panel for an analysis
  const renderDetailPanel = (analysisId: string) => {
    const data = expandedRows[analysisId];
    if (!data) return null;

    const currentlyAddingToThis = addingAnalytes === analysisId;
    const linkedAnalyteIds = new Set(data.analytes.map(a => a.id));
    const availableAnalytes = allAnalytes.filter(a => !linkedAnalyteIds.has(a.id));

    return (
      <Collapse in={true} timeout="auto" unmountOnExit>
        <Paper
          sx={{
            mx: 2,
            mb: 2,
            p: 2,
            bgcolor: 'grey.50',
            borderLeft: 4,
            borderColor: 'primary.main',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <LinkIcon color="primary" fontSize="small" />
              <Typography variant="subtitle1" fontWeight="bold">
                Linked Analytes
              </Typography>
              <Chip label={data.analytes.length} size="small" color="primary" />
            </Box>
            {canManage && !currentlyAddingToThis && (
              <Button
                size="small"
                startIcon={<Add />}
                onClick={() => handleStartAddAnalytes(analysisId)}
              >
                Add Analytes
              </Button>
            )}
          </Box>

          {/* Add Analytes Section */}
          {currentlyAddingToThis && (
            <Box sx={{ mb: 2, p: 2, bgcolor: 'background.paper', borderRadius: 1, border: 1, borderColor: 'divider' }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Search and select analytes to add:
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'flex-start' }}>
                <Autocomplete
                  multiple
                  options={availableAnalytes}
                  getOptionLabel={(option) => {
                    const casInfo = option.cas_number ? ` (${option.cas_number})` : '';
                    return `${option.name}${casInfo}`;
                  }}
                  value={selectedAnalytesToAdd}
                  onChange={(_, newValue) => setSelectedAnalytesToAdd(newValue)}
                  onInputChange={(_, value) => setAnalyteSearchTerm(value)}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Search analytes"
                      placeholder="Type to search..."
                      size="small"
                    />
                  )}
                  renderOption={(props, option) => (
                    <li {...props} key={option.id}>
                      <Box>
                        <Typography variant="body2">{option.name}</Typography>
                        {option.cas_number && (
                          <Typography variant="caption" color="text.secondary">
                            CAS: {option.cas_number}
                          </Typography>
                        )}
                      </Box>
                    </li>
                  )}
                  sx={{ flex: 1, minWidth: 300 }}
                  isOptionEqualToValue={(option, value) => option.id === value.id}
                  noOptionsText="No analytes found"
                  ChipProps={{ size: 'small' }}
                />
                <Button
                  variant="contained"
                  size="small"
                  onClick={handleConfirmAddAnalytes}
                  disabled={selectedAnalytesToAdd.length === 0}
                >
                  Add ({selectedAnalytesToAdd.length})
                </Button>
                <Button
                  size="small"
                  onClick={handleCancelAddAnalytes}
                >
                  Cancel
                </Button>
              </Box>
            </Box>
          )}

          {/* Loading State */}
          {data.loading && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Skeleton variant="rectangular" height={40} />
              <Skeleton variant="rectangular" height={40} />
              <Skeleton variant="rectangular" height={40} />
            </Box>
          )}

          {/* Error State */}
          {data.error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {data.error}
            </Alert>
          )}

          {/* Analytes List */}
          {!data.loading && !data.error && (
            <>
              {data.analytes.length > 0 ? (
                <Box sx={{ overflowX: 'auto' }}>
                  <DataGrid
                    rows={data.analytes}
                    columns={[
                      { field: 'name', headerName: 'Analyte Name', width: 200, flex: 1 },
                      { 
                        field: 'cas_number', 
                        headerName: 'CAS Number', 
                        width: 130,
                        valueGetter: (value) => value || 'N/A',
                      },
                      { 
                        field: 'data_type', 
                        headerName: 'Data Type', 
                        width: 120,
                        renderCell: (params) => getDataTypeChip(params.value),
                      },
                      {
                        field: 'actions',
                        type: 'actions',
                        headerName: '',
                        width: 60,
                        getActions: (params) => {
                          if (!canManage) return [];
                          return [
                            <GridActionsCellItem
                              icon={
                                <Tooltip title="Remove from analysis">
                                  <Delete color="error" fontSize="small" />
                                </Tooltip>
                              }
                              label="Remove"
                              onClick={() => handleRemoveAnalyte(analysisId, params.id as string)}
                            />,
                          ];
                        },
                      },
                    ]}
                    autoHeight
                    hideFooter={data.analytes.length <= 5}
                    pageSizeOptions={[5, 10]}
                    initialState={{
                      pagination: { paginationModel: { pageSize: 5 } },
                    }}
                    disableRowSelectionOnClick
                    density="compact"
                    sx={{
                      '& .MuiDataGrid-root': { border: 'none' },
                      bgcolor: 'background.paper',
                    }}
                  />
                </Box>
              ) : (
                <Box
                  sx={{
                    py: 3,
                    textAlign: 'center',
                    color: 'text.secondary',
                    bgcolor: 'background.paper',
                    borderRadius: 1,
                  }}
                >
                  <Typography>No analytes linked to this analysis</Typography>
                  {canManage && (
                    <Typography variant="caption">
                      Click "Add Analytes" to link analytes
                    </Typography>
                  )}
                </Box>
              )}
            </>
          )}
        </Paper>
      </Collapse>
    );
  };

  if (loading && analyses.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, position: 'relative' }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Analyses</Typography>
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
          placeholder="Search by name or method..."
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
        <CardContent sx={{ p: 0, '&:last-child': { pb: 0 } }}>
          {/* Custom rendering to support expandable rows */}
          <Box>
            <DataGrid
              rows={analyses}
              columns={columns}
              rowCount={totalRows}
              loading={loading}
              paginationMode="server"
              paginationModel={paginationModel}
              onPaginationModelChange={setPaginationModel}
              pageSizeOptions={[10, 25, 50, 100]}
              sx={{ 
                height: 600,
                border: 'none',
                '& .MuiDataGrid-row': {
                  cursor: 'pointer',
                },
              }}
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
          </Box>
          
          {/* Expanded Detail Panels - rendered below the grid for each expanded row */}
          {analyses.map((analysis) => (
            expandedRows[analysis.id] && (
              <Box key={`detail-${analysis.id}`}>
                {renderDetailPanel(analysis.id)}
              </Box>
            )
          ))}
        </CardContent>
      </Card>

      {/* FAB for Create */}
      {canManage && (
        <Fab
          color="primary"
          aria-label="Create analysis"
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
        aria-labelledby="analysis-form-dialog-title"
      >
        <Formik
          initialValues={getInitialValues()}
          validationSchema={validationSchema}
          onSubmit={handleSubmit}
          enableReinitialize
        >
          {({ values, errors, touched, setFieldValue, isValid, dirty }) => (
            <Form>
              <DialogTitle id="analysis-form-dialog-title">
                {selectedAnalysis ? `Edit Analysis: ${selectedAnalysis.name}` : 'Create New Analysis'}
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
                        helperText={meta.touched && meta.error ? meta.error : 'Unique name for this analysis'}
                      />
                    )}
                  </Field>

                  <Field name="method">
                    {({ field, meta }: any) => (
                      <TextField
                        {...field}
                        label="Method"
                        fullWidth
                        required
                        error={meta.touched && !!meta.error}
                        helperText={meta.touched && meta.error ? meta.error : 'Testing method (e.g., EPA 8080)'}
                      />
                    )}
                  </Field>

                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <Field name="turnaround_time">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          value={field.value ?? ''}
                          label="Turnaround Time (days)"
                          type="number"
                          fullWidth
                          error={meta.touched && !!meta.error}
                          helperText={meta.touched && meta.error ? meta.error : 'Days to complete'}
                          inputProps={{ min: 0 }}
                          onChange={(e) => {
                            const val = e.target.value === '' ? null : parseInt(e.target.value, 10);
                            setFieldValue('turnaround_time', val);
                          }}
                        />
                      )}
                    </Field>

                    <Field name="cost">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          value={field.value ?? ''}
                          label="Cost ($)"
                          type="number"
                          fullWidth
                          error={meta.touched && !!meta.error}
                          helperText={meta.touched && meta.error ? meta.error : 'Optional cost'}
                          inputProps={{ min: 0, step: '0.01' }}
                          onChange={(e) => {
                            const val = e.target.value === '' ? null : parseFloat(e.target.value);
                            setFieldValue('cost', val);
                          }}
                        />
                      )}
                    </Field>
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
                  disabled={submitting || !isValid || (!selectedAnalysis && !dirty)}
                >
                  {submitting ? 'Saving...' : selectedAnalysis ? 'Update' : 'Create'}
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

export default AnalysesManagement;
