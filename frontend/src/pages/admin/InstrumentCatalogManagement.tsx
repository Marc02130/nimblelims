/**
 * Admin CRUD for instrument types, instrument instances, and CRO sources (data-parsers P0).
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControlLabel,
  IconButton,
  InputAdornment,
  Switch,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import { Add, Clear, Edit, Search } from '@mui/icons-material';
import { DataGrid, GridActionsCellItem, GridColDef, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';
import { FillHeightPage, FillHeightTable } from '../../components/common/FillHeightPage';

interface InstrumentType {
  id: string;
  name: string;
  description?: string;
  vendor?: string;
  model?: string;
  active: boolean;
}

interface Instrument {
  id: string;
  name: string;
  description?: string;
  instrument_type_id: string;
  instrument_type_name?: string;
  serial_number?: string;
  active: boolean;
}

interface CroSource {
  id: string;
  name: string;
  description?: string;
  client_id?: string | null;
  client_name?: string;
  active: boolean;
}

interface ClientOption {
  id: string;
  name: string;
}

type TabKey = 'types' | 'instances' | 'cro';

const emptyTypeForm = {
  name: '',
  description: '',
  vendor: '',
  model: '',
  active: true,
};

const emptyInstrumentForm = {
  name: '',
  description: '',
  instrument_type_id: '',
  serial_number: '',
  active: true,
};

const emptyCroForm = {
  name: '',
  description: '',
  client_id: '' as string | null,
  active: true,
};

const InstrumentCatalogManagement: React.FC = () => {
  const { hasPermission } = useUser();
  const canEdit = hasPermission('config:edit');

  const [tab, setTab] = useState<TabKey>('types');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [types, setTypes] = useState<InstrumentType[]>([]);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [croSources, setCroSources] = useState<CroSource[]>([]);
  const [clients, setClients] = useState<ClientOption[]>([]);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [typeForm, setTypeForm] = useState(emptyTypeForm);
  const [instrumentForm, setInstrumentForm] = useState(emptyInstrumentForm);
  const [croForm, setCroForm] = useState(emptyCroForm);
  const [submitting, setSubmitting] = useState(false);

  const loadAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [typesData, instrumentsData, croData] = await Promise.all([
        apiService.getInstrumentTypes(),
        apiService.getInstruments(),
        apiService.getCroSources(),
      ]);
      setTypes(typesData || []);
      setInstruments(instrumentsData || []);
      setCroSources(croData || []);
      try {
        const clientsData = await apiService.getClients();
        const list = Array.isArray(clientsData)
          ? clientsData
          : clientsData?.clients || clientsData?.items || [];
        setClients(
          list.map((c: any) => ({ id: c.id, name: c.name })).filter((c: ClientOption) => c.id && c.name)
        );
      } catch {
        setClients([]);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load instrument / CRO catalogs');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const filterBySearch = <T extends { name: string; description?: string }>(
    rows: T[],
    extra?: (row: T) => string
  ) => {
    if (!searchTerm) return rows;
    const term = searchTerm.toLowerCase();
    return rows.filter((row) => {
      const blob = [
        row.name,
        row.description || '',
        extra ? extra(row) : '',
      ]
        .join(' ')
        .toLowerCase();
      return blob.includes(term);
    });
  };

  const filteredTypes = useMemo(
    () =>
      filterBySearch(types, (t) => `${t.vendor || ''} ${t.model || ''}`),
    [types, searchTerm]
  );
  const filteredInstruments = useMemo(
    () =>
      filterBySearch(
        instruments,
        (i) => `${i.instrument_type_name || ''} ${i.serial_number || ''}`
      ),
    [instruments, searchTerm]
  );
  const filteredCro = useMemo(
    () => filterBySearch(croSources, (c) => c.client_name || ''),
    [croSources, searchTerm]
  );

  const openCreate = () => {
    setEditingId(null);
    setTypeForm(emptyTypeForm);
    setInstrumentForm(emptyInstrumentForm);
    setCroForm(emptyCroForm);
    setDialogOpen(true);
  };

  const openEdit = (row: InstrumentType | Instrument | CroSource) => {
    setEditingId(row.id);
    if (tab === 'types') {
      const t = row as InstrumentType;
      setTypeForm({
        name: t.name,
        description: t.description || '',
        vendor: t.vendor || '',
        model: t.model || '',
        active: t.active,
      });
    } else if (tab === 'instances') {
      const i = row as Instrument;
      setInstrumentForm({
        name: i.name,
        description: i.description || '',
        instrument_type_id: i.instrument_type_id,
        serial_number: i.serial_number || '',
        active: i.active,
      });
    } else {
      const c = row as CroSource;
      setCroForm({
        name: c.name,
        description: c.description || '',
        client_id: c.client_id || null,
        active: c.active,
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      if (tab === 'types') {
        const payload = {
          name: typeForm.name.trim(),
          description: typeForm.description.trim() || undefined,
          vendor: typeForm.vendor.trim() || undefined,
          model: typeForm.model.trim() || undefined,
          active: typeForm.active,
        };
        if (!payload.name) throw new Error('Name is required');
        if (editingId) await apiService.updateInstrumentType(editingId, payload);
        else await apiService.createInstrumentType(payload);
        setSuccess(editingId ? 'Instrument type updated' : 'Instrument type created');
      } else if (tab === 'instances') {
        const payload = {
          name: instrumentForm.name.trim(),
          description: instrumentForm.description.trim() || undefined,
          instrument_type_id: instrumentForm.instrument_type_id,
          serial_number: instrumentForm.serial_number.trim() || undefined,
          active: instrumentForm.active,
        };
        if (!payload.name) throw new Error('Name is required');
        if (!payload.instrument_type_id) throw new Error('Instrument type is required');
        if (editingId) await apiService.updateInstrument(editingId, payload);
        else await apiService.createInstrument(payload);
        setSuccess(editingId ? 'Instrument updated' : 'Instrument created');
      } else {
        const payload = {
          name: croForm.name.trim(),
          description: croForm.description.trim() || undefined,
          client_id: croForm.client_id || null,
          active: croForm.active,
        };
        if (!payload.name) throw new Error('Name is required');
        if (editingId) await apiService.updateCroSource(editingId, payload);
        else await apiService.createCroSource(payload);
        setSuccess(editingId ? 'CRO source updated' : 'CRO source created');
      }
      setDialogOpen(false);
      await loadAll();
    } catch (err: any) {
      setError(
        err.message ||
          err.response?.data?.detail ||
          'Save failed'
      );
    } finally {
      setSubmitting(false);
    }
  };

  const softDeactivate = async (row: InstrumentType | Instrument | CroSource) => {
    try {
      if (tab === 'types') await apiService.deleteInstrumentType(row.id);
      else if (tab === 'instances') await apiService.deleteInstrument(row.id);
      else await apiService.deleteCroSource(row.id);
      setSuccess('Deactivated');
      await loadAll();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Deactivate failed');
    }
  };

  const activeCol: GridColDef = {
    field: 'active',
    headerName: 'Active',
    width: 100,
    renderCell: (params) => (
      <Chip
        size="small"
        label={params.value ? 'Active' : 'Inactive'}
        color={params.value ? 'success' : 'default'}
      />
    ),
  };

  const actionsCol = (getRow: (p: GridRowParams) => any): GridColDef => ({
    field: 'actions',
    type: 'actions',
    headerName: 'Actions',
    width: 100,
    getActions: (params) => {
      if (!canEdit) return [];
      const row = getRow(params);
      return [
        <GridActionsCellItem
          key="edit"
          icon={<Edit />}
          label="Edit"
          onClick={() => openEdit(row)}
        />,
      ];
    },
  });

  const typeColumns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 140 },
    { field: 'vendor', headerName: 'Vendor', width: 140 },
    { field: 'model', headerName: 'Model', width: 140 },
    { field: 'description', headerName: 'Description', flex: 1, minWidth: 160 },
    activeCol,
    actionsCol((p) => p.row),
  ];

  const instrumentColumns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 140 },
    { field: 'instrument_type_name', headerName: 'Type', width: 160 },
    { field: 'serial_number', headerName: 'Serial', width: 140 },
    { field: 'description', headerName: 'Description', flex: 1, minWidth: 140 },
    activeCol,
    actionsCol((p) => p.row),
  ];

  const croColumns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 140 },
    { field: 'client_name', headerName: 'Client (label)', width: 180 },
    { field: 'description', headerName: 'Description', flex: 1, minWidth: 160 },
    activeCol,
    actionsCol((p) => p.row),
  ];

  const title =
    tab === 'types'
      ? 'Instrument types'
      : tab === 'instances'
        ? 'Instruments'
        : 'CRO sources';

  if (!canEdit) {
    return (
      <Box p={2}>
        <Alert severity="warning">
          You need <strong>config:edit</strong> to manage instrument and CRO catalogs.
        </Alert>
      </Box>
    );
  }

  return (
    <FillHeightPage
      header={
        <>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="h4">Instruments &amp; CRO sources</Typography>
            <Button variant="contained" startIcon={<Add />} onClick={openCreate}>
              Create {tab === 'types' ? 'type' : tab === 'instances' ? 'instrument' : 'CRO source'}
            </Button>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Lab-global catalogs for data import (P0). Types = vendor/model; instruments = named instances; CRO
            sources = external export origins.
          </Typography>
          <Tabs
            value={tab}
            onChange={(_, v) => {
              setTab(v);
              setSearchTerm('');
            }}
            sx={{ mb: 1 }}
          >
            <Tab label="Instrument types" value="types" />
            <Tab label="Instruments" value="instances" />
            <Tab label="CRO sources" value="cro" />
          </Tabs>
          {error && (
            <Alert severity="error" sx={{ mb: 1 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          {success && (
            <Alert severity="success" sx={{ mb: 1 }} onClose={() => setSuccess(null)}>
              {success}
            </Alert>
          )}
          <TextField
            fullWidth
            size="small"
            placeholder={`Search ${title.toLowerCase()}...`}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
              endAdornment: searchTerm ? (
                <InputAdornment position="end">
                  <IconButton size="small" onClick={() => setSearchTerm('')}>
                    <Clear />
                  </IconButton>
                </InputAdornment>
              ) : undefined,
            }}
          />
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
            rows={
              tab === 'types'
                ? filteredTypes
                : tab === 'instances'
                  ? filteredInstruments
                  : filteredCro
            }
            columns={
              tab === 'types'
                ? typeColumns
                : tab === 'instances'
                  ? instrumentColumns
                  : croColumns
            }
            getRowId={(row) => row.id}
            pageSizeOptions={[10, 25, 50]}
            initialState={{ pagination: { paginationModel: { page: 0, pageSize: 25 } } }}
            disableRowSelectionOnClick
            slots={{
              noRowsOverlay: () => (
                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                  <Typography>No rows — create a {title.slice(0, -1).toLowerCase()} to get started</Typography>
                </Box>
              ),
            }}
          />
        </FillHeightTable>
      )}

      <Dialog open={dialogOpen} onClose={() => !submitting && setDialogOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>
          {editingId ? 'Edit' : 'Create'}{' '}
          {tab === 'types' ? 'instrument type' : tab === 'instances' ? 'instrument' : 'CRO source'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            {tab === 'types' && 'Vendor/model class (e.g. Agilent 6495C).'}
            {tab === 'instances' && 'Physical or named unit (e.g. LCMS-1) linked to a type.'}
            {tab === 'cro' && 'External lab export source for file lineage. Client is optional label only.'}
          </DialogContentText>
          {tab === 'types' && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Name"
                required
                value={typeForm.name}
                onChange={(e) => setTypeForm({ ...typeForm, name: e.target.value })}
                fullWidth
              />
              <TextField
                label="Vendor"
                value={typeForm.vendor}
                onChange={(e) => setTypeForm({ ...typeForm, vendor: e.target.value })}
                fullWidth
              />
              <TextField
                label="Model"
                value={typeForm.model}
                onChange={(e) => setTypeForm({ ...typeForm, model: e.target.value })}
                fullWidth
              />
              <TextField
                label="Description"
                value={typeForm.description}
                onChange={(e) => setTypeForm({ ...typeForm, description: e.target.value })}
                fullWidth
                multiline
                minRows={2}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={typeForm.active}
                    onChange={(e) => setTypeForm({ ...typeForm, active: e.target.checked })}
                  />
                }
                label="Active"
              />
            </Box>
          )}
          {tab === 'instances' && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Name"
                required
                value={instrumentForm.name}
                onChange={(e) => setInstrumentForm({ ...instrumentForm, name: e.target.value })}
                fullWidth
                helperText="Lab nickname (e.g. LCMS-1)"
              />
              <Autocomplete
                options={types.filter((t) => t.active || t.id === instrumentForm.instrument_type_id)}
                getOptionLabel={(o) =>
                  o.vendor || o.model ? `${o.name} (${[o.vendor, o.model].filter(Boolean).join(' ')})` : o.name
                }
                value={types.find((t) => t.id === instrumentForm.instrument_type_id) || null}
                onChange={(_, v) =>
                  setInstrumentForm({ ...instrumentForm, instrument_type_id: v?.id || '' })
                }
                renderInput={(params) => <TextField {...params} label="Instrument type" required />}
              />
              <TextField
                label="Serial number"
                value={instrumentForm.serial_number}
                onChange={(e) => setInstrumentForm({ ...instrumentForm, serial_number: e.target.value })}
                fullWidth
              />
              <TextField
                label="Description"
                value={instrumentForm.description}
                onChange={(e) => setInstrumentForm({ ...instrumentForm, description: e.target.value })}
                fullWidth
                multiline
                minRows={2}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={instrumentForm.active}
                    onChange={(e) =>
                      setInstrumentForm({ ...instrumentForm, active: e.target.checked })
                    }
                  />
                }
                label="Active"
              />
            </Box>
          )}
          {tab === 'cro' && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Name"
                required
                value={croForm.name}
                onChange={(e) => setCroForm({ ...croForm, name: e.target.value })}
                fullWidth
              />
              <Autocomplete
                options={clients}
                getOptionLabel={(o) => o.name}
                value={clients.find((c) => c.id === croForm.client_id) || null}
                onChange={(_, v) => setCroForm({ ...croForm, client_id: v?.id || null })}
                renderInput={(params) => (
                  <TextField {...params} label="Client (optional label)" />
                )}
              />
              <TextField
                label="Description"
                value={croForm.description}
                onChange={(e) => setCroForm({ ...croForm, description: e.target.value })}
                fullWidth
                multiline
                minRows={2}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={croForm.active}
                    onChange={(e) => setCroForm({ ...croForm, active: e.target.checked })}
                  />
                }
                label="Active"
              />
              {editingId && croForm.active === false && (
                <Typography variant="caption" color="text.secondary">
                  Inactive sources are hidden from most users.
                </Typography>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          {editingId && (
            <Button
              color="warning"
              disabled={submitting}
              onClick={async () => {
                const row =
                  tab === 'types'
                    ? types.find((t) => t.id === editingId)
                    : tab === 'instances'
                      ? instruments.find((i) => i.id === editingId)
                      : croSources.find((c) => c.id === editingId);
                if (row) {
                  await softDeactivate(row);
                  setDialogOpen(false);
                }
              }}
            >
              Deactivate
            </Button>
          )}
          <Box sx={{ flex: 1 }} />
          <Button onClick={() => setDialogOpen(false)} disabled={submitting}>
            Cancel
          </Button>
          <Button variant="contained" onClick={handleSubmit} disabled={submitting}>
            {submitting ? 'Saving…' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </FillHeightPage>
  );
};

export default InstrumentCatalogManagement;
