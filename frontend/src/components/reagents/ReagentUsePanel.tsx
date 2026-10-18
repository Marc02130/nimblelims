/**
 * Reagents used on a LIMS run or an experiment. On an experiment the template
 * list is the default: the tech can add any active catalog reagent, then pick
 * a usable lot. Expired, QC-rejected, and inactive lots are refused by the API.
 * A wrong entry is voided (no delete).
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
  usable?: boolean;
  active?: boolean;
  released?: boolean;
  expired?: boolean;
  qc_status?: string | null;
}

interface CatalogReagent {
  id: string;
  name: string;
}

interface Props {
  limsRunId?: string;
  experimentId?: string;
  analysisId?: string | null;
  /**
   * Reagents saved on the experiment. Undefined on a LIMS run, which offers
   * every usable lot. An empty list is an experiment with nothing saved yet.
   */
  defaultReagentIds?: string[];
  /** Reload the experiment after a reagent is saved, so a new entry appears. */
  onReagentsChanged?: () => void;
}

const lotIsUsable = (lot: LotOption) => {
  if (lot.usable === false || lot.active === false || lot.released === false) return false;
  if (lot.expired === true || lot.qc_status === 'rejected') return false;
  return true;
};

const lotLabel = (lot: LotOption) =>
  `${lot.lot_number}${lot.effective_expiration_date ? ` · exp ${lot.effective_expiration_date}` : ''}${
    lot.quantity_remaining != null ? ` · ${lot.quantity_remaining} ${lot.unit || ''} left` : ''
  }`;

const ReagentLotPicker: React.FC<{
  reagentId: string;
  reagentName: string;
  lots: LotOption[];
  canRecord: boolean;
  saving: boolean;
  onRecord: (lotId: string, quantity: string) => Promise<void>;
}> = ({ reagentId, reagentName, lots, canRecord, saving, onRecord }) => {
  const [lotId, setLotId] = useState('');
  const [quantity, setQuantity] = useState('');
  const label = `Lot for ${reagentName}`;
  return (
    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 1, flexWrap: 'wrap' }}>
      <Typography sx={{ minWidth: 160, pt: 1 }}>{reagentName}</Typography>
      <FormControl size="small" sx={{ minWidth: 240 }}>
        <InputLabel id={`lot-for-${reagentId}`}>{label}</InputLabel>
        <Select
          labelId={`lot-for-${reagentId}`}
          label={label}
          value={lotId}
          onChange={(event) => setLotId(String(event.target.value))}
        >
          {lots.map((lot) => (
            <MenuItem key={lot.id} value={lot.id}>
              {lotLabel(lot)}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {lots.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ pt: 1 }}>
          No usable lots for {reagentName}.
        </Typography>
      )}
      {canRecord && (
        <>
          <TextField
            label={`Quantity for ${reagentName}`}
            size="small"
            type="number"
            required
            value={quantity}
            onChange={(event) => setQuantity(event.target.value)}
            sx={{ width: 160 }}
          />
          <Button
            variant="contained"
            size="small"
            sx={{ mt: 0.5 }}
            disabled={saving || !lotId || quantity === ''}
            onClick={() => onRecord(lotId, quantity)}
          >
            Record
          </Button>
        </>
      )}
    </Box>
  );
};

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
  defaultReagentIds,
  onReagentsChanged,
}) => {
  const { hasPermission } = useUser();
  const canRecord = hasPermission('experiment:manage');
  const onExperiment = Boolean(experimentId);
  const [uses, setUses] = useState<ReagentUseRow[]>([]);
  const [lots, setLots] = useState<LotOption[]>([]);
  const [catalog, setCatalog] = useState<CatalogReagent[]>([]);
  const [names, setNames] = useState<CatalogReagent[]>([]);
  const [chosenIds, setChosenIds] = useState<string[]>(defaultReagentIds ?? []);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [lotId, setLotId] = useState('');
  const [quantity, setQuantity] = useState('');
  const [usedOn, setUsedOn] = useState('');
  const [note, setNote] = useState('');
  const [saving, setSaving] = useState(false);
  const snapshotKey = defaultReagentIds === undefined ? '' : defaultReagentIds.join('\n');

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

  useEffect(() => {
    if (defaultReagentIds === undefined) return;
    setChosenIds(defaultReagentIds);
    // snapshotKey is the stable identity of the prefilled ids.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshotKey]);

  useEffect(() => {
    if (!experimentId) return;
    let cancelled = false;
    apiService
      .getReagents({ include_inactive: true })
      .then((raw) => {
        if (cancelled) return;
        const list = (Array.isArray(raw) ? raw : []) as Array<{
          id?: string;
          name?: string;
          active?: boolean;
        }>;
        const named = list
          .filter((row) => row?.id && row?.name)
          .map((row) => ({ id: String(row.id), name: String(row.name), active: row.active }));
        setNames(named.map((row) => ({ id: row.id, name: row.name })));
        setCatalog(
          named
            .filter((row) => row.active !== false)
            .map((row) => ({ id: row.id, name: row.name })),
        );
      })
      .catch((err) => {
        if (!cancelled) setError(errorText(err, 'Failed to load reagents'));
      });
    return () => {
      cancelled = true;
    };
  }, [experimentId]);

  const loadLots = useCallback(async () => {
    const loaded = ((await apiService.getReagentLots({ usable: true })) || []) as LotOption[];
    setLots(loaded.filter(lotIsUsable));
  }, []);

  useEffect(() => {
    if (!experimentId) return;
    let cancelled = false;
    loadLots().catch((err) => {
      if (!cancelled) setError(errorText(err, 'Failed to load reagent lots'));
    });
    return () => {
      cancelled = true;
    };
  }, [experimentId, loadLots]);

  const addReagent = async (reagentId: string) => {
    if (!experimentId || !reagentId || reagentId === '__none') return;
    try {
      const saved = await apiService.addExperimentReagent(experimentId, reagentId);
      const ids = Array.isArray(saved?.allowed_reagent_ids)
        ? saved.allowed_reagent_ids.map((id: unknown) => String(id))
        : chosenIds;
      setChosenIds(ids);
      if (onReagentsChanged) await onReagentsChanged();
    } catch (err) {
      setError(errorText(err, 'Could not add the reagent'));
    }
  };

  const openDialog = async () => {
    setError(null);
    setLotId('');
    setQuantity('');
    setUsedOn('');
    setNote('');
    setOpen(true);
    try {
      await loadLots();
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
      if (limsRunId) {
        try {
          await loadLots();
        } catch {
          // The use was recorded; the lot list refreshes on the next open.
        }
      }
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

  const addable = catalog.filter((row) => !chosenIds.includes(row.id));
  const reagentName = (id: string) => names.find((row) => row.id === id)?.name || id;

  const recordForReagent = async (lotIdForReagent: string, quantityForReagent: string) => {
    setSaving(true);
    setError(null);
    try {
      await apiService.recordReagentUse({
        reagent_lot_id: lotIdForReagent,
        ...target,
        analysis_id: analysisId || undefined,
        quantity_used: quantityForReagent,
        unit: lots.find((lot) => lot.id === lotIdForReagent)?.unit || undefined,
      });
      await load();
      await loadLots();
    } catch (err) {
      setError(errorText(err, 'Could not record the reagent use'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card sx={{ mt: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1, gap: 1 }}>
          <Typography variant="h6">Reagents used</Typography>
          {canRecord && onExperiment && (
            <FormControl size="small" sx={{ minWidth: 220 }}>
              <InputLabel id="add-reagent-label">Add reagent</InputLabel>
              <Select
                labelId="add-reagent-label"
                label="Add reagent"
                value=""
                onChange={(event) => addReagent(String(event.target.value || ''))}
              >
                <MenuItem value="" sx={{ display: 'none' }} />
                {addable.length === 0 ? (
                  <MenuItem value="__none" disabled>
                    {catalog.length === 0
                      ? 'No active reagents in the catalog'
                      : 'Every active reagent is already on this experiment'}
                  </MenuItem>
                ) : (
                  addable.map((row) => (
                    <MenuItem key={row.id} value={row.id}>
                      {row.name}
                    </MenuItem>
                  ))
                )}
              </Select>
            </FormControl>
          )}
          {canRecord && !onExperiment && (
            <Button variant="outlined" size="small" onClick={openDialog}>
              Record lot used
            </Button>
          )}
        </Box>
        {onExperiment && chosenIds.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            No reagents yet. Add a reagent, then record its lot.
          </Typography>
        )}
        {onExperiment &&
          chosenIds.map((reagentId) => {
            const name = reagentName(reagentId);
            const mine = lots.filter((lot) => lot.reagent_id === reagentId && lotIsUsable(lot));
            return (
              <ReagentLotPicker
                key={reagentId}
                reagentId={reagentId}
                reagentName={name}
                lots={mine}
                canRecord={canRecord}
                saving={saving}
                onRecord={recordForReagent}
              />
            );
          })}
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
              {onExperiment
                ? chosenIds.length === 0
                  ? 'Add a reagent, then record its lot.'
                  : 'No usable lots of the reagents on this experiment. Receive a lot under Admin → Reagents.'
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
