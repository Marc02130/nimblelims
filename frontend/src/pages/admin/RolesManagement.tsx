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
  Tooltip,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Search,
  Clear,
  ExpandMore,
  ExpandLess,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';
import RoleFormDialog from './RoleFormDialog';

interface Permission {
  id: string;
  name: string;
  description?: string;
}

interface Role {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  created_at: string;
  modified_at: string;
  permissions?: Permission[];
  permissions_count?: number;
}

const RolesManagement: React.FC = () => {
  const { user, hasPermission } = useUser();
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [formOpen, setFormOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Role | null>(null);

  const canEdit = hasPermission('user:manage') || hasPermission('config:edit');

  useEffect(() => {
    loadRoles();
  }, []);

  const loadRoles = async () => {
    try {
      setLoading(true);
      setError(null);
      const rolesData = await apiService.getRoles();
      
      // Load permissions for each role
      const rolesWithPermissions = await Promise.all(
        (rolesData || []).map(async (role: Role) => {
          try {
            const permissions = await apiService.getRolePermissions(role.id);
            return {
              ...role,
              permissions: permissions || [],
              permissions_count: permissions?.length || 0,
            };
          } catch {
            // If endpoint doesn't exist, use permissions from role if available
            return {
              ...role,
              permissions: role.permissions || [],
              permissions_count: role.permissions?.length || 0,
            };
          }
        })
      );
      
      setRoles(rolesWithPermissions);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view roles management');
      } else {
        setError(err.response?.data?.detail || 'Failed to load roles');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredRoles = useMemo(() => {
    if (!searchTerm) return roles;
    const term = searchTerm.toLowerCase();
    return roles.filter(
      (role) =>
        role.name.toLowerCase().includes(term) ||
        role.description?.toLowerCase().includes(term) ||
        role.permissions?.some((p) =>
          p.name.toLowerCase().includes(term) ||
          p.description?.toLowerCase().includes(term)
        )
    );
  }, [roles, searchTerm]);

  const handleCreate = async (data: {
    name: string;
    description?: string;
    permission_ids: string[];
  }) => {
    const { permission_ids, ...roleData } = data;
    const role = await apiService.createRole(roleData);
    
    // Assign permissions
    if (permission_ids.length > 0) {
      await apiService.updateRolePermissions(role.id, permission_ids);
    }
    
    await loadRoles();
  };

  const handleUpdate = async (data: {
    name: string;
    description?: string;
    permission_ids: string[];
  }) => {
    if (!selectedRole) return;
    
    const { permission_ids, ...roleData } = data;
    await apiService.updateRole(selectedRole.id, roleData);
    
    // Update permissions
    await apiService.updateRolePermissions(selectedRole.id, permission_ids);
    
    await loadRoles();
    setSelectedRole(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteRole(deleteTarget.id);
      await loadRoles();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      if (err.response?.status === 400) {
        setError(err.response?.data?.detail || 'Cannot delete role that is assigned to users');
      } else {
        setError(err.response?.data?.detail || 'Failed to delete role');
      }
      setDeleteDialogOpen(false);
    }
  };

  const toggleRowExpansion = (roleId: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(roleId)) {
      newExpanded.delete(roleId);
    } else {
      newExpanded.add(roleId);
    }
    setExpandedRows(newExpanded);
  };

  const columns: GridColDef[] = [
    {
      field: 'expand',
      headerName: '',
      width: 60,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const role = params.row as Role;
        const isExpanded = expandedRows.has(role.id);
        const hasPermissions = (role.permissions_count || 0) > 0;
        
        if (!hasPermissions && !isExpanded) return null;
        
        return (
          <Tooltip title={isExpanded ? 'Collapse permissions' : 'Expand permissions'}>
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                toggleRowExpansion(role.id);
              }}
            >
              {isExpanded ? <ExpandLess /> : <ExpandMore />}
            </IconButton>
          </Tooltip>
        );
      },
    },
    {
      field: 'name',
      headerName: 'Role Name',
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
      field: 'permissions_count',
      headerName: 'Permissions',
      width: 120,
      valueGetter: (value, row) => (row as Role).permissions_count || 0,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={params.value === 0 ? 'default' : 'primary'}
        />
      ),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 120,
      getActions: (params: GridRowParams) => {
        const role = params.row as Role;
        const actions = [];

        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedRole(role);
                setFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget(role);
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
          You do not have permission to view roles management.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Roles & Permissions Management</Typography>
        {canEdit && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setSelectedRole(null);
              setFormOpen(true);
            }}
          >
            Create Role
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
          placeholder="Search roles and permissions..."
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
        <>
          <Box sx={{ height: 600, width: '100%', mb: 2 }}>
            <DataGrid
              rows={filteredRoles}
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
                    <Typography>No roles found</Typography>
                  </Box>
                ),
              }}
            />
          </Box>

          {/* Expanded rows for permissions */}
          {Array.from(expandedRows).map((roleId) => {
            const role = roles.find((r) => r.id === roleId);
            if (!role) return null;

            return (
              <Box
                key={`permissions-${roleId}`}
                sx={{
                  mt: 2,
                  mb: 3,
                  p: 2,
                  bgcolor: 'background.paper',
                  borderRadius: 1,
                  border: 1,
                  borderColor: 'divider',
                }}
              >
                <Typography variant="h6" gutterBottom>
                  Permissions for {role.name}
                </Typography>
                {role.permissions && role.permissions.length > 0 ? (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {role.permissions.map((permission) => (
                      <Chip
                        key={permission.id}
                        label={permission.name}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    ))}
                  </Box>
                ) : (
                  <Typography color="text.secondary">
                    No permissions assigned to this role
                  </Typography>
                )}
              </Box>
            );
          })}
        </>
      )}

      {/* Role Form Dialog */}
      <RoleFormDialog
        open={formOpen}
        role={selectedRole}
        existingNames={roles.map((r) => r.name)}
        onClose={() => {
          setFormOpen(false);
          setSelectedRole(null);
        }}
        onSubmit={selectedRole ? handleUpdate : handleCreate}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete role <strong>{deleteTarget?.name}</strong>?
            <Box component="span" sx={{ display: 'block', mt: 1, color: 'warning.main' }}>
              This action cannot be undone. If this role is assigned to any users, the deletion will fail.
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

export default RolesManagement;

