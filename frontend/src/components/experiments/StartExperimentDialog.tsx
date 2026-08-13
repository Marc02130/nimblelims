/**
 * Decision #24 — ephemeral start dialog (dual list).
 * Opened from process accordion / Start action; closes after start.
 * Not a permanent panel on experiment detail.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  TextField,
  Typography,
  Stack,
} from '@mui/material';
import KeyboardArrowLeftIcon from '@mui/icons-material/KeyboardArrowLeft';
import KeyboardArrowRightIcon from '@mui/icons-material/KeyboardArrowRight';
import KeyboardDoubleArrowLeftIcon from '@mui/icons-material/KeyboardDoubleArrowLeft';
import KeyboardDoubleArrowRightIcon from '@mui/icons-material/KeyboardDoubleArrowRight';
import QrCodeScannerIcon from '@mui/icons-material/QrCodeScanner';
import { apiService } from '../../services/apiService';

const apiErrorMsg = (err: any, fallback: string): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) return detail[0]?.msg || fallback;
  return fallback;
};

export interface EligibleSample {
  sample_id: string;
  client_sample_id?: string | null;
  sample_name?: string | null;
  process_sample_status?: string | null;
}

export interface StartExperimentDialogProps {
  open: boolean;
  onClose: () => void;
  /** Process + step start (primary path) */
  processId?: string;
  stepId?: string;
  stepLabel?: string;
  /** Ad hoc: start existing experiment that is not process-linked */
  experimentId?: string;
  onStarted?: (result: {
    experimentId?: string;
    linkedCount?: number;
    processSamplesUpdated?: number;
  }) => void;
}

const sampleLabel = (s: EligibleSample) =>
  s.client_sample_id || s.sample_name || `${s.sample_id.slice(0, 8)}…`;

const StartExperimentDialog: React.FC<StartExperimentDialogProps> = ({
  open,
  onClose,
  processId,
  stepId,
  stepLabel,
  experimentId,
  onStarted,
}) => {
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState('');
  const [barcode, setBarcode] = useState('');
  const [scanning, setScanning] = useState(false);
  const [available, setAvailable] = useState<EligibleSample[]>([]);
  const [selected, setSelected] = useState<EligibleSample[]>([]);
  const [highlightAvail, setHighlightAvail] = useState<Set<string>>(new Set());
  const [highlightSel, setHighlightSel] = useState<Set<string>>(new Set());

  const loadEligible = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let rows: EligibleSample[] = [];
      if (processId && stepId) {
        const res: any = await apiService.getElnProcessStepEligibleSamples(processId, stepId);
        rows = (res?.samples || []).map((r: any) => ({
          sample_id: r.sample_id,
          client_sample_id: r.client_sample_id,
          sample_name: r.sample_name,
          process_sample_status: r.process_sample_status,
        }));
      } else {
        const res: any = await apiService.getCohortEligibleSamples();
        rows = (res?.samples || []).map((r: any) => ({
          sample_id: r.sample_id,
          client_sample_id: r.client_sample_id,
          sample_name: r.sample_name,
        }));
      }
      setAvailable(rows);
      setSelected([]);
      setHighlightAvail(new Set());
      setHighlightSel(new Set());
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to load eligible samples'));
      setAvailable([]);
    } finally {
      setLoading(false);
    }
  }, [processId, stepId]);

  useEffect(() => {
    if (open) {
      void loadEligible();
      setFilter('');
      setBarcode('');
      setError(null);
    }
  }, [open, loadEligible]);

  const selectedIds = useMemo(() => new Set(selected.map((s) => s.sample_id)), [selected]);

  const filteredAvailable = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return available.filter((s) => {
      if (selectedIds.has(s.sample_id)) return false;
      if (!q) return true;
      return (
        (s.client_sample_id || '').toLowerCase().includes(q) ||
        (s.sample_name || '').toLowerCase().includes(q) ||
        s.sample_id.toLowerCase().includes(q)
      );
    });
  }, [available, selectedIds, filter]);

  const toggleHighlight = (
    id: string,
    set: React.Dispatch<React.SetStateAction<Set<string>>>,
  ) => {
    set((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const moveToSelected = (ids: string[]) => {
    if (!ids.length) return;
    const idSet = new Set(ids);
    const moving = available.filter((s) => idSet.has(s.sample_id) && !selectedIds.has(s.sample_id));
    setSelected((prev) => [...prev, ...moving]);
    setHighlightAvail(new Set());
  };

  const moveToAvailable = (ids: string[]) => {
    if (!ids.length) return;
    const idSet = new Set(ids);
    setSelected((prev) => prev.filter((s) => !idSet.has(s.sample_id)));
    setHighlightSel(new Set());
  };

  const handleScan = async () => {
    const code = barcode.trim();
    if (!code) return;
    setScanning(true);
    setError(null);
    try {
      const res: any = await apiService.resolveExperimentScan(code, {
        process_id: processId,
      });
      if (res.match_type === 'none' || !res.samples?.length) {
        setError(`No container or sample found for “${code}”`);
        return;
      }
      const eligible = (res.samples as any[]).filter((s) => s.eligible !== false);
      const ineligible = (res.samples as any[]).filter((s) => s.eligible === false);
      if (!eligible.length) {
        const reason =
          ineligible[0]?.ineligible_reason ||
          'Scanned sample(s) are not eligible (status / process)';
        setError(reason);
        return;
      }
      const mapped: EligibleSample[] = eligible.map((s) => ({
        sample_id: s.sample_id,
        client_sample_id: s.client_sample_id,
        sample_name: s.sample_name,
      }));
      setAvailable((prev) => {
        const byId = new Map(prev.map((x) => [x.sample_id, x]));
        for (const m of mapped) byId.set(m.sample_id, m);
        return Array.from(byId.values());
      });
      setSelected((prev) => {
        const byId = new Map(prev.map((x) => [x.sample_id, x]));
        for (const m of mapped) byId.set(m.sample_id, m);
        return Array.from(byId.values());
      });
      if (ineligible.length) {
        setError(
          `${ineligible.length} scanned sample(s) skipped (not Available for Testing or not on process)`,
        );
      }
      setBarcode('');
    } catch (err) {
      setError(apiErrorMsg(err, 'Scan failed'));
    } finally {
      setScanning(false);
    }
  };

  const handleStart = async () => {
    if (selected.length === 0) {
      setError('Select at least one sample');
      return;
    }
    setStarting(true);
    setError(null);
    try {
      const ids = selected.map((s) => s.sample_id);
      if (processId && stepId) {
        const res: any = await apiService.startElnProcessStep(processId, stepId, {
          sample_ids: ids,
        });
        onStarted?.({
          experimentId: res.experiment_id,
          linkedCount: res.linked_count,
          processSamplesUpdated: res.process_samples_updated,
        });
        onClose();
      } else if (experimentId) {
        const res: any = await apiService.startExperiment(experimentId, {
          sample_ids: ids,
          set_started_at: true,
        });
        onStarted?.({
          experimentId,
          linkedCount: (res.linked_count || 0) + (res.already_linked_count || 0),
          processSamplesUpdated: res.process_samples_updated,
        });
        onClose();
      } else {
        setError('No process step or experiment configured');
      }
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to start experiment'));
    } finally {
      setStarting(false);
    }
  };

  const listBox = (
    title: string,
    items: EligibleSample[],
    highlight: Set<string>,
    onToggle: (id: string) => void,
  ) => (
    <Box
      sx={{
        flex: 1,
        minWidth: 220,
        border: 1,
        borderColor: 'divider',
        borderRadius: 1,
        display: 'flex',
        flexDirection: 'column',
        maxHeight: 360,
      }}
    >
      <Typography variant="subtitle2" sx={{ px: 1.5, py: 1, borderBottom: 1, borderColor: 'divider' }}>
        {title} ({items.length})
      </Typography>
      <List dense sx={{ overflow: 'auto', flex: 1, py: 0 }}>
        {items.length === 0 ? (
          <ListItem>
            <ListItemText secondary="None" />
          </ListItem>
        ) : (
          items.map((s) => (
            <ListItemButton
              key={s.sample_id}
              selected={highlight.has(s.sample_id)}
              onClick={() => onToggle(s.sample_id)}
            >
              <ListItemText
                primary={sampleLabel(s)}
                secondary={
                  s.process_sample_status
                    ? `${s.process_sample_status} · ${s.sample_id.slice(0, 8)}…`
                    : `${s.sample_id.slice(0, 8)}…`
                }
              />
            </ListItemButton>
          ))
        )}
      </List>
    </Box>
  );

  return (
    <Dialog open={open} onClose={() => !starting && onClose()} maxWidth="md" fullWidth>
      <DialogTitle>
        Start experiment{stepLabel ? `: ${stepLabel}` : ''}
      </DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Move samples from <strong>Available</strong> (eligible queue) to <strong>Selected</strong>,
          then Start. Only samples with status <strong>Available for Testing</strong>
          {processId ? ' that are assigned to this process' : ''} can be selected. Cohort is fixed
          after start.
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <TextField
          size="small"
          fullWidth
          label="Filter available"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          sx={{ mb: 2 }}
          disabled={loading || starting}
        />

        <Box display="flex" gap={1} mb={2} flexWrap="wrap">
          <TextField
            size="small"
            label="Optional scan / paste"
            placeholder="Plate, tube, or client sample ID"
            value={barcode}
            onChange={(e) => setBarcode(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                void handleScan();
              }
            }}
            sx={{ flex: 1, minWidth: 200 }}
            disabled={scanning || starting || loading}
          />
          <Button
            variant="outlined"
            startIcon={scanning ? <CircularProgress size={16} /> : <QrCodeScannerIcon />}
            onClick={() => void handleScan()}
            disabled={scanning || starting || loading || !barcode.trim()}
          >
            Resolve
          </Button>
        </Box>

        {loading ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        ) : (
          <Box display="flex" gap={1} alignItems="stretch">
            {listBox('Available', filteredAvailable, highlightAvail, (id) =>
              toggleHighlight(id, setHighlightAvail),
            )}
            <Stack spacing={0.5} justifyContent="center" alignItems="center" sx={{ px: 0.5 }}>
              <IconButton
                size="small"
                onClick={() => moveToSelected(Array.from(highlightAvail))}
                disabled={!highlightAvail.size}
                aria-label="Move selected to Selected"
              >
                <KeyboardArrowRightIcon />
              </IconButton>
              <IconButton
                size="small"
                onClick={() => moveToSelected(filteredAvailable.map((s) => s.sample_id))}
                disabled={!filteredAvailable.length}
                aria-label="Move all available to Selected"
              >
                <KeyboardDoubleArrowRightIcon />
              </IconButton>
              <IconButton
                size="small"
                onClick={() => moveToAvailable(Array.from(highlightSel))}
                disabled={!highlightSel.size}
                aria-label="Move selected to Available"
              >
                <KeyboardArrowLeftIcon />
              </IconButton>
              <IconButton
                size="small"
                onClick={() => moveToAvailable(selected.map((s) => s.sample_id))}
                disabled={!selected.length}
                aria-label="Move all Selected to Available"
              >
                <KeyboardDoubleArrowLeftIcon />
              </IconButton>
            </Stack>
            {listBox('Selected', selected, highlightSel, (id) =>
              toggleHighlight(id, setHighlightSel),
            )}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={starting}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={() => void handleStart()}
          disabled={starting || selected.length === 0 || loading}
        >
          {starting
            ? 'Starting…'
            : `Start with ${selected.length} sample${selected.length === 1 ? '' : 's'}`}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default StartExperimentDialog;
