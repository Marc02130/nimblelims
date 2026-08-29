import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
} from '@mui/material';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import DeleteIcon from '@mui/icons-material/Delete';
import { apiService, ApiService } from '../../services/apiService';
import { useUser } from '../../contexts/UserContext';
import { FillHeightPage, FillHeightTable } from '../../components/common/FillHeightPage';

interface RoutingMapRow {
  id: string;
  analysis_id: string;
  sample_type_id: string;
  tat_min: number;
  tat_max: number;
  process_definition_ids: string[];
  active: boolean;
}

const RoutingMapManagement: React.FC = () => {
  const { hasPermission } = useUser();
  const canEdit = hasPermission('config:edit');
  const [rows, setRows] = useState<RoutingMapRow[]>([]);
  const [analyses, setAnalyses] = useState<{ id: string; name: string }[]>([]);
  const [sampleTypes, setSampleTypes] = useState<{ id: string; name: string }[]>([]);
  const [definitions, setDefinitions] = useState<{ id: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [analysisId, setAnalysisId] = useState('');
  const [sampleTypeId, setSampleTypeId] = useState('');
  const [tatMin, setTatMin] = useState(1);
  const [tatMax, setTatMax] = useState(10);
  const [definitionId, setDefinitionId] = useState('');
  const [saving, setSaving] = useState(false);

  const nameOf = (id: string, list: { id: string; name: string }[]) =>
    list.find((x) => x.id === id)?.name || id;

  const load = async () => {
    try {
      setLoading(true);
      const [maps, analysesRaw, typesRaw, defsRaw] = await Promise.all([
        apiService.getRoutingMap({ active_only: false }),
        apiService.getAnalyses({ size: 200, active: true }),
        apiService.getListEntries('sample_types'),
        apiService.getElnProcessDefinitions({ page: 1, size: 200, active: true }),
      ]);
      setRows(Array.isArray(maps) ? maps : []);
      setAnalyses(ApiService.unwrapAnalysesList(analysesRaw));
      setSampleTypes(Array.isArray(typesRaw) ? typesRaw : []);
      setDefinitions(Array.isArray(defsRaw?.definitions) ? defsRaw.definitions : []);
      setError(null);
    } catch (err) {
      setError(ApiService.formatError(err, 'Failed to load routing map'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleCreate = async () => {
    if (!analysisId || !sampleTypeId || !definitionId) return;
    setSaving(true);
    try {
      await apiService.createRoutingMap({
        analysis_id: analysisId,
        sample_type_id: sampleTypeId,
        tat_min: tatMin,
        tat_max: tatMax,
        process_definition_ids: [definitionId],
      });
      setOpen(false);
      setAnalysisId('');
      setSampleTypeId('');
      setDefinitionId('');
      await load();
    } catch (err) {
      setError(ApiService.formatError(err, 'Could not save routing map row'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await apiService.deleteRoutingMap(id);
      await load();
    } catch (err) {
      setError(ApiService.formatError(err, 'Could not delete routing map row'));
    }
  };

  const columns: GridColDef[] = [
    {
      field: 'analysis_id',
      headerName: 'Analysis',
      flex: 1,
      minWidth: 160,
      valueGetter: (_v, row) => nameOf(row.analysis_id, analyses),
    },
    {
      field: 'sample_type_id',
      headerName: 'Sample type',
      flex: 1,
      minWidth: 140,
      valueGetter: (_v, row) => nameOf(row.sample_type_id, sampleTypes),
    },
    {
      field: 'tat',
      headerName: 'TAT days',
      width: 120,
      valueGetter: (_v, row) => `${row.tat_min}–${row.tat_max}`,
    },
    {
      field: 'process_definition_ids',
      headerName: 'Process chain',
      flex: 1,
      minWidth: 180,
      valueGetter: (_v, row) =>
        (row.process_definition_ids || []).map((id: string) => nameOf(id, definitions)).join(' → '),
    },
    { field: 'active', headerName: 'Active', width: 90 },
    {
      field: 'actions',
      type: 'actions',
      width: 80,
      getActions: (params) =>
        canEdit
          ? [
              <GridActionsCellItem
                key="delete"
                icon={<DeleteIcon />}
                label="Delete"
                onClick={() => void handleDelete(params.id as string)}
              />,
            ]
          : [],
    },
  ];

  return (
    <FillHeightPage
      header={
        <>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h4">Routing map</Typography>
            {canEdit && (
              <Button variant="contained" onClick={() => setOpen(true)}>
                Add route
              </Button>
            )}
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            analysis × sample type × TAT range → process definition. Every step in the chain
            must accept that sample type. Overlapping TAT ranges are refused.
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
      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add routing map row</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
          <FormControl fullWidth>
            <InputLabel>Analysis</InputLabel>
            <Select
              label="Analysis"
              value={analysisId}
              onChange={(e) => setAnalysisId(e.target.value)}
            >
              {analyses.map((a) => (
                <MenuItem key={a.id} value={a.id}>
                  {a.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth>
            <InputLabel>Sample type</InputLabel>
            <Select
              label="Sample type"
              value={sampleTypeId}
              onChange={(e) => setSampleTypeId(e.target.value)}
            >
              {sampleTypes.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Box display="flex" gap={1}>
            <TextField
              label="TAT min"
              type="number"
              value={tatMin}
              onChange={(e) => setTatMin(Number(e.target.value))}
              inputProps={{ min: 1 }}
            />
            <TextField
              label="TAT max"
              type="number"
              value={tatMax}
              onChange={(e) => setTatMax(Number(e.target.value))}
              inputProps={{ min: 1 }}
            />
          </Box>
          <FormControl fullWidth>
            <InputLabel>Process definition</InputLabel>
            <Select
              label="Process definition"
              value={definitionId}
              onChange={(e) => setDefinitionId(e.target.value)}
            >
              {definitions.map((d) => (
                <MenuItem key={d.id} value={d.id}>
                  {d.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => void handleCreate()}
            disabled={saving || !analysisId || !sampleTypeId || !definitionId || tatMax < tatMin}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </FillHeightPage>
  );
};

export default RoutingMapManagement;
