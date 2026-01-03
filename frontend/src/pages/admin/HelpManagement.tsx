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
  DialogContentText,
  DialogActions,
  Chip,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
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
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';
import HelpEntryDialog from '../../components/admin/HelpEntryDialog';

interface HelpEntry {
  id: string;
  section: string;
  content: string;
  role_filter: string | null;
  active: boolean;
  created_at: string;
  modified_at: string;
}

interface Role {
  id: string;
  name: string;
}

const HelpManagement: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const { user, hasPermission } = useUser();
  const [helpEntries, setHelpEntries] = useState<HelpEntry[]>([]);
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [formOpen, setFormOpen] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<HelpEntry | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<HelpEntry | null>(null);
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(10);
  const [total, setTotal] = useState(0);

  const canEdit = hasPermission('config:edit');

  useEffect(() => {
    loadData();
  }, [page, pageSize, roleFilter]);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [rolesData, helpData] = await Promise.all([
        apiService.getRoles(),
        apiService.getHelp({
          // Only pass role filter if explicitly selected (not empty string)
          // If no filter, backend will show all entries for users with config:edit permission
          ...(roleFilter ? { role: roleFilter } : {}),
          page: page + 1,
          size: pageSize,
        }),
      ]);

      setRoles(rolesData || []);
      const entries = helpData.help_entries || helpData || [];
      setHelpEntries(entries);
      setTotal(helpData.total || entries.length);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view help management');
      } else {
        setError(err.response?.data?.detail || 'Failed to load help entries');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredEntries = useMemo(() => {
    let filtered = helpEntries;
    
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      filtered = filtered.filter(
        (entry) =>
          entry.section.toLowerCase().includes(term) ||
          entry.content.toLowerCase().includes(term) ||
          entry.role_filter?.toLowerCase().includes(term)
      );
    }
    
    return filtered;
  }, [helpEntries, searchTerm]);

  const handleCreate = async (data: {
    section?: string;
    content?: string;
    role_filter?: string | null;
    active?: boolean;
  }) => {
    // Validate required fields for create
    if (!data.section || !data.content) {
      throw new Error('Section and content are required');
    }
    await apiService.createHelpEntry({
      section: data.section,
      content: data.content,
      role_filter: data.role_filter || null,
    });
    await loadData();
  };

  const handleUpdate = async (data: {
    section?: string;
    content?: string;
    role_filter?: string | null;
    active?: boolean;
  }) => {
    if (!selectedEntry) return;
    await apiService.updateHelpEntry(selectedEntry.id, data);
    await loadData();
    setSelectedEntry(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteHelpEntry(deleteTarget.id);
      await loadData();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete help entry');
      setDeleteDialogOpen(false);
    }
  };

  const getRoleName = (roleFilter: string | null) => {
    if (!roleFilter) return 'Public';
    const role = roles.find((r) => {
      const roleSlug = r.name.toLowerCase().replace(' ', '-');
      return roleSlug === roleFilter;
    });
    return role?.name || roleFilter;
  };

  const columns: GridColDef[] = [
    {
      field: 'section',
      headerName: 'Section',
      width: 200,
      flex: isMobile ? 0 : 1.5,
    },
    {
      field: 'content',
      headerName: 'Content Preview',
      width: 300,
      flex: isMobile ? 0 : 2,
      valueGetter: (value, row) => {
        const content = (row as HelpEntry).content || '';
        if (!content) return '';
        const preview = content.length > 100 ? content.substring(0, 100) + '...' : content;
        return preview;
      },
      renderCell: (params) => (
        <Box
          sx={{
            maxWidth: 300,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
          title={params.row.content}
        >
          {params.value}
        </Box>
      ),
    },
    {
      field: 'role_filter',
      headerName: 'Role',
      width: 150,
      flex: isMobile ? 0 : 1,
      valueGetter: (value, row) => getRoleName((row as HelpEntry).role_filter),
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={params.row.role_filter ? 'primary' : 'default'}
          variant={params.row.role_filter ? 'filled' : 'outlined'}
        />
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
        const entry = params.row as HelpEntry;
        const actions = [];

        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedEntry(entry);
                setFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget(entry);
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
          You do not have permission to view help management. Requires config:edit permission.
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
        <Typography variant="h4">Help Management</Typography>
        {canEdit && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setSelectedEntry(null);
              setFormOpen(true);
            }}
          >
            Create Help Entry
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
          placeholder="Search by section or content..."
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
          <InputLabel>Filter by Role</InputLabel>
          <Select
            value={roleFilter}
            label="Filter by Role"
            onChange={(e) => {
              setRoleFilter(e.target.value);
              setPage(0);
            }}
          >
            <MenuItem value="">All Roles</MenuItem>
            {roles.map((role) => {
              const roleSlug = role.name.toLowerCase().replace(' ', '-');
              return (
                <MenuItem key={role.id} value={roleSlug}>
                  {role.name}
                </MenuItem>
              );
            })}
            <MenuItem value="null">Public (No Role)</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
          <CircularProgress />
        </Box>
      ) : (
        <Box sx={{ height: 600, width: '100%' }}>
          <DataGrid
            rows={filteredEntries}
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
            sx={{
              '& .MuiDataGrid-cell': {
                borderBottom: '1px solid rgba(224, 224, 224, 1)',
              },
            }}
          />
        </Box>
      )}

      <HelpEntryDialog
        open={formOpen}
        entry={selectedEntry}
        roles={roles}
        onClose={() => {
          setFormOpen(false);
          setSelectedEntry(null);
        }}
        onSubmit={selectedEntry ? handleUpdate : handleCreate}
      />

      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        aria-labelledby="delete-dialog-title"
        aria-describedby="delete-dialog-description"
      >
        <DialogTitle id="delete-dialog-title">Delete Help Entry</DialogTitle>
        <DialogContentText id="delete-dialog-description" sx={{ px: 3, pb: 2 }}>
          Are you sure you want to delete the help entry &quot;{deleteTarget?.section}&quot;? 
          This will soft-delete the entry (set it to inactive).
        </DialogContentText>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default HelpManagement;

