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
import { DataGrid, GridColDef, GridActionsCellItem, GridRowSelectionModel } from '@mui/x-data-grid';
import CancelOutlinedIcon from '@mui/icons-material/CancelOutlined';
import AltRouteIcon from '@mui/icons-material/AltRoute';
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
  routed_work_order_id?: string | null;
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
  const [info, setInfo] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [selection, setSelection] = useState<GridRowSelectionModel>({
    type: 'include',
    ids: new Set(),
  });
  const selectedIds = Array.from(selection.ids).map(String);

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

  const summarizeRoute = (items: Array<{ no_route?: boolean; work_order?: unknown }>) => {
    const routed = items.filter((i) => i.work_order).length;
    const unmatched = items.filter((i) => i.no_route).length;
    const parts: string[] = [];
    if (routed) parts.push(`${routed} routed`);
    if (unmatched) parts.push(`${unmatched} with no routing-map match (stayed requested)`);
    return parts.join('; ') || 'Route complete';
  };

  const handleRouteOne = async (id: string) => {
    try {
      const res = await apiService.routeAskedFor(id);
      setInfo(summarizeRoute(res?.items || []));
      setError(null);
      await loadData();
    } catch (err) {
      setError(ApiService.formatError(err, 'Could not route asked-for'));
    }
  };

  const handleRouteSelected = async () => {
    const ids = selectedIds.filter(
      (id) => rows.find((r) => r.id === id)?.status === 'requested'
    );
    if (!ids.length) return;
    try {
      const res = await apiService.routeAskedForBatch(ids);
      setInfo(summarizeRoute(res?.items || []));
      setError(null);
      setSelection({ type: 'include', ids: new Set() });
      await loadData();
    } catch (err) {
      setError(ApiService.formatError(err, 'Could not route asked-for'));
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
      width: 140,
      getActions: (params) => {
        if (!canAssign || params.row.status !== 'requested') return [];
        return [
          <GridActionsCellItem
            key="route"
            icon={<AltRouteIcon />}
            label="Route"
            onClick={() => void handleRouteOne(params.id as string)}
            showInMenu={false}
          />,
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
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} gap={1} flexWrap="wrap">
            <Typography variant="h4">Asked-for</Typography>
            <Box display="flex" gap={1}>
              {canAssign && (
                <Button
                  variant="outlined"
                  startIcon={<AltRouteIcon />}
                  disabled={
                    !selectedIds.length ||
                    !rows.some(
                      (r) => selectedIds.includes(r.id) && r.status === 'requested'
                    )
                  }
                  onClick={() => void handleRouteSelected()}
                >
                  Route selected
                </Button>
              )}
              {canAssign && (
                <Button variant="contained" onClick={() => setShowForm(true)}>
                  Record requested analysis
                </Button>
              )}
            </Box>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Record requested analysis + TAT. Route matches a routing map and mints a work
            order; it does not start a Test or a LimsRun. No match stays requested.
          </Typography>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          {info && (
            <Alert severity="info" sx={{ mb: 2 }} onClose={() => setInfo(null)}>
              {info}
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
          checkboxSelection={canAssign}
          disableRowSelectionOnClick
          rowSelectionModel={selection}
          onRowSelectionModelChange={setSelection}
          isRowSelectable={(params) => params.row.status === 'requested'}
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
