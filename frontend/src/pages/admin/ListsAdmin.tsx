import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Chip,
  Snackbar,
} from '@mui/material';
import MuiAlert, { AlertProps } from '@mui/material/Alert';
import {
  Add,
  Edit,
  Delete,
  ArrowBack,
  ChevronRight,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';
import ListFormDialog from './ListFormDialog';
import EntryFormDialog from './EntryFormDialog';
import { slugToDisplayName } from '../../utils/listUtils';

interface ListEntry {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  created_at?: string;
  modified_at?: string;
  list_id: string;
}

interface List {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  created_at?: string;
  modified_at?: string;
  entries: ListEntry[];
}

const AlertComponent = React.forwardRef<HTMLDivElement, AlertProps>(function Alert(props, ref) {
  return <MuiAlert elevation={6} ref={ref} variant="filled" {...props} />;
});

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleString();
}

const ListsAdmin: React.FC = () => {
  const { hasPermission } = useUser();
  const [lists, setLists] = useState<List[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedList, setSelectedList] = useState<List | null>(null);
  const [listFormOpen, setListFormOpen] = useState(false);
  const [listFormList, setListFormList] = useState<List | null>(null);
  const [entryFormOpen, setEntryFormOpen] = useState(false);
  const [selectedEntry, setSelectedEntry] = useState<ListEntry | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{
    type: 'list' | 'entry';
    id: string;
    name: string;
  } | null>(null);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning';
  }>({ open: false, message: '', severity: 'success' });

  const canEdit = hasPermission('config:edit');
  const isAdmin = hasPermission('config:edit');

  const loadLists = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getLists();
      setLists(data || []);
      if (selectedList) {
        const updated = (data || []).find((l: List) => l.id === selectedList.id);
        setSelectedList(updated || null);
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Failed to load lists';
      setError(msg);
      setSnackbar({ open: true, message: msg, severity: 'error' });
    } finally {
      setLoading(false);
    }
  }, [selectedList?.id]);

  useEffect(() => {
    loadLists();
  }, []);

  const handleSnackbarClose = () => {
    setSnackbar((prev) => ({ ...prev, open: false }));
  };

  const handleCreateList = async (data: { name: string; description?: string }) => {
    try {
      await apiService.createList(data);
      setSnackbar({ open: true, message: 'List created', severity: 'success' });
      setListFormOpen(false);
      await loadLists();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to create list',
        severity: 'error',
      });
      throw err;
    }
  };

  const handleUpdateList = async (data: { name: string; description?: string }) => {
    if (!listFormList) return;
    try {
      await apiService.updateList(listFormList.id, data);
      setSnackbar({ open: true, message: 'List updated', severity: 'success' });
      setListFormOpen(false);
      setListFormList(null);
      await loadLists();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to update list',
        severity: 'error',
      });
      throw err;
    }
  };

  const handleDeleteList = async () => {
    if (!deleteTarget || deleteTarget.type !== 'list') return;
    try {
      await apiService.deleteList(deleteTarget.id);
      setSnackbar({ open: true, message: 'List deleted', severity: 'success' });
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      setSelectedList(null);
      await loadLists();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to delete list',
        severity: 'error',
      });
      setDeleteDialogOpen(false);
    }
  };

  const handleCreateEntry = async (data: {
    name: string;
    description?: string;
    active: boolean;
  }) => {
    if (!selectedList) return;
    try {
      await apiService.createListEntry(selectedList.name, data);
      setSnackbar({ open: true, message: 'Entry created', severity: 'success' });
      setEntryFormOpen(false);
      await loadLists();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to create entry',
        severity: 'error',
      });
      throw err;
    }
  };

  const handleUpdateEntry = async (data: {
    name: string;
    description?: string;
    active: boolean;
  }) => {
    if (!selectedList || !selectedEntry) return;
    try {
      await apiService.updateListEntry(selectedList.name, selectedEntry.id, data);
      setSnackbar({ open: true, message: 'Entry updated', severity: 'success' });
      setEntryFormOpen(false);
      setSelectedEntry(null);
      await loadLists();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to update entry',
        severity: 'error',
      });
      throw err;
    }
  };

  const handleDeleteEntry = async () => {
    if (!deleteTarget || deleteTarget.type !== 'entry' || !selectedList) return;
    try {
      await apiService.deleteListEntry(selectedList.name, deleteTarget.id);
      setSnackbar({ open: true, message: 'Entry deleted', severity: 'success' });
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      await loadLists();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.detail || 'Failed to delete entry',
        severity: 'error',
      });
      setDeleteDialogOpen(false);
    }
  };

  const openEntriesForList = (list: List) => {
    setSelectedList(list);
  };

  const existingListNames = lists.map((l) => l.name);

  const listColumns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Name',
      width: 220,
      flex: 1,
      renderCell: (params) => (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <ChevronRight color="action" fontSize="small" />
          {slugToDisplayName((params.row as List).name)}
        </Box>
      ),
    },
    {
      field: 'description',
      headerName: 'Description',
      flex: 1,
      minWidth: 200,
      valueGetter: (value) => value || '—',
    },
    {
      field: 'created_at',
      headerName: 'Created At',
      width: 170,
      valueFormatter: (value) => formatDate(value as string),
    },
    ...(canEdit
      ? [
          {
            field: 'actions',
            type: 'actions' as const,
            headerName: 'Actions',
            width: 140,
            getActions: (params: GridRowParams) => {
              const list = params.row as List;
              return [
                <GridActionsCellItem
                  key="edit"
                  icon={<Edit />}
                  label="Edit"
                  onClick={(e) => {
                    e.stopPropagation();
                    setListFormList(list);
                    setListFormOpen(true);
                  }}
                />,
                <GridActionsCellItem
                  key="delete"
                  icon={<Delete />}
                  label="Delete"
                  onClick={(e) => {
                    e.stopPropagation();
                    setDeleteTarget({
                      type: 'list',
                      id: list.id,
                      name: slugToDisplayName(list.name),
                    });
                    setDeleteDialogOpen(true);
                  }}
                />,
              ];
            },
          },
        ]
      : []),
  ];

  const entryColumns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Value',
      width: 200,
      flex: 1,
    },
    {
      field: 'description',
      headerName: 'Description',
      flex: 1,
      minWidth: 200,
      valueGetter: (value) => value || '—',
    },
    {
      field: 'active',
      headerName: 'Is Active',
      width: 110,
      renderCell: (params) => (
        <Chip
          label={params.value ? 'Active' : 'Inactive'}
          size="small"
          color={params.value ? 'success' : 'default'}
        />
      ),
    },
    ...(canEdit && selectedList
      ? [
          {
            field: 'actions',
            type: 'actions' as const,
            headerName: 'Actions',
            width: 140,
            getActions: (params: GridRowParams) => {
              const entry = params.row as ListEntry;
              return [
                <GridActionsCellItem
                  key="edit"
                  icon={<Edit />}
                  label="Edit"
                  onClick={() => {
                    setSelectedEntry(entry);
                    setEntryFormOpen(true);
                  }}
                />,
                <GridActionsCellItem
                  key="delete"
                  icon={<Delete />}
                  label="Delete"
                  onClick={() => {
                    setDeleteTarget({
                      type: 'entry',
                      id: entry.id,
                      name: entry.name,
                    });
                    setDeleteDialogOpen(true);
                  }}
                />,
              ];
            },
          },
        ]
      : []),
  ];

  if (!isAdmin) {
    return (
      <Box>
        <Alert severity="warning">
          You do not have permission to view lists. Admin access is required.
        </Alert>
      </Box>
    );
  }

  if (selectedList) {
    return (
      <Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
          <Button
            startIcon={<ArrowBack />}
            onClick={() => {
              setSelectedList(null);
              setSelectedEntry(null);
            }}
            size="small"
          >
            Back to lists
          </Button>
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5">
            Entries: {slugToDisplayName(selectedList.name)}
          </Typography>
          {canEdit && (
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => {
                setSelectedEntry(null);
                setEntryFormOpen(true);
              }}
            >
              Add Entry
            </Button>
          )}
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {selectedList.entries.length === 0 ? (
          <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
            No entries in this list. {canEdit && 'Click "Add Entry" to create one.'}
          </Typography>
        ) : (
          <Box sx={{ height: 500, width: '100%' }}>
            <DataGrid
              rows={selectedList.entries}
              columns={entryColumns}
              getRowId={(row) => row.id}
              pageSizeOptions={[10, 25, 50]}
              initialState={{
                pagination: { paginationModel: { page: 0, pageSize: 10 } },
              }}
              disableRowSelectionOnClick
            />
          </Box>
        )}

        <EntryFormDialog
          open={entryFormOpen}
          listName={slugToDisplayName(selectedList.name)}
          entry={selectedEntry}
          existingNames={selectedList.entries.map((e) => e.name)}
          onClose={() => {
            setEntryFormOpen(false);
            setSelectedEntry(null);
          }}
          onSubmit={selectedEntry ? handleUpdateEntry : handleCreateEntry}
        />

        <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
          <DialogTitle>Confirm Delete</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Delete entry <strong>{deleteTarget?.name}</strong>? This cannot be undone.
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
            <Button color="error" variant="contained" onClick={handleDeleteEntry}>
              Delete
            </Button>
          </DialogActions>
        </Dialog>

        <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={handleSnackbarClose}>
          <AlertComponent onClose={handleSnackbarClose} severity={snackbar.severity}>
            {snackbar.message}
          </AlertComponent>
        </Snackbar>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Lists</Typography>
        {canEdit && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setListFormList(null);
              setListFormOpen(true);
            }}
          >
            Create List
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
          <CircularProgress />
        </Box>
      ) : (
        <Box sx={{ height: 560, width: '100%' }}>
          <DataGrid
            rows={lists}
            columns={listColumns}
            getRowId={(row) => row.id}
            pageSizeOptions={[10, 25, 50]}
            initialState={{
              pagination: { paginationModel: { page: 0, pageSize: 10 } },
            }}
            disableRowSelectionOnClick
            onRowClick={(params) => openEntriesForList(params.row as List)}
            sx={{
              '& .MuiDataGrid-row': { cursor: 'pointer' },
            }}
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
                  <Typography>No lists found</Typography>
                </Box>
              ),
            }}
          />
        </Box>
      )}

      <ListFormDialog
        open={listFormOpen}
        list={listFormList}
        existingNames={existingListNames}
        onClose={() => {
          setListFormOpen(false);
          setListFormList(null);
        }}
        onSubmit={listFormList ? handleUpdateList : handleCreateList}
      />

      {deleteTarget?.type === 'list' && (
        <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
          <DialogTitle>Confirm Delete</DialogTitle>
          <DialogContent>
            <DialogContentText>
              Delete list <strong>{deleteTarget?.name}</strong>? This will also delete all entries in
              this list. This action cannot be undone.
            </DialogContentText>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
            <Button color="error" variant="contained" onClick={handleDeleteList}>
              Delete
            </Button>
          </DialogActions>
        </Dialog>
      )}

      <Snackbar open={snackbar.open} autoHideDuration={6000} onClose={handleSnackbarClose}>
        <AlertComponent onClose={handleSnackbarClose} severity={snackbar.severity}>
          {snackbar.message}
        </AlertComponent>
      </Snackbar>
    </Box>
  );
};

export default ListsAdmin;
