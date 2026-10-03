import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Tooltip,
} from '@mui/material';
import ViewColumnIcon from '@mui/icons-material/ViewColumn';
import { DataGrid, GridActionsCellItem, GridColDef } from '@mui/x-data-grid';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiService, ApiService } from '../../../services/apiService';
import { useUser } from '../../../contexts/UserContext';
import { FillHeightPage, FillHeightTable } from '../../../components/common/FillHeightPage';
import SchemaChrome from './SchemaChrome';
import {
  SchemaTableRow,
  sortTables,
  tableCategory,
  tableCategoryLabel,
  tableSourceLabel,
} from './schemaBrowser';

const SchemaTables: React.FC = () => {
  const { hasPermission } = useUser();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const canEdit = hasPermission('schema:edit');
  const [rows, setRows] = useState<SchemaTableRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [displayName, setDisplayName] = useState('');
  const fromCustomFields = searchParams.get('from') === 'custom-fields';

  const load = async () => {
    try {
      setLoading(true);
      const data = await apiService.getSchemaTables();
      setRows(sortTables(Array.isArray(data) ? (data as SchemaTableRow[]) : []));
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

  const browse = (id: string) => navigate(`/admin/schema/columns?table=${id}`);

  const columns: GridColDef<SchemaTableRow>[] = [
    { field: 'display_name', headerName: 'Table', flex: 1, minWidth: 180 },
    {
      field: 'category',
      headerName: 'Scope',
      width: 110,
      sortable: false,
      renderCell: (params) => (
        <Chip
          size="small"
          label={tableCategoryLabel(params.row)}
          color={tableCategory(params.row) === 'system' ? 'default' : 'primary'}
          variant={tableCategory(params.row) === 'system' ? 'outlined' : 'filled'}
        />
      ),
    },
    {
      field: 'kind',
      headerName: 'Source',
      width: 120,
      valueGetter: (_value, row) => tableSourceLabel(row),
    },
    { field: 'physical_name', headerName: 'Database name', flex: 1, minWidth: 160 },
    { field: 'status', headerName: 'Status', width: 110 },
    { field: 'column_count', headerName: 'Fields', width: 90 },
    { field: 'relation_count', headerName: 'Links', width: 80 },
    {
      field: 'actions',
      type: 'actions',
      width: 110,
      getActions: (params) => {
        const actions = [
          <GridActionsCellItem
            key="browse"
            icon={
              <Tooltip title="Browse fields">
                <ViewColumnIcon />
              </Tooltip>
            }
            label="Browse fields"
            onClick={() => browse(params.id as string)}
          />,
        ];
        if (!canEdit || !params.row.can_remove) return actions;
        return [
          ...actions,
          <GridActionsCellItem
            key="dep"
            label="Deprecate"
            showInMenu
            onClick={() =>
              void apiService
                .deprecateSchemaTable(params.id as string)
                .then(load)
                .catch((e) => setError(ApiService.formatError(e, 'Deprecate failed')))
            }
          />,
          <GridActionsCellItem
            key="drop"
            label="Drop (confirm)"
            showInMenu
            onClick={() => {
              if (window.confirm('Drop this table and its data? This is audited.')) {
                void apiService
                  .dropSchemaTable(params.id as string)
                  .then(load)
                  .catch((e) => setError(ApiService.formatError(e, 'Drop failed')));
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
          {fromCustomFields && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Custom Fields are removed. A field is a column on a table — add a real field under
              Schema → Columns.
            </Alert>
          )}
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1} gap={2}>
            <Box color="text.secondary" fontSize={14}>
              <strong>Lab</strong> tables hold sample-centric data. <strong>System</strong> tables are
              reference data (lists, units, types) and are read-only here. Engine internals are not
              listed.
            </Box>
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
        <DataGrid
          rows={rows}
          columns={columns}
          loading={loading}
          pageSizeOptions={[25, 50]}
          initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
          onRowDoubleClick={(params) => browse(params.id as string)}
        />
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
