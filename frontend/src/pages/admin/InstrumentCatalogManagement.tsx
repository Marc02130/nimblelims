/**
 * Admin catalog for instrument types (list), instruments, CRO sources,
 * maintenance schedules, and downtime. Nothing is deleted: retire with
 * active / status flags. Types are a configurable list — add or retire
 * (Active off). A run is not locked to one type.
 *
 * Lab Managers reach schedules and first-due through the role-gated
 * Instrument maintenance view (maintenanceOnly).
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
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Switch,
  Tab,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import { Add, Edit, Search } from '@mui/icons-material';
import { DataGrid, GridActionsCellItem, GridColDef, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';
import { FillHeightPage, FillHeightTable } from '../../components/common/FillHeightPage';

interface InstrumentType {
  id: string;
  name: string;
  description?: string;
  active: boolean;
}

interface VendorOption {
  id: string;
  name: string;
}

interface Instrument {
  id: string;
  name: string;
  description?: string;
  instrument_type_id: string;
  instrument_type_name?: string;
  vendor_id?: string | null;
  vendor_name?: string;
  model?: string;
  serial_number?: string;
  asset_tag?: string;
  location_id?: string | null;
  status: string;
  active: boolean;
  maintenance_tracked?: boolean;
}

interface CroSource {
  id: string;
  name: string;
  description?: string;
  client_id?: string | null;
  client_name?: string;
  active: boolean;
}

interface Schedule {
  id: string;
  instrument_id: string;
  instrument_name?: string;
  kind_id: string;
  kind_name?: string;
  interval_days: number;
  last_done?: string | null;
  next_due?: string | null;
  service_vendor_id?: string | null;
  service_vendor_name?: string;
  active: boolean;
}

interface Downtime {
  id: string;
  instrument_id: string;
  instrument_name?: string;
  started_at: string;
  ended_at?: string | null;
  reason_id: string;
  reason_name?: string;
  note?: string;
  active: boolean;
}

interface ClientOption {
  id: string;
  name: string;
}

interface ListEntryOption {
  id: string;
  name: string;
}

type TabKey = 'types' | 'instances' | 'cro' | 'maintenance' | 'downtime';

const emptyTypeForm = { name: '', description: '', active: true };
const emptyInstrumentForm = {
  name: '',
  description: '',
  instrument_type_id: '',
  vendor_id: '' as string,
  model: '',
  serial_number: '',
  asset_tag: '',
  status: 'in_service',
  active: true,
  maintenance_tracked: false,
};
const emptyCroForm = {
  name: '',
  description: '',
  client_id: '' as string | null,
  active: true,
};
const emptyScheduleForm = {
  instrument_id: '',
  kind_id: '',
  interval_days: '365',
  service_vendor_id: '',
  active: true,
};
const emptyDowntimeForm = {
  instrument_id: '',
  started_at: '',
  ended_at: '',
  reason_id: '',
  note: '',
  active: true,
};

const STATUSES = [
  { value: 'in_service', label: 'In service' },
  { value: 'out_of_service', label: 'Out of service' },
  { value: 'retired', label: 'Retired' },
];

const AWAITING_FIRST_DUE = 'Awaiting first due date';

const InstrumentCatalogManagement: React.FC<{ maintenanceOnly?: boolean }> = ({
  maintenanceOnly = false,
}) => {
  const { hasPermission, user } = useUser();
  const canEdit = hasPermission('config:edit');
  const canBench = hasPermission('experiment:manage');
  const canManageSchedules = user?.role === 'Administrator' || user?.role === 'Lab Manager';

  const [tab, setTab] = useState<TabKey>(maintenanceOnly ? 'maintenance' : 'types');
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [types, setTypes] = useState<InstrumentType[]>([]);
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [croSources, setCroSources] = useState<CroSource[]>([]);
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [downtime, setDowntime] = useState<Downtime[]>([]);
  const [vendors, setVendors] = useState<VendorOption[]>([]);
  const [clients, setClients] = useState<ClientOption[]>([]);
  const [maintenanceKinds, setMaintenanceKinds] = useState<ListEntryOption[]>([]);
  const [downtimeReasons, setDowntimeReasons] = useState<ListEntryOption[]>([]);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [typeForm, setTypeForm] = useState(emptyTypeForm);
  const [instrumentForm, setInstrumentForm] = useState(emptyInstrumentForm);
  const [croForm, setCroForm] = useState(emptyCroForm);
  const [scheduleForm, setScheduleForm] = useState(emptyScheduleForm);
  const [downtimeForm, setDowntimeForm] = useState(emptyDowntimeForm);
  const [submitting, setSubmitting] = useState(false);
  const [stopReason, setStopReason] = useState<string | null>(null);
  const [firstDueId, setFirstDueId] = useState<string | null>(null);
  const [firstDueDate, setFirstDueDate] = useState('');

  const loadAll = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [typesData, instrumentsData, croData, schedData, downData, vendorData] = await Promise.all([
        apiService.getInstrumentTypes(),
        apiService.getInstruments(),
        apiService.getCroSources(),
        apiService.getInstrumentMaintenanceSchedules({ include_inactive: true }),
        apiService.getInstrumentDowntime({ include_inactive: true }),
        apiService.getVendors({ active: true }),
      ]);
      setTypes(typesData || []);
      setInstruments(instrumentsData || []);
      setCroSources(croData || []);
      setSchedules(schedData || []);
      setDowntime(downData || []);
      setVendors((vendorData || []).map((v: any) => ({ id: v.id, name: v.name })));
      try {
        const clientsData = await apiService.getClients();
        const list = Array.isArray(clientsData)
          ? clientsData
          : clientsData?.clients || clientsData?.items || [];
        setClients(list.map((c: any) => ({ id: c.id, name: c.name })).filter((c: ClientOption) => c.id && c.name));
      } catch {
        setClients([]);
      }
      try {
        const kinds = await apiService.getListEntries('maintenance_types');
        setMaintenanceKinds((kinds || []).map((e: any) => ({ id: e.id, name: e.name })));
      } catch {
        setMaintenanceKinds([]);
      }
      try {
        const reasons = await apiService.getListEntries('downtime_reasons');
        setDowntimeReasons((reasons || []).map((e: any) => ({ id: e.id, name: e.name })));
      } catch {
        setDowntimeReasons([]);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load instrument catalogs');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const awaitingByInstrument = useMemo(() => {
    const awaiting = new Set<string>();
    for (const row of schedules) {
      if (row.active && !row.next_due) awaiting.add(row.instrument_id);
    }
    return awaiting;
  }, [schedules]);

  const filterBySearch = <T,>(rows: T[], extra?: (row: T) => string) => {
    if (!searchTerm) return rows;
    const term = searchTerm.toLowerCase();
    return rows.filter((row) => {
      const named =
        row && typeof row === 'object' && 'name' in row && typeof (row as { name?: unknown }).name === 'string'
          ? (row as { name: string }).name
          : '';
      const blob = [named, extra ? extra(row) : ''].join(' ').toLowerCase();
      return blob.includes(term);
    });
  };

  const filteredTypes = useMemo(() => filterBySearch(types), [types, searchTerm]);
  const filteredInstruments = useMemo(
    () =>
      filterBySearch(
        instruments,
        (i) => `${i.instrument_type_name || ''} ${i.vendor_name || ''} ${i.model || ''} ${i.serial_number || ''} ${i.status}`
      ),
    [instruments, searchTerm]
  );
  const filteredCro = useMemo(() => filterBySearch(croSources, (c) => c.client_name || ''), [croSources, searchTerm]);
  const filteredSchedules = useMemo(
    () => filterBySearch(schedules, (s) => `${s.instrument_name || ''} ${s.kind_name || ''}`),
    [schedules, searchTerm]
  );
  const filteredDowntime = useMemo(
    () => filterBySearch(downtime, (d) => `${d.instrument_name || ''} ${d.reason_name || ''}`),
    [downtime, searchTerm]
  );

  const openCreate = () => {
    setEditingId(null);
    setTypeForm(emptyTypeForm);
    setInstrumentForm(emptyInstrumentForm);
    setCroForm(emptyCroForm);
    setScheduleForm(emptyScheduleForm);
    setDowntimeForm(emptyDowntimeForm);
    setStopReason(null);
    setDialogOpen(true);
  };

  const openEdit = (row: any) => {
    setEditingId(row.id);
    setStopReason(null);
    if (tab === 'types') {
      setTypeForm({
        name: row.name,
        description: row.description || '',
        active: row.active,
      });
    } else if (tab === 'instances') {
      setInstrumentForm({
        name: row.name,
        description: row.description || '',
        instrument_type_id: row.instrument_type_id,
        vendor_id: row.vendor_id || '',
        model: row.model || '',
        serial_number: row.serial_number || '',
        asset_tag: row.asset_tag || '',
        status: row.status || 'in_service',
        active: row.active,
        maintenance_tracked: Boolean(row.maintenance_tracked),
      });
    } else if (tab === 'cro') {
      setCroForm({
        name: row.name,
        description: row.description || '',
        client_id: row.client_id || null,
        active: row.active,
      });
    } else if (tab === 'maintenance') {
      setScheduleForm({
        instrument_id: row.instrument_id,
        kind_id: row.kind_id,
        interval_days: String(row.interval_days),
        service_vendor_id: row.service_vendor_id || '',
        active: row.active,
      });
    } else {
      setDowntimeForm({
        instrument_id: row.instrument_id,
        started_at: row.started_at ? String(row.started_at).slice(0, 16) : '',
        ended_at: row.ended_at ? String(row.ended_at).slice(0, 16) : '',
        reason_id: row.reason_id,
        note: row.note || '',
        active: row.active,
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);
    setStopReason(null);
    try {
      if (tab === 'types') {
        const payload = {
          name: typeForm.name.trim(),
          description: typeForm.description.trim() || undefined,
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
          vendor_id: instrumentForm.vendor_id || null,
          model: instrumentForm.model.trim() || undefined,
          serial_number: instrumentForm.serial_number.trim() || undefined,
          asset_tag: instrumentForm.asset_tag.trim() || undefined,
          status: instrumentForm.status,
          active: instrumentForm.active,
          maintenance_tracked: instrumentForm.maintenance_tracked,
        };
        if (!payload.name) throw new Error('Name is required');
        if (!payload.instrument_type_id) throw new Error('Instrument type is required');
        if (editingId) await apiService.updateInstrument(editingId, payload);
        else await apiService.createInstrument(payload);
        setSuccess(editingId ? 'Instrument updated' : 'Instrument created');
      } else if (tab === 'cro') {
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
      } else if (tab === 'maintenance') {
        const payload = {
          instrument_id: scheduleForm.instrument_id,
          kind_id: scheduleForm.kind_id,
          interval_days: Number(scheduleForm.interval_days),
          service_vendor_id: scheduleForm.service_vendor_id || undefined,
          active: scheduleForm.active,
        };
        if (!payload.instrument_id || !payload.kind_id) throw new Error('Instrument and kind are required');
        if (editingId) await apiService.updateInstrumentMaintenanceSchedule(editingId, payload);
        else await apiService.createInstrumentMaintenanceSchedule(payload);
        setSuccess(editingId ? 'Schedule updated' : 'Schedule created');
      } else {
        const payload = {
          instrument_id: downtimeForm.instrument_id,
          started_at: downtimeForm.started_at,
          ended_at: downtimeForm.ended_at || undefined,
          reason_id: downtimeForm.reason_id,
          note: downtimeForm.note || undefined,
          active: downtimeForm.active,
        };
        if (!payload.instrument_id || !payload.reason_id || !payload.started_at) {
          throw new Error('Instrument, reason, and start are required');
        }
        if (editingId) await apiService.updateInstrumentDowntime(editingId, payload);
        else await apiService.createInstrumentDowntime(payload);
        setSuccess(editingId ? 'Downtime updated' : 'Downtime recorded');
      }
      setDialogOpen(false);
      await loadAll();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      const message =
        (detail && typeof detail === 'object' && detail.message) ||
        err.message ||
        (typeof detail === 'string' ? detail : 'Save failed');
      if (detail && typeof detail === 'object' && detail.code) {
        setStopReason(message);
      }
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const retireInstrument = async (row: Instrument) => {
    try {
      await apiService.updateInstrument(row.id, { status: 'retired', active: false });
      setSuccess('Instrument retired');
      await loadAll();
    } catch (err: any) {
      setError(err.response?.data?.detail?.message || err.response?.data?.detail || 'Retire failed');
    }
  };

  const submitFirstDue = async () => {
    if (!firstDueId || !firstDueDate) return;
    setSubmitting(true);
    setError(null);
    try {
      await apiService.setInstrumentScheduleFirstDue(firstDueId, firstDueDate);
      setSuccess('First due date set');
      setFirstDueId(null);
      setFirstDueDate('');
      await loadAll();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      setError(
        (detail && typeof detail === 'object' && detail.message) ||
          err.message ||
          (typeof detail === 'string' ? detail : 'Could not set the first due date')
      );
    } finally {
      setSubmitting(false);
    }
  };

  const activeCol: GridColDef = {
    field: 'active',
    headerName: 'Active',
    width: 100,
    renderCell: (params) => (
      <Chip size="small" label={params.value ? 'Active' : 'Inactive'} color={params.value ? 'success' : 'default'} />
    ),
  };

  const canActOnTab =
    tab === 'maintenance' ? canManageSchedules : tab === 'downtime' ? canBench || canEdit : canEdit;

  const actionsCol = (
    onEdit: (p: GridRowParams) => void,
    extra?: (p: GridRowParams) => React.ReactElement[]
  ): GridColDef => ({
    field: 'actions',
    type: 'actions',
    headerName: 'Actions',
    width: 140,
    getActions: (params) => {
      const items: React.ReactElement[] = [];
      if (canActOnTab) {
        items.push(
          <GridActionsCellItem key="edit" icon={<Edit />} label="Edit" onClick={() => onEdit(params)} />
        );
      }
      if (extra) items.push(...extra(params));
      return items;
    },
  });

  const typeColumns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 140 },
    { field: 'description', headerName: 'Description', flex: 1, minWidth: 160 },
    activeCol,
    actionsCol((p) => openEdit(p.row)),
  ];

  const instrumentColumns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 140 },
    { field: 'instrument_type_name', headerName: 'Type', width: 140 },
    { field: 'vendor_name', headerName: 'Vendor', width: 140 },
    { field: 'model', headerName: 'Model', width: 120 },
    { field: 'serial_number', headerName: 'Serial', width: 120 },
    { field: 'status', headerName: 'Status', width: 140 },
    { field: 'maintenance_tracked', headerName: 'Track maintenance', width: 160 },
    {
      field: 'due_status',
      headerName: 'Next due',
      width: 180,
      valueGetter: (_value, row) => {
        if (!row.maintenance_tracked) return '';
        return awaitingByInstrument.has(row.id) ? AWAITING_FIRST_DUE : '';
      },
      renderCell: (params) =>
        params.value ? <Chip size="small" color="warning" label={params.value} /> : null,
    },
    activeCol,
    actionsCol(
      (p) => openEdit(p.row),
      canEdit
        ? (p) => [
            <GridActionsCellItem
              key="retire"
              label="Retire"
              showInMenu
              onClick={() => retireInstrument(p.row)}
            />,
          ]
        : undefined
    ),
  ];

  const croColumns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 140 },
    { field: 'client_name', headerName: 'Client (label)', width: 180 },
    { field: 'description', headerName: 'Description', flex: 1, minWidth: 160 },
    activeCol,
    actionsCol((p) => openEdit(p.row)),
  ];

  const scheduleColumns: GridColDef[] = [
    { field: 'instrument_name', headerName: 'Instrument', flex: 1, minWidth: 140 },
    { field: 'kind_name', headerName: 'Kind', width: 140 },
    { field: 'interval_days', headerName: 'Interval (days)', width: 140 },
    { field: 'last_done', headerName: 'Last done', width: 120 },
    {
      field: 'next_due',
      headerName: 'Next due',
      width: 180,
      renderCell: (params) =>
        params.value ? (
          String(params.value)
        ) : (
          <Chip size="small" color="warning" label={AWAITING_FIRST_DUE} />
        ),
    },
    { field: 'service_vendor_name', headerName: 'Service vendor', width: 160 },
    activeCol,
    actionsCol((p) => openEdit(p.row), (p) => {
      if (!canManageSchedules || p.row.next_due || p.row.last_done) return [];
      return [
        <GridActionsCellItem
          key="first-due"
          label="Set first due date"
          showInMenu
          onClick={() => {
            setFirstDueId(p.row.id);
            setFirstDueDate('');
          }}
        />,
      ];
    }),
  ];

  const downtimeColumns: GridColDef[] = [
    { field: 'instrument_name', headerName: 'Instrument', flex: 1, minWidth: 140 },
    { field: 'reason_name', headerName: 'Reason', width: 180 },
    { field: 'started_at', headerName: 'Started', flex: 1, minWidth: 160 },
    { field: 'ended_at', headerName: 'Ended', flex: 1, minWidth: 160 },
    { field: 'note', headerName: 'Note', flex: 1, minWidth: 140 },
    activeCol,
    actionsCol((p) => openEdit(p.row)),
  ];

  const title =
    tab === 'types'
      ? 'Instrument types'
      : tab === 'instances'
        ? 'Instruments'
        : tab === 'cro'
          ? 'CRO sources'
          : tab === 'maintenance'
            ? 'Maintenance'
            : 'Downtime';

  const rows =
    tab === 'types'
      ? filteredTypes
      : tab === 'instances'
        ? filteredInstruments
        : tab === 'cro'
          ? filteredCro
          : tab === 'maintenance'
            ? filteredSchedules
            : filteredDowntime;
  const columns =
    tab === 'types'
      ? typeColumns
      : tab === 'instances'
        ? instrumentColumns
        : tab === 'cro'
          ? croColumns
          : tab === 'maintenance'
            ? scheduleColumns
            : downtimeColumns;

  const canCreate =
    tab === 'maintenance' ? canManageSchedules : tab === 'downtime' ? canBench || canEdit : canEdit;

  return (
    <FillHeightPage>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
        <Typography variant="h5">{maintenanceOnly ? 'Instrument maintenance' : 'Instruments'}</Typography>
        {canCreate && (
          <Button startIcon={<Add />} variant="contained" onClick={openCreate}>
            Add {title.replace(/s$/, '')}
          </Button>
        )}
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        {maintenanceOnly
          ? 'Lab managers and administrators set schedules and the first due date. Retire a schedule with Active off; there is no delete.'
          : 'Types are a configurable list. Add a type or retire it with Active off — there is no delete. A run is not locked to one type. Vendor and model live on each instrument.'}
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 1 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {stopReason && (
        <Alert severity="error" sx={{ mb: 1 }} onClose={() => setStopReason(null)}>
          {stopReason}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 1 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}
      {!maintenanceOnly && (
        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 1 }}>
          <Tab value="types" label="Types" />
          <Tab value="instances" label="Instruments" />
          <Tab value="cro" label="CRO sources" />
          <Tab value="maintenance" label="Maintenance" />
          <Tab value="downtime" label="Downtime" />
        </Tabs>
      )}
      <TextField
        size="small"
        placeholder="Search"
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        InputProps={{ startAdornment: <Search fontSize="small" /> }}
        sx={{ mb: 1, maxWidth: 360 }}
      />
      <FillHeightTable>
        {loading ? (
          <Box display="flex" justifyContent="center" p={4}>
            <CircularProgress />
          </Box>
        ) : (
          <DataGrid rows={rows} columns={columns} disableRowSelectionOnClick getRowId={(r) => r.id} />
        )}
      </FillHeightTable>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingId ? 'Edit' : 'Add'} {title.replace(/s$/, '')}
        </DialogTitle>
        <DialogContent>
          {tab === 'types' && (
            <>
              <TextField
                label="Name"
                fullWidth
                margin="normal"
                value={typeForm.name}
                onChange={(e) => setTypeForm({ ...typeForm, name: e.target.value })}
              />
              <TextField
                label="Description"
                fullWidth
                margin="normal"
                value={typeForm.description}
                onChange={(e) => setTypeForm({ ...typeForm, description: e.target.value })}
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
            </>
          )}
          {tab === 'instances' && (
            <>
              <TextField
                label="Name"
                fullWidth
                margin="normal"
                value={instrumentForm.name}
                onChange={(e) => setInstrumentForm({ ...instrumentForm, name: e.target.value })}
              />
              <FormControl fullWidth margin="normal">
                <InputLabel id="instrument-type-label">Type</InputLabel>
                <Select
                  labelId="instrument-type-label"
                  label="Type"
                  value={instrumentForm.instrument_type_id}
                  onChange={(e) =>
                    setInstrumentForm({
                      ...instrumentForm,
                      instrument_type_id: String(e.target.value),
                    })
                  }
                >
                  {types.map((t) => (
                    <MenuItem key={t.id} value={t.id}>
                      {t.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Autocomplete
                options={vendors}
                getOptionLabel={(o) => o.name}
                value={vendors.find((v) => v.id === instrumentForm.vendor_id) || null}
                onChange={(_, v) => setInstrumentForm({ ...instrumentForm, vendor_id: v?.id || '' })}
                renderInput={(params) => <TextField {...params} label="Vendor" margin="normal" />}
              />
              <TextField
                label="Model"
                fullWidth
                margin="normal"
                value={instrumentForm.model}
                onChange={(e) => setInstrumentForm({ ...instrumentForm, model: e.target.value })}
              />
              <TextField
                label="Serial number"
                fullWidth
                margin="normal"
                value={instrumentForm.serial_number}
                onChange={(e) => setInstrumentForm({ ...instrumentForm, serial_number: e.target.value })}
              />
              <TextField
                label="Asset tag"
                fullWidth
                margin="normal"
                value={instrumentForm.asset_tag}
                onChange={(e) => setInstrumentForm({ ...instrumentForm, asset_tag: e.target.value })}
              />
              <FormControl fullWidth margin="normal">
                <InputLabel id="instrument-status-label">Status</InputLabel>
                <Select
                  labelId="instrument-status-label"
                  label="Status"
                  value={instrumentForm.status}
                  onChange={(e) => setInstrumentForm({ ...instrumentForm, status: String(e.target.value) })}
                >
                  {STATUSES.map((s) => (
                    <MenuItem key={s.value} value={s.value}>
                      {s.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControlLabel
                control={
                  <Switch
                    checked={instrumentForm.active}
                    onChange={(e) => setInstrumentForm({ ...instrumentForm, active: e.target.checked })}
                  />
                }
                label="Active"
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={instrumentForm.maintenance_tracked}
                    onChange={(e) =>
                      setInstrumentForm({
                        ...instrumentForm,
                        maintenance_tracked: e.target.checked,
                      })
                    }
                  />
                }
                label="Track maintenance"
              />
            </>
          )}
          {tab === 'cro' && (
            <>
              <TextField
                label="Name"
                fullWidth
                margin="normal"
                value={croForm.name}
                onChange={(e) => setCroForm({ ...croForm, name: e.target.value })}
              />
              <Autocomplete
                options={clients}
                getOptionLabel={(o) => o.name}
                value={clients.find((c) => c.id === croForm.client_id) || null}
                onChange={(_, v) => setCroForm({ ...croForm, client_id: v?.id || null })}
                renderInput={(params) => <TextField {...params} label="Client" margin="normal" />}
              />
              <TextField
                label="Description"
                fullWidth
                margin="normal"
                value={croForm.description}
                onChange={(e) => setCroForm({ ...croForm, description: e.target.value })}
              />
              <FormControlLabel
                control={
                  <Switch checked={croForm.active} onChange={(e) => setCroForm({ ...croForm, active: e.target.checked })} />
                }
                label="Active"
              />
            </>
          )}
          {tab === 'maintenance' && (
            <>
              <FormControl fullWidth margin="normal">
                <InputLabel>Instrument</InputLabel>
                <Select
                  label="Instrument"
                  value={scheduleForm.instrument_id}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, instrument_id: String(e.target.value) })}
                >
                  {instruments.map((i) => (
                    <MenuItem key={i.id} value={i.id}>
                      {i.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl fullWidth margin="normal">
                <InputLabel>Kind</InputLabel>
                <Select
                  label="Kind"
                  value={scheduleForm.kind_id}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, kind_id: String(e.target.value) })}
                >
                  {maintenanceKinds.map((k) => (
                    <MenuItem key={k.id} value={k.id}>
                      {k.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                label="Interval (days)"
                type="number"
                fullWidth
                margin="normal"
                value={scheduleForm.interval_days}
                onChange={(e) => setScheduleForm({ ...scheduleForm, interval_days: e.target.value })}
              />
              <Autocomplete
                options={vendors}
                getOptionLabel={(o) => o.name}
                value={vendors.find((v) => v.id === scheduleForm.service_vendor_id) || null}
                onChange={(_, v) => setScheduleForm({ ...scheduleForm, service_vendor_id: v?.id || '' })}
                renderInput={(params) => <TextField {...params} label="Service vendor" margin="normal" />}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={scheduleForm.active}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, active: e.target.checked })}
                  />
                }
                label="Active"
              />
            </>
          )}
          {tab === 'downtime' && (
            <>
              <FormControl fullWidth margin="normal">
                <InputLabel>Instrument</InputLabel>
                <Select
                  label="Instrument"
                  value={downtimeForm.instrument_id}
                  onChange={(e) => setDowntimeForm({ ...downtimeForm, instrument_id: String(e.target.value) })}
                >
                  {instruments.map((i) => (
                    <MenuItem key={i.id} value={i.id}>
                      {i.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl fullWidth margin="normal">
                <InputLabel>Reason</InputLabel>
                <Select
                  label="Reason"
                  value={downtimeForm.reason_id}
                  onChange={(e) => setDowntimeForm({ ...downtimeForm, reason_id: String(e.target.value) })}
                >
                  {downtimeReasons.map((k) => (
                    <MenuItem key={k.id} value={k.id}>
                      {k.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                label="Started at"
                type="datetime-local"
                fullWidth
                margin="normal"
                InputLabelProps={{ shrink: true }}
                value={downtimeForm.started_at}
                onChange={(e) => setDowntimeForm({ ...downtimeForm, started_at: e.target.value })}
              />
              <TextField
                label="Ended at"
                type="datetime-local"
                fullWidth
                margin="normal"
                InputLabelProps={{ shrink: true }}
                value={downtimeForm.ended_at}
                onChange={(e) => setDowntimeForm({ ...downtimeForm, ended_at: e.target.value })}
              />
              <TextField
                label="Note"
                fullWidth
                margin="normal"
                value={downtimeForm.note}
                onChange={(e) => setDowntimeForm({ ...downtimeForm, note: e.target.value })}
              />
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSubmit} disabled={submitting} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(firstDueId)} onClose={() => setFirstDueId(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Set first due date</DialogTitle>
        <DialogContent>
          <TextField
            label="First due date"
            type="date"
            fullWidth
            margin="normal"
            InputLabelProps={{ shrink: true }}
            value={firstDueDate}
            onChange={(e) => setFirstDueDate(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFirstDueId(null)}>Cancel</Button>
          <Button onClick={submitFirstDue} disabled={submitting || !firstDueDate} variant="contained">
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </FillHeightPage>
  );
};

export default InstrumentCatalogManagement;
