/**
 * Atomic receive CORE UI (Phase 4).
 * Scan loop: sticky type/matrix/project, primary + optional additional barcodes,
 * stay on form after success. No sample-ID, status, tube-type, or aliquot dialog.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Snackbar,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import { apiService } from '../services/apiService';

const STICKY_KEY = 'nimble.atomicReceive.sticky';

type LookupItem = { id: string; name: string };

type StickyState = {
  sample_type: string;
  matrix: string;
  project_id: string;
};

function loadSticky(): StickyState {
  try {
    const raw = sessionStorage.getItem(STICKY_KEY);
    if (!raw) return { sample_type: '', matrix: '', project_id: '' };
    const parsed = JSON.parse(raw);
    return {
      sample_type: parsed.sample_type || '',
      matrix: parsed.matrix || '',
      project_id: parsed.project_id || '',
    };
  } catch {
    return { sample_type: '', matrix: '', project_id: '' };
  }
}

function saveSticky(state: StickyState) {
  sessionStorage.setItem(STICKY_KEY, JSON.stringify(state));
}

const AtomicReceive: React.FC = () => {
  const primaryRef = useRef<HTMLInputElement>(null);

  const [sampleTypes, setSampleTypes] = useState<LookupItem[]>([]);
  const [matrices, setMatrices] = useState<LookupItem[]>([]);
  const [projects, setProjects] = useState<LookupItem[]>([]);
  const [loadingLookups, setLoadingLookups] = useState(true);
  const [lookupError, setLookupError] = useState<string | null>(null);

  const sticky = loadSticky();
  const [sampleType, setSampleType] = useState(sticky.sample_type);
  const [matrix, setMatrix] = useState(sticky.matrix);
  const [projectId, setProjectId] = useState(sticky.project_id);
  const [primaryBarcode, setPrimaryBarcode] = useState('');
  const [additionalBarcodes, setAdditionalBarcodes] = useState<string[]>([]);
  const [extraDraft, setExtraDraft] = useState('');
  const [temperature, setTemperature] = useState<string>('');
  const [clientSampleId, setClientSampleId] = useState('');

  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const loadLookups = useCallback(async () => {
    setLoadingLookups(true);
    setLookupError(null);
    try {
      const [typesRaw, matricesRaw, projectsRaw] = await Promise.all([
        apiService.getListEntries('sample_types').catch(() =>
          apiService.getListEntries('Sample Type')
        ),
        apiService.getListEntries('matrix_types').catch(() =>
          apiService.getListEntries('Matrix')
        ),
        apiService.getProjects({ page: 1, size: 200 }),
      ]);

      const toItems = (raw: any): LookupItem[] => {
        const arr = Array.isArray(raw) ? raw : raw?.entries || raw?.list_entries || [];
        return (arr as any[])
          .filter((x) => x && x.id && x.name)
          .map((x) => ({ id: String(x.id), name: String(x.name) }));
      };

      setSampleTypes(toItems(typesRaw));
      setMatrices(toItems(matricesRaw));
      const projList = Array.isArray(projectsRaw)
        ? projectsRaw
        : projectsRaw?.projects || [];
      setProjects(
        (projList as any[])
          .filter((p) => p && p.id && p.name)
          .map((p) => ({ id: String(p.id), name: String(p.name) }))
      );
    } catch (err: any) {
      console.error(err);
      setLookupError(err?.response?.data?.detail || 'Failed to load receive lookups');
    } finally {
      setLoadingLookups(false);
      // Focus barcode after lookups load
      setTimeout(() => primaryRef.current?.focus(), 0);
    }
  }, []);

  useEffect(() => {
    loadLookups();
  }, [loadLookups]);

  useEffect(() => {
    saveSticky({ sample_type: sampleType, matrix, project_id: projectId });
  }, [sampleType, matrix, projectId]);

  const addExtraBarcode = () => {
    const value = extraDraft.trim();
    if (!value) return;
    const all = [primaryBarcode.trim(), ...additionalBarcodes];
    if (all.includes(value)) {
      setFormError(`Barcode already listed: ${value}`);
      return;
    }
    setAdditionalBarcodes((prev) => [...prev, value]);
    setExtraDraft('');
    setFormError(null);
  };

  const removeExtraBarcode = (barcode: string) => {
    setAdditionalBarcodes((prev) => prev.filter((b) => b !== barcode));
  };

  const resetBarcodesAndFocus = () => {
    setPrimaryBarcode('');
    setAdditionalBarcodes([]);
    setExtraDraft('');
    setClientSampleId('');
    setTemperature('');
    // Keep sticky type/matrix/project.
    setTimeout(() => primaryRef.current?.focus(), 0);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const primary = primaryBarcode.trim();
    if (!primary) {
      setFormError('Primary barcode is required');
      primaryRef.current?.focus();
      return;
    }
    if (!sampleType || !matrix || !projectId) {
      setFormError('Sample type, matrix, and project are required (sticky)');
      return;
    }

    const extras = additionalBarcodes.map((b) => b.trim()).filter(Boolean);
    const all = [primary, ...extras];
    if (new Set(all).size !== all.length) {
      setFormError('Duplicate barcode in this receive');
      return;
    }

    let temp: number | null = null;
    if (temperature.trim() !== '') {
      const parsed = Number(temperature);
      if (Number.isNaN(parsed)) {
        setFormError('Temperature must be a number');
        return;
      }
      temp = parsed;
    }

    setSubmitting(true);
    try {
      const result = await apiService.receiveSample({
        container_barcode: primary,
        additional_container_barcodes: extras,
        sample_type: sampleType,
        matrix,
        project_id: projectId,
        temperature: temp,
        client_sample_id: clientSampleId.trim() || null,
      });

      const vesselCount = result?.containers?.length ?? 1 + extras.length;
      const sampleName = result?.sample_name || 'sample';
      setToast({
        open: true,
        message: `Received ${sampleName} · ${vesselCount} vessel${vesselCount === 1 ? '' : 's'}`,
        severity: 'success',
      });
      resetBarcodesAndFocus();
    } catch (err: any) {
      const detail =
        err?.response?.data?.detail ||
        err?.message ||
        'Receive failed';
      const message = typeof detail === 'string' ? detail : JSON.stringify(detail);
      setFormError(message);
      setToast({ open: true, message, severity: 'error' });
      // Stay on form; keep barcodes so tech can fix duplicate / retry
      primaryRef.current?.focus();
    } finally {
      setSubmitting(false);
    }
  };

  if (loadingLookups) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={240}>
        <CircularProgress aria-label="Loading receive form" />
      </Box>
    );
  }

  return (
    <Box maxWidth={720} mx="auto">
      <Typography variant="h5" gutterBottom>
        Receive
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Scan vessels into one sample. Sample ID is assigned by the system. Status becomes Available
        for Testing. Stay on this screen for the next rack.
      </Typography>

      {lookupError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setLookupError(null)}>
          {lookupError}
        </Alert>
      )}
      {formError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setFormError(null)}>
          {formError}
        </Alert>
      )}

      <Paper component="form" onSubmit={handleSubmit} sx={{ p: 3 }} elevation={1}>
        <Stack spacing={2.5}>
          <TextField
            inputRef={primaryRef}
            label="Primary barcode"
            value={primaryBarcode}
            onChange={(e) => setPrimaryBarcode(e.target.value)}
            required
            fullWidth
            autoComplete="off"
            inputProps={{ 'data-testid': 'primary-barcode', 'aria-label': 'Primary barcode' }}
            helperText="Required. Tube barcode as scanned — not the lab sample ID."
          />

          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Additional barcodes (same sample)
            </Typography>
            <Stack direction="row" spacing={1} alignItems="flex-start">
              <TextField
                label="Additional tube / barcode"
                value={extraDraft}
                onChange={(e) => setExtraDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addExtraBarcode();
                  }
                }}
                fullWidth
                autoComplete="off"
                inputProps={{ 'data-testid': 'additional-barcode-draft' }}
                helperText="Optional extra vessels for this sample — not an aliquot."
              />
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={addExtraBarcode}
                sx={{ whiteSpace: 'nowrap', mt: 0.5 }}
                aria-label="Add additional barcode"
              >
                Add
              </Button>
            </Stack>
            {additionalBarcodes.length > 0 && (
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mt: 1 }}>
                {additionalBarcodes.map((b) => (
                  <Chip
                    key={b}
                    label={b}
                    onDelete={() => removeExtraBarcode(b)}
                    deleteIcon={<DeleteOutlineIcon />}
                    data-testid={`extra-barcode-${b}`}
                  />
                ))}
              </Stack>
            )}
          </Box>

          <FormControl fullWidth required>
            <InputLabel id="receive-sample-type-label">Sample type</InputLabel>
            <Select
              labelId="receive-sample-type-label"
              label="Sample type"
              value={sampleType}
              onChange={(e) => setSampleType(String(e.target.value))}
              inputProps={{ 'data-testid': 'sample-type' }}
            >
              {sampleTypes.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth required>
            <InputLabel id="receive-matrix-label">Matrix</InputLabel>
            <Select
              labelId="receive-matrix-label"
              label="Matrix"
              value={matrix}
              onChange={(e) => setMatrix(String(e.target.value))}
              inputProps={{ 'data-testid': 'matrix' }}
            >
              {matrices.map((m) => (
                <MenuItem key={m.id} value={m.id}>
                  {m.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth required>
            <InputLabel id="receive-project-label">Project</InputLabel>
            <Select
              labelId="receive-project-label"
              label="Project"
              value={projectId}
              onChange={(e) => setProjectId(String(e.target.value))}
              inputProps={{ 'data-testid': 'project' }}
            >
              {projects.map((p) => (
                <MenuItem key={p.id} value={p.id}>
                  {p.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
            <TextField
              label="Temperature (°C)"
              value={temperature}
              onChange={(e) => setTemperature(e.target.value)}
              fullWidth
              inputProps={{ 'data-testid': 'temperature', inputMode: 'decimal' }}
            />
            <TextField
              label="Client sample ID"
              value={clientSampleId}
              onChange={(e) => setClientSampleId(e.target.value)}
              fullWidth
              autoComplete="off"
              inputProps={{ 'data-testid': 'client-sample-id' }}
            />
          </Stack>

          <Box display="flex" gap={2} justifyContent="flex-end">
            <Button
              type="submit"
              variant="contained"
              disabled={submitting}
              data-testid="receive-submit"
            >
              {submitting ? <CircularProgress size={22} color="inherit" /> : 'Receive'}
            </Button>
          </Box>
        </Stack>
      </Paper>

      <Snackbar
        open={toast.open}
        autoHideDuration={4000}
        onClose={() => setToast((t) => ({ ...t, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          severity={toast.severity}
          onClose={() => setToast((t) => ({ ...t, open: false }))}
          sx={{ width: '100%' }}
        >
          {toast.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default AtomicReceive;
