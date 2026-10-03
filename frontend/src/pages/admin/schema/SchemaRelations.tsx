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
  MenuItem,
  Radio,
  RadioGroup,
  Select,
  TextField,
  Typography,
} from '@mui/material';
import { DataGrid, GridActionsCellItem, GridColDef } from '@mui/x-data-grid';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import { useSearchParams } from 'react-router-dom';
import { apiService, ApiService } from '../../../services/apiService';
import { useUser } from '../../../contexts/UserContext';
import { FillHeightPage, FillHeightTable } from '../../../components/common/FillHeightPage';
import SchemaChrome from './SchemaChrome';
import {
  CARDINALITY_LABEL,
  Cardinality,
  SchemaColumnRow,
  SchemaRelationRow,
  SchemaTableRow,
  keyColumnsFor,
  relationSentence,
  sortTables,
  tableCategoryLabel,
} from './schemaBrowser';

const EMPTY_FORM = {
  display_name: '',
  from_table_id: '',
  to_table_id: '',
  fk_column_id: '',
  cardinality: 'one_to_many' as Cardinality,
};

const SchemaRelations: React.FC = () => {
  const { hasPermission } = useUser();
  const [searchParams] = useSearchParams();
  const canEdit = hasPermission('schema:edit');
  const [tables, setTables] = useState<SchemaTableRow[]>([]);
  const [rows, setRows] = useState<SchemaRelationRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [childColumns, setChildColumns] = useState<SchemaColumnRow[]>([]);
  const filterTableId = searchParams.get('table') || '';

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [t, r] = await Promise.all([
        apiService.getSchemaTables(),
        apiService.getSchemaRelations(filterTableId ? { table_id: filterTableId } : undefined),
      ]);
      setTables(sortTables(Array.isArray(t) ? (t as SchemaTableRow[]) : []));
      setRows(Array.isArray(r) ? (r as SchemaRelationRow[]) : []);
      setError(null);
    } catch (err) {
      setError(ApiService.formatError(err, 'Failed to load relations'));
    } finally {
      setLoading(false);
    }
  }, [filterTableId]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!form.to_table_id) {
      setChildColumns([]);
      return;
    }
    apiService
      .getSchemaColumns(form.to_table_id)
      .then((d) => setChildColumns(Array.isArray(d) ? (d as SchemaColumnRow[]) : []))
      .catch(() => setChildColumns([]));
  }, [form.to_table_id]);

  const parent = useMemo(() => tables.find((t) => t.id === form.from_table_id), [tables, form.from_table_id]);
  const child = useMemo(() => tables.find((t) => t.id === form.to_table_id), [tables, form.to_table_id]);
  const keyCandidates = useMemo(
    () => keyColumnsFor(childColumns, parent?.physical_name),
    [childColumns, parent],
  );
  const keyColumn = keyCandidates.find((c) => c.id === form.fk_column_id);
  const oneToOneBlocked = Boolean(keyColumn && !keyColumn.is_unique);

  useEffect(() => {
    if (form.fk_column_id && !keyCandidates.some((c) => c.id === form.fk_column_id)) {
      setForm((f) => ({ ...f, fk_column_id: '' }));
    }
  }, [keyCandidates, form.fk_column_id]);

  useEffect(() => {
    if (oneToOneBlocked && form.cardinality === 'one_to_one') {
      setForm((f) => ({ ...f, cardinality: 'one_to_many' }));
    }
  }, [oneToOneBlocked, form.cardinality]);

  const filterTable = tables.find((t) => t.id === filterTableId);

  const columns: GridColDef<SchemaRelationRow>[] = [
    { field: 'display_name', headerName: 'Relation', flex: 1, minWidth: 180 },
    { field: 'from_table_name', headerName: 'Parent (one)', flex: 1, minWidth: 140 },
    { field: 'to_table_name', headerName: 'Child (holds the key)', flex: 1, minWidth: 160 },
    {
      field: 'fk_column_name',
      headerName: 'Key on child',
      flex: 1,
      minWidth: 150,
      valueGetter: (_value, row) => `${row.fk_column_name} (${row.fk_physical_name})`,
    },
    {
      field: 'cardinality',
      headerName: 'How they relate',
      width: 140,
      renderCell: (params) => (
        <Chip size="small" variant="outlined" label={CARDINALITY_LABEL[params.row.cardinality] || params.row.cardinality} />
      ),
    },
    { field: 'status', headerName: 'Status', width: 100 },
    {
      field: 'actions',
      type: 'actions',
      width: 70,
      getActions: (params) => {
        if (!canEdit) return [];
        return [
          <GridActionsCellItem
            key="remove"
            icon={<DeleteOutlineIcon />}
            label="Remove link definition"
            onClick={() => {
              if (
                window.confirm(
                  `Remove the link definition "${params.row.display_name}"? The key column and its data stay in the database. Only the declared relation is removed.`,
                )
              ) {
                void apiService
                  .deleteSchemaRelation(params.id as string)
                  .then(() => {
                    setInfo(`Removed "${params.row.display_name}". No database change was made.`);
                    return load();
                  })
                  .catch((e) => setError(ApiService.formatError(e, 'Remove failed')));
              }
            }}
          />,
        ];
      },
    },
  ];

  const sentence =
    parent && child && keyColumn
      ? relationSentence(form.cardinality, parent.display_name, child.display_name, keyColumn.display_name)
      : null;

  const submit = async () => {
    try {
      const created = await apiService.createSchemaRelation({
        display_name: form.display_name.trim(),
        from_table_id: form.from_table_id,
        to_table_id: form.to_table_id,
        fk_column_id: form.fk_column_id,
        cardinality: form.cardinality,
      });
      setOpen(false);
      setForm(EMPTY_FORM);
      setInfo(`Declared "${created.display_name}" over ${created.to_physical_name}.${created.fk_physical_name}. No database change was made.`);
      await load();
    } catch (err) {
      setError(ApiService.formatError(err, 'Could not declare relation'));
    }
  };

  return (
    <FillHeightPage
      header={
        <SchemaChrome>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          {info && (
            <Alert severity="success" sx={{ mb: 2 }} onClose={() => setInfo(null)}>
              {info}
            </Alert>
          )}
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1} gap={2} flexWrap="wrap">
            <Typography variant="body2" color="text.secondary">
              One-to-many and one-to-one links between tables. The key is a real foreign key
              column on the child, already in Postgres. Declaring a link never changes the database.
              Many-to-many waits until ids are globally unique.
              {filterTable && (
                <>
                  {' '}
                  Showing links for <strong>{filterTable.display_name}</strong>.
                </>
              )}
            </Typography>
            {canEdit && (
              <Button variant="contained" onClick={() => setOpen(true)}>
                Add relation
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
          localeText={{ noRowsLabel: 'No relations declared yet. Add relation to declare a link over a real key.' }}
        />
      </FillHeightTable>
      <Dialog open={open} onClose={() => setOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Add relation</DialogTitle>
        <DialogContent>
          <FormControl fullWidth margin="dense">
            <InputLabel>Parent table (the one side)</InputLabel>
            <Select
              label="Parent table (the one side)"
              value={form.from_table_id}
              onChange={(e) => setForm({ ...form, from_table_id: e.target.value, fk_column_id: '' })}
            >
              {tables.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.display_name} — {tableCategoryLabel(t)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth margin="dense">
            <InputLabel>Child table (holds the key)</InputLabel>
            <Select
              label="Child table (holds the key)"
              value={form.to_table_id}
              onChange={(e) => setForm({ ...form, to_table_id: e.target.value, fk_column_id: '' })}
            >
              {tables.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.display_name} — {tableCategoryLabel(t)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth margin="dense" disabled={!parent || !child}>
            <InputLabel>Key column on child</InputLabel>
            <Select
              label="Key column on child"
              value={form.fk_column_id}
              onChange={(e) => setForm({ ...form, fk_column_id: e.target.value })}
            >
              {keyCandidates.map((c) => (
                <MenuItem key={c.id} value={c.id}>
                  {c.display_name} ({c.physical_name}){c.is_unique ? ' — unique' : ''}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {parent && child && keyCandidates.length === 0 && (
            <Alert severity="warning" sx={{ mt: 1 }}>
              {child.display_name} has no foreign key that points at {parent.display_name}. Add the
              key with a migration first; the Schema screen does not change the database.
            </Alert>
          )}
          <FormControl margin="dense">
            <Typography variant="body2" sx={{ mt: 1 }}>
              How they relate
            </Typography>
            <RadioGroup
              row
              value={form.cardinality}
              onChange={(e) => setForm({ ...form, cardinality: e.target.value as Cardinality })}
            >
              <FormControlLabel value="one_to_many" control={<Radio />} label="One to many" />
              <FormControlLabel
                value="one_to_one"
                control={<Radio />}
                label="One to one"
                disabled={oneToOneBlocked}
              />
            </RadioGroup>
            {oneToOneBlocked && (
              <Typography variant="caption" color="text.secondary">
                One to one needs a UNIQUE key. {keyColumn?.display_name} is not unique in Postgres.
              </Typography>
            )}
          </FormControl>
          <TextField
            margin="dense"
            label="Relation name (what people read)"
            fullWidth
            value={form.display_name}
            onChange={(e) => setForm({ ...form, display_name: e.target.value })}
            placeholder={parent && child ? `${parent.display_name} ${child.display_name.toLowerCase()}` : ''}
          />
          {sentence && (
            <Alert severity="info" sx={{ mt: 1 }}>
              {sentence}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setOpen(false);
              setForm(EMPTY_FORM);
            }}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            disabled={!form.display_name.trim() || !form.from_table_id || !form.to_table_id || !form.fk_column_id}
            onClick={() => void submit()}
          >
            Declare relation
          </Button>
        </DialogActions>
      </Dialog>
    </FillHeightPage>
  );
};

export default SchemaRelations;
