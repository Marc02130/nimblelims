import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Switch,
  Typography,
} from '@mui/material';
import { Add, Delete, Edit } from '@mui/icons-material';
import { DataGrid, GridActionsCellItem, GridColDef } from '@mui/x-data-grid';
import { apiService } from '../../services/apiService';
import { useUser } from '../../contexts/UserContext';
import { FillHeightPage, FillHeightTable } from '../../components/common/FillHeightPage';

interface TransitionRow {
  id: string;
  source_sample_type: string;
  source_sample_type_name?: string | null;
  operation: 'aliquot' | 'pool';
  allowed_dest_sample_type: string;
  allowed_dest_sample_type_name?: string | null;
  active: boolean;
}

interface TypeOption {
  id: string;
  name: string;
}

const emptyForm = {
  source_sample_type: '',
  operation: 'aliquot' as 'aliquot' | 'pool',
  allowed_dest_sample_type: '',
  active: true,
};

const SampleTypeTransitionsManagement: React.FC = () => {
  const { hasPermission } = useUser();
  const canEdit = hasPermission('config:edit');
  const [rows, setRows] = useState<TransitionRow[]>([]);
  const [types, setTypes] = useState<TypeOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<TransitionRow | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [deleteTarget, setDeleteTarget] = useState<TransitionRow | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const [raw, typeRaw] = await Promise.all([
        apiService.getSampleTypeTransitions(),
        apiService.getListEntries('sample_types'),
      ]);
      setRows(Array.isArray(raw) ? raw : []);
      const list = Array.isArray(typeRaw) ? typeRaw : typeRaw?.entries || [];
      setTypes(
        (list as Array<{ id?: string; name?: string; active?: boolean }>)
          .filter((t) => t?.id && t?.name)
          .map((t) => ({ id: String(t.id), name: String(t.name) })),
      );
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      setError(
        status === 403
          ? 'You do not have permission to view dest-type transitions'
          : 'Failed to load dest-type transitions',
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm);
    setFormOpen(true);
  };

  const openEdit = (row: TransitionRow) => {
    setEditing(row);
    setForm({
      source_sample_type: row.source_sample_type,
      operation: row.operation,
      allowed_dest_sample_type: row.allowed_dest_sample_type,
      active: row.active,
    });
    setFormOpen(true);
  };

  const save = async () => {
    if (!form.source_sample_type || !form.allowed_dest_sample_type) {
      setError('Source type, operation, and dest type are required');
      return;
    }
    try {
      if (editing) {
        await apiService.updateSampleTypeTransition(editing.id, form);
      } else {
        await apiService.createSampleTypeTransition(form);
      }
      setFormOpen(false);
      await load();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response
        ?.data?.detail;
      const msg =
        typeof detail === 'string'
          ? detail
          : (detail as { message?: string } | undefined)?.message ||
            'Failed to save transition';
      setError(msg);
    }
  };

  const deactivate = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteSampleTypeTransition(deleteTarget.id);
      setDeleteTarget(null);
      await load();
    } catch {
      setError('Failed to deactivate transition');
      setDeleteTarget(null);
    }
  };

  const columns: GridColDef[] = useMemo(
    () => [
      {
        field: 'source_sample_type_name',
        headerName: 'Source type',
        flex: 1,
        minWidth: 140,
      },
      { field: 'operation', headerName: 'Operation', width: 120 },
      {
        field: 'allowed_dest_sample_type_name',
        headerName: 'Dest type',
        flex: 1,
        minWidth: 140,
      },
      {
        field: 'active',
        headerName: 'Active',
        width: 100,
        type: 'boolean',
      },
      {
        field: 'actions',
        type: 'actions',
        width: 100,
        getActions: (params) =>
          canEdit
            ? [
                <GridActionsCellItem
                  key="edit"
                  icon={<Edit />}
                  label="Edit"
                  onClick={() => openEdit(params.row as TransitionRow)}
                />,
                <GridActionsCellItem
                  key="del"
                  icon={<Delete />}
                  label="Deactivate"
                  onClick={() => setDeleteTarget(params.row as TransitionRow)}
                />,
              ]
            : [],
      },
    ],
    [canEdit],
  );

  return (
    <FillHeightPage>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 2 }}>
        <Typography variant="h5" sx={{ flex: 1 }}>
          Dest-type transitions
        </Typography>
        {canEdit && (
          <Button variant="contained" startIcon={<Add />} onClick={openCreate}>
            Add transition
          </Button>
        )}
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Catalog of allowed aliquot/pool destination sample types (source × operation → dest).
        Execute still refuses dests not in this catalog. Requires config:edit to change.
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      <FillHeightTable>
        <DataGrid
          rows={rows}
          columns={columns}
          loading={loading}
          disableRowSelectionOnClick
          pageSizeOptions={[25, 50]}
          initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
        />
      </FillHeightTable>

      <Dialog open={formOpen} onClose={() => setFormOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{editing ? 'Edit transition' : 'Add transition'}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <FormControl fullWidth size="small" sx={{ mt: 1 }}>
            <InputLabel>Source sample type</InputLabel>
            <Select
              label="Source sample type"
              value={form.source_sample_type}
              onChange={(e) =>
                setForm((f) => ({ ...f, source_sample_type: String(e.target.value) }))
              }
            >
              {types.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth size="small">
            <InputLabel>Operation</InputLabel>
            <Select
              label="Operation"
              value={form.operation}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  operation: e.target.value as 'aliquot' | 'pool',
                }))
              }
            >
              <MenuItem value="aliquot">aliquot</MenuItem>
              <MenuItem value="pool">pool</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth size="small">
            <InputLabel>Dest sample type</InputLabel>
            <Select
              label="Dest sample type"
              value={form.allowed_dest_sample_type}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  allowed_dest_sample_type: String(e.target.value),
                }))
              }
            >
              {types.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControlLabel
            control={
              <Switch
                checked={form.active}
                onChange={(e) => setForm((f) => ({ ...f, active: e.target.checked }))}
              />
            }
            label="Active"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFormOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={save}>
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Deactivate transition?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {deleteTarget
              ? `${deleteTarget.source_sample_type_name} × ${deleteTarget.operation} → ${deleteTarget.allowed_dest_sample_type_name} will no longer be offered at execute.`
              : ''}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button color="error" onClick={deactivate}>
            Deactivate
          </Button>
        </DialogActions>
      </Dialog>
    </FillHeightPage>
  );
};

export default SampleTypeTransitionsManagement;
