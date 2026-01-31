import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
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
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Search,
  Clear,
  Visibility,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../contexts/UserContext';
import { apiService } from '../services/apiService';
import ClientDialog from '../components/clients/ClientDialog';

interface Client {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  created_at: string;
  modified_at: string;
}

const ClientsManagement: React.FC = () => {
  const { user, hasPermission } = useUser();
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Client | null>(null);
  const [viewMode, setViewMode] = useState(false);

  // Create/Edit/Delete client require config:edit (backend uses require_permission('config:edit'))
  const canEditClients = hasPermission('config:edit');
  const canRead = hasPermission('sample:read') || hasPermission('project:manage') || canEditClients;

  useEffect(() => {
    if (!canRead) {
      navigate('/dashboard');
      return;
    }
    loadData();
  }, [canRead, navigate]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const clientsData = await apiService.getClients();
      setClients(clientsData || []);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view clients management');
      } else {
        setError(err.response?.data?.detail || 'Failed to load clients');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredClients = useMemo(() => {
    if (!searchTerm) return clients;
    const term = searchTerm.toLowerCase();
    return clients.filter(
      (client) =>
        client.name.toLowerCase().includes(term) ||
        (client.description && client.description.toLowerCase().includes(term))
    );
  }, [clients, searchTerm]);

  const handleCreate = async (data: {
    name: string;
    description?: string;
    active: boolean;
  }) => {
    await apiService.createClient(data);
    await loadData();
  };

  const handleUpdate = async (data: {
    name: string;
    description?: string;
    active: boolean;
  }) => {
    if (!selectedClient) return;
    await apiService.updateClient(selectedClient.id, data);
    await loadData();
    setSelectedClient(null);
  };

  const handleView = (client: Client) => {
    setSelectedClient(client);
    setViewMode(true);
    setFormOpen(true);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteClient(deleteTarget.id);
      await loadData();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      if (err.response?.status === 400) {
        setError(err.response?.data?.detail || 'Cannot delete client with active users or projects');
      } else {
        setError(err.response?.data?.detail || 'Failed to delete client');
      }
      setDeleteDialogOpen(false);
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Name',
      width: 200,
      flex: 1,
      minWidth: 150,
    },
    {
      field: 'description',
      headerName: 'Description',
      width: 300,
      flex: 1,
      minWidth: 200,
      valueGetter: (value) => value || 'N/A',
    },
    {
      field: 'active',
      headerName: 'Active',
      width: 100,
      type: 'boolean',
      renderCell: (params) => (
        <Typography variant="body2" color={params.value ? 'success.main' : 'text.secondary'}>
          {params.value ? 'Yes' : 'No'}
        </Typography>
      ),
    },
    {
      field: 'created_at',
      headerName: 'Created At',
      width: 180,
      valueGetter: (value, row) => formatDate((row as Client).created_at),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 120,
      getActions: (params: GridRowParams) => {
        const clientRow = params.row as Client;
        const actions = [];

        // View button - available to all users
        actions.push(
          <GridActionsCellItem
            icon={<Visibility />}
            label="View"
            onClick={() => handleView(clientRow)}
          />
        );

        // Edit and Delete - only for users with config:edit (same as backend create/update/delete client)
        if (canEditClients) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedClient(clientRow);
                setViewMode(false);
                setFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget(clientRow);
                setDeleteDialogOpen(true);
              }}
            />
          );
        }

        return actions;
      },
    },
  ];

  if (!canRead) {
    return null; // Will redirect via useEffect
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
          gap: isMobile ? 2 : 0,
        }}
      >
        <Typography variant="h4">Clients Management</Typography>
        {canEditClients && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setSelectedClient(null);
              setFormOpen(true);
            }}
            fullWidth={isMobile}
          >
            Create Client
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
          placeholder="Search clients..."
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
            rows={filteredClients}
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
                  <Typography>No clients found</Typography>
                </Box>
              ),
            }}
          />
        </Box>
      )}

      {/* Client Form Dialog */}
      <ClientDialog
        open={formOpen}
        client={selectedClient}
        existingNames={clients.map((c) => c.name)}
        onClose={() => {
          setFormOpen(false);
          setSelectedClient(null);
          setViewMode(false);
        }}
        onSubmit={selectedClient ? handleUpdate : handleCreate}
        readOnly={viewMode}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete client <strong>{deleteTarget?.name}</strong>?
            <Box component="span" sx={{ display: 'block', mt: 1, color: 'warning.main' }}>
              This will soft-delete the client (set active=false). If this client has active users or projects, the deletion will fail.
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

export default ClientsManagement;

