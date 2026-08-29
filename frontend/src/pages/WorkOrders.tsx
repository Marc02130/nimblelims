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
  created_at: string;
}

const WorkOrders: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useUser();
  const canStart = hasPermission('experiment:manage');
  const [rows, setRows] = useState<WorkOrderRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      setLoading(true);
      const res = await apiService.getWorkOrders();
      setRows(Array.isArray(res?.items) ? res.items : []);
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
      if (wo?.process_id) {
        navigate(`/experiments/processes/${wo.process_id}`);
      }
    } catch (err) {
      setError(ApiService.formatError(err, 'Could not start work order'));
    }
  };

  const columns: GridColDef[] = [
    { field: 'sample_name', headerName: 'Sample', flex: 1, minWidth: 140 },
    { field: 'analysis_name', headerName: 'Analysis', flex: 1, minWidth: 160 },
    { field: 'status', headerName: 'Status', width: 130 },
    {
      field: 'process_id',
      headerName: 'Process',
      width: 140,
      valueGetter: (_v, row) => (row.process_id ? 'Open' : '—'),
    },
    {
      field: 'actions',
      type: 'actions',
      width: 90,
      getActions: (params) => {
        if (!canStart || params.row.status !== 'queued') return [];
        return [
          <GridActionsCellItem
            key="start"
            icon={<PlayArrowIcon />}
            label="Start process"
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
            Backlog minted by Route. Start instantiates the first process in the snapshot
            chain. Tests are still minted later, at LimsRun start.
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
