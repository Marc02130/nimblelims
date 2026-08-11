/**
 * Start experiment cohort: scan plate/tube barcode or pick samples, then start.
 * After start, cohort is fixed (no mid-flight adds).
 */
import React, { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Paper,
} from '@mui/material';
import QrCodeScannerIcon from '@mui/icons-material/QrCodeScanner';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { apiService } from '../../services/apiService';

const apiErrorMsg = (err: any, fallback: string): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) return detail[0]?.msg || fallback;
  return fallback;
};

export interface ScanSample {
  sample_id: string;
  client_sample_id?: string;
  sample_name?: string;
  container_id?: string;
  container_name?: string;
}

export interface StartCohortPanelProps {
  experimentId: string;
  startedAt?: string | null;
  existingSampleIds?: string[];
  canEdit?: boolean;
  onStarted?: () => void;
}

const StartCohortPanel: React.FC<StartCohortPanelProps> = ({
  experimentId,
  startedAt,
  existingSampleIds = [],
  canEdit = true,
  onStarted,
}) => {
  const [barcode, setBarcode] = useState('');
  const [scanning, setScanning] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [matchType, setMatchType] = useState<string | null>(null);
  const [containerName, setContainerName] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<ScanSample[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [manualId, setManualId] = useState('');

  const locked = Boolean(startedAt) && existingSampleIds.length > 0;

  const mergeCandidates = (samples: ScanSample[]) => {
    setCandidates((prev) => {
      const byId = new Map(prev.map((s) => [s.sample_id, s]));
      for (const s of samples) byId.set(s.sample_id, s);
      return Array.from(byId.values());
    });
    setSelected((prev) => {
      const next = new Set(prev);
      for (const s of samples) next.add(s.sample_id);
      return next;
    });
  };

  const handleScan = async () => {
    const code = barcode.trim();
    if (!code) {
      setError('Enter a plate/tube barcode or client sample ID');
      return;
    }
    setScanning(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await apiService.resolveExperimentScan(code);
      setMatchType(res.match_type);
      setContainerName(res.container_name || null);
      if (res.match_type === 'none' || res.total === 0) {
        setError(`No container or sample found for “${code}”`);
        return;
      }
      mergeCandidates(res.samples || []);
      setSuccess(
        res.match_type === 'container'
          ? `Found ${res.total} sample(s) on container ${res.container_name || code}`
          : `Found sample ${res.samples[0]?.client_sample_id || res.samples[0]?.sample_id}`,
      );
      setBarcode('');
    } catch (err) {
      setError(apiErrorMsg(err, 'Scan failed'));
    } finally {
      setScanning(false);
    }
  };

  const handleAddManual = () => {
    const id = manualId.trim();
    if (!id) return;
    // UUID-ish or any id string — start API validates existence
    mergeCandidates([{ sample_id: id }]);
    setManualId('');
  };

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = () => {
    setSelected(new Set(candidates.map((c) => c.sample_id)));
  };

  const handleStart = async () => {
    const ids = Array.from(selected);
    if (ids.length === 0) {
      setError('Select at least one sample for the cohort');
      return;
    }
    setStarting(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await apiService.startExperiment(experimentId, {
        sample_ids: ids,
        set_started_at: true,
      });
      setSuccess(
        `Started with ${res.linked_count + res.already_linked_count} sample(s)` +
          (res.linked_count ? ` (${res.linked_count} newly linked)` : ''),
      );
      onStarted?.();
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to start experiment'));
    } finally {
      setStarting(false);
    }
  };

  if (locked) {
    return (
      <Alert severity="info" sx={{ mb: 2 }}>
        Cohort locked — experiment started{' '}
        {startedAt ? new Date(startedAt).toLocaleString() : ''}. {existingSampleIds.length}{' '}
        sample(s). Mid-flight adds are not allowed; cancel/restart or create a new experiment to
        change the set.
      </Alert>
    );
  }

  if (!canEdit) {
    return (
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        No permission to start cohort.
      </Typography>
    );
  }

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" sx={{ mb: 1 }}>
        Start cohort
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Scan a <strong>plate</strong> (all samples on it) or <strong>tube</strong> (including
        pools), or add sample IDs. Select 1..N, then Start — the cohort becomes fixed for this
        experiment.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Box display="flex" gap={1} flexWrap="wrap" alignItems="flex-start" mb={2}>
        <TextField
          size="small"
          label="Scan barcode"
          placeholder="Plate / tube name or client sample ID"
          value={barcode}
          onChange={(e) => setBarcode(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              void handleScan();
            }
          }}
          sx={{ minWidth: 280, flex: 1 }}
          disabled={scanning || starting}
        />
        <Button
          variant="outlined"
          startIcon={scanning ? <CircularProgress size={16} /> : <QrCodeScannerIcon />}
          onClick={() => void handleScan()}
          disabled={scanning || starting}
        >
          Resolve
        </Button>
      </Box>

      <Box display="flex" gap={1} flexWrap="wrap" alignItems="flex-start" mb={2}>
        <TextField
          size="small"
          label="Sample UUID"
          placeholder="Paste sample id"
          value={manualId}
          onChange={(e) => setManualId(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              handleAddManual();
            }
          }}
          sx={{ minWidth: 280, flex: 1 }}
          disabled={starting}
        />
        <Button variant="outlined" onClick={handleAddManual} disabled={starting || !manualId.trim()}>
          Add
        </Button>
      </Box>

      {matchType && containerName && (
        <Chip size="small" label={`Container: ${containerName}`} sx={{ mb: 1, mr: 1 }} />
      )}

      {candidates.length > 0 && (
        <>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={1}>
            <Typography variant="subtitle2">
              Candidates ({selected.size} of {candidates.length} selected)
            </Typography>
            <Button size="small" onClick={selectAll}>
              Select all
            </Button>
          </Box>
          <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox" />
                  <TableCell>Client sample ID</TableCell>
                  <TableCell>Name</TableCell>
                  <TableCell>Sample ID</TableCell>
                  <TableCell>Container</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {candidates.map((s) => (
                  <TableRow key={s.sample_id} hover onClick={() => toggle(s.sample_id)}>
                    <TableCell padding="checkbox">
                      <Checkbox
                        checked={selected.has(s.sample_id)}
                        onChange={() => toggle(s.sample_id)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </TableCell>
                    <TableCell>{s.client_sample_id || '—'}</TableCell>
                    <TableCell>{s.sample_name || '—'}</TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                        {s.sample_id.slice(0, 8)}…
                      </Typography>
                    </TableCell>
                    <TableCell>{s.container_name || '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          <Button
            variant="contained"
            color="primary"
            startIcon={starting ? <CircularProgress size={16} color="inherit" /> : <PlayArrowIcon />}
            disabled={starting || selected.size === 0}
            onClick={() => void handleStart()}
          >
            {starting ? 'Starting…' : `Start with ${selected.size} sample${selected.size === 1 ? '' : 's'}`}
          </Button>
        </>
      )}

      {candidates.length === 0 && existingSampleIds.length === 0 && (
        <Alert severity="info">
          No samples linked yet. Scan a plate/tube or add sample IDs, then Start.
        </Alert>
      )}

      {candidates.length === 0 && existingSampleIds.length > 0 && !startedAt && (
        <Box mt={2}>
          <Alert severity="warning" sx={{ mb: 1 }}>
            {existingSampleIds.length} sample(s) already linked but experiment not started. You can
            start with those IDs, or scan more first.
          </Alert>
          <Button
            variant="contained"
            startIcon={<PlayArrowIcon />}
            disabled={starting}
            onClick={() => {
              setSelected(new Set(existingSampleIds));
              setCandidates(
                existingSampleIds.map((id) => ({ sample_id: id })),
              );
            }}
          >
            Load linked samples to start
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default StartCohortPanel;
