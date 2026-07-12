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
import { FillHeightPage, FillHeightTable } from '../../components/common/FillHeightPage';
import ListFormDialog from './ListFormDialog';
import EntryFormDialog from './EntryFormDialog';
import { slugToDisplayName } from '../../utils/listUtils';

interface ListEntry {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  created_at: string;
  modified_at: string;
  list_id: string;
}

interface List {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  created_at: string;
  modified_at: string;
  entries: ListEntry[];
}

const ListsManagement: React.FC = () => {
  const { user, hasPermission } = useUser();
  const [lists, setLists] = useState<List[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [listFormOpen, setListFormOpen] = useState(false);
  const [entryFormOpen, setEntryFormOpen] = useState(false);
  const [selectedList, setSelectedList] = useState<List | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<ListEntry | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ type: 'list' | 'entry'; id: string; name: string } | null>(null);

  const canEdit = hasPermission('config:edit');

  useEffect(() => {
    loadLists();
  }, []);

  const loadLists = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getLists();
      setLists(data || []);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view lists');
      } else {
        setError(err.response?.data?.detail || 'Failed to load lists');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredLists = useMemo(() => {
    if (!searchTerm) return lists;
    const term = searchTerm.toLowerCase();
    return lists.filter(
      (list) =>
        list.name.toLowerCase().includes(term) ||
        slugToDisplayName(list.name).toLowerCase().includes(term) ||
        list.description?.toLowerCase().includes(term) ||
        list.entries.some((entry) =>
          entry.name.toLowerCase().includes(term) ||
          entry.description?.toLowerCase().includes(term)
        )
    );
  }, [lists, searchTerm]);

  const handleCreateList = async (data: { name: string; description?: string }) => {
    await apiService.createList(data);
    await loadLists();
  };

  const handleUpdateList = async (data: { name: string; description?: string }) => {
    if (!selectedList) return;
    await apiService.updateList(selectedList.id, data);
    await loadLists();
    setSelectedList(null);
  };

  const handleDeleteList = async () => {
    if (!deleteTarget || deleteTarget.type !== 'list') return;
    try {
      await apiService.deleteList(deleteTarget.id);
      await loadLists();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete list');
      setDeleteDialogOpen(false);
    }
  };

  const handleCreateEntry = async (data: { name: string; description?: string; active: boolean }) => {
    if (!selectedList) return;
    await apiService.createListEntry(selectedList.name, data);
    await loadLists();
  };

  const handleUpdateEntry = async (data: { name: string; description?: string; active: boolean }) => {
    if (!selectedList || !selectedEntry) return;
    await apiService.updateListEntry(selectedList.name, selectedEntry.id, data);
    await loadLists();
    setSelectedEntry(null);
  };

  const handleDeleteEntry = async () => {
    if (!deleteTarget || deleteTarget.type !== 'entry' || !selectedList) return;
    try {
      await apiService.deleteListEntry(selectedList.name, deleteTarget.id);
      await loadLists();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete entry');
      setDeleteDialogOpen(false);
    }
  };

  const toggleRowExpansion = (listId: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(listId)) {
      newExpanded.delete(listId);
    } else {
      newExpanded.add(listId);
    }
    setExpandedRows(newExpanded);
  };

  const existingListNames = lists.map((l) => l.name);

  const columns: GridColDef[] = [
    {
      field: 'expand',
      headerName: '',
      width: 60,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const list = params.row as List;
        const isExpanded = expandedRows.has(list.id);
        // Always show expand button so users can add entries to empty lists
        return (
          <Tooltip title={isExpanded ? 'Collapse entries' : (list.entries.length === 0 ? 'Expand to add entries' : 'Expand entries')}>
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                toggleRowExpansion(list.id);
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
      headerName: 'List Name',
      width: 200,
      flex: 1,
      valueGetter: (value, row) => slugToDisplayName((row as List).name),
    },
    {
      field: 'description',
      headerName: 'Description',
      width: 250,
      flex: 1,
    },
    {
      field: 'entries_count',
      headerName: 'Entries',
      width: 100,
      valueGetter: (value, row) => (row as List).entries.length,
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
      width: 150,
      getActions: (params: GridRowParams) => {
        const list = params.row as List;
        const actions = [];

        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedList(list);
                setListFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget({
                  type: 'list',
                  id: list.id,
                  name: slugToDisplayName(list.name),
                });
                setDeleteDialogOpen(true);
              }}
            />
          );
        }

        return actions;
      },
    },
  ];

  const getEntryColumns = (list: List): GridColDef[] => [
    {
      field: 'name',
      headerName: 'Entry Name',
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
      width: 150,
      getActions: (params: GridRowParams) => {
        const entry = params.row as ListEntry;
        const actions = [];

        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedList(list);
                setSelectedEntry(entry);
                setEntryFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setSelectedList(list);
                setDeleteTarget({
                  type: 'entry',
                  id: entry.id,
                  name: entry.name,
                });
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
          You do not have permission to view lists management.
        </Alert>
      </Box>
    );
  }

  return (
    <FillHeightPage
      header={
        <>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h4">Lists Management</Typography>
            {canEdit && (
              <Button
                variant="contained"
                startIcon={<Add />}
                onClick={() => {
                  setSelectedList(null);
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

          <TextField
            fullWidth
            size="small"
            placeholder="Search lists and entries..."
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

          {/* Expanded entry sub-tables (capped height so main grid keeps fill-height) */}
          {expandedRows.size > 0 && (
            <Box sx={{ mt: 2, maxHeight: 220, overflowY: 'auto' }}>
              {Array.from(expandedRows).map((listId) => {
                const list = lists.find((l) => l.id === listId);
                if (!list) return null;

                return (
                  <Box
                    key={`entries-${listId}`}
                    sx={{
                      mb: 1,
                      p: 1.5,
                      bgcolor: 'background.paper',
                      borderRadius: 1,
                      border: 1,
                      borderColor: 'divider',
                    }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                      <Typography variant="subtitle2">
                        Entries for {slugToDisplayName(list.name)}
                      </Typography>
                      {canEdit && (
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<Add />}
                          onClick={() => {
                            setSelectedList(list);
                            setSelectedEntry(null);
                            setEntryFormOpen(true);
                          }}
                        >
                          Add Entry
                        </Button>
                      )}
                    </Box>
                    {list.entries.length === 0 ? (
                      <Typography color="text.secondary" sx={{ textAlign: 'center', py: 2 }}>
                        No entries in this list
                      </Typography>
                    ) : (
                      <Box sx={{ width: '100%', maxHeight: 200, minHeight: 120, overflow: 'auto' }}>
                        <DataGrid
                          rows={list.entries}
                          columns={getEntryColumns(list)}
                          getRowId={(row) => row.id}
                          pageSizeOptions={[10, 25, 50]}
                          initialState={{
                            pagination: {
                              paginationModel: { page: 0, pageSize: 10 },
                            },
                          }}
                          disableRowSelectionOnClick
                          sx={{
                            border: 0,
                            minHeight: 120,
                            maxHeight: 200,
                          }}
                        />
                      </Box>
                    )}
                  </Box>
                );
              })}
            </Box>
          )}
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
            rows={filteredLists}
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
                  <Typography>No lists found</Typography>
                </Box>
              ),
            }}
          />
        </FillHeightTable>
      )}

      <ListFormDialog
        open={listFormOpen}
        list={selectedList}
        existingNames={existingListNames}
        onClose={() => {
          setListFormOpen(false);
          setSelectedList(null);
        }}
        onSubmit={selectedList ? handleUpdateList : handleCreateList}
      />

      <EntryFormDialog
        open={entryFormOpen}
        listName={selectedList ? slugToDisplayName(selectedList.name) : ''}
        entry={selectedEntry}
        existingNames={selectedList?.entries.map((e) => e.name) || []}
        onClose={() => {
          setEntryFormOpen(false);
          setSelectedEntry(null);
          setSelectedList(null);
        }}
        onSubmit={selectedEntry ? handleUpdateEntry : handleCreateEntry}
      />

      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete {deleteTarget?.type === 'list' ? 'list' : 'entry'}{' '}
            <strong>{deleteTarget?.name}</strong>?
            {deleteTarget?.type === 'list' && (
              <Box component="span" sx={{ display: 'block', mt: 1, color: 'warning.main' }}>
                This will also delete all entries in this list. This action cannot be undone.
              </Box>
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={deleteTarget?.type === 'list' ? handleDeleteList : handleDeleteEntry} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </FillHeightPage>
  );
};

export default ListsManagement;
