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
  data_type: 'text' | 'number' | 'date' | 'boolean' | 'list';
  validation_rules: Record<string, any>;
  source_list_id?: string;
  description?: string;
  active: boolean;
  created_at: string;
  modified_at: string;
}

// Internal display model that unifies OOB + Custom
interface FieldRow extends Partial<CustomAttributeConfig> {
  source: 'oob' | 'custom';
  id: string; // synthetic for OOB rows
}

// All entities that can have fields / validation rules defined
const ENTITY_TYPES = [
  'samples',
  'tests',
  'results',
  'projects',
  'client_projects',
  'batches',
  'units',
  'clients',
  'experiments',
  'analyses',
  'containers',
];
const DATA_TYPES = ['text', 'number', 'date', 'boolean', 'list'];

// OOB (built-in / out-of-the-box) fields per entity.
// These are the fields that ship with the system and use list-backed or direct storage today.
// We surface them here (denoted) so admins see the complete picture for an entity and can manage
// their validation rules / options.
const OOB_FIELDS: Record<string, Array<{
  attr_name: string;
  data_type: 'text' | 'number' | 'date' | 'boolean' | 'list';
  description: string;
  validation_rules?: Record<string, any>;
}>> = {
  samples: [
    {
      attr_name: 'sample_type',
      data_type: 'list',
      description: 'Type of sample material',
      validation_rules: {},
    },
    {
      attr_name: 'status',
      data_type: 'list',
      description: 'Current status of the sample',
      validation_rules: {},
    },
    {
      attr_name: 'matrix',
      data_type: 'list',
      description: 'Sample matrix / material type',
      validation_rules: {},
    },
    {
      attr_name: 'qc_type',
      data_type: 'list',
      description: 'QC classification for the sample',
      validation_rules: {},
    },
    {
      attr_name: 'specimen_biotype',
      data_type: 'list',
      description: 'Biological type / classification of the specimen (list-backed)',
      validation_rules: {},
    },
    // Example OOB scalar fields to demonstrate validation rules for numeric/date
    {
      attr_name: 'volume_ml',
      data_type: 'number',
      description: 'Sample volume in milliliters',
      validation_rules: { min: 0, max: 10000 },
    },
    {
      attr_name: 'received_date',
      data_type: 'date',
      description: 'Date the sample was received',
      validation_rules: {},
    },
  ],
  projects: [
    {
      attr_name: 'status',
      data_type: 'list',
      description: 'Project status',
      validation_rules: {},
    },
    {
      attr_name: 'access_level',
      data_type: 'list',
      description: 'Access / visibility level',
      validation_rules: {},
    },
  ],
  tests: [
    {
      attr_name: 'status',
      data_type: 'list',
      description: 'Test / assay status',
      validation_rules: {},
    },
  ],
  batches: [
    {
      attr_name: 'type',
      data_type: 'list',
      description: 'Batch type',
      validation_rules: {},
    },
    {
      attr_name: 'status',
      data_type: 'list',
      description: 'Batch status',
      validation_rules: {},
    },
  ],
  units: [
    {
      attr_name: 'type',
      data_type: 'list',
      description: 'Unit of measure category',
      validation_rules: {},
    },
  ],
  clients: [
    {
      attr_name: 'type',
      data_type: 'list',
      description: 'Client type',
      validation_rules: {},
    },
    {
      attr_name: 'role',
      data_type: 'list',
      description: 'Role / relationship type',
      validation_rules: {},
    },
  ],
  experiments: [
    {
      attr_name: 'status',
      data_type: 'list',
      description: 'Experiment status',
      validation_rules: {},
    },
  ],
  results: [
    {
      attr_name: 'qualifiers',
      data_type: 'list',
      description: 'Result qualifiers / flags',
      validation_rules: {},
    },
  ],
  analyses: [],
  containers: [],
};

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
      // Use new FieldDefinition endpoint for the new Field Management path
      const response = await apiService.getFieldDefinitions(filters);
      // Map FieldDefinition response (items) to legacy shape for minimal UI change
      const mapped = (response.items || []).map((f: any) => ({
        id: f.id,
        entity_type: f.entity_type,
        attr_name: f.name,
        data_type: f.data_type,
        validation_rules: f.validation_rules || {},
        // do not pollute validation_rules with list info; source separate
        source_list_id: f.source_list_id,
        description: f.description || f.display_name,
        active: f.active,
        created_at: f.created_at,
        modified_at: f.modified_at,
      }));
      setConfigs(mapped);
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

  // Build unified list of OOB + Custom for display
  const allFields: FieldRow[] = useMemo(() => {
    const oobRows: FieldRow[] = [];

    const relevantEntities = entityTypeFilter ? [entityTypeFilter] : ENTITY_TYPES;

    relevantEntities.forEach((et) => {
      const oobs = OOB_FIELDS[et] || [];
      oobs.forEach((oob) => {
        oobRows.push({
          id: `oob-${et}-${oob.attr_name}`,
          entity_type: et,
          attr_name: oob.attr_name,
          data_type: oob.data_type,
          validation_rules: oob.validation_rules || {},
          description: oob.description,
          active: true,
          source: 'oob',
        });
      });
    });

    const customRows: FieldRow[] = configs.map((c) => ({
      ...c,
      source: 'custom',
    }));

    // If filtering by entity, only include relevant
    let combined = [...oobRows, ...customRows];

    if (entityTypeFilter) {
      combined = combined.filter((f) => f.entity_type === entityTypeFilter);
    }

    // Sort: OOB first (by name), then customs
    combined.sort((a, b) => {
      if (a.source !== b.source) return a.source === 'oob' ? -1 : 1;
      if (a.entity_type !== b.entity_type) return a.entity_type!.localeCompare(b.entity_type!);
      return a.attr_name!.localeCompare(b.attr_name!);
    });

    return combined;
  }, [configs, entityTypeFilter]);

  const filteredFields = useMemo(() => {
    if (!searchTerm) return allFields;
    const term = searchTerm.toLowerCase();
    return allFields.filter(
      (f) =>
        f.attr_name?.toLowerCase().includes(term) ||
        f.description?.toLowerCase().includes(term) ||
        f.entity_type?.toLowerCase().includes(term)
    );
  }, [allFields, searchTerm]);

  const handleCreate = async (data: {
    entity_type?: string;
    attr_name?: string;
    data_type?: 'text' | 'number' | 'date' | 'boolean' | 'list';
    validation_rules?: Record<string, any>;
    description?: string;
    active?: boolean;
    source_list_id?: string;  // for list types
  }) => {
    // Ensure all required fields are present
    if (!data.entity_type || !data.attr_name || !data.data_type) {
      throw new Error('Missing required fields: entity_type, attr_name, and data_type are required');
    }
    // Switch to new FieldDefinition endpoint - stop calling legacy
    const payload: any = {
      entity_type: data.entity_type,
      name: data.attr_name,  // map attr_name -> name
      display_name: data.description || data.attr_name,
      data_type: data.data_type,
      validation_rules: data.validation_rules || {},
      description: data.description,
      active: data.active ?? true,
      is_required: data.validation_rules?.required || false,
    };
    if (data.data_type === 'list' && data.source_list_id) {
      payload.source_list_id = data.source_list_id;
    }
    await apiService.createFieldDefinition(payload);
    await loadConfigs();
  };

  const handleUpdate = async (data: {
    entity_type?: string;
    attr_name?: string;
    data_type?: 'text' | 'number' | 'date' | 'boolean' | 'list';
    validation_rules?: Record<string, any>;
    description?: string;
    active?: boolean;
    source_list_id?: string;
  }) => {
    if (!selectedConfig) return;
    const isOob = (selectedConfig as any).source === 'oob' || String(selectedConfig.id).startsWith('oob-');
    if (isOob) {
      // OOB fields are defined in the system. For now we just refresh the local view.
      await loadConfigs();
      setSelectedConfig(null);
      return;
    }
    // Switch to new FieldDefinition endpoint
    const payload: any = {
      entity_type: data.entity_type,
      name: data.attr_name,
      display_name: data.description,
      data_type: data.data_type,
      validation_rules: data.validation_rules,
      description: data.description,
      active: data.active,
    };
    if (data.data_type === 'list' && data.source_list_id) {
      payload.source_list_id = data.source_list_id;
    }
    await apiService.updateFieldDefinition(selectedConfig.id, payload);
    await loadConfigs();
    setSelectedConfig(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      const isOob = (deleteTarget as any).source === 'oob' || String(deleteTarget.id).startsWith('oob-');
      if (!isOob) {
        await apiService.deleteFieldDefinition(deleteTarget.id);
      }
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
      field: 'source',
      headerName: 'Type',
      width: 100,
      flex: isMobile ? 0 : 0.6,
      renderCell: (params) => {
        const isOob = params.value === 'oob';
        return (
          <Chip
            label={isOob ? 'OOB' : 'Custom'}
            size="small"
            color={isOob ? 'default' : 'success'}
            variant={isOob ? 'outlined' : 'filled'}
          />
        );
      },
    },
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
      headerName: 'Field Name',
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
        const row = params.row as FieldRow;
        const actions = [];

        if (canEdit) {
          // OOB rows are editable for validation rules etc., but we pass a synthetic object
          const configForDialog: any = {
            id: row.id,
            entity_type: row.entity_type,
            attr_name: row.attr_name,
            data_type: row.data_type,
            validation_rules: row.validation_rules,
            description: row.description,
            active: row.active ?? true,
            source: row.source,
          };

          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedConfig(configForDialog);
                setFormOpen(true);
              }}
            />
          );

          // Only customs are deletable in this view
          if (row.source === 'custom') {
            actions.push(
              <GridActionsCellItem
                icon={<Delete />}
                label="Delete"
                onClick={() => {
                  setDeleteTarget(configForDialog);
                  setDeleteDialogOpen(true);
                }}
              />
            );
          }
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
          <Typography variant="h4">Field Management</Typography>
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
        <Box sx={{ width: '100%' }}>
          <DataGrid
            rows={filteredFields}
            autoHeight
            columns={columns}
            getRowId={(row) => row.id}
            pageSizeOptions={[10, 25, 50]}
            // Client-side pagination for the unified OOB + Custom view (OOB are in-memory)
            paginationMode="client"
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
                  <Typography>No fields found for the current filter</Typography>
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
        // Pass the full unified list (OOB + customs) so the dialog can show rich context
        existingFields={allFields}
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

