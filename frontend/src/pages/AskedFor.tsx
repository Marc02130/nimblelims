import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  Typography,
} from '@mui/material';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import CancelOutlinedIcon from '@mui/icons-material/CancelOutlined';
import { apiService, ApiService } from '../services/apiService';
import { useUser } from '../contexts/UserContext';
import { FillHeightPage, FillHeightTable } from '../components/common/FillHeightPage';
import AskedForForm, { AskedForFormValues } from '../components/asked-for/AskedForForm';

interface AskedForRow {
  id: string;
  sample_id: string;
  sample_name?: string;
  analysis_id: string;
  analysis_name?: string;
  tat_days: number;
  params: Record<string, unknown>;
  status: string;
  created_at: string;
}

interface SampleOption {
  id: string;
  name: string;
  status?: string;
  status_name?: string;
}

const AskedFor: React.FC = () => {
  const { hasPermission } = useUser();
  const canAssign = hasPermission('test:assign');
  const [rows, setRows] = useState<AskedForRow[]>([]);
  const [samples, setSamples] = useState<SampleOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [asked, samplesRaw, statusesRaw] = await Promise.all([
        apiService.getAskedFor(),
        apiService.getSamples({ size: '100' }),
        apiService.getListEntries('sample_status'),
      ]);
      const statuses = Array.isArray(statusesRaw) ? statusesRaw : [];
      const availableId = statuses.find((s: { name: string }) => s.name === 'Available for Testing')?.id;
      const sampleList: SampleOption[] = (Array.isArray(samplesRaw) ? samplesRaw : []).map(
        (s: SampleOption) => ({
          ...s,
          status_name: statuses.find((st: { id: string }) => st.id === s.status)?.name,
        })
      );
      setSamples(
        availableId
          ? sampleList.filter((s) => s.status === availableId)
          : sampleList.filter((s) => s.status_name === 'Available for Testing')
      );
      setRows(Array.isArray(asked?.items) ? asked.items : []);
      setError(null);
    } catch (err) {
      setError(ApiService.formatError(err, 'Failed to load asked-for'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreate = async (values: AskedForFormValues) => {
    await apiService.createAskedFor(values);
    setShowForm(false);
    await loadData();
  };

  const handleCancel = async (id: string) => {
    try {
      await apiService.cancelAskedFor(id);
      await loadData();
    } catch (err) {
      setError(ApiService.formatError(err, 'Could not cancel asked-for'));
    }
  };

  const columns: GridColDef[] = [
    { field: 'sample_name', headerName: 'Sample', flex: 1, minWidth: 140 },
    { field: 'analysis_name', headerName: 'Requested analysis', flex: 1, minWidth: 180 },
    { field: 'tat_days', headerName: 'TAT (days)', width: 110 },
    { field: 'status', headerName: 'Status', width: 120 },
    {
      field: 'params',
      headerName: 'Params',
      flex: 1,
      minWidth: 140,
      valueGetter: (_value, row) => {
        const p = row?.params || {};
        const keys = Object.keys(p);
        return keys.length ? keys.map((k) => `${k}=${p[k]}`).join(', ') : '—';
      },
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 100,
      getActions: (params) => {
        if (!canAssign || params.row.status !== 'requested') return [];
        return [
          <GridActionsCellItem
            key="cancel"
            icon={<CancelOutlinedIcon />}
            label="Cancel asked-for"
            onClick={() => void handleCancel(params.id as string)}
            showInMenu={false}
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
            <Typography variant="h4">Asked-for</Typography>
            {canAssign && (
              <Button variant="contained" onClick={() => setShowForm(true)}>
                Record requested analysis
              </Button>
            )}
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            After receive, record what was asked for. This does not assign a test or start work.
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
          initialState={{
            pagination: { paginationModel: { page: 0, pageSize: 25 } },
          }}
          disableRowSelectionOnClick
        />
      </FillHeightTable>

      <Dialog
        open={showForm}
        onClose={() => setShowForm(false)}
        maxWidth="sm"
        fullWidth
        aria-labelledby="asked-for-form-title"
      >
        <DialogTitle id="asked-for-form-title">Record requested analysis</DialogTitle>
        <DialogContent>
          <AskedForForm
            sampleOptions={samples}
            onSubmit={handleCreate}
            onCancel={() => setShowForm(false)}
          />
        </DialogContent>
      </Dialog>
    </FillHeightPage>
  );
};

export default AskedFor;
