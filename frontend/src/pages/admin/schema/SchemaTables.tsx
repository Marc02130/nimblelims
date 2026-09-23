import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
} from '@mui/material';
import { DataGrid, GridActionsCellItem, GridColDef } from '@mui/x-data-grid';
import { apiService, ApiService } from '../../../services/apiService';
import { useUser } from '../../../contexts/UserContext';
import { FillHeightPage, FillHeightTable } from '../../../components/common/FillHeightPage';
import SchemaChrome from './SchemaChrome';

interface TableRow {
  id: string;
  display_name: string;
  physical_name: string;
  kind: string;
  status: string;
  column_count: number;
}

const SchemaTables: React.FC = () => {
  const { hasPermission } = useUser();
  const canEdit = hasPermission('schema:edit');
  const [rows, setRows] = useState<TableRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [displayName, setDisplayName] = useState('');

  const load = async () => {
    try {
      setLoading(true);
      const data = await apiService.getSchemaTables();
      setRows(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      setError(ApiService.formatError(err, 'Failed to load tables'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const columns: GridColDef[] = [
    { field: 'display_name', headerName: 'Table', flex: 1, minWidth: 160 },
    { field: 'physical_name', headerName: 'Database name', flex: 1, minWidth: 160 },
    { field: 'kind', headerName: 'Kind', width: 100 },
    { field: 'status', headerName: 'Status', width: 120 },
    { field: 'column_count', headerName: 'Fields', width: 100 },
    {
      field: 'actions',
      type: 'actions',
      width: 120,
      getActions: (params) => {
        if (!canEdit || params.row.kind === 'core') return [];
        return [
          <GridActionsCellItem
            key="dep"
            label="Deprecate"
            showInMenu
            onClick={() => void apiService.deprecateSchemaTable(params.id as string).then(load)}
          />,
          <GridActionsCellItem
            key="drop"
            label="Drop (confirm)"
            showInMenu
            onClick={() => {
              if (window.confirm('Drop this table and its data? This is audited.')) {
                void apiService.dropSchemaTable(params.id as string).then(load).catch((e) =>
                  setError(ApiService.formatError(e, 'Drop failed')),
                );
              }
            }}
          />,
        ];
      },
    },
  ];

  return (
    <FillHeightPage
      header={
        <SchemaChrome>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          <Box display="flex" justifyContent="flex-end" mb={1}>
            {canEdit && (
              <Button variant="contained" onClick={() => setOpen(true)}>
                Add table
              </Button>
            )}
          </Box>
        </SchemaChrome>
      }
    >
      <FillHeightTable>
        <DataGrid rows={rows} columns={columns} loading={loading} pageSizeOptions={[10, 25]} />
      </FillHeightTable>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Add table</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Display name"
            fullWidth
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            helperText="Creates a real database table with id, client, timestamps, and active."
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={!displayName.trim()}
            onClick={async () => {
              try {
                await apiService.createSchemaTable({ display_name: displayName.trim() });
                setOpen(false);
                setDisplayName('');
                await load();
              } catch (err) {
                setError(ApiService.formatError(err, 'Could not create table'));
              }
            }}
          >
            Create real table
          </Button>
        </DialogActions>
      </Dialog>
    </FillHeightPage>
  );
};

export default SchemaTables;
