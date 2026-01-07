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
import UnitFormDialog from './UnitFormDialog';

interface Unit {
  id: string;
  name: string;
  description?: string;
  multiplier?: number;
  type: string;
  type_name?: string;
  active: boolean;
  created_at: string;
  modified_at: string;
}

const UnitsManagement: React.FC = () => {
  const { user, hasPermission } = useUser();
  const [units, setUnits] = useState<Unit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [selectedUnit, setSelectedUnit] = useState<Unit | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Unit | null>(null);

  const canEdit = hasPermission('config:edit');

  useEffect(() => {
    loadUnits();
  }, []);

  const loadUnits = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getUnits();
      setUnits(data || []);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view units');
      } else {
        setError(err.response?.data?.detail || 'Failed to load units');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredUnits = useMemo(() => {
    if (!searchTerm) return units;
    const term = searchTerm.toLowerCase();
    return units.filter(
      (unit) =>
        unit.name.toLowerCase().includes(term) ||
        unit.description?.toLowerCase().includes(term) ||
        unit.type_name?.toLowerCase().includes(term) ||
        (unit.multiplier !== undefined && unit.multiplier !== null && unit.multiplier.toString().includes(term))
    );
  }, [units, searchTerm]);

  const handleCreate = async (data: {
    name: string;
    description?: string;
    multiplier?: number;
    type: string;
    active?: boolean;
  }) => {
    await apiService.createUnit(data);
    await loadUnits();
  };

  const handleUpdate = async (data: {
    name: string;
    description?: string;
    multiplier?: number;
    type: string;
    active?: boolean;
  }) => {
    if (!selectedUnit) return;
    await apiService.updateUnit(selectedUnit.id, data);
    await loadUnits();
    setSelectedUnit(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteUnit(deleteTarget.id);
      await loadUnits();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      if (err.response?.status === 400) {
        setError(err.response?.data?.detail || 'Cannot delete unit that is in use');
      } else {
        setError(err.response?.data?.detail || 'Failed to delete unit');
      }
      setDeleteDialogOpen(false);
    }
  };

  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Name',
      width: 150,
      flex: 1,
    },
    {
      field: 'description',
      headerName: 'Description',
      width: 250,
      flex: 1,
    },
    {
      field: 'type_name',
      headerName: 'Type',
      width: 150,
      valueGetter: (value) => value ?? 'N/A',
      renderCell: (params) => (
        <Chip
          label={params.value || 'N/A'}
          size="small"
          color={
            params.value === 'concentration' ? 'primary' :
            params.value === 'mass' ? 'secondary' :
            params.value === 'volume' ? 'info' :
            params.value === 'molar' ? 'success' : 'default'
          }
        />
      ),
    },
    {
      field: 'multiplier',
      headerName: 'Multiplier',
      width: 120,
      valueGetter: (value) => value ?? 'N/A',
      type: 'number',
    },
    {
      field: 'active',
      headerName: 'Active',
      width: 100,
      type: 'boolean',
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
        const unit = params.row as Unit;
        const actions = [];

        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedUnit(unit);
                setFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget(unit);
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
          You do not have permission to view units management.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Units Management</Typography>
        {canEdit && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setSelectedUnit(null);
              setFormOpen(true);
            }}
          >
            Create Unit
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
          placeholder="Search units..."
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
            rows={filteredUnits}
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
                  <Typography>No units found</Typography>
                </Box>
              ),
            }}
          />
        </Box>
      )}

      {/* Unit Form Dialog */}
      <UnitFormDialog
        open={formOpen}
        unit={selectedUnit}
        existingNames={units.map((u) => u.name)}
        onClose={() => {
          setFormOpen(false);
          setSelectedUnit(null);
        }}
        onSubmit={selectedUnit ? handleUpdate : handleCreate}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete unit <strong>{deleteTarget?.name}</strong>?
            <Box component="span" sx={{ display: 'block', mt: 1, color: 'warning.main' }}>
              This action cannot be undone. If this unit is referenced by existing containers or contents, the deletion will fail.
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

export default UnitsManagement;

