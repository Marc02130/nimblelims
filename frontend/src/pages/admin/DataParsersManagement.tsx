/**
 * Admin: Data parsers (P1) — versioned parse configs for instrument or CRO.
 */
import React, { useCallback, useEffect, useState } from 'react';
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
  FormControlLabel,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { Add, PlayArrow, CheckCircle } from '@mui/icons-material';
import { DataGrid, GridActionsCellItem, GridColDef } from '@mui/x-data-grid';
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

const DataParsersManagement: React.FC = () => {
  const { hasPermission } = useUser();
  const canEdit = hasPermission('config:edit');
  const [rows, setRows] = useState<DataParser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [instruments, setInstruments] = useState<any[]>([]);
  const [croSources, setCroSources] = useState<any[]>([]);
  const [analyses, setAnalyses] = useState<any[]>([]);
  const [form, setForm] = useState({
    name: '',
    description: '',
    sourceType: 'instrument' as 'instrument' | 'cro',
    instrument_id: '',
    cro_source_id: '',
    analysis_ids: [] as string[],
    parser_config_json: JSON.stringify(defaultConfig, null, 2),
    activate: true,
  });
  const [testFiles, setTestFiles] = useState<FileList | null>(null);
  const [testResult, setTestResult] = useState<any>(null);
  const [submitting, setSubmitting] = useState(false);

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

  const runTests = async () => {
    if (!testFiles?.length) {
      setError('Select test file(s)');
      return;
    }
    try {
      const cfg = JSON.parse(form.parser_config_json);
      const res = await apiService.testDataParserConfig(cfg, Array.from(testFiles));
      setTestResult(res);
      if (res.all_clean) setSuccess('All test files clean');
      else setError('Some tests have hard errors — activate will require all clean');
    } catch (e: any) {
      setError(e.response?.data?.detail || e.message || 'Test failed');
    }
  };

  const handleCreate = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const cfg = JSON.parse(form.parser_config_json);
      if (form.activate && testResult && !testResult.all_clean) {
        throw new Error('Cannot activate: tests not all clean');
      }
      await apiService.createDataParser({
        name: form.name.trim(),
        description: form.description || undefined,
        instrument_id: form.sourceType === 'instrument' ? form.instrument_id : undefined,
        cro_source_id: form.sourceType === 'cro' ? form.cro_source_id : undefined,
        parser_config: cfg,
        analyses: form.analysis_ids.map((id, i) => ({
          analysis_id: id,
          is_default: i === 0,
        })),
        activate: form.activate && (!testResult || testResult.all_clean),
      });
      setDialogOpen(false);
      setSuccess('Data parser created');
      await load();
    } catch (e: any) {
      setError(
        typeof e.response?.data?.detail === 'string'
          ? e.response.data.detail
          : e.message || 'Create failed'
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
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Activate failed');
    }
  };

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 140 },
    {
      field: 'source',
      headerName: 'Source',
      width: 180,
      valueGetter: (_v, row) => row.instrument_name || row.cro_source_name || '—',
    },
    { field: 'version', headerName: 'Ver', width: 70 },
    {
      field: 'active',
      headerName: 'Active',
      width: 100,
      renderCell: (p) => (
        <Chip size="small" label={p.value ? 'Active' : 'Inactive'} color={p.value ? 'success' : 'default'} />
      ),
    },
    {
      field: 'analysis_ids',
      headerName: 'Analyses',
      width: 100,
      valueGetter: (_v, row) => (row.analysis_ids || []).length,
    },
    {
      field: 'actions',
      type: 'actions',
      width: 100,
      getActions: (params) =>
        canEdit && !params.row.active
          ? [
              <GridActionsCellItem
                key="act"
                icon={<CheckCircle />}
                label="Activate"
                onClick={() => activate(params.row.id)}
              />,
            ]
          : [],
    },
  ];

  if (!canEdit) {
    return (
      <Box p={2}>
        <Alert severity="warning">config:edit required for data parsers</Alert>
      </Box>
    );
  }

  return (
    <FillHeightPage
      header={
        <>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
            <Typography variant="h4">Data parsers</Typography>
            <Button
              variant="contained"
              startIcon={<Add />}
              onClick={() => {
                setTestResult(null);
                setDialogOpen(true);
              }}
            >
              Create parser
            </Button>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Versioned file instructions for instrument or CRO exports. Link one or more analyses. Activate after
            tests are hard-error-free.
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
            rows={rows}
            columns={columns}
            getRowId={(r) => r.id}
            pageSizeOptions={[10, 25, 50]}
            initialState={{ pagination: { paginationModel: { pageSize: 25, page: 0 } } }}
            disableRowSelectionOnClick
          />
        </FillHeightTable>
      )}

      <Dialog open={dialogOpen} onClose={() => !submitting && setDialogOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>Create data parser (v1)</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
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
              onChange={(_, v) => setForm({ ...form, instrument_id: v?.id || '' })}
              renderInput={(p) => <TextField {...p} label="Instrument" required />}
            />
          ) : (
            <Autocomplete
              options={croSources}
              getOptionLabel={(o) => o.name}
              onChange={(_, v) => setForm({ ...form, cro_source_id: v?.id || '' })}
              renderInput={(p) => <TextField {...p} label="CRO source" required />}
            />
          )}
          <Autocomplete
            multiple
            options={analyses}
            getOptionLabel={(o) => o.name}
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
            <Typography variant="subtitle2">Test files (required for activate confidence)</Typography>
            <input type="file" multiple onChange={(e) => setTestFiles(e.target.files)} />
            <Button startIcon={<PlayArrow />} onClick={runTests} sx={{ ml: 1 }}>
              Run tests
            </Button>
            {testResult && (
              <Box sx={{ mt: 1 }}>
                <Chip
                  label={testResult.all_clean ? 'All clean' : 'Has hard errors'}
                  color={testResult.all_clean ? 'success' : 'error'}
                  size="small"
                />
                {testResult.files?.map((f: any) => (
                  <Typography key={f.filename} variant="caption" display="block">
                    {f.filename}: {f.ok ? 'ok' : f.hard_errors?.join('; ')} ({f.row_count} rows)
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
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" disabled={submitting} onClick={handleCreate}>
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </FillHeightPage>
  );
};

export default DataParsersManagement;
