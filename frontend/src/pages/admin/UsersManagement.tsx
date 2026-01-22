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
  FormControlLabel,
  Switch,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Search,
  Clear,
  CheckCircle,
  Cancel,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';
import UserFormDialog from './UserFormDialog';

interface User {
  id: string;
  name: string;
  description?: string;
  username: string;
  email: string;
  role_id: string;
  role?: {
    id: string;
    name: string;
  };
  client_id?: string;
  client?: {
    id: string;
    name: string;
  };
  last_login?: string;
  active: boolean;
  created_at: string;
  modified_at: string;
}

const UsersManagement: React.FC = () => {
  const { user, hasPermission } = useUser();
  const [users, setUsers] = useState<User[]>([]);
  const [roles, setRoles] = useState<Array<{ id: string; name: string }>>([]);
  const [clients, setClients] = useState<Array<{ id: string; name: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [showInactive, setShowInactive] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<User | null>(null);

  const canEdit = hasPermission('user:manage') || hasPermission('config:edit');

  useEffect(() => {
    loadData();
  }, [showInactive]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [usersData, rolesData, clientsData] = await Promise.all([
        apiService.getUsers({ include_inactive: showInactive }),
        apiService.getRoles(),
        apiService.getClients(),
      ]);

      setUsers(usersData || []);
      setRoles(rolesData || []);
      setClients(clientsData || []);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view users management');
      } else {
        setError(err.response?.data?.detail || 'Failed to load users');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredUsers = useMemo(() => {
    if (!searchTerm) return users;
    const term = searchTerm.toLowerCase();
    return users.filter(
      (user) =>
        user.username.toLowerCase().includes(term) ||
        user.email.toLowerCase().includes(term) ||
        user.role?.name.toLowerCase().includes(term) ||
        user.client?.name.toLowerCase().includes(term)
    );
  }, [users, searchTerm]);

  const handleCreate = async (data: {
    name?: string;
    description?: string;
    username: string;
    email: string;
    password?: string;
    role_id: string;
    client_id?: string;
  }) => {
    await apiService.createUser(data);
    await loadData();
  };

  const handleUpdate = async (data: {
    name?: string;
    description?: string;
    username: string;
    email: string;
    password?: string;
    role_id: string;
    client_id?: string;
    active?: boolean;
  }) => {
    if (!selectedUser) return;
    await apiService.updateUser(selectedUser.id, data);
    await loadData();
    setSelectedUser(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteUser(deleteTarget.id);
      await loadData();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      if (err.response?.status === 400) {
        setError(err.response?.data?.detail || 'Cannot delete user with active assignments');
      } else {
        setError(err.response?.data?.detail || 'Failed to delete user');
      }
      setDeleteDialogOpen(false);
    }
  };

  const getRoleName = (roleId: string) => {
    const role = roles.find((r) => r.id === roleId);
    return role?.name || 'Unknown';
  };

  const getClientName = (clientId?: string) => {
    if (!clientId) return 'N/A';
    const client = clients.find((c) => c.id === clientId);
    return client?.name || 'Unknown';
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  const columns: GridColDef[] = [
    {
      field: 'username',
      headerName: 'Username',
      width: 150,
      flex: 1,
    },
    {
      field: 'email',
      headerName: 'Email',
      width: 200,
      flex: 1,
    },
    {
      field: 'role',
      headerName: 'Role',
      width: 150,
      valueGetter: (value, row) => getRoleName((row as User).role_id),
    },
    {
      field: 'client',
      headerName: 'Client',
      width: 150,
      valueGetter: (value, row) => getClientName((row as User).client_id),
    },
    {
      field: 'last_login',
      headerName: 'Last Login',
      width: 180,
      valueGetter: (value, row) => formatDate((row as User).last_login),
    },
    {
      field: 'active',
      headerName: 'Status',
      width: 100,
      renderCell: (params) => {
        const userRow = params.row as User;
        return (
          <Chip
            icon={userRow.active ? <CheckCircle /> : <Cancel />}
            label={userRow.active ? 'Active' : 'Inactive'}
            color={userRow.active ? 'success' : 'default'}
            size="small"
          />
        );
      },
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 120,
      getActions: (params: GridRowParams) => {
        const userRow = params.row as User;
        const actions = [];

        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedUser(userRow);
                setFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget(userRow);
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
          You do not have permission to view users management.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Users Management</Typography>
        {canEdit && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setSelectedUser(null);
              setFormOpen(true);
            }}
          >
            Create User
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ mb: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
        <TextField
          sx={{ flex: 1 }}
          placeholder="Search users..."
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
        <FormControlLabel
          control={
            <Switch
              checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              color="primary"
            />
          }
          label="Show inactive"
        />
      </Box>

      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <CircularProgress />
        </Box>
      ) : (
        <Box sx={{ height: 600, width: '100%' }}>
          <DataGrid
            rows={filteredUsers}
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
                  <Typography>No users found</Typography>
                </Box>
              ),
            }}
          />
        </Box>
      )}

      {/* User Form Dialog */}
      <UserFormDialog
        open={formOpen}
        user={selectedUser}
        existingUsernames={users.map((u) => u.username)}
        existingEmails={users.map((u) => u.email)}
        existingNames={users.map((u) => u.name)}
        roles={roles}
        clients={clients}
        onClose={() => {
          setFormOpen(false);
          setSelectedUser(null);
        }}
        onSubmit={selectedUser ? handleUpdate : handleCreate}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete user <strong>{deleteTarget?.username}</strong>?
            <Box component="span" sx={{ display: 'block', mt: 1, color: 'warning.main' }}>
              This action cannot be undone. If this user has active assignments (samples, tests, results, etc.), the deletion will fail.
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

export default UsersManagement;

