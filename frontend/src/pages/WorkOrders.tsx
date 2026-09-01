import React, { useEffect, useState } from 'react';
import { Alert, Box, Button, Typography } from '@mui/material';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { useNavigate } from 'react-router-dom';
import { apiService, ApiService } from '../services/apiService';
import { useUser } from '../contexts/UserContext';
import { FillHeightPage, FillHeightTable } from '../components/common/FillHeightPage';

interface WorkOrderRow {
  id: string;
  asked_for_id: string;
  sample_id: string;
  sample_name?: string;
  analysis_id: string;
  analysis_name?: string;
  process_definition_ids: string[];
  status: string;
  process_id?: string | null;
  latest_process_id?: string | null;
  started_count?: number;
  created_at: string;
}

const WorkOrders: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useUser();
  const canStart = hasPermission('experiment:manage');
  const [rows, setRows] = useState<WorkOrderRow[]>([]);
  const [definitions, setDefinitions] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      const [res, defsRaw] = await Promise.all([
        apiService.getWorkOrders(),
        apiService.getElnProcessDefinitions({ page: 1, size: 200, active: true }),
      ]);
      setRows(Array.isArray(res?.items) ? res.items : []);
      setDefinitions(Array.isArray(defsRaw?.definitions) ? defsRaw.definitions : []);
      setError(null);
    } catch (err) {
      setError(ApiService.formatError(err, 'Failed to load work orders'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleStart = async (id: string) => {
    try {
      const wo = await apiService.startWorkOrder(id);
      await load();
      const openId = wo?.latest_process_id || wo?.process_id;
      if (openId) {
        navigate(`/experiments/processes/${openId}`);
      }
    } catch (err) {
      setError(ApiService.formatError(err, 'Could not start work order'));
    }
  };

  const columns: GridColDef[] = [
    { field: 'sample_name', headerName: 'Sample', flex: 1, minWidth: 140 },
    { field: 'analysis_name', headerName: 'Analysis', flex: 1, minWidth: 160 },
    {
      field: 'process_definition_ids',
      headerName: 'Process chain',
      flex: 1.6,
      minWidth: 220,
      valueGetter: (_v, row) =>
        (row.process_definition_ids || [])
          .map((id: string, i: number) => {
            const name = definitions.find((d) => d.id === id)?.name || id.slice(0, 8);
            return `${i + 1}. ${name}`;
          })
          .join(' → ') || '—',
    },
    { field: 'status', headerName: 'Status', width: 130 },
    {
      field: 'process_id',
      headerName: 'Started',
      width: 130,
      valueGetter: (_v, row) => {
        const chain = (row.process_definition_ids || []).length;
        const started = row.started_count || (row.process_id ? 1 : 0);
        if (!started) return '—';
        return `${started} of ${chain || started}`;
      },
    },
    {
      field: 'actions',
      type: 'actions',
      width: 90,
      getActions: (params) => {
        const chain = (params.row.process_definition_ids || []).length;
        const started = params.row.started_count || (params.row.process_id ? 1 : 0);
        const pending =
          params.row.status === 'queued' ||
          (params.row.status === 'in_progress' && started < chain);
        if (!canStart || !pending) return [];
        return [
          <GridActionsCellItem
            key="start"
            icon={<PlayArrowIcon />}
            label={started ? 'Start next process' : 'Start process'}
            onClick={() => void handleStart(params.id as string)}
          />,
        ];
      },
    },
  ];

  return (
    <FillHeightPage
      header={
        <>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h4">Work orders</Typography>
            <Button onClick={() => void load()}>Refresh</Button>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Backlog minted by Route. The process chain is ordered. Start instantiates
            the next pending process only (first start = process 1). Later starts
            gate the sample’s current type. Tests are minted later, at LimsRun start.
          </Typography>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
        </>
      }
    >
      <FillHeightTable>
        <DataGrid
          rows={rows}
          columns={columns}
          loading={loading}
          pageSizeOptions={[10, 25, 50]}
          initialState={{ pagination: { paginationModel: { page: 0, pageSize: 25 } } }}
          disableRowSelectionOnClick
        />
      </FillHeightTable>
    </FillHeightPage>
  );
};

export default WorkOrders;
