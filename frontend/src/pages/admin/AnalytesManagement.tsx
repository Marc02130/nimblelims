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
import AnalyteFormDialog from './AnalyteFormDialog';

interface Analyte {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  created_at: string;
  modified_at: string;
}

const AnalytesManagement: React.FC = () => {
  const { user, hasPermission } = useUser();
  const [analytes, setAnalytes] = useState<Analyte[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [selectedAnalyte, setSelectedAnalyte] = useState<Analyte | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Analyte | null>(null);

  const canEdit = hasPermission('config:edit') || hasPermission('test:configure');

  useEffect(() => {
    loadAnalytes();
  }, []);

  const loadAnalytes = async () => {
    try {
      setLoading(true);
      setError(null);
      const analytesData = await apiService.getAnalytes();
      setAnalytes(analytesData || []);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view analytes management');
      } else {
        setError(err.response?.data?.detail || 'Failed to load analytes');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredAnalytes = useMemo(() => {
    if (!searchTerm) return analytes;
    const term = searchTerm.toLowerCase();
    return analytes.filter(
      (analyte) =>
        analyte.name.toLowerCase().includes(term) ||
        analyte.description?.toLowerCase().includes(term)
    );
  }, [analytes, searchTerm]);

  const handleCreate = async (data: {
    name: string;
    description?: string;
  }) => {
    await apiService.createAnalyte(data);
    await loadAnalytes();
  };

  const handleUpdate = async (data: {
    name: string;
    description?: string;
  }) => {
    if (!selectedAnalyte) return;
    await apiService.updateAnalyte(selectedAnalyte.id, data);
    await loadAnalytes();
    setSelectedAnalyte(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteAnalyte(deleteTarget.id);
      await loadAnalytes();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      if (err.response?.status === 400) {
        setError(err.response?.data?.detail || 'Cannot delete analyte that is referenced in analyses');
      } else {
        setError(err.response?.data?.detail || 'Failed to delete analyte');
      }
      setDeleteDialogOpen(false);
    }
  };

  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Analyte Name',
      width: 200,
      flex: 1,
    },
    {
      field: 'description',
      headerName: 'Description',
      width: 300,
      flex: 2,
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 120,
      getActions: (params: GridRowParams) => {
        const analyte = params.row as Analyte;
        const actions = [];

        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedAnalyte(analyte);
                setFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget(analyte);
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
          You do not have permission to view analytes management.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Analytes Management</Typography>
        {canEdit && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setSelectedAnalyte(null);
              setFormOpen(true);
            }}
          >
            Create Analyte
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
          placeholder="Search analytes..."
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
            rows={filteredAnalytes}
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
                  <Typography>No analytes found</Typography>
                </Box>
              ),
            }}
          />
        </Box>
      )}

      {/* Analyte Form Dialog */}
      <AnalyteFormDialog
        open={formOpen}
        analyte={selectedAnalyte}
        existingNames={analytes.map((a) => a.name)}
        onClose={() => {
          setFormOpen(false);
          setSelectedAnalyte(null);
        }}
        onSubmit={selectedAnalyte ? handleUpdate : handleCreate}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete analyte <strong>{deleteTarget?.name}</strong>?
            <Box component="span" sx={{ display: 'block', mt: 1, color: 'warning.main' }}>
              This action cannot be undone. If this analyte is referenced in any analyses, the deletion will fail.
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

export default AnalytesManagement;

