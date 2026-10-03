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
  Star,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';
import { FillHeightPage, FillHeightTable } from '../../components/common/FillHeightPage';
import UnitFormDialog from './UnitFormDialog';
import { isBaseUnit } from './unitBase';

interface Unit {
  id: string;
  name: string;
  description?: string;
  multiplier?: number | string | null;
  type: string;
  type_name?: string;
  active: boolean;
  is_base?: boolean;
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
  const [baseTarget, setBaseTarget] = useState<Unit | null>(null);
  const [baseSaving, setBaseSaving] = useState(false);

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
    multiplier?: number | string | null;
    type: string;
    active?: boolean;
  }) => {
    await apiService.createUnit(data);
    await loadUnits();
  };

  const handleUpdate = async (data: {
    name: string;
    description?: string;
    multiplier?: number | string | null;
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

  const duplicateBases = useMemo(() => {
    const byType = new Map<string, Unit[]>();
    units.filter((unit) => unit.active && isBaseUnit(unit)).forEach((unit) => {
      const key = unit.type_name || unit.type;
      const group = byType.get(key) || [];
      group.push(unit);
      byType.set(key, group);
    });
    return Array.from(byType.entries())
      .filter(([, group]) => group.length > 1)
      .map(([typeName, group]) => `${typeName} (${group.map((unit) => unit.name).join(', ')})`);
  }, [units]);

  const handleSetBase = async () => {
    if (!baseTarget) return;
    try {
      setBaseSaving(true);
      setError(null);
      await apiService.setBaseUnit(baseTarget.id);
      setBaseTarget(null);
      await loadUnits();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to set the base unit');
      setBaseTarget(null);
    } finally {
      setBaseSaving(false);
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
      width: 160,
      valueGetter: (_value, row) => (row as Unit).multiplier ?? 'N/A',
      renderCell: (params) => {
        const unit = params.row as Unit;
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <span>{unit.multiplier ?? 'N/A'}</span>
            {isBaseUnit(unit) && <Chip label="Base" size="small" color="primary" />}
          </Box>
        );
      },
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
          if (!isBaseUnit(unit) && unit.active) {
            actions.push(
              <GridActionsCellItem
                icon={<Star />}
                label="Use as base"
                showInMenu
                onClick={() => setBaseTarget(unit)}
              />
            );
          }
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
    <FillHeightPage
      header={
        <>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Box>
              <Typography variant="h4">Units Management</Typography>
              <Typography variant="body2" color="text.secondary">
                Pick one base unit per type. Its multiplier is 1. Other units store how many of
                that base are in one of them. Calculations convert to the base.
              </Typography>
            </Box>
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

          {duplicateBases.length > 0 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              More than one base (multiplier 1) in {duplicateBases.join('; ')}. Pick one base.
              Set the others relative to it, or use one of them as the base after their
              multipliers differ.
            </Alert>
          )}

          <TextField
            fullWidth
            size="small"
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
        </>
      }
    >
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" flex={1}>
          <CircularProgress />
        </Box>
      ) : (
        <FillHeightTable>
          <DataGrid
            rows={filteredUnits}
            columns={columns}
            getRowId={(row) => row.id}
            pageSizeOptions={[10, 25, 50]}
            initialState={{
              pagination: {
                paginationModel: { page: 0, pageSize: 25 },
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
        </FillHeightTable>
      )}

      <UnitFormDialog
        open={formOpen}
        unit={selectedUnit}
        existingNames={units.map((u) => u.name)}
        units={units}
        onClose={() => {
          setFormOpen(false);
          setSelectedUnit(null);
        }}
        onSubmit={selectedUnit ? handleUpdate : handleCreate}
      />

      <Dialog open={!!baseTarget} onClose={() => !baseSaving && setBaseTarget(null)}>
        <DialogTitle>Use as base</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Use <strong>{baseTarget?.name}</strong> as the base for {baseTarget?.type_name || 'this type'}?
            Its multiplier becomes 1. Every other unit of that type is rescaled so amounts still
            convert to the same base.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBaseTarget(null)} disabled={baseSaving}>Cancel</Button>
          <Button onClick={handleSetBase} variant="contained" disabled={baseSaving}>
            {baseSaving ? 'Saving...' : 'Use as base'}
          </Button>
        </DialogActions>
      </Dialog>

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
    </FillHeightPage>
  );
};

export default UnitsManagement;

