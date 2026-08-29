import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
} from '@mui/material';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import AddIcon from '@mui/icons-material/Add';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
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

interface GroupedMapRow {
  id: string;
  ids: string[];
  analysis_id: string;
  sample_type_ids: string[];
  tat_min: number;
  tat_max: number;
  process_definition_ids: string[];
  active: boolean;
}

interface DefinitionStep {
  id: string;
  name?: string;
  step_kind?: string;
  sort_order: number;
}

interface DefinitionDetail {
  id: string;
  name: string;
  steps: DefinitionStep[];
  firstAcceptedTypeIds: string[];
}

const kindLabel = (kind?: string) => (kind === 'lims_run' ? 'LIMS Run' : 'ELN Experiment');

const sortSteps = (steps: DefinitionStep[] = []) =>
  [...steps].sort((a, b) => a.sort_order - b.sort_order);

const firstTypedStep = (steps: DefinitionStep[]) => {
  const ordered = sortSteps(steps);
  return (
    ordered.find((s) => s.step_kind === 'eln_experiment' || s.step_kind === 'lims_run') ||
    ordered[0] ||
    null
  );
};

const stepLine = (step: DefinitionStep, index: number) => {
  const label = step.name?.trim() || kindLabel(step.step_kind);
  return `${index + 1}. ${label} (${kindLabel(step.step_kind)})`;
};

const groupMapRows = (rows: RoutingMapRow[]): GroupedMapRow[] => {
  const order: string[] = [];
  const grouped = new Map<string, GroupedMapRow>();
  rows.forEach((row) => {
    const key = [
      row.analysis_id,
      row.tat_min,
      row.tat_max,
      (row.process_definition_ids || []).join(','),
      String(row.active),
    ].join('|');
    const existing = grouped.get(key);
    if (!existing) {
      grouped.set(key, {
        id: row.id,
        ids: [row.id],
        analysis_id: row.analysis_id,
        sample_type_ids: row.sample_type_id ? [row.sample_type_id] : [],
        tat_min: row.tat_min,
        tat_max: row.tat_max,
        process_definition_ids: row.process_definition_ids || [],
        active: row.active,
      });
      order.push(key);
      return;
    }
    existing.ids.push(row.id);
    if (row.sample_type_id && !existing.sample_type_ids.includes(row.sample_type_id)) {
      existing.sample_type_ids.push(row.sample_type_id);
    }
  });
  return order.map((key) => grouped.get(key) as GroupedMapRow);
};

const RoutingMapManagement: React.FC = () => {
  const { hasPermission } = useUser();
  const canEdit = hasPermission('config:edit');
  const [rows, setRows] = useState<RoutingMapRow[]>([]);
  const [analyses, setAnalyses] = useState<{ id: string; name: string }[]>([]);
  const [sampleTypes, setSampleTypes] = useState<{ id: string; name: string }[]>([]);
  const [definitions, setDefinitions] = useState<{ id: string; name: string }[]>([]);
  const [definitionDetails, setDefinitionDetails] = useState<Record<string, DefinitionDetail>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [analysisId, setAnalysisId] = useState('');
  const [tatMin, setTatMin] = useState(1);
  const [tatMax, setTatMax] = useState(10);
  const [chainIds, setChainIds] = useState<string[]>([]);
  const [addProcessId, setAddProcessId] = useState('');
  const [saving, setSaving] = useState(false);

  const nameOf = (id: string, list: { id: string; name: string }[]) =>
    list.find((x) => x.id === id)?.name || id;

  const loadDefinitionDetail = async (id: string): Promise<DefinitionDetail | null> => {
    try {
      const def: any = await apiService.getElnProcessDefinition(id);
      const steps: DefinitionStep[] = Array.isArray(def?.steps) ? def.steps : [];
      const first = firstTypedStep(steps);
      let firstAcceptedTypeIds: string[] = [];
      if (first?.id) {
        try {
          const types: any = await apiService.getStepAcceptedSampleTypes(id, first.id);
          firstAcceptedTypeIds = Array.isArray(types?.sample_type_ids)
            ? types.sample_type_ids
            : [];
        } catch {
          firstAcceptedTypeIds = [];
        }
      }
      return {
        id,
        name: def?.name || id,
        steps: sortSteps(steps),
        firstAcceptedTypeIds,
      };
    } catch {
      return null;
    }
  };

  const load = async () => {
    try {
      setLoading(true);
      const [maps, analysesRaw, typesRaw, defsRaw] = await Promise.all([
        apiService.getRoutingMap({ active_only: false }),
        apiService.getAnalyses({ size: 200, active: true }),
        apiService.getListEntries('sample_types'),
        apiService.getElnProcessDefinitions({ page: 1, size: 200, active: true }),
      ]);
      const defList = Array.isArray(defsRaw?.definitions) ? defsRaw.definitions : [];
      setRows(Array.isArray(maps) ? maps : []);
      setAnalyses(ApiService.unwrapAnalysesList(analysesRaw));
      setSampleTypes(Array.isArray(typesRaw) ? typesRaw : []);
      setDefinitions(defList);
      const details = await Promise.all(defList.map((d: { id: string }) => loadDefinitionDetail(d.id)));
      const byId: Record<string, DefinitionDetail> = {};
      details.forEach((d) => {
        if (d) byId[d.id] = d;
      });
      setDefinitionDetails(byId);
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

  const firstProcessId = chainIds[0] || '';
  const selectedDetail = firstProcessId ? definitionDetails[firstProcessId] : undefined;
  const firstTyped = selectedDetail ? firstTypedStep(selectedDetail.steps) : null;
  const firstTypeNames = useMemo(() => {
    if (!selectedDetail) return [];
    return selectedDetail.firstAcceptedTypeIds.map((id) => nameOf(id, sampleTypes));
  }, [selectedDetail, sampleTypes]);

  const groupedRows = useMemo(() => groupMapRows(rows), [rows]);

  const firstStepTypesLabel = (processIds: string[], fallbackIds: string[]) => {
    const defId = processIds?.[0];
    const detail = defId ? definitionDetails[defId] : undefined;
    const first = detail ? firstTypedStep(detail.steps) : null;
    const typeIds =
      detail?.firstAcceptedTypeIds?.length ? detail.firstAcceptedTypeIds : fallbackIds;
    const types = typeIds.map((id) => nameOf(id, sampleTypes)).join(', ') || 'none';
    if (!first) return types;
    return `${stepLine(first, 0)} — ${types}`;
  };

  const processDisplay = (ids: string[]) => {
    if (!ids?.length) return '—';
    return ids
      .map((id, i) => {
        const detail = definitionDetails[id];
        const name = detail?.name || nameOf(id, definitions);
        const tag = i === 0 ? 'sample-type' : 'type-independent';
        return `${i + 1}. ${name} (${tag})`;
      })
      .join(' → ');
  };

  const moveChain = (idx: number, dir: -1 | 1) => {
    const next = [...chainIds];
    const j = idx + dir;
    if (j < 0 || j >= next.length) return;
    [next[idx], next[j]] = [next[j], next[idx]];
    setChainIds(next);
  };

  const handleCreate = async () => {
    if (!analysisId || !chainIds.length) return;
    setSaving(true);
    try {
      await apiService.createRoutingMap({
        analysis_id: analysisId,
        tat_min: tatMin,
        tat_max: tatMax,
        process_definition_ids: chainIds,
      });
      setOpen(false);
      setAnalysisId('');
      setChainIds([]);
      setAddProcessId('');
      await load();
    } catch (err) {
      setError(ApiService.formatError(err, 'Could not save routing map row'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (ids: string[]) => {
    try {
      await Promise.all(ids.map((id) => apiService.deleteRoutingMap(id)));
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
      field: 'first_step_types',
      headerName: 'First experiment / LIMS Run types',
      flex: 1.4,
      minWidth: 220,
      valueGetter: (_v, row) =>
        firstStepTypesLabel(row.process_definition_ids || [], row.sample_type_ids || []),
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
      flex: 2,
      minWidth: 280,
      valueGetter: (_v, row) => processDisplay(row.process_definition_ids || []),
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
                onClick={() => void handleDelete(params.row.ids || [params.id as string])}
              />,
            ]
          : [],
    },
  ];

  const canSave =
    !saving &&
    Boolean(analysisId) &&
    chainIds.length > 0 &&
    tatMax >= tatMin &&
    firstTypeNames.length > 0;
  const unusedDefinitions = definitions.filter((d) => !chainIds.includes(d.id));

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
            analysis × TAT range → an ordered process chain. The first process is sample-type
            dependent (extract). Later processes are sample-type independent (analysis, reporting).
            Route assignment checks the sample against the first experiment or LIMS Run of the
            first process only. Overlapping TAT ranges for the same analysis and first-step type
            are refused.
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
          rows={groupedRows}
          columns={columns}
          loading={loading}
          pageSizeOptions={[10, 25, 50]}
          initialState={{ pagination: { paginationModel: { page: 0, pageSize: 25 } } }}
          disableRowSelectionOnClick
        />
      </FillHeightTable>
      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth>
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
          <Typography variant="subtitle2">Ordered processes</Typography>
          <Typography variant="caption" color="text.secondary">
            First process is sample-type dependent. Later processes are not (analysis / target
            genes / reporting).
          </Typography>
          {chainIds.map((id, idx) => {
            const detail = definitionDetails[id];
            const name = detail?.name || nameOf(id, definitions);
            return (
              <Box key={`${id}-${idx}`}>
                <Box display="flex" gap={1} alignItems="center" flexWrap="wrap">
                  <Chip size="small" label={`${idx + 1}`} />
                  <Typography variant="body2" sx={{ flex: 1 }}>
                    {name}
                  </Typography>
                  <Chip
                    size="small"
                    color={idx === 0 ? 'primary' : 'default'}
                    label={idx === 0 ? 'sample-type' : 'type-independent'}
                  />
                  <IconButton
                    size="small"
                    aria-label={`move process ${idx + 1} up`}
                    onClick={() => moveChain(idx, -1)}
                    disabled={idx === 0}
                  >
                    <ArrowUpwardIcon fontSize="small" />
                  </IconButton>
                  <IconButton
                    size="small"
                    aria-label={`move process ${idx + 1} down`}
                    onClick={() => moveChain(idx, 1)}
                    disabled={idx === chainIds.length - 1}
                  >
                    <ArrowDownwardIcon fontSize="small" />
                  </IconButton>
                  <IconButton
                    size="small"
                    aria-label={`remove process ${idx + 1}`}
                    onClick={() => setChainIds(chainIds.filter((_, i) => i !== idx))}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>
                {idx === 0 && detail && (
                  <Box sx={{ pl: 5, mt: 0.5 }}>
                    {detail.steps.map((s, i) => (
                      <Typography key={s.id || i} variant="body2">
                        {stepLine(s, i)}
                        {firstTyped && s.id === firstTyped.id
                          ? ' (first experiment / LIMS Run)'
                          : ''}
                      </Typography>
                    ))}
                    <Typography variant="body2" sx={{ mt: 0.5 }}>
                      First experiment / LIMS Run sample types:{' '}
                      {firstTypeNames.length ? firstTypeNames.join(', ') : 'none recorded'}
                    </Typography>
                  </Box>
                )}
              </Box>
            );
          })}
          <Box display="flex" gap={1} alignItems="center">
            <FormControl fullWidth>
              <InputLabel>Add process</InputLabel>
              <Select
                label="Add process"
                value={addProcessId}
                onChange={(e) => setAddProcessId(e.target.value)}
              >
                {unusedDefinitions.map((d) => (
                  <MenuItem key={d.id} value={d.id}>
                    {d.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button
              startIcon={<AddIcon />}
              onClick={() => {
                if (!addProcessId) return;
                setChainIds([...chainIds, addProcessId]);
                setAddProcessId('');
              }}
              disabled={!addProcessId}
            >
              Add
            </Button>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => void handleCreate()}
            disabled={!canSave}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </FillHeightPage>
  );
};

export default RoutingMapManagement;
