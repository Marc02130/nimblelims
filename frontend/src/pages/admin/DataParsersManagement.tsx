/**
 * Admin: Data parsers (P1) — view, activate, create, and new version (edit).
 * Versions are immutable: "Edit" creates a new version in the same group.
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
  Divider,
  FormControlLabel,
  IconButton,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import {
  Add,
  PlayArrow,
  CheckCircle,
  Visibility,
  Edit,
  History,
  Close,
} from '@mui/icons-material';
import { DataGrid, GridActionsCellItem, GridColDef, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';
import { FillHeightPage, FillHeightTable } from '../../components/common/FillHeightPage';

interface DataParser {
  id: string;
  name: string;
  description?: string;
  instrument_id?: string;
  cro_source_id?: string;
  instrument_name?: string;
  cro_source_name?: string;
  version_group_id: string;
  version: number;
  active: boolean;
  parser_config: any;
  analysis_ids: string[];
  analyses?: { analysis_id: string; is_default: boolean }[];
  created_at?: string;
  modified_at?: string;
}

const defaultConfig = {
  schema_version: '1',
  delimiter: ',',
  encoding: 'utf-8',
  skip_rows: 0,
  header_row: 0,
  columns: [
    { source_col: 'Well', field_name: 'well_position', data_type: 'string' },
    { source_col: 'Value', field_name: 'raw_value', data_type: 'float' },
  ],
  well_col: 'Well',
  sample_col: null as string | null,
};

type DialogMode = 'create' | 'edit-version' | null;

const emptyForm = {
  name: '',
  description: '',
  sourceType: 'instrument' as 'instrument' | 'cro',
  instrument_id: '',
  cro_source_id: '',
  analysis_ids: [] as string[],
  parser_config_json: JSON.stringify(defaultConfig, null, 2),
  activate: true,
};

const DataParsersManagement: React.FC = () => {
  const { hasPermission } = useUser();
  const canEdit = hasPermission('config:edit');
  const [rows, setRows] = useState<DataParser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [instruments, setInstruments] = useState<any[]>([]);
  const [croSources, setCroSources] = useState<any[]>([]);
  const [analyses, setAnalyses] = useState<any[]>([]);

  const [viewParser, setViewParser] = useState<DataParser | null>(null);
  const [versionHistory, setVersionHistory] = useState<DataParser[]>([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [dialogMode, setDialogMode] = useState<DialogMode>(null);
  const [editBase, setEditBase] = useState<DataParser | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [testFiles, setTestFiles] = useState<FileList | null>(null);
  const [testResult, setTestResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [showInactiveVersions, setShowInactiveVersions] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [parsers, inst, cro, an] = await Promise.all([
        apiService.getDataParsers({ active_only: false }),
        apiService.getInstruments(),
        apiService.getCroSources(),
        apiService.getAnalyses(),
      ]);
      setRows(parsers || []);
      setInstruments(inst || []);
      setCroSources(cro || []);
      const list = Array.isArray(an) ? an : an?.analyses || [];
      setAnalyses(list);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load data parsers');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  /** Prefer active version per group; optionally show all versions. */
  const gridRows = useMemo(() => {
    if (showInactiveVersions) {
      return [...rows].sort((a, b) => {
        const n = (a.name || '').localeCompare(b.name || '');
        if (n !== 0) return n;
        return (b.version || 0) - (a.version || 0);
      });
    }
    const byGroup = new Map<string, DataParser>();
    for (const p of rows) {
      const g = p.version_group_id;
      const cur = byGroup.get(g);
      if (!cur) {
        byGroup.set(g, p);
        continue;
      }
      // Prefer active; else highest version
      if (p.active && !cur.active) byGroup.set(g, p);
      else if (p.active === cur.active && p.version > cur.version) byGroup.set(g, p);
    }
    return Array.from(byGroup.values()).sort((a, b) =>
      (a.name || '').localeCompare(b.name || '')
    );
  }, [rows, showInactiveVersions]);

  const analysisName = (id: string) =>
    analyses.find((a) => a.id === id)?.name || id.slice(0, 8) + '…';

  const openView = async (row: DataParser) => {
    try {
      const full = await apiService.getDataParser(row.id);
      setViewParser(full);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load parser');
    }
  };

  const openHistory = async (row: DataParser) => {
    setHistoryOpen(true);
    setHistoryLoading(true);
    try {
      const list = await apiService.getDataParsers({
        active_only: false,
        version_group_id: row.version_group_id,
      });
      setVersionHistory(
        [...(list || [])].sort((a: DataParser, b: DataParser) => b.version - a.version)
      );
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load version history');
    } finally {
      setHistoryLoading(false);
    }
  };

  const openCreate = () => {
    setDialogMode('create');
    setEditBase(null);
    setForm(emptyForm);
    setTestFiles(null);
    setTestResult(null);
  };

  const openEditVersion = async (row: DataParser) => {
    try {
      const full: DataParser = await apiService.getDataParser(row.id);
      setEditBase(full);
      setDialogMode('edit-version');
      setForm({
        name: full.name,
        description: full.description || '',
        sourceType: full.instrument_id ? 'instrument' : 'cro',
        instrument_id: full.instrument_id || '',
        cro_source_id: full.cro_source_id || '',
        analysis_ids: full.analysis_ids || [],
        parser_config_json: JSON.stringify(full.parser_config || defaultConfig, null, 2),
        activate: true,
      });
      setTestFiles(null);
      setTestResult(null);
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Failed to load parser for edit');
    }
  };

  const runTests = async () => {
    if (!testFiles?.length) {
      setError('Select test file(s)');
      return;
    }
    setTesting(true);
    setError(null);
    setSuccess(null);
    setTestResult(null);
    try {
      const cfg = JSON.parse(form.parser_config_json);
      const fileList = Array.from(testFiles);
      const res = await apiService.testDataParserConfig(cfg, fileList);
      setTestResult(res);
      const n = res.files?.length ?? 0;
      if (n !== fileList.length) {
        setError(
          `Expected results for ${fileList.length} files but got ${n}. Re-select files and try again.`
        );
      } else if (res.all_clean) {
        setSuccess(`All ${n} test file(s) clean`);
      } else {
        setError('Some tests have hard errors — activate will require all clean');
      }
    } catch (e: any) {
      const d = e.response?.data?.detail;
      let msg = e.message || 'Test failed';
      if (typeof d === 'string') msg = d;
      else if (Array.isArray(d)) {
        // FastAPI validation errors
        msg = d
          .map((x: any) => {
            const loc = (x.loc || []).join('.');
            return loc ? `${loc}: ${x.msg}` : x.msg || JSON.stringify(x);
          })
          .join('; ');
      } else if (d) msg = JSON.stringify(d);
      setError(msg);
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const cfg = JSON.parse(form.parser_config_json);
      if (form.activate && testResult && !testResult.all_clean) {
        throw new Error('Cannot activate: tests not all clean');
      }
      if (!form.analysis_ids.length) {
        throw new Error('Select at least one analysis');
      }
      const analysesPayload = form.analysis_ids.map((id, i) => ({
        analysis_id: id,
        is_default: i === 0,
      }));
      const activate = form.activate && (!testResult || testResult.all_clean);

      if (dialogMode === 'edit-version' && editBase) {
        await apiService.createDataParserVersion(editBase.version_group_id, {
          name: form.name.trim(),
          description: form.description || undefined,
          parser_config: cfg,
          analyses: analysesPayload,
          activate,
        });
        setSuccess(
          activate
            ? 'New version saved and activated (previous active deactivated)'
            : 'New version saved (inactive)'
        );
      } else {
        if (form.sourceType === 'instrument' && !form.instrument_id) {
          throw new Error('Select an instrument');
        }
        if (form.sourceType === 'cro' && !form.cro_source_id) {
          throw new Error('Select a CRO source');
        }
        await apiService.createDataParser({
          name: form.name.trim(),
          description: form.description || undefined,
          instrument_id: form.sourceType === 'instrument' ? form.instrument_id : undefined,
          cro_source_id: form.sourceType === 'cro' ? form.cro_source_id : undefined,
          parser_config: cfg,
          analyses: analysesPayload,
          activate,
        });
        setSuccess('Data parser created');
      }
      setDialogMode(null);
      setEditBase(null);
      await load();
    } catch (e: any) {
      setError(
        typeof e.response?.data?.detail === 'string'
          ? e.response.data.detail
          : e.message || 'Save failed'
      );
    } finally {
      setSubmitting(false);
    }
  };

  const activate = async (id: string) => {
    try {
      await apiService.activateDataParser(id);
      setSuccess('Version activated');
      await load();
      if (viewParser?.id === id) {
        const full = await apiService.getDataParser(id);
        setViewParser(full);
      }
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Activate failed');
    }
  };

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 140 },
    {
      field: 'source',
      headerName: 'Source',
      width: 160,
      valueGetter: (_v, row) => row.instrument_name || row.cro_source_name || '—',
    },
    {
      field: 'version',
      headerName: 'Ver',
      width: 70,
    },
    {
      field: 'active',
      headerName: 'Active',
      width: 100,
      renderCell: (p) => (
        <Chip
          size="small"
          label={p.value ? 'Active' : 'Inactive'}
          color={p.value ? 'success' : 'default'}
        />
      ),
    },
    {
      field: 'analysis_ids',
      headerName: 'Analyses',
      width: 90,
      valueGetter: (_v, row) => (row.analysis_ids || []).length,
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 160,
      getActions: (params: GridRowParams) => {
        const row = params.row as DataParser;
        const actions = [
          <GridActionsCellItem
            key="view"
            icon={<Visibility />}
            label="View"
            onClick={() => openView(row)}
          />,
          <GridActionsCellItem
            key="hist"
            icon={<History />}
            label="Version history"
            onClick={() => openHistory(row)}
          />,
        ];
        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              key="edit"
              icon={<Edit />}
              label="Edit (new version)"
              onClick={() => openEditVersion(row)}
            />
          );
          if (!row.active) {
            actions.push(
              <GridActionsCellItem
                key="act"
                icon={<CheckCircle />}
                label="Activate"
                onClick={() => activate(row.id)}
              />
            );
          }
        }
        return actions;
      },
    },
  ];

  if (!canEdit) {
    return (
      <Box p={2}>
        <Alert severity="warning">config:edit required for data parsers</Alert>
      </Box>
    );
  }

  const configPretty = viewParser
    ? JSON.stringify(viewParser.parser_config ?? {}, null, 2)
    : '';

  return (
    <FillHeightPage
      header={
        <>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1, alignItems: 'center' }}>
            <Typography variant="h4">Data parsers</Typography>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <FormControlLabel
                control={
                  <Switch
                    size="small"
                    checked={showInactiveVersions}
                    onChange={(e) => setShowInactiveVersions(e.target.checked)}
                  />
                }
                label="Show all versions"
              />
              <Button variant="contained" startIcon={<Add />} onClick={openCreate}>
                Create parser
              </Button>
            </Box>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            View config anytime. Edit creates a <strong>new version</strong> (config is immutable after
            save). Activate one version per logical parser.
          </Typography>
          {error && (
            <Alert severity="error" sx={{ mb: 1 }} onClose={() => setError(null)}>
              {typeof error === 'string' ? error : JSON.stringify(error)}
            </Alert>
          )}
          {success && (
            <Alert severity="success" sx={{ mb: 1 }} onClose={() => setSuccess(null)}>
              {success}
            </Alert>
          )}
        </>
      }
    >
      {loading ? (
        <Box display="flex" justifyContent="center" flex={1} alignItems="center">
          <CircularProgress />
        </Box>
      ) : (
        <FillHeightTable>
          <DataGrid
            rows={gridRows}
            columns={columns}
            getRowId={(r) => r.id}
            pageSizeOptions={[10, 25, 50]}
            initialState={{ pagination: { paginationModel: { pageSize: 25, page: 0 } } }}
            disableRowSelectionOnClick
            onRowDoubleClick={(p) => openView(p.row as DataParser)}
          />
        </FillHeightTable>
      )}

      {/* View dialog */}
      <Dialog
        open={!!viewParser}
        onClose={() => setViewParser(null)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>
            {viewParser?.name}{' '}
            <Chip size="small" label={`v${viewParser?.version}`} sx={{ ml: 1 }} />
            {viewParser?.active && (
              <Chip size="small" color="success" label="Active" sx={{ ml: 0.5 }} />
            )}
          </span>
          <IconButton size="small" onClick={() => setViewParser(null)}>
            <Close />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers>
          {viewParser && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Typography variant="body2">
                <strong>Source:</strong>{' '}
                {viewParser.instrument_name || viewParser.cro_source_name || '—'}
                {viewParser.instrument_id
                  ? ' (instrument)'
                  : viewParser.cro_source_id
                    ? ' (CRO)'
                    : ''}
              </Typography>
              <Typography variant="body2">
                <strong>Version group:</strong>{' '}
                <Box component="span" sx={{ fontFamily: 'monospace', fontSize: 12 }}>
                  {viewParser.version_group_id}
                </Box>
              </Typography>
              {viewParser.description && (
                <Typography variant="body2">
                  <strong>Description:</strong> {viewParser.description}
                </Typography>
              )}
              <Typography variant="body2">
                <strong>Analyses:</strong>{' '}
                {(viewParser.analysis_ids || []).map((id) => analysisName(id)).join(', ') || '—'}
              </Typography>
              <Divider />
              <Typography variant="subtitle2">ParserConfig</Typography>
              <Box
                component="pre"
                sx={{
                  m: 0,
                  p: 1.5,
                  bgcolor: 'action.hover',
                  borderRadius: 1,
                  overflow: 'auto',
                  maxHeight: 360,
                  fontSize: 12,
                  fontFamily: 'monospace',
                }}
              >
                {configPretty}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          {viewParser && (
            <>
              <Button startIcon={<History />} onClick={() => openHistory(viewParser)}>
                Versions
              </Button>
              {canEdit && (
                <Button
                  startIcon={<Edit />}
                  onClick={() => {
                    const p = viewParser;
                    setViewParser(null);
                    openEditVersion(p);
                  }}
                >
                  New version
                </Button>
              )}
              {canEdit && viewParser && !viewParser.active && (
                <Button
                  color="success"
                  startIcon={<CheckCircle />}
                  onClick={() => activate(viewParser.id)}
                >
                  Activate
                </Button>
              )}
            </>
          )}
          <Box sx={{ flex: 1 }} />
          <Button onClick={() => setViewParser(null)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Version history */}
      <Dialog open={historyOpen} onClose={() => setHistoryOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Version history</DialogTitle>
        <DialogContent dividers>
          {historyLoading ? (
            <CircularProgress size={28} />
          ) : (
            versionHistory.map((v) => (
              <Box
                key={v.id}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  py: 1,
                  borderBottom: 1,
                  borderColor: 'divider',
                }}
              >
                <Typography sx={{ minWidth: 40 }}>v{v.version}</Typography>
                <Chip
                  size="small"
                  label={v.active ? 'Active' : 'Inactive'}
                  color={v.active ? 'success' : 'default'}
                />
                <Typography variant="body2" sx={{ flex: 1 }} noWrap>
                  {v.name}
                </Typography>
                <Button size="small" onClick={() => { setHistoryOpen(false); openView(v); }}>
                  View
                </Button>
                {canEdit && (
                  <Button size="small" onClick={() => { setHistoryOpen(false); openEditVersion(v); }}>
                    New version
                  </Button>
                )}
                {canEdit && !v.active && (
                  <Button size="small" color="success" onClick={() => activate(v.id)}>
                    Activate
                  </Button>
                )}
              </Box>
            ))
          )}
          {!historyLoading && !versionHistory.length && (
            <Typography color="text.secondary">No versions found.</Typography>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setHistoryOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Create / new version dialog */}
      <Dialog
        open={dialogMode !== null}
        onClose={() => !submitting && setDialogMode(null)}
        fullWidth
        maxWidth="md"
      >
        <DialogTitle>
          {dialogMode === 'edit-version'
            ? `New version (from v${editBase?.version ?? '?'})`
            : 'Create data parser (v1)'}
        </DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          {dialogMode === 'edit-version' && (
            <Alert severity="info">
              Config cannot be changed in place. Saving creates a new version in the same group.
              Instrument/CRO source stays the same as the previous version.
            </Alert>
          )}
          <TextField
            label="Name"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            fullWidth
          />
          <TextField
            label="Description"
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            fullWidth
          />
          {dialogMode === 'create' && (
            <>
              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button
                  variant={form.sourceType === 'instrument' ? 'contained' : 'outlined'}
                  onClick={() => setForm({ ...form, sourceType: 'instrument' })}
                >
                  Instrument
                </Button>
                <Button
                  variant={form.sourceType === 'cro' ? 'contained' : 'outlined'}
                  onClick={() => setForm({ ...form, sourceType: 'cro' })}
                >
                  CRO source
                </Button>
              </Box>
              {form.sourceType === 'instrument' ? (
                <Autocomplete
                  options={instruments}
                  getOptionLabel={(o) => o.name}
                  value={instruments.find((i) => i.id === form.instrument_id) || null}
                  onChange={(_, v) => setForm({ ...form, instrument_id: v?.id || '' })}
                  renderInput={(p) => <TextField {...p} label="Instrument" required />}
                />
              ) : (
                <Autocomplete
                  options={croSources}
                  getOptionLabel={(o) => o.name}
                  value={croSources.find((c) => c.id === form.cro_source_id) || null}
                  onChange={(_, v) => setForm({ ...form, cro_source_id: v?.id || '' })}
                  renderInput={(p) => <TextField {...p} label="CRO source" required />}
                />
              )}
            </>
          )}
          {dialogMode === 'edit-version' && editBase && (
            <Typography variant="body2" color="text.secondary">
              Source: {editBase.instrument_name || editBase.cro_source_name || '—'} (fixed for this
              group)
            </Typography>
          )}
          <Autocomplete
            multiple
            options={analyses}
            getOptionLabel={(o) => o.name}
            value={analyses.filter((a) => form.analysis_ids.includes(a.id))}
            onChange={(_, v) => setForm({ ...form, analysis_ids: v.map((a) => a.id) })}
            renderInput={(p) => <TextField {...p} label="Analyses" required />}
          />
          <TextField
            label="ParserConfig JSON"
            value={form.parser_config_json}
            onChange={(e) => setForm({ ...form, parser_config_json: e.target.value })}
            fullWidth
            multiline
            minRows={10}
            inputProps={{ style: { fontFamily: 'monospace', fontSize: 12 } }}
          />
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Test files — select multiple (max 10)
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
              <input
                type="file"
                multiple
                accept=".csv,text/csv,text/plain"
                onChange={(e) => {
                  setTestFiles(e.target.files);
                  setTestResult(null);
                }}
              />
              <Typography variant="caption" color="text.secondary">
                {testFiles?.length ? `${testFiles.length} file(s) selected` : 'No files selected'}
              </Typography>
              <Button
                startIcon={<PlayArrow />}
                onClick={runTests}
                disabled={testing || !testFiles?.length}
                variant="outlined"
                size="small"
              >
                {testing ? 'Running…' : 'Run tests'}
              </Button>
            </Box>
            {testResult && (
              <Box
                sx={{
                  mt: 1.5,
                  p: 1.5,
                  border: 1,
                  borderColor: 'divider',
                  borderRadius: 1,
                  maxHeight: 220,
                  overflow: 'auto',
                  bgcolor: 'action.hover',
                }}
              >
                <Chip
                  label={
                    testResult.all_clean
                      ? `All clean (${testResult.files?.length ?? 0} files)`
                      : `Has hard errors (${testResult.files?.length ?? 0} files)`
                  }
                  color={testResult.all_clean ? 'success' : 'error'}
                  size="small"
                  sx={{ mb: 1 }}
                />
                {(testResult.files || []).map((f: any, idx: number) => (
                  <Typography
                    key={`${f.filename}-${idx}`}
                    variant="body2"
                    sx={{ fontFamily: 'monospace', fontSize: 12, mb: 0.5 }}
                    color={f.ok ? 'success.main' : 'error.main'}
                  >
                    {f.ok ? '✓' : '✗'} {f.filename}:{' '}
                    {f.ok ? `ok (${f.row_count} rows)` : (f.hard_errors || []).join('; ')}
                  </Typography>
                ))}
              </Box>
            )}
          </Box>
          <FormControlLabel
            control={
              <Switch
                checked={form.activate}
                onChange={(e) => setForm({ ...form, activate: e.target.checked })}
              />
            }
            label="Activate this version"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogMode(null)} disabled={submitting}>
            Cancel
          </Button>
          <Button variant="contained" disabled={submitting} onClick={handleSave}>
            {submitting
              ? 'Saving…'
              : dialogMode === 'edit-version'
                ? 'Save new version'
                : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </FillHeightPage>
  );
};

export default DataParsersManagement;
