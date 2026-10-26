/**
 * Instruments used on a LIMS run or an experiment. On an experiment the
 * template names the default catalog instruments. The tech can add any
 * eligible instrument, then record its use.
 */
import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
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
import { localDateString } from '../../utils/localDate';

export interface InstrumentUseRow {
  id: string;
  instrument_id: string;
  instrument_name?: string;
  used_on: string;
  note?: string;
  active: boolean;
}

interface CatalogInstrument {
  id: string;
  name: string;
  active?: boolean;
  status?: string;
  maintenance_tracked?: boolean;
}

interface InstrumentSlot {
  key: string;
  label?: string;
  instrument_type_id?: string | null;
  required?: boolean;
  run_import?: boolean;
}

interface Props {
  experimentId?: string;
  limsRunId?: string;
  entryId?: string;
  slots?: InstrumentSlot[];
  instrumentTypeId?: string;
  defaultInstrumentIds?: string[];
  onInstrumentsChanged?: () => void;
}

const apiErrorMsg = (err: any, fallback: string): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object' && detail.message) return detail.message;
  return fallback;
};

const InstrumentUsePanel: React.FC<Props> = ({
  experimentId,
  limsRunId,
  entryId,
  slots,
  instrumentTypeId,
  defaultInstrumentIds,
  onInstrumentsChanged,
}) => {
  const [uses, setUses] = useState<InstrumentUseRow[]>([]);
  const [catalog, setCatalog] = useState<CatalogInstrument[]>([]);
  const [chosenIds, setChosenIds] = useState<string[]>(defaultInstrumentIds ?? []);
  const [usedOn, setUsedOn] = useState(localDateString());
  const [note, setNote] = useState('');
  const [slotKey, setSlotKey] = useState(slots?.[0]?.key || '');
  const [error, setError] = useState<string | null>(null);
  const [stop, setStop] = useState<string | null>(null);
  const [localSlots, setLocalSlots] = useState<InstrumentSlot[]>(slots || []);
  const [typeOptions, setTypeOptions] = useState<{ id: string; name: string }[]>([]);
  const snapshotKey = defaultInstrumentIds === undefined ? '' : defaultInstrumentIds.join('\n');
  const selectedSlot = (localSlots || []).find((s) => s.key === slotKey);
  const pickerTypeId = selectedSlot?.instrument_type_id || instrumentTypeId;

  const target = limsRunId ? { lims_run_id: limsRunId } : experimentId ? { experiment_id: experimentId } : {};

  const load = async () => {
    setUses((await apiService.getInstrumentUses(target)) || []);
  };

  useEffect(() => {
    load().catch(() => undefined);
  }, [limsRunId, experimentId]);

  useEffect(() => {
    if (defaultInstrumentIds === undefined) return;
    setChosenIds(defaultInstrumentIds);
  }, [snapshotKey]);

  useEffect(() => {
    setLocalSlots(slots || []);
    if (slots && slots.length && !slotKey) {
      setSlotKey(slots[0].key);
    }
  }, [slots, slotKey]);

  useEffect(() => {
    if (!experimentId || !entryId) return;
    apiService
      .getInstrumentTypes()
      .then((rows: any) => setTypeOptions((rows || []).filter((t: any) => t.active !== false)))
      .catch(() => setTypeOptions([]));
  }, [experimentId, entryId]);

  const persistSlots = async (next: InstrumentSlot[]) => {
    if (!entryId) return;
    setError(null);
    try {
      await apiService.updateEntry(entryId, {
        config: { slots: next, allowed_instrument_ids: chosenIds },
      });
      setLocalSlots(next);
      if (onInstrumentsChanged) await onInstrumentsChanged();
    } catch (err: any) {
      setError(apiErrorMsg(err, 'Could not update instrument slots'));
    }
  };

  useEffect(() => {
    apiService
      .getInstruments({
        active: true,
        eligible: true,
        instrument_type_id: pickerTypeId,
      })
      .then((rows) => setCatalog(rows || []))
      .catch(() => setCatalog([]));
  }, [pickerTypeId]);

  const addInstrument = async (instrumentId: string) => {
    if (!experimentId || !instrumentId) return;
    setError(null);
    setStop(null);
    try {
      const elig = await apiService.getInstrumentEligibility(instrumentId);
      if (elig && elig.allowed === false) {
        const awaiting = elig.code === 'instrument_awaiting_first_due' ? 'Awaiting first due date. ' : '';
        const tracked = elig.maintenance_tracked ? 'Maintenance is tracked. ' : '';
        setStop(`${awaiting}${tracked}${elig.message || 'This instrument cannot be used.'}`);
        return;
      }
      const saved = await apiService.addExperimentInstrument(experimentId, instrumentId);
      setChosenIds(saved.allowed_instrument_ids || [...chosenIds, instrumentId]);
      if (onInstrumentsChanged) await onInstrumentsChanged();
    } catch (err: any) {
      const message = apiErrorMsg(err, 'Could not add instrument');
      setStop(message);
      setError(message);
    }
  };

  const recordUse = async (instrumentId: string) => {
    setError(null);
    setStop(null);
    try {
      const elig = await apiService.getInstrumentEligibility(instrumentId);
      if (elig && elig.allowed === false) {
        const awaiting = elig.code === 'instrument_awaiting_first_due' ? 'Awaiting first due date. ' : '';
        const tracked = elig.maintenance_tracked ? 'Maintenance is tracked. ' : '';
        setStop(`${awaiting}${tracked}${elig.message || 'This instrument cannot be used.'}`);
        return;
      }
      if ((slots || []).length > 0 && !slotKey) {
        setError('Pick an instrument slot first.');
        return;
      }
      await apiService.recordInstrumentUse({
        instrument_id: instrumentId,
        lims_run_id: limsRunId,
        experiment_id: experimentId,
        entry_id: entryId,
        slot_key: slotKey || undefined,
        used_on: usedOn || localDateString(),
        note: note || undefined,
      });
      setNote('');
      await load();
    } catch (err: any) {
      const message = apiErrorMsg(err, 'Could not record instrument use');
      setStop(message);
      setError(message);
    }
  };

  const removeInstrument = async (instrumentId: string) => {
    if (!experimentId) return;
    try {
      const saved = await apiService.setExperimentInstrumentActive(experimentId, instrumentId, false);
      setChosenIds(saved.allowed_instrument_ids || chosenIds.filter((id) => id !== instrumentId));
      if (onInstrumentsChanged) await onInstrumentsChanged();
    } catch (err: any) {
      setError(apiErrorMsg(err, 'Could not remove instrument'));
    }
  };

  const voidUse = async (id: string) => {
    await apiService.voidInstrumentUse(id);
    await load();
  };

  const canRecord = Boolean(experimentId || limsRunId);
  const available = catalog.filter((row) => !chosenIds.includes(row.id));

  return (
    <Box>
      <Typography variant="h6">Instruments used</Typography>
      {stop && (
        <Alert severity="error" sx={{ my: 1 }} onClose={() => setStop(null)}>
          {stop}
        </Alert>
      )}
      {error && !stop && (
        <Alert severity="error" sx={{ my: 1 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {(localSlots || []).length > 0 && (
        <FormControl size="small" sx={{ minWidth: 220, my: 1, mr: 1 }}>
          <InputLabel>Slot</InputLabel>
          <Select
            label="Slot"
            value={slotKey}
            onChange={(event) => setSlotKey(String(event.target.value || ''))}
          >
            {(localSlots || []).map((slot) => (
              <MenuItem key={slot.key} value={slot.key}>
                {slot.label || slot.key}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      )}
      {experimentId && entryId && (
        <Box sx={{ my: 1 }}>
          <Typography variant="subtitle2">Slots on this entry</Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            Types change on this entry, not the template. Changing a type voids the old use.
          </Typography>
          {localSlots.map((slot, si) => (
            <Box key={`${slot.key}-${si}`} display="flex" gap={1} flexWrap="wrap" sx={{ my: 0.5 }}>
              <TextField
                size="small"
                label="Key"
                value={slot.key}
                onChange={(e) => {
                  const next = localSlots.map((s, i) => (i === si ? { ...s, key: e.target.value } : s));
                  setLocalSlots(next);
                }}
                onBlur={() => persistSlots(localSlots)}
              />
              <FormControl size="small" sx={{ minWidth: 160 }}>
                <InputLabel>Type</InputLabel>
                <Select
                  label="Type"
                  value={slot.instrument_type_id || ''}
                  onChange={(e) => {
                    const next = localSlots.map((s, i) =>
                      i === si ? { ...s, instrument_type_id: String(e.target.value || '') || null } : s,
                    );
                    void persistSlots(next);
                  }}
                  inputProps={{ 'aria-label': `Slot ${slot.key} type` }}
                >
                  {!slot.run_import && <MenuItem value="">None</MenuItem>}
                  {typeOptions.map((t) => (
                    <MenuItem key={t.id} value={t.id}>
                      {t.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button
                size="small"
                onClick={() => void persistSlots(localSlots.filter((_, i) => i !== si))}
              >
                Remove slot
              </Button>
            </Box>
          ))}
          <Button
            size="small"
            onClick={() =>
              void persistSlots([
                ...localSlots,
                {
                  key: `slot_${localSlots.length + 1}`,
                  label: '',
                  instrument_type_id: null,
                  required: false,
                  run_import: false,
                },
              ])
            }
          >
            Add slot
          </Button>
        </Box>
      )}
      {experimentId && (
        <FormControl size="small" sx={{ minWidth: 280, my: 1 }}>
          <InputLabel>Add instrument</InputLabel>
          <Select
            label="Add instrument"
            value=""
            onChange={(event) => addInstrument(String(event.target.value || ''))}
          >
            {available.length === 0 ? (
              <MenuItem value="" disabled>
                No other active instruments
              </MenuItem>
            ) : (
              available.map((row) => (
                <MenuItem key={row.id} value={row.id}>
                  {row.name}
                </MenuItem>
              ))
            )}
          </Select>
        </FormControl>
      )}
      {canRecord && (
        <Box display="flex" gap={1} flexWrap="wrap" alignItems="center" sx={{ my: 1 }}>
          <TextField
            size="small"
            type="date"
            label="Used on"
            InputLabelProps={{ shrink: true }}
            value={usedOn}
            onChange={(e) => setUsedOn(e.target.value)}
          />
          <TextField size="small" label="Note" value={note} onChange={(e) => setNote(e.target.value)} />
        </Box>
      )}
      {chosenIds.map((instrumentId) => {
        const row = catalog.find((item) => item.id === instrumentId);
        const name = row?.name || instrumentId;
        return (
          <Box key={instrumentId} display="flex" gap={1} alignItems="center" sx={{ mb: 1 }}>
            <Typography>
              {name}
              {row?.maintenance_tracked ? ' (maintenance tracked)' : ''}
            </Typography>
            {canRecord && (
              <Button size="small" variant="outlined" onClick={() => recordUse(instrumentId)}>
                Record use
              </Button>
            )}
            {experimentId && (
              <Button size="small" onClick={() => removeInstrument(instrumentId)}>
                Remove
              </Button>
            )}
          </Box>
        );
      })}
      <Table size="small" aria-label="Instruments used">
        <TableHead>
          <TableRow>
            <TableCell>Instrument</TableCell>
            <TableCell>Used on</TableCell>
            <TableCell>Note</TableCell>
            <TableCell />
          </TableRow>
        </TableHead>
        <TableBody>
          {uses.map((row) => (
            <TableRow key={row.id}>
              <TableCell>{row.instrument_name || row.instrument_id}</TableCell>
              <TableCell>{row.used_on}</TableCell>
              <TableCell>{row.note}</TableCell>
              <TableCell>
                {row.active && (
                  <Button size="small" onClick={() => voidUse(row.id)}>
                    Void
                  </Button>
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Box>
  );
};

export default InstrumentUsePanel;
