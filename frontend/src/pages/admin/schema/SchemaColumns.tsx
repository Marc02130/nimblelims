import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  Link,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import LockIcon from '@mui/icons-material/Lock';
import { DataGrid, GridActionsCellItem, GridColDef } from '@mui/x-data-grid';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { apiService, ApiService } from '../../../services/apiService';
import { useUser } from '../../../contexts/UserContext';
import { FillHeightPage, FillHeightTable } from '../../../components/common/FillHeightPage';
import SchemaChrome from './SchemaChrome';
import {
  CARDINALITY_LABEL,
  SchemaColumnRow,
  SchemaTableRow,
  TableLinks,
  columnLockReason,
  columnScopeLabel,
  isColumnEditable,
  isSystemColumn,
  sortTables,
  tableCategoryLabel,
} from './schemaBrowser';

const TYPES = [
  { value: 'text', label: 'Text' },
  { value: 'numeric', label: 'Number' },
  { value: 'integer', label: 'Whole number' },
  { value: 'boolean', label: 'Yes/No' },
  { value: 'date', label: 'Date' },
  { value: 'timestamptz', label: 'Date and time' },
  { value: 'list', label: 'List' },
];

const TYPE_LABEL: Record<string, string> = {
  text: 'Text',
  numeric: 'Number',
  integer: 'Whole number',
  boolean: 'Yes/No',
  date: 'Date',
  timestamptz: 'Date and time',
  list: 'List',
  uuid: 'Key',
  jsonb: 'Payload (JSON)',
  other: 'Other',
};

const HINTS = [
  { value: '', label: 'None' },
  { value: 'barcode', label: 'Barcode' },
  { value: 'container', label: 'Container (vessel)' },
  { value: 'parent', label: 'Parent sample' },
  { value: 'sample_type', label: 'Sample type' },
];

const SchemaColumns: React.FC = () => {
  const { hasPermission } = useUser();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const canEdit = hasPermission('schema:edit');
  const [tables, setTables] = useState<SchemaTableRow[]>([]);
  const tableId = searchParams.get('table') || '';
  const [rows, setRows] = useState<SchemaColumnRow[]>([]);
  const [links, setLinks] = useState<TableLinks | null>(null);
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

  const setTableId = useCallback(
    (id: string) => {
      const next = new URLSearchParams(searchParams);
      if (id) next.set('table', id);
      else next.delete('table');
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const loadTables = useCallback(async () => {
    try {
      const data = await apiService.getSchemaTables();
      const list = sortTables(Array.isArray(data) ? (data as SchemaTableRow[]) : []);
      setTables(list);
      if (!tableId && list[0]) {
        const samples = list.find((t) => t.physical_name === 'samples') || list[0];
        setTableId(samples.id);
      }
    } catch (err) {
      setError(ApiService.formatError(err, 'Failed to load tables'));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadCols = useCallback(async (id: string) => {
    if (!id) return;
    try {
      setLoading(true);
      const [cols, linkData] = await Promise.all([
        apiService.getSchemaColumns(id),
        apiService.getSchemaTableLinks(id).catch(() => null),
      ]);
      setRows(Array.isArray(cols) ? (cols as SchemaColumnRow[]) : []);
      setLinks(linkData as TableLinks | null);
      setError(null);
    } catch (err) {
      setError(ApiService.formatError(err, 'Failed to load fields'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadTables();
    apiService
      .getLists()
      .then((d) => setLists(Array.isArray(d) ? d : []))
      .catch(() => setLists([]));
  }, [loadTables]);

  useEffect(() => {
    if (tableId) void loadCols(tableId);
  }, [tableId, loadCols]);

  const table = useMemo(() => tables.find((t) => t.id === tableId), [tables, tableId]);
  const tableName = table?.display_name || 'table';
  const canAdd = Boolean(canEdit && table?.can_add_columns);

  const columns: GridColDef<SchemaColumnRow>[] = [
    {
      field: 'display_name',
      headerName: 'Field',
      flex: 1,
      minWidth: 160,
      renderCell: (params) => {
        const reason = columnLockReason(params.row);
        return (
          <Box display="flex" alignItems="center" gap={0.75}>
            {reason && (
              <Tooltip title={reason}>
                <LockIcon fontSize="inherit" color="disabled" />
              </Tooltip>
            )}
            <span>{params.row.display_name}</span>
          </Box>
        );
      },
    },
    {
      field: 'scope',
      headerName: 'Scope',
      width: 100,
      sortable: false,
      renderCell: (params) => (
        <Chip
          size="small"
          label={columnScopeLabel(params.row)}
          color={isSystemColumn(params.row) ? 'default' : 'primary'}
          variant={isSystemColumn(params.row) ? 'outlined' : 'filled'}
        />
      ),
    },
    { field: 'physical_name', headerName: 'Database name', flex: 1, minWidth: 150 },
    {
      field: 'data_type',
      headerName: 'Type',
      width: 140,
      valueGetter: (_value, row) => TYPE_LABEL[row.data_type] || row.data_type,
    },
    {
      field: 'fk_table',
      headerName: 'Points at',
      width: 150,
      renderCell: (params) => {
        const row = params.row;
        if (!row.is_fk || !row.fk_table) return '';
        if (row.fk_table === 'list_entries') return 'List';
        const target = tables.find((t) => t.physical_name === row.fk_table);
        return target ? (
          <Link
            component="button"
            variant="body2"
            onClick={() => setTableId(target.id)}
            underline="hover"
          >
            {target.display_name}
          </Link>
        ) : (
          row.fk_table
        );
      },
    },
    { field: 'nullable', headerName: 'Optional', width: 95, type: 'boolean' },
    { field: 'sop_hint', headerName: 'SOP name', width: 120 },
    { field: 'status', headerName: 'Status', width: 105 },
    {
      field: 'actions',
      type: 'actions',
      width: 70,
      getActions: (params) => {
        if (!canEdit || !isColumnEditable(params.row)) return [];
        return [
          <GridActionsCellItem
            key="dep"
            label="Deprecate"
            showInMenu
            onClick={() =>
              void apiService
                .deprecateSchemaColumn(params.id as string)
                .then(() => loadCols(tableId))
                .catch((e) => setError(ApiService.formatError(e, 'Deprecate failed')))
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

  const hasLinks =
    links && (links.keys.length > 0 || links.children.length > 0 || links.parents.length > 0);

  return (
    <FillHeightPage
      header={
        <SchemaChrome>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          <Box display="flex" gap={2} mb={1} alignItems="center" flexWrap="wrap">
            <FormControl size="small" sx={{ minWidth: 280 }}>
              <InputLabel>Table</InputLabel>
              <Select label="Table" value={tableId} onChange={(e) => setTableId(e.target.value)}>
                {tables.map((t) => (
                  <MenuItem key={t.id} value={t.id}>
                    <Box display="flex" alignItems="center" gap={1} width="100%">
                      <span>{t.display_name}</span>
                      <Chip
                        size="small"
                        label={tableCategoryLabel(t)}
                        variant="outlined"
                        sx={{ ml: 'auto', height: 20 }}
                      />
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            {canEdit && (
              <Tooltip
                title={
                  canAdd
                    ? ''
                    : table?.kind === 'system'
                      ? 'System reference tables are read-only here.'
                      : 'Built-in lab tables get fields through migrations, not the UI.'
                }
              >
                <span>
                  <Button variant="contained" disabled={!tableId || !canAdd} onClick={() => setOpen(true)}>
                    Add field
                  </Button>
                </span>
              </Tooltip>
            )}
            {table && (
              <Typography variant="body2" color="text.secondary">
                <LockIcon fontSize="inherit" sx={{ verticalAlign: 'middle', mr: 0.5 }} />
                System fields (id, timestamps, created-by, keys) are locked. Lab fields added here
                keep Deprecate / Drop.
              </Typography>
            )}
          </Box>
          {hasLinks && links && (
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }} alignItems="center">
              <Typography variant="body2" color="text.secondary">
                Links:
              </Typography>
              {links.children.map((r) => (
                <Tooltip key={r.id} title={`${CARDINALITY_LABEL[r.cardinality] || r.cardinality} via ${r.fk_column_name}`}>
                  <Chip
                    size="small"
                    color="primary"
                    variant="outlined"
                    label={`${r.display_name} → ${r.to_table_name}`}
                    onClick={() => setTableId(r.to_table_id)}
                  />
                </Tooltip>
              ))}
              {links.parents.map((r) => (
                <Tooltip key={r.id} title={`${CARDINALITY_LABEL[r.cardinality] || r.cardinality} via ${r.fk_column_name}`}>
                  <Chip
                    size="small"
                    variant="outlined"
                    label={`${r.display_name} ← ${r.from_table_name}`}
                    onClick={() => setTableId(r.from_table_id)}
                  />
                </Tooltip>
              ))}
              {links.keys
                .filter((k) => !links.parents.some((p) => p.fk_column_id === k.column_id))
                .map((k) => (
                  <Tooltip key={k.column_id} title="Real foreign key without a declared relation">
                    <Chip
                      size="small"
                      variant="outlined"
                      color="default"
                      label={`${k.column_name} → ${k.fk_table_name || k.fk_table}`}
                      onClick={k.fk_table_id ? () => setTableId(k.fk_table_id as string) : undefined}
                    />
                  </Tooltip>
                ))}
              {canEdit && (
                <Link
                  component="button"
                  variant="body2"
                  underline="hover"
                  onClick={() => navigate(`/admin/schema/relations?table=${tableId}`)}
                >
                  Manage relations
                </Link>
              )}
            </Stack>
          )}
        </SchemaChrome>
      }
    >
      <FillHeightTable>
        <DataGrid
          rows={rows}
          columns={columns}
          loading={loading}
          pageSizeOptions={[25, 50, 100]}
          initialState={{ pagination: { paginationModel: { pageSize: 50 } } }}
          getRowClassName={(params) => (isSystemColumn(params.row) ? 'schema-system-row' : '')}
          sx={{ '& .schema-system-row': { color: 'text.secondary' } }}
        />
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
            Adds a real column on {tableName}. Links to another table are declared under Relations,
            over a real key.
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
