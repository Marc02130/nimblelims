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
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Search,
  Clear,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';
import ContainerTypeForm from './ContainerTypeForm';

interface ContainerType {
  id: string;
  name: string;
  description?: string;
  capacity?: number;
  material?: string;
  dimensions?: string;
  preservative?: string;
  active: boolean;
  created_at: string;
  modified_at: string;
}

const ContainerTypesManagement: React.FC = () => {
  const { user, hasPermission } = useUser();
  const [containerTypes, setContainerTypes] = useState<ContainerType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [selectedContainerType, setSelectedContainerType] = useState<ContainerType | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ContainerType | null>(null);

  const canEdit = hasPermission('config:edit');

  useEffect(() => {
    loadContainerTypes();
  }, []);

  const loadContainerTypes = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getContainerTypes();
      setContainerTypes(data || []);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view container types');
      } else {
        setError(err.response?.data?.detail || 'Failed to load container types');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredContainerTypes = useMemo(() => {
    if (!searchTerm) return containerTypes;
    const term = searchTerm.toLowerCase();
    return containerTypes.filter(
      (type) =>
        type.name.toLowerCase().includes(term) ||
        type.description?.toLowerCase().includes(term) ||
        type.material?.toLowerCase().includes(term) ||
        type.dimensions?.toLowerCase().includes(term) ||
        type.preservative?.toLowerCase().includes(term) ||
        (type.capacity !== undefined && type.capacity !== null && type.capacity.toString().includes(term))
    );
  }, [containerTypes, searchTerm]);

  const handleCreate = async (data: {
    name: string;
    description?: string;
    capacity?: number;
    material?: string;
    dimensions?: string;
    preservative?: string;
  }) => {
    await apiService.createContainerType(data);
    await loadContainerTypes();
  };

  const handleUpdate = async (data: {
    name: string;
    description?: string;
    capacity?: number;
    material?: string;
    dimensions?: string;
    preservative?: string;
  }) => {
    if (!selectedContainerType) return;
    await apiService.updateContainerType(selectedContainerType.id, data);
    await loadContainerTypes();
    setSelectedContainerType(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteContainerType(deleteTarget.id);
      await loadContainerTypes();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      if (err.response?.status === 400) {
        setError(err.response?.data?.detail || 'Cannot delete container type that is in use');
      } else {
        setError(err.response?.data?.detail || 'Failed to delete container type');
      }
      setDeleteDialogOpen(false);
    }
  };

  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Name',
      width: 200,
      flex: 1,
    },
    {
      field: 'description',
      headerName: 'Description',
      width: 250,
      flex: 1,
    },
    {
      field: 'capacity',
      headerName: 'Capacity',
      width: 120,
      valueGetter: (value) => value ?? 'N/A',
      type: 'number',
    },
    {
      field: 'material',
      headerName: 'Material',
      width: 150,
      valueGetter: (value) => value ?? 'N/A',
    },
    {
      field: 'dimensions',
      headerName: 'Dimensions',
      width: 150,
      valueGetter: (value) => value ?? 'N/A',
    },
    {
      field: 'preservative',
      headerName: 'Preservative',
      width: 150,
      valueGetter: (value) => value ?? 'N/A',
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 120,
      getActions: (params: GridRowParams) => {
        const containerType = params.row as ContainerType;
        const actions = [];

        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedContainerType(containerType);
                setFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget(containerType);
                setDeleteDialogOpen(true);
              }}
            />
          );
        }

        return actions;
      },
    },
  ];

  if (!canEdit && !hasPermission('sample:read')) {
    return (
      <Box>
        <Alert severity="warning">
          You do not have permission to view container types management.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Container Types Management</Typography>
        {canEdit && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setSelectedContainerType(null);
              setFormOpen(true);
            }}
          >
            Create Container Type
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ mb: 2 }}>
        <TextField
          fullWidth
          placeholder="Search container types..."
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

      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <CircularProgress />
        </Box>
      ) : (
        <Box sx={{ height: 600, width: '100%' }}>
          <DataGrid
            rows={filteredContainerTypes}
            columns={columns}
            getRowId={(row) => row.id}
            pageSizeOptions={[10, 25, 50]}
            initialState={{
              pagination: {
                paginationModel: { page: 0, pageSize: 10 },
              },
            }}
            disableRowSelectionOnClick
            slots={{
              noRowsOverlay: () => (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  <Typography>No container types found</Typography>
                </Box>
              ),
            }}
          />
        </Box>
      )}

      {/* Container Type Form Dialog */}
      <ContainerTypeForm
        open={formOpen}
        containerType={selectedContainerType}
        existingNames={containerTypes.map((t) => t.name)}
        onClose={() => {
          setFormOpen(false);
          setSelectedContainerType(null);
        }}
        onSubmit={selectedContainerType ? handleUpdate : handleCreate}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete container type <strong>{deleteTarget?.name}</strong>?
            <Box component="span" sx={{ display: 'block', mt: 1, color: 'warning.main' }}>
              This action cannot be undone. If this container type is referenced by existing containers, the deletion will fail.
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

export default ContainerTypesManagement;
