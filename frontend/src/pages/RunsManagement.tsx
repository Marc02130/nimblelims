import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
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
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    apiService
      .getExperimentTemplates({ page: 1, size: 500 })
      .then((res: any) => setTemplates(res?.templates ?? []))
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
      const res = await apiService.getExperimentRuns(params);
      setRuns(res?.runs ?? []);
      setPagination((p) => ({ ...p, total: res?.total ?? 0, pages: res?.pages ?? 1 }));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load runs');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!createName.trim() || !createTemplateId) return;
    setCreating(true);
    setError(null);
    try {
      const run = await apiService.createExperimentRun({
        name: createName.trim(),
        description: createDesc.trim() || undefined,
        experiment_template_id: createTemplateId,
      });
      setShowCreate(false);
      setCreateName('');
      setCreateDesc('');
      setCreateTemplateId('');
      navigate(`/runs/${run.id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create run');
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
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
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

      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
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
          {loading ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress />
            </Box>
          ) : (
            <DataGrid
              rows={filtered}
              columns={columns}
              pageSizeOptions={[10, 25, 50]}
              paginationMode="server"
              rowCount={pagination.total}
              paginationModel={{ page: pagination.page - 1, pageSize: pagination.size }}
              onPaginationModelChange={(m) =>
                setPagination((p) => ({ ...p, page: m.page + 1, size: m.pageSize }))
              }
              autoHeight
              disableRowSelectionOnClick
              onRowClick={(params) => navigate(`/runs/${params.id}`)}
              sx={{ cursor: 'pointer' }}
            />
          )}
        </CardContent>
      </Card>

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
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCreate(false)} disabled={creating}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={!createName.trim() || !createTemplateId || creating}
          >
            {creating ? 'Creating…' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default RunsManagement;
