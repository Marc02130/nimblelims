/**
 * Method-driven aliquot/pool plan editor (all v1 methods).
 * Saves plan lines to entry; dry-run / execute via API.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Paper,
  Chip,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import ScienceIcon from '@mui/icons-material/Science';
import { apiService } from '../../services/apiService';

const apiErrorMsg = (err: any, fallback: string): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) return detail[0]?.msg || fallback;
  return fallback;
};

const METHODS = [
  { value: 'by_mass', label: 'By mass', fields: ['amount'] },
  { value: 'by_volume', label: 'By volume', fields: ['volume', 'concentration'] },
  { value: 'by_count', label: 'By count', fields: ['amount'] },
  { value: 'target_mass', label: 'Target mass', fields: ['target_amount'] },
  { value: 'target_volume', label: 'Target volume', fields: ['target_volume', 'concentration'] },
  {
    value: 'target_concentration',
    label: 'Target concentration',
    fields: ['target_concentration', 'amount'],
  },
  { value: 'target_count', label: 'Target count', fields: ['target_amount'] },
] as const;

type MethodValue = (typeof METHODS)[number]['value'];

interface PlanLine {
  line_id?: string;
  method: MethodValue;
  source_sample_id: string;
  source_container_id?: string;
  amount?: number | '';
  volume?: number | '';
  concentration?: number | '';
  target_amount?: number | '';
  target_volume?: number | '';
  target_concentration?: number | '';
  dest_container_type_id?: string;
  dest_container_name?: string;
  pool_group?: string;
}

const blankLine = (): PlanLine => ({
  method: 'by_mass',
  source_sample_id: '',
  amount: '',
});

export interface AliquotPlanEditorProps {
  entryId: string;
  canEdit?: boolean;
  sampleIds?: string[];
}

const AliquotPlanEditor: React.FC<AliquotPlanEditorProps> = ({
  entryId,
  canEdit = true,
  sampleIds = [],
}) => {
  const [lines, setLines] = useState<PlanLine[]>([blankLine()]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res: any = await apiService.getAliquotPlan(entryId);
      const raw = res?.lines || [];
      if (raw.length > 0) {
        setLines(
          raw.map((l: any) => ({
            line_id: l.line_id,
            method: l.method || 'by_mass',
            source_sample_id: l.source_sample_id || '',
            source_container_id: l.source_container_id || '',
            amount: l.amount ?? '',
            volume: l.volume ?? '',
            concentration: l.concentration ?? '',
            target_amount: l.target_amount ?? '',
            target_volume: l.target_volume ?? '',
            target_concentration: l.target_concentration ?? '',
            dest_container_type_id: l.dest_container_type_id || '',
            dest_container_name: l.dest_container_name || '',
            pool_group: l.pool_group || '',
          })),
        );
      } else {
        setLines([blankLine()]);
      }
    } catch (err) {
      // New plan entry may 400 if wrong type — show soft message
      setError(apiErrorMsg(err, 'Failed to load plan'));
    } finally {
      setLoading(false);
    }
  }, [entryId]);

  useEffect(() => {
    void load();
  }, [load]);

  const updateLine = (i: number, patch: Partial<PlanLine>) => {
    setLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  };

  const toPayload = (list: PlanLine[]) =>
    list
      .filter((l) => l.source_sample_id.trim())
      .map((l) => {
        const num = (v: number | '' | undefined) =>
          v === '' || v === undefined || v === null ? undefined : Number(v);
        return {
          line_id: l.line_id,
          method: l.method,
          source_sample_id: l.source_sample_id.trim(),
          source_container_id: l.source_container_id?.trim() || undefined,
          amount: num(l.amount),
          volume: num(l.volume),
          concentration: num(l.concentration),
          target_amount: num(l.target_amount),
          target_volume: num(l.target_volume),
          target_concentration: num(l.target_concentration),
          dest_container_type_id: l.dest_container_type_id?.trim() || undefined,
          dest_container_name: l.dest_container_name?.trim() || undefined,
          pool_group: l.pool_group?.trim() || undefined,
        };
      });

  const handleSave = async () => {
    const payload = toPayload(lines);
    if (payload.length === 0) {
      setError('Add at least one plan line with a source sample');
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const res: any = await apiService.saveAliquotPlan(entryId, payload);
      setSuccess(`Saved ${res.line_count} plan line(s)`);
      await load();
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to save plan'));
    } finally {
      setSaving(false);
    }
  };

  const handleExecute = async (dryRun: boolean) => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      // Save first so execute uses latest lines
      const payload = toPayload(lines);
      if (payload.length > 0) {
        await apiService.saveAliquotPlan(entryId, payload);
      }
      const res: any = await apiService.executeAliquotPlan(entryId, { dry_run: dryRun });
      setSuccess(
        `${dryRun ? 'Dry-run' : 'Execute'}: ${res.success_count} ok, ${res.error_count} error(s)`,
      );
      if (!dryRun) await load();
    } catch (err) {
      setError(apiErrorMsg(err, dryRun ? 'Dry-run failed' : 'Execute failed'));
    } finally {
      setSaving(false);
    }
  };

  const methodFields = (method: MethodValue) =>
    METHODS.find((m) => m.value === method)?.fields || ['amount'];

  if (loading) {
    return (
      <Box py={2} display="flex" justifyContent="center">
        <CircularProgress size={28} />
      </Box>
    );
  }

  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="subtitle1" gutterBottom>
        Aliquot / pool plan
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Choose a method per line — inputs change by method. Amount stored is mass or count only;
        volume methods convert via concentration. Same <strong>pool group</strong> shares one dest
        container (multi-content pool).
      </Typography>

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

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1 }}>
        {METHODS.map((m) => (
          <Chip key={m.value} size="small" label={m.label} variant="outlined" />
        ))}
      </Box>

      <TableContainer component={Paper} variant="outlined" sx={{ mb: 1, overflowX: 'auto' }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Method</TableCell>
              <TableCell>Source sample</TableCell>
              <TableCell>Source container</TableCell>
              <TableCell>Inputs</TableCell>
              <TableCell>Dest name / pool group</TableCell>
              <TableCell width={48} />
            </TableRow>
          </TableHead>
          <TableBody>
            {lines.map((line, i) => {
              const fields = methodFields(line.method);
              return (
                <TableRow key={i}>
                  <TableCell>
                    <FormControl size="small" sx={{ minWidth: 140 }} disabled={!canEdit}>
                      <Select
                        value={line.method}
                        onChange={(e) =>
                          updateLine(i, { method: e.target.value as MethodValue })
                        }
                      >
                        {METHODS.map((m) => (
                          <MenuItem key={m.value} value={m.value}>
                            {m.label}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </TableCell>
                  <TableCell>
                    {sampleIds.length > 0 ? (
                      <FormControl size="small" sx={{ minWidth: 160 }} disabled={!canEdit}>
                        <Select
                          displayEmpty
                          value={line.source_sample_id}
                          onChange={(e) =>
                            updateLine(i, { source_sample_id: e.target.value as string })
                          }
                        >
                          <MenuItem value="">
                            <em>Select…</em>
                          </MenuItem>
                          {sampleIds.map((sid) => (
                            <MenuItem key={sid} value={sid}>
                              {sid.slice(0, 8)}…
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                    ) : (
                      <TextField
                        size="small"
                        placeholder="Sample UUID"
                        value={line.source_sample_id}
                        disabled={!canEdit}
                        onChange={(e) => updateLine(i, { source_sample_id: e.target.value })}
                        sx={{ minWidth: 160 }}
                      />
                    )}
                  </TableCell>
                  <TableCell>
                    <TextField
                      size="small"
                      placeholder="Optional"
                      value={line.source_container_id || ''}
                      disabled={!canEdit}
                      onChange={(e) => updateLine(i, { source_container_id: e.target.value })}
                      sx={{ minWidth: 120 }}
                    />
                  </TableCell>
                  <TableCell>
                    <Box display="flex" gap={0.5} flexWrap="wrap">
                      {fields.map((f) => (
                        <TextField
                          key={f}
                          size="small"
                          type="number"
                          label={f.replace(/_/g, ' ')}
                          value={(line as any)[f] ?? ''}
                          disabled={!canEdit}
                          onChange={(e) =>
                            updateLine(i, {
                              [f]: e.target.value === '' ? '' : Number(e.target.value),
                            } as any)
                          }
                          sx={{ width: 110 }}
                        />
                      ))}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box display="flex" flexDirection="column" gap={0.5}>
                      <TextField
                        size="small"
                        placeholder="Dest container name"
                        value={line.dest_container_name || ''}
                        disabled={!canEdit}
                        onChange={(e) => updateLine(i, { dest_container_name: e.target.value })}
                      />
                      <TextField
                        size="small"
                        placeholder="Pool group (optional)"
                        value={line.pool_group || ''}
                        disabled={!canEdit}
                        onChange={(e) => updateLine(i, { pool_group: e.target.value })}
                      />
                      <TextField
                        size="small"
                        placeholder="Dest container type UUID"
                        value={line.dest_container_type_id || ''}
                        disabled={!canEdit}
                        onChange={(e) =>
                          updateLine(i, { dest_container_type_id: e.target.value })
                        }
                      />
                    </Box>
                  </TableCell>
                  <TableCell>
                    {canEdit && (
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => setLines((prev) => prev.filter((_, j) => j !== i))}
                        disabled={lines.length <= 1}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {canEdit && (
        <Box display="flex" gap={1} flexWrap="wrap">
          <Button
            size="small"
            startIcon={<AddIcon />}
            onClick={() => setLines((p) => [...p, blankLine()])}
          >
            Add line
          </Button>
          <Button
            size="small"
            variant="outlined"
            disabled={saving}
            onClick={() => void handleSave()}
          >
            {saving ? 'Saving…' : 'Save plan'}
          </Button>
          <Button
            size="small"
            variant="outlined"
            startIcon={<ScienceIcon />}
            disabled={saving}
            onClick={() => void handleExecute(true)}
          >
            Dry-run
          </Button>
          <Button
            size="small"
            variant="contained"
            color="warning"
            startIcon={saving ? <CircularProgress size={14} color="inherit" /> : <PlayArrowIcon />}
            disabled={saving}
            onClick={() => void handleExecute(false)}
          >
            Execute
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default AliquotPlanEditor;
