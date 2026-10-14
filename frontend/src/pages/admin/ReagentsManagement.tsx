/**
 * Reagent tracking catalog: vendors, vendor-agnostic reagents, reagent-vendor
 * sources (catalog number, reorder info), and received lots.
 * No delete: retire a row with Active off; use a lot up with Quantity remaining 0.
 * The lot used on a run is recorded on the LIMS run page (Reagents used).
 */
import React, { useCallback, useEffect, useState } from 'react';
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
  Paper,
  Select,
  Switch,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import { Add, Edit } from '@mui/icons-material';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';

type TabKey = 'vendors' | 'reagents' | 'sources' | 'lots';
type Row = Record<string, any>;

interface Field {
  key: string;
  label: string;
  type?: 'text' | 'date' | 'number' | 'vendor' | 'reagent' | 'source' | 'bool' | 'choice';
  choices?: string[];
  required?: boolean;
  createOnly?: boolean;
}

const FIELDS: Record<TabKey, Field[]> = {
  vendors: [
    { key: 'name', label: 'Name', required: true },
    { key: 'contact', label: 'Contact' },
    { key: 'email', label: 'Email' },
    { key: 'phone', label: 'Phone' },
    { key: 'website', label: 'Website' },
  ],
  reagents: [
    { key: 'name', label: 'Name', required: true },
    { key: 'storage_condition', label: 'Storage condition', type: 'choice', choices: ['-80C', '-20C', '4C', 'RT'] },
    { key: 'unit', label: 'Unit' },
    { key: 'stability_after_opening_days', label: 'Stability after opening (days)', type: 'number' },
    { key: 'hazard_class', label: 'Hazard class' },
    { key: 'sds_url', label: 'SDS link' },
  ],
  sources: [
    { key: 'reagent_id', label: 'Reagent', type: 'reagent', required: true, createOnly: true },
    { key: 'vendor_id', label: 'Vendor', type: 'vendor', required: true, createOnly: true },
    { key: 'catalog_number', label: 'Catalog number' },
    { key: 'unit', label: 'Unit' },
    { key: 'unit_of_sale', label: 'Unit of sale' },
    { key: 'quantity_per_unit_of_sale', label: 'Quantity per unit of sale', type: 'number' },
    { key: 'price_per_unit', label: 'Price per unit', type: 'number' },
    { key: 'reorder_point', label: 'Reorder point', type: 'number' },
    { key: 'reorder_quantity', label: 'Reorder quantity', type: 'number' },
    { key: 'lead_time_days', label: 'Lead time (days)', type: 'number' },
    { key: 'is_preferred', label: 'Preferred vendor', type: 'bool' },
  ],
  lots: [
    { key: 'reagent_id', label: 'Reagent', type: 'reagent', required: true, createOnly: true },
    { key: 'reagent_vendor_id', label: 'Bought from', type: 'source' },
    { key: 'lot_number', label: 'Lot number', required: true },
    { key: 'expiration_date', label: 'Expiration', type: 'date' },
    { key: 'purchased_date', label: 'Purchased', type: 'date' },
    { key: 'received_date', label: 'Received', type: 'date' },
    { key: 'opened_date', label: 'Opened', type: 'date' },
    { key: 'quantity_received', label: 'Quantity received', type: 'number' },
    { key: 'quantity_remaining', label: 'Quantity remaining', type: 'number' },
    { key: 'unit', label: 'Unit' },
    { key: 'storage_location', label: 'Storage location' },
    { key: 'qc_status', label: 'QC status', type: 'choice', choices: ['pending', 'released', 'rejected'] },
    { key: 'coa_url', label: 'Certificate of analysis (link)' },
  ],
};

const COLUMNS: Record<TabKey, { key: string; label: string }[]> = {
  vendors: [
    { key: 'name', label: 'Name' },
    { key: 'contact', label: 'Contact' },
    { key: 'email', label: 'Email' },
  ],
  reagents: [
    { key: 'name', label: 'Name' },
    { key: 'vendor_names', label: 'Vendors' },
    { key: 'storage_condition', label: 'Storage' },
    { key: 'quantity_on_hand', label: 'On hand' },
  ],
  sources: [
    { key: 'reagent_name', label: 'Reagent' },
    { key: 'vendor_name', label: 'Vendor' },
    { key: 'catalog_number', label: 'Catalog #' },
    { key: 'unit_of_sale', label: 'Unit of sale' },
    { key: 'price_per_unit', label: 'Price / unit' },
    { key: 'reorder_point', label: 'Reorder point' },
    { key: 'is_preferred', label: 'Preferred' },
  ],
  lots: [
    { key: 'reagent_name', label: 'Reagent' },
    { key: 'lot_number', label: 'Lot' },
    { key: 'effective_expiration_date', label: 'Expires' },
    { key: 'quantity_remaining', label: 'Remaining' },
    { key: 'unit', label: 'Unit' },
    { key: 'storage_location', label: 'Location' },
    { key: 'qc_status', label: 'QC' },
  ],
};

const LABELS: Record<TabKey, string> = { vendors: 'vendor', reagents: 'reagent', sources: 'reagent vendor', lots: 'lot' };

const cell = (value: any) => (Array.isArray(value) ? value.join(', ') || '—' : value === true ? 'Yes' : value === false ? '' : value ?? '—');

const errorText = (err: any, fallback: string) => {
  const detail = err?.response?.data?.detail;
  return typeof detail === 'string' ? detail : fallback;
};

const ReagentsManagement: React.FC = () => {
  const { hasPermission } = useUser();
  const canEdit = hasPermission('config:edit');
  const [tab, setTab] = useState<TabKey>('vendors');
  const [vendors, setVendors] = useState<Row[]>([]);
  const [reagents, setReagents] = useState<Row[]>([]);
  const [sources, setSources] = useState<Row[]>([]);
  const [lots, setLots] = useState<Row[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Row | null>(null);
  const [form, setForm] = useState<Row>({});
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [v, r, src, l] = await Promise.all([
        apiService.getVendors(),
        apiService.getReagents(),
        apiService.getReagentVendors(),
        apiService.getReagentLots(),
      ]);
      setVendors(v || []);
      setReagents(r || []);
      setSources(src || []);
      setLots(l || []);
    } catch (err) {
      setError(errorText(err, 'Failed to load reagent catalog'));
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const rows = { vendors, reagents, sources, lots }[tab];

  const openDialog = (row: Row | null) => {
    setError(null);
    setEditing(row || {});
    const initial: Row = { active: row ? row.active : true };
    FIELDS[tab].forEach((f) => {
      initial[f.key] = row?.[f.key] ?? (f.type === 'bool' ? false : f.key === 'qc_status' ? 'pending' : '');
    });
    setForm(initial);
  };

  const save = async () => {
    setSaving(true);
    const body: Row = { active: form.active };
    FIELDS[tab].forEach((f) => {
      if (editing?.id && f.createOnly) return;
      const value = form[f.key];
      body[f.key] = value === '' ? null : value;
    });
    try {
      const id = editing?.id;
      if (tab === 'vendors') {
        await (id ? apiService.updateVendor(id, body) : apiService.createVendor(body));
      } else if (tab === 'reagents') {
        await (id ? apiService.updateReagent(id, body) : apiService.createReagent(body));
      } else if (tab === 'sources') {
        await (id ? apiService.updateReagentVendor(id, body) : apiService.createReagentVendor(body));
      } else {
        await (id ? apiService.updateReagentLot(id, body) : apiService.createReagentLot(body));
      }
      setEditing(null);
      await load();
    } catch (err) {
      setError(errorText(err, `Could not save the ${LABELS[tab]}`));
    } finally {
      setSaving(false);
    }
  };

  const renderField = (f: Field) => {
    const disabled = Boolean(editing?.id && f.createOnly);
    if (f.type === 'bool') {
      return (
        <FormControlLabel
          key={f.key}
          sx={{ mt: 2, display: 'block' }}
          control={<Switch checked={Boolean(form[f.key])} onChange={(e) => setForm({ ...form, [f.key]: e.target.checked })} />}
          label={f.label}
        />
      );
    }
    if (f.type === 'vendor' || f.type === 'reagent' || f.type === 'source' || f.type === 'choice') {
      const pool =
        f.type === 'choice'
          ? (f.choices || []).map((c) => ({ id: c, name: c, active: true }))
          : f.type === 'vendor'
            ? vendors
            : f.type === 'reagent'
              ? reagents
              : sources
                  .filter((src) => !form.reagent_id || src.reagent_id === form.reagent_id)
                  .map((src) => ({ ...src, name: `${src.vendor_name}${src.catalog_number ? ` · ${src.catalog_number}` : ''}` }));
      const options = pool.filter((o: Row) => o.active || o.id === form[f.key]);
      return (
        <FormControl key={f.key} fullWidth size="small" sx={{ mt: 2 }} disabled={disabled}>
          <InputLabel id={`${f.key}-label`}>{f.label}</InputLabel>
          <Select
            labelId={`${f.key}-label`}
            label={f.label}
            value={form[f.key] || ''}
            onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
          >
            {!f.required && (
              <MenuItem value="">
                <em>None</em>
              </MenuItem>
            )}
            {options.map((o) => (
              <MenuItem key={o.id} value={o.id}>
                {o.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      );
    }
    return (
      <TextField
        key={f.key}
        label={f.label}
        size="small"
        fullWidth
        required={f.required}
        sx={{ mt: 2 }}
        type={f.type === 'date' ? 'date' : f.type === 'number' ? 'number' : 'text'}
        InputLabelProps={f.type === 'date' ? { shrink: true } : undefined}
        value={form[f.key] ?? ''}
        onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
      />
    );
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        Reagents
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Vendors, reagents (vendor-agnostic), the vendors each reagent is bought from, and received lots. Record the lot used on a run from the LIMS run page. Nothing is
        deleted: turn Active off to retire a row, or set a lot&apos;s quantity remaining to 0. An opened lot expires at the earlier of its printed expiry and opened date + stability.
      </Typography>
      {error && !editing && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Tabs value={tab} onChange={(_e, v) => setTab(v)}>
          <Tab value="vendors" label="Vendors" />
          <Tab value="reagents" label="Reagents" />
          <Tab value="sources" label="Reagent vendors" />
          <Tab value="lots" label="Lots" />
        </Tabs>
        {canEdit && (
          <Button startIcon={<Add />} variant="contained" onClick={() => openDialog(null)}>
            {`Add ${LABELS[tab]}`}
          </Button>
        )}
      </Box>
      <TableContainer component={Paper} sx={{ mt: 2 }}>
        <Table size="small" aria-label={`${tab} table`}>
          <TableHead>
            <TableRow>
              {COLUMNS[tab].map((c) => (
                <TableCell key={c.key}>{c.label}</TableCell>
              ))}
              <TableCell>Status</TableCell>
              {canEdit && <TableCell />}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length === 0 && (
              <TableRow>
                <TableCell colSpan={COLUMNS[tab].length + 2}>
                  <Typography variant="body2" color="text.secondary">
                    {`No ${tab} yet.`}
                  </Typography>
                </TableCell>
              </TableRow>
            )}
            {rows.map((row) => (
              <TableRow key={row.id}>
                {COLUMNS[tab].map((c) => (
                  <TableCell key={c.key}>{cell(row[c.key])}</TableCell>
                ))}
                <TableCell>
                  {!row.active ? (
                    <Chip size="small" label="Inactive" />
                  ) : row.expired ? (
                    <Chip size="small" color="error" label="Expired" />
                  ) : row.qc_status === 'rejected' ? (
                    <Chip size="small" color="error" label="QC rejected" />
                  ) : row.below_reorder_point ? (
                    <Chip size="small" color="warning" label="Reorder" />
                  ) : (
                    <Chip size="small" color="success" label="Active" />
                  )}
                </TableCell>
                {canEdit && (
                  <TableCell>
                    <Button size="small" startIcon={<Edit />} onClick={() => openDialog(row)}>
                      Edit
                    </Button>
                  </TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={Boolean(editing)} onClose={() => !saving && setEditing(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{`${editing?.id ? 'Edit' : 'Add'} ${LABELS[tab]}`}</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 1 }}>
              {error}
            </Alert>
          )}
          {FIELDS[tab].map(renderField)}
          <FormControlLabel
            sx={{ mt: 2 }}
            control={<Switch checked={Boolean(form.active)} onChange={(e) => setForm({ ...form, active: e.target.checked })} />}
            label="Active"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditing(null)} disabled={saving}>
            Cancel
          </Button>
          <Button variant="contained" onClick={save} disabled={saving}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ReagentsManagement;
