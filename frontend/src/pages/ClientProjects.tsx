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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Search,
  Clear,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../contexts/UserContext';
import { apiService } from '../services/apiService';
import ClientProjectForm from '../components/client-projects/ClientProjectForm';

interface Client {
  id: string;
  name: string;
}

interface ClientProject {
  id: string;
  name: string;
  description?: string;
  client_id: string;
  active: boolean;
  created_at: string;
  modified_at: string;
  client?: Client;
}

const ClientProjects: React.FC = () => {
  const { user, hasPermission } = useUser();
  const [clientProjects, setClientProjects] = useState<ClientProject[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [clientFilter, setClientFilter] = useState<string>('');
  const [formOpen, setFormOpen] = useState(false);
  const [selectedClientProject, setSelectedClientProject] = useState<ClientProject | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ClientProject | null>(null);
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 10 });
  const [total, setTotal] = useState(0);

  const canManage = hasPermission('project:manage');

  useEffect(() => {
    loadClients();
  }, []);

  useEffect(() => {
    loadClientProjects();
  }, [paginationModel, clientFilter]);

  const loadClients = async () => {
    try {
      const clientsData = await apiService.getClients();
      setClients(clientsData || []);
    } catch (err: any) {
      console.error('Failed to load clients:', err);
    }
  };

  const loadClientProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      const filters: { client_id?: string; page?: number; size?: number } = {
        page: paginationModel.page + 1,
        size: paginationModel.pageSize,
      };
      if (clientFilter) {
        filters.client_id = clientFilter;
      }
      const response = await apiService.getClientProjects(filters);
      
      // Handle both paginated and non-paginated responses
      if (response.client_projects) {
        setClientProjects(response.client_projects || []);
        setTotal(response.total || 0);
      } else {
        setClientProjects(response || []);
        setTotal(response?.length || 0);
      }
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view client projects');
      } else {
        setError(err.response?.data?.detail || 'Failed to load client projects');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredClientProjects = useMemo(() => {
    if (!searchTerm) return clientProjects;
    const term = searchTerm.toLowerCase();
    return clientProjects.filter(
      (cp) =>
        cp.name.toLowerCase().includes(term) ||
        cp.description?.toLowerCase().includes(term) ||
        clients.find((c) => c.id === cp.client_id)?.name.toLowerCase().includes(term)
    );
  }, [clientProjects, searchTerm, clients]);

  const getClientName = (clientId: string): string => {
    const client = clients.find((c) => c.id === clientId);
    return client?.name || 'Unknown';
  };

  const handleCreate = async (data: {
    name: string;
    description?: string;
    client_id: string;
  }) => {
    await apiService.createClientProject(data);
    await loadClientProjects();
  };

  const handleUpdate = async (data: {
    name: string;
    description?: string;
    client_id: string;
  }) => {
    if (!selectedClientProject) return;
    await apiService.updateClientProject(selectedClientProject.id, data);
    await loadClientProjects();
    setSelectedClientProject(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteClientProject(deleteTarget.id);
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      await loadClientProjects();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete client project');
    }
  };

  const existingNames = clientProjects
    .filter((cp) => !selectedClientProject || cp.id !== selectedClientProject.id)
    .map((cp) => cp.name);

  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Name',
      width: 250,
      flex: 1,
    },
    {
      field: 'description',
      headerName: 'Description',
      width: 300,
      flex: 1,
      valueGetter: (value) => value || '',
    },
    {
      field: 'client_name',
      headerName: 'Client',
      width: 200,
      valueGetter: (value, row) => {
        const cp = row as ClientProject;
        return getClientName(cp.client_id);
      },
    },
    {
      field: 'active',
      headerName: 'Status',
      width: 120,
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
      width: 150,
      getActions: (params: GridRowParams) => {
        const cp = params.row as ClientProject;
        const actions = [];

        if (canManage) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedClientProject(cp);
                setFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget(cp);
                setDeleteDialogOpen(true);
              }}
            />
          );
        }

        return actions;
      },
    },
  ];

  if (!canManage && !hasPermission('sample:read')) {
    return (
      <Box>
        <Alert severity="warning">
          You do not have permission to view client projects.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Client Projects</Typography>
        {canManage && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setSelectedClientProject(null);
              setFormOpen(true);
            }}
          >
            Create Client Project
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box mb={2} display="flex" gap={2}>
        <TextField
          fullWidth
          size="small"
          placeholder="Search by name, description, or client..."
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
        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Filter by Client</InputLabel>
          <Select
            value={clientFilter}
            onChange={(e) => {
              setClientFilter(e.target.value);
              setPaginationModel({ page: 0, pageSize: paginationModel.pageSize });
            }}
            label="Filter by Client"
          >
            <MenuItem value="">All Clients</MenuItem>
            {clients.map((client) => (
              <MenuItem key={client.id} value={client.id}>
                {client.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {loading ? (
        <Box display="flex" justifyContent="center" p={3}>
          <CircularProgress />
        </Box>
      ) : (
        <DataGrid
          rows={filteredClientProjects}
          columns={columns}
          getRowId={(row) => row.id}
          autoHeight
          disableRowSelectionOnClick
          paginationModel={paginationModel}
          onPaginationModelChange={setPaginationModel}
          pageSizeOptions={[10, 25, 50, 100]}
          rowCount={total}
          paginationMode="server"
          sx={{
            '& .MuiDataGrid-cell': {
              display: 'flex',
              alignItems: 'center',
            },
          }}
        />
      )}

      <ClientProjectForm
        open={formOpen}
        clientProject={selectedClientProject}
        existingNames={existingNames}
        onClose={() => {
          setFormOpen(false);
          setSelectedClientProject(null);
        }}
        onSubmit={selectedClientProject ? handleUpdate : handleCreate}
      />

      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Client Project</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete "{deleteTarget?.name}"? This action cannot be undone.
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

export default ClientProjects;

