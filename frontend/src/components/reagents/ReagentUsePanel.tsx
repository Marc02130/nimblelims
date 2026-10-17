/**
 * Reagents used on a LIMS run (or experiment): pick a lot, enter the quantity
 * used; the lot's quantity remaining goes down. Expired (effective expiry),
 * QC-rejected and inactive lots are refused by the API; the picker only offers
 * usable lots. A wrong entry is voided (no delete).
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { apiService } from '../../services/apiService';
import { useUser } from '../../contexts/UserContext';

export interface ReagentUseRow {
  id: string;
  reagent_name?: string;
  lot_number: string;
  expiration_date?: string | null;
  used_on: string;
  quantity_used: string | number;
  unit?: string | null;
  note?: string | null;
}

interface LotOption {
  id: string;
  reagent_id?: string;
  reagent_name?: string;
  lot_number: string;
  effective_expiration_date?: string | null;
  quantity_remaining?: string | number | null;
  unit?: string | null;
}

interface Props {
  limsRunId?: string;
  experimentId?: string;
  analysisId?: string | null;
  /** When set, the picker offers lots of these catalog reagents only. */
  allowedReagentIds?: string[];
}

const errorText = (err: any, fallback: string) => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && typeof detail.message === 'string') {
    return detail.message;
  }
  return fallback;
};

const ReagentUsePanel: React.FC<Props> = ({
  limsRunId,
  experimentId,
  analysisId,
  allowedReagentIds,
}) => {
  const { hasPermission } = useUser();
  const canRecord = hasPermission('experiment:manage');
  const [uses, setUses] = useState<ReagentUseRow[]>([]);
  const [lots, setLots] = useState<LotOption[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [lotId, setLotId] = useState('');
  const [quantity, setQuantity] = useState('');
  const [usedOn, setUsedOn] = useState('');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);

  const target = limsRunId ? { lims_run_id: limsRunId } : { experiment_id: experimentId };

  const load = useCallback(async () => {
    try {
      setUses((await apiService.getReagentUses(target)) || []);
    } catch (err) {
      setError(errorText(err, 'Failed to load reagents used'));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [limsRunId, experimentId]);

  useEffect(() => {
    load();
  }, [load]);

  const openDialog = async () => {
    setError(null);
    setLotId('');
    setQuantity('');
    setUsedOn('');
    setNote('');
    setOpen(true);
    try {
      const loaded = ((await apiService.getReagentLots({ usable: true })) || []) as LotOption[];
      if (allowedReagentIds !== undefined) {
        const allow = new Set(allowedReagentIds);
        setLots(loaded.filter((lot) => lot.reagent_id != null && allow.has(lot.reagent_id)));
      } else {
        setLots(loaded);
      }
    } catch (err) {
      setError(errorText(err, 'Failed to load reagent lots'));
    }
  };

  const save = async () => {
    setSaving(true);
    try {
      await apiService.recordReagentUse({
        reagent_lot_id: lotId,
        ...target,
        analysis_id: analysisId || undefined,
        quantity_used: quantity,
        unit: lots.find((l) => l.id === lotId)?.unit || undefined,
        used_on: usedOn || undefined,
        note: note || undefined,
      });
      setOpen(false);
      await load();
    } catch (err) {
      setError(errorText(err, 'Could not record the reagent use'));
    } finally {
      setSaving(false);
    }
  };

  const voidUse = async (id: string) => {
    try {
      await apiService.voidReagentUse(id);
      await load();
    } catch (err) {
      setError(errorText(err, 'Could not void the reagent use'));
    }
  };

  return (
    <Card sx={{ mt: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Typography variant="h6">Reagents used</Typography>
          {canRecord && (
            <Button variant="outlined" size="small" onClick={openDialog}>
              Record lot used
            </Button>
          )}
        </Box>
        {error && !open && (
          <Alert severity="error" sx={{ mb: 1 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        {uses.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No reagent lots recorded.
          </Typography>
        ) : (
          <Table size="small" aria-label="Reagents used">
            <TableHead>
              <TableRow>
                <TableCell>Reagent</TableCell>
                <TableCell>Lot</TableCell>
                <TableCell>Expires</TableCell>
                <TableCell>Used on</TableCell>
                <TableCell>Quantity</TableCell>
                <TableCell>Note</TableCell>
                {canRecord && <TableCell />}
              </TableRow>
            </TableHead>
            <TableBody>
              {uses.map((u) => (
                <TableRow key={u.id}>
                  <TableCell>{u.reagent_name}</TableCell>
                  <TableCell>{u.lot_number}</TableCell>
                  <TableCell>{u.expiration_date || '—'}</TableCell>
                  <TableCell>{u.used_on}</TableCell>
                  <TableCell>{`${u.quantity_used} ${u.unit || ''}`.trim()}</TableCell>
                  <TableCell>{u.note || ''}</TableCell>
                  {canRecord && (
                    <TableCell>
                      <Button size="small" onClick={() => voidUse(u.id)}>
                        Void
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <Dialog open={open} onClose={() => !saving && setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Record lot used</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 1 }}>
              {error}
            </Alert>
          )}
          <FormControl fullWidth size="small" sx={{ mt: 1 }}>
            <InputLabel id="reagent-lot-label">Lot</InputLabel>
            <Select labelId="reagent-lot-label" label="Lot" value={lotId} onChange={(e) => setLotId(e.target.value as string)}>
              {lots.map((l) => (
                <MenuItem key={l.id} value={l.id}>
                  {`${l.reagent_name || ''} · ${l.lot_number}${l.effective_expiration_date ? ` · exp ${l.effective_expiration_date}` : ''}${
                    l.quantity_remaining != null ? ` · ${l.quantity_remaining} ${l.unit || ''} left` : ''
                  }`}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {lots.length === 0 && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {allowedReagentIds !== undefined
                ? 'No usable lots of the reagents named on this experiment template.'
                : 'No usable lots. Receive a lot under Admin → Reagents.'}
            </Typography>
          )}
          <TextField
            label={`Quantity used${lots.find((l) => l.id === lotId)?.unit ? ` (${lots.find((l) => l.id === lotId)?.unit})` : ''}`}
            size="small"
            type="number"
            required
            fullWidth
            sx={{ mt: 2 }}
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
          />
          <TextField
            label="Used on"
            size="small"
            type="date"
            fullWidth
            sx={{ mt: 2 }}
            InputLabelProps={{ shrink: true }}
            value={usedOn}
            onChange={(e) => setUsedOn(e.target.value)}
            helperText="Leave empty for today"
          />
          <TextField label="Note" size="small" fullWidth sx={{ mt: 2 }} value={note} onChange={(e) => setNote(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)} disabled={saving}>
            Cancel
          </Button>
          <Button variant="contained" onClick={save} disabled={saving || !lotId || quantity === ''}>
            Record
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default ReagentUsePanel;
