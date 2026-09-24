import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Switch,
  TextField,
} from '@mui/material';
import { DataGrid, GridActionsCellItem, GridColDef } from '@mui/x-data-grid';
import { apiService, ApiService } from '../../../services/apiService';
import { useUser } from '../../../contexts/UserContext';
import { FillHeightPage, FillHeightTable } from '../../../components/common/FillHeightPage';
import SchemaChrome from './SchemaChrome';

const TYPES = [
  { value: 'text', label: 'Text' },
  { value: 'numeric', label: 'Number' },
  { value: 'integer', label: 'Whole number' },
  { value: 'boolean', label: 'Yes/No' },
  { value: 'date', label: 'Date' },
  { value: 'timestamptz', label: 'Date and time' },
  { value: 'list', label: 'List' },
];

const HINTS = [
  { value: '', label: 'None' },
  { value: 'barcode', label: 'Barcode' },
  { value: 'container', label: 'Container (vessel)' },
  { value: 'parent', label: 'Parent sample' },
  { value: 'sample_type', label: 'Sample type' },
];

interface TableOpt {
  id: string;
  display_name: string;
}

const SchemaColumns: React.FC = () => {
  const { hasPermission } = useUser();
  const canEdit = hasPermission('schema:edit');
  const [tables, setTables] = useState<TableOpt[]>([]);
  const [tableId, setTableId] = useState('');
  const [rows, setRows] = useState<any[]>([]);
  const [lists, setLists] = useState<Array<{ id: string; name: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    display_name: '',
    data_type: 'text',
    nullable: true,
    list_id: '',
    sop_hint: '',
  });

  const loadTables = async () => {
    try {
      const data = await apiService.getSchemaTables();
      const list = Array.isArray(data) ? data : [];
      setTables(list);
      if (!tableId && list[0]) setTableId(list[0].id);
    } catch (err) {
      setError(ApiService.formatError(err, 'Failed to load tables'));
    }
  };

  const loadCols = async (id: string) => {
    if (!id) return;
    try {
      setLoading(true);
      const data = await apiService.getSchemaColumns(id);
      setRows(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err) {
      setError(ApiService.formatError(err, 'Failed to load fields'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadTables();
    apiService
      .getLists()
      .then((d) => setLists(Array.isArray(d) ? d : []))
      .catch(() => setLists([]));
  }, []);

  useEffect(() => {
    if (tableId) void loadCols(tableId);
  }, [tableId]);

  const columns: GridColDef[] = [
    { field: 'display_name', headerName: 'Field', flex: 1, minWidth: 140 },
    { field: 'physical_name', headerName: 'Database name', flex: 1, minWidth: 140 },
    { field: 'data_type', headerName: 'Type', width: 120 },
    { field: 'nullable', headerName: 'Optional', width: 100, type: 'boolean' },
    { field: 'sop_hint', headerName: 'SOP name', width: 130 },
    { field: 'status', headerName: 'Status', width: 110 },
    {
      field: 'actions',
      type: 'actions',
      width: 120,
      getActions: (params) => {
        if (!canEdit || params.row.is_identity || params.row.is_platform) return [];
        return [
          <GridActionsCellItem
            key="dep"
            label="Deprecate"
            showInMenu
            onClick={() =>
              void apiService.deprecateSchemaColumn(params.id as string).then(() => loadCols(tableId))
            }
          />,
          <GridActionsCellItem
            key="drop"
            label="Drop (confirm)"
            showInMenu
            onClick={() => {
              if (window.confirm('Drop this field? Data is removed. This is audited.')) {
                void apiService
                  .dropSchemaColumn(params.id as string)
                  .then(() => loadCols(tableId))
                  .catch((e) => setError(ApiService.formatError(e, 'Drop failed')));
              }
            }}
          />,
        ];
      },
    },
  ];

  const tableName = tables.find((t) => t.id === tableId)?.display_name || 'table';

  return (
    <FillHeightPage
      header={
        <SchemaChrome>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          <Box display="flex" gap={2} mb={1} alignItems="center">
            <FormControl size="small" sx={{ minWidth: 240 }}>
              <InputLabel>Table</InputLabel>
              <Select
                label="Table"
                value={tableId}
                onChange={(e) => setTableId(e.target.value)}
              >
                {tables.map((t) => (
                  <MenuItem key={t.id} value={t.id}>
                    {t.display_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            {canEdit && (
              <Button variant="contained" disabled={!tableId} onClick={() => setOpen(true)}>
                Add field
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
        <DialogTitle>Add field</DialogTitle>
        <DialogContent>
          <TextField
            margin="dense"
            label="Display name"
            fullWidth
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
          />
          <FormControl fullWidth margin="dense">
            <InputLabel>Type</InputLabel>
            <Select
              label="Type"
              value={form.data_type}
              onChange={(e) => setForm({ ...form, data_type: e.target.value })}
            >
              {TYPES.map((t) => (
                <MenuItem key={t.value} value={t.value}>
                  {t.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {form.data_type === 'list' && (
            <FormControl fullWidth margin="dense">
              <InputLabel>List source</InputLabel>
              <Select
                label="List source"
                value={form.list_id}
                onChange={(e) => setForm({ ...form, list_id: e.target.value })}
              >
                {lists.map((l) => (
                  <MenuItem key={l.id} value={l.id}>
                    {l.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
          <FormControl fullWidth margin="dense">
            <InputLabel>SOP name</InputLabel>
            <Select
              label="SOP name"
              value={form.sop_hint}
              onChange={(e) => setForm({ ...form, sop_hint: e.target.value })}
            >
              {HINTS.map((h) => (
                <MenuItem key={h.value} value={h.value}>
                  {h.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControlLabel
            control={
              <Switch
                checked={form.nullable}
                onChange={(e) => setForm({ ...form, nullable: e.target.checked })}
              />
            }
            label="Optional"
          />
          <Alert severity="info" sx={{ mt: 1 }}>
            Adds a real field on {tableName}. Not a custom-attribute JSON key.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            disabled={!form.display_name.trim() || (form.data_type === 'list' && !form.list_id)}
            onClick={async () => {
              try {
                await apiService.createSchemaColumn({
                  table_id: tableId,
                  display_name: form.display_name.trim(),
                  data_type: form.data_type,
                  nullable: form.nullable,
                  list_id: form.list_id || undefined,
                  sop_hint: form.sop_hint || undefined,
                });
                setOpen(false);
                setForm({
                  display_name: '',
                  data_type: 'text',
                  nullable: true,
                  list_id: '',
                  sop_hint: '',
                });
                await loadCols(tableId);
              } catch (err) {
                setError(ApiService.formatError(err, 'Could not add field'));
              }
            }}
          >
            Add real field
          </Button>
        </DialogActions>
      </Dialog>
    </FillHeightPage>
  );
};

export default SchemaColumns;
