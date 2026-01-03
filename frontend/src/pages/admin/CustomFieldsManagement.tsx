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
  Select,
  FormControl,
  InputLabel,
  useMediaQuery,
  useTheme,
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
import CustomFieldDialog from '../../components/admin/CustomFieldDialog';

interface CustomAttributeConfig {
  id: string;
  entity_type: string;
  attr_name: string;
  data_type: 'text' | 'number' | 'date' | 'boolean' | 'select';
  validation_rules: Record<string, any>;
  description?: string;
  active: boolean;
  created_at: string;
  modified_at: string;
}

const ENTITY_TYPES = ['samples', 'tests', 'results', 'projects', 'client_projects', 'batches'];
const DATA_TYPES = ['text', 'number', 'date', 'boolean', 'select'];

const CustomFieldsManagement: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const { user, hasPermission } = useUser();
  const [configs, setConfigs] = useState<CustomAttributeConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('');
  const [formOpen, setFormOpen] = useState(false);
  const [selectedConfig, setSelectedConfig] = useState<CustomAttributeConfig | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<CustomAttributeConfig | null>(null);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);

  const canEdit = hasPermission('config:edit');

  useEffect(() => {
    loadConfigs();
  }, [page, pageSize, entityTypeFilter]);

  const loadConfigs = async () => {
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
      const response = await apiService.getCustomAttributeConfigs(filters);
      setConfigs(response.configs || []);
      setTotal(response.total || 0);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view custom fields management');
      } else {
        setError(err.response?.data?.detail || 'Failed to load custom fields');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredConfigs = useMemo(() => {
    if (!searchTerm) return configs;
    const term = searchTerm.toLowerCase();
    return configs.filter(
      (config) =>
        config.attr_name.toLowerCase().includes(term) ||
        config.description?.toLowerCase().includes(term) ||
        config.entity_type.toLowerCase().includes(term)
    );
  }, [configs, searchTerm]);

  const handleCreate = async (data: {
    entity_type?: string;
    attr_name?: string;
    data_type?: 'text' | 'number' | 'date' | 'boolean' | 'select';
    validation_rules?: Record<string, any>;
    description?: string;
    active?: boolean;
  }) => {
    // Ensure all required fields are present
    if (!data.entity_type || !data.attr_name || !data.data_type) {
      throw new Error('Missing required fields: entity_type, attr_name, and data_type are required');
    }
    await apiService.createCustomAttributeConfig({
      entity_type: data.entity_type,
      attr_name: data.attr_name,
      data_type: data.data_type,
      validation_rules: data.validation_rules || {},
      description: data.description,
      active: data.active ?? true,
    });
    await loadConfigs();
  };

  const handleUpdate = async (data: {
    entity_type?: string;
    attr_name?: string;
    data_type?: 'text' | 'number' | 'date' | 'boolean' | 'select';
    validation_rules?: Record<string, any>;
    description?: string;
    active?: boolean;
  }) => {
    if (!selectedConfig) return;
    await apiService.updateCustomAttributeConfig(selectedConfig.id, data);
    await loadConfigs();
    setSelectedConfig(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteCustomAttributeConfig(deleteTarget.id);
      await loadConfigs();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete custom field');
      setDeleteDialogOpen(false);
    }
  };

  const formatValidationRules = (rules: Record<string, any>): string => {
    if (!rules || Object.keys(rules).length === 0) return 'None';
    return JSON.stringify(rules, null, 2);
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
      field: 'attr_name',
      headerName: 'Attribute Name',
      width: 200,
      flex: isMobile ? 0 : 1,
    },
    {
      field: 'data_type',
      headerName: 'Data Type',
      width: 120,
      flex: isMobile ? 0 : 1,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color="secondary"
          variant="outlined"
        />
      ),
    },
    {
      field: 'description',
      headerName: 'Description',
      width: 250,
      flex: isMobile ? 0 : 2,
      valueGetter: (value) => value || 'N/A',
    },
    {
      field: 'validation_rules',
      headerName: 'Validation Rules',
      width: 200,
      flex: isMobile ? 0 : 1,
      valueGetter: (value) => formatValidationRules(value),
      renderCell: (params) => (
        <Box
          sx={{
            maxWidth: 200,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
          title={params.value}
        >
          {params.value}
        </Box>
      ),
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
        const config = params.row as CustomAttributeConfig;
        const actions = [];

        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedConfig(config);
                setFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget(config);
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
          You do not have permission to view custom fields management.
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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h4">Custom Fields Management</Typography>
          <Tooltip title="Edit help: Use config:edit permission to manage help entries in Help Management">
            <Typography variant="caption" color="text.secondary" sx={{ cursor: 'help' }}>
              (EAV)
            </Typography>
          </Tooltip>
        </Box>
        {canEdit && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setSelectedConfig(null);
              setFormOpen(true);
            }}
          >
            Create Custom Field
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
          placeholder="Search by attribute name or description..."
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
            rows={filteredConfigs}
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
                  <Typography>No custom fields found</Typography>
                </Box>
              ),
            }}
          />
        </Box>
      )}

      {/* Custom Field Form Dialog */}
      <CustomFieldDialog
        open={formOpen}
        config={selectedConfig}
        entityTypes={ENTITY_TYPES}
        dataTypes={DATA_TYPES}
        existingConfigs={configs}
        onClose={() => {
          setFormOpen(false);
          setSelectedConfig(null);
        }}
        onSubmit={selectedConfig ? handleUpdate : handleCreate}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete custom field <strong>{deleteTarget?.attr_name}</strong> for entity
            type <strong>{deleteTarget?.entity_type}</strong>?
            <Box component="span" sx={{ display: 'block', mt: 1, color: 'warning.main' }}>
              This will set the field to inactive. Existing data using this field will not be affected, but
              new entries will not be able to use this field.
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

export default CustomFieldsManagement;

