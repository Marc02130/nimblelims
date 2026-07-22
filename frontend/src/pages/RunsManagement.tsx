import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Chip,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/apiService';
import { FillHeightPage, FillHeightTable } from '../components/common/FillHeightPage';

const apiErrorMsg = (err: any, fallback: string): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) return detail[0]?.msg || fallback;
  return fallback;
};

interface RunListItem {
  id: string;
  name: string;
  description?: string;
  experiment_template_id: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
}

const STATUS_COLORS: Record<string, 'success' | 'warning' | 'info' | 'default' | 'error'> = {
  published: 'success',
  running: 'warning',
  results_received: 'warning',
  ordered: 'info',
  complete: 'info',
  draft: 'default',
  failed: 'error',
  canceled: 'default',
};

const STATUS_LABELS: Record<string, string> = {
  results_received: 'Results Received',
  ordered: 'Ordered',
  canceled: 'Canceled',
};

const RunsManagement: React.FC = () => {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState('');
  const [nameSearch, setNameSearch] = useState('');
  const [pagination, setPagination] = useState({ page: 1, size: 25, total: 0, pages: 0 });
  const [templates, setTemplates] = useState<{ id: string; name: string }[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDesc, setCreateDesc] = useState('');
  const [createTemplateId, setCreateTemplateId] = useState('');
  const [createAnalysisId, setCreateAnalysisId] = useState('');
  const [analyses, setAnalyses] = useState<{ id: string; name: string }[]>([]);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    apiService
      .getExperimentTemplates({ page: 1, size: 500 })
      .then((res: any) => setTemplates(res?.templates ?? []))
      .catch(() => {});
    apiService
      .getAnalyses({ page: 1, size: 500, active: true })
      .then((res: any) => {
        const list = res?.analyses ?? (Array.isArray(res) ? res : []);
        setAnalyses(list.map((a: any) => ({ id: a.id, name: a.name })));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadRuns();
  }, [statusFilter, pagination.page, pagination.size]);

  const loadRuns = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: Record<string, unknown> = {
        page: pagination.page,
        size: pagination.size,
      };
      if (statusFilter) params.status = statusFilter;
      const res = await apiService.getLimsRuns(params);
      setRuns(res?.runs ?? []);
      setPagination((p) => ({ ...p, total: res?.total ?? 0, pages: res?.pages ?? 1 }));
    } catch (err: any) {
      setError(apiErrorMsg(err, 'Failed to load runs'));
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!createName.trim() || !createTemplateId || !createAnalysisId) return;
    setCreating(true);
    setError(null);
    try {
      const run = await apiService.createLimsRun({
        name: createName.trim(),
        description: createDesc.trim() || undefined,
        experiment_template_id: createTemplateId,
        analysis_id: createAnalysisId,
      });
      setShowCreate(false);
      setCreateName('');
      setCreateDesc('');
      setCreateTemplateId('');
      setCreateAnalysisId('');
      navigate(`/runs/${run.id}`);
    } catch (err: any) {
      setError(apiErrorMsg(err, 'Failed to create run'));
    } finally {
      setCreating(false);
    }
  };

  const filtered = nameSearch.trim()
    ? runs.filter((r) => r.name.toLowerCase().includes(nameSearch.trim().toLowerCase()))
    : runs;

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', flex: 1, minWidth: 180 },
    {
      field: 'status',
      headerName: 'Status',
      width: 120,
      renderCell: (params) => (
        <Chip size="small" label={STATUS_LABELS[params.value] ?? (params.value.charAt(0).toUpperCase() + params.value.slice(1))} color={STATUS_COLORS[params.value] ?? 'default'} />
      ),
    },
    {
      field: 'started_at',
      headerName: 'Started',
      width: 120,
      valueGetter: (v) => (v ? new Date(v as string).toLocaleDateString() : '—'),
    },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 120,
      valueGetter: (v) => new Date(v as string).toLocaleDateString(),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: '',
      width: 80,
      getActions: (params) => [
        <GridActionsCellItem
          key="view"
          icon={<VisibilityIcon />}
          label="View"
          onClick={() => navigate(`/runs/${params.id}`)}
        />,
      ],
    },
  ];

  return (
    <FillHeightPage
      header={
        <>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h4">Experiment Runs</Typography>
            <Button variant="contained" onClick={() => setShowCreate(true)}>
              New Run
            </Button>
          </Box>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <TextField
              size="small"
              label="Search by name"
              value={nameSearch}
              onChange={(e) => setNameSearch(e.target.value)}
              sx={{ minWidth: 200 }}
            />
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel>Status</InputLabel>
              <Select value={statusFilter} label="Status" onChange={(e) => setStatusFilter(e.target.value)}>
                <MenuItem value="">All</MenuItem>
                {['draft', 'ordered', 'running', 'results_received', 'complete', 'published', 'canceled', 'failed'].map((s) => (
                  <MenuItem key={s} value={s}>
                    {STATUS_LABELS[s] ?? s.charAt(0).toUpperCase() + s.slice(1)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>
        </>
      }
    >
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" flex={1}>
          <CircularProgress />
        </Box>
      ) : (
        <FillHeightTable>
          <DataGrid
            rows={filtered}
            columns={columns}
            pageSizeOptions={[10, 25, 50, 100]}
            paginationMode="server"
            rowCount={pagination.total}
            paginationModel={{ page: pagination.page - 1, pageSize: pagination.size }}
            onPaginationModelChange={(m) =>
              setPagination((p) => ({ ...p, page: m.page + 1, size: m.pageSize }))
            }
            disableRowSelectionOnClick
            onRowClick={(params) => navigate(`/runs/${params.id}`)}
            sx={{ cursor: 'pointer' }}
          />
        </FillHeightTable>
      )}

      <Dialog open={showCreate} onClose={() => !creating && setShowCreate(false)} maxWidth="sm" fullWidth>
        <DialogTitle>New Experiment Run</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Name"
            fullWidth
            required
            value={createName}
            onChange={(e) => setCreateName(e.target.value)}
          />
          <TextField
            margin="dense"
            label="Description"
            fullWidth
            multiline
            rows={2}
            value={createDesc}
            onChange={(e) => setCreateDesc(e.target.value)}
          />
          <FormControl fullWidth size="small" sx={{ mt: 1 }} required>
            <InputLabel>Template</InputLabel>
            <Select
              value={createTemplateId}
              label="Template"
              onChange={(e) => setCreateTemplateId(e.target.value)}
            >
              {templates.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth size="small" sx={{ mt: 2 }} required>
            <InputLabel>Analysis</InputLabel>
            <Select
              value={createAnalysisId}
              label="Analysis"
              onChange={(e) => setCreateAnalysisId(e.target.value)}
            >
              {analyses.map((a) => (
                <MenuItem key={a.id} value={a.id}>
                  {a.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Template defines protocol and lifecycle. Analysis is required (assay for import and
            promote-on-publish).
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCreate(false)} disabled={creating}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={
              !createName.trim() || !createTemplateId || !createAnalysisId || creating
            }
          >
            {creating ? 'Creating…' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </FillHeightPage>
  );
};

export default RunsManagement;
