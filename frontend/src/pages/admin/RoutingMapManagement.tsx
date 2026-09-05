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
  analysis_id?: string | null;
  analysis_ids?: string[];
  sample_type_id: string;
  tat_min: number;
  tat_max: number;
  process_definition_ids: string[];
  active: boolean;
}

interface GroupedMapRow {
  id: string;
  ids: string[];
  analysis_ids: string[];
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
  analysis_id?: string | null;
  sort_order: number;
  acceptedTypeIds?: string[];
}

interface DefinitionDetail {
  id: string;
  name: string;
  steps: DefinitionStep[];
  firstAcceptedTypeIds: string[];
  limsAnalysisIds: string[];
  emergingTypeIds: string[];
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
        analysis_ids: [...(row.analysis_ids || [])],
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
    (row.analysis_ids || []).forEach((id) => {
      if (!existing.analysis_ids.includes(id)) existing.analysis_ids.push(id);
    });
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
  const [tatMin, setTatMin] = useState(1);
  const [tatMax, setTatMax] = useState(10);
  const [chainIds, setChainIds] = useState<string[]>([]);
  const [askedForStepId, setAskedForStepId] = useState('');
  const [addProcessId, setAddProcessId] = useState('');
  const [saving, setSaving] = useState(false);

  const nameOf = (id: string, list: { id: string; name: string }[]) =>
    list.find((x) => x.id === id)?.name || id;

  const typeNames = (ids: string[] = []) =>
    ids.map((id) => nameOf(id, sampleTypes)).join(', ') || 'none';

  const analysisNames = (ids: string[] = []) =>
    ids.map((id) => nameOf(id, analyses)).join(', ') || 'none';

  const processPickerLabel = (id: string) => {
    const detail = definitionDetails[id];
    const name = detail?.name || nameOf(id, definitions);
    const types = typeNames(detail?.firstAcceptedTypeIds);
    const anals = analysisNames(detail?.limsAnalysisIds);
    return `${name} — types: ${types} · analyses: ${anals}`;
  };

  const loadDefinitionDetail = async (id: string): Promise<DefinitionDetail | null> => {
    try {
      const def: any = await apiService.getElnProcessDefinition(id);
      const rawSteps: DefinitionStep[] = Array.isArray(def?.steps) ? def.steps : [];
      const steps = await Promise.all(
        sortSteps(rawSteps).map(async (step) => {
          const typed =
            step.step_kind === 'eln_experiment' || step.step_kind === 'lims_run';
          if (!typed || !step.id) return { ...step, acceptedTypeIds: [] as string[] };
          try {
            const types: any = await apiService.getStepAcceptedSampleTypes(id, step.id);
            return {
              ...step,
              acceptedTypeIds: Array.isArray(types?.sample_type_ids)
                ? types.sample_type_ids
                : [],
            };
          } catch {
            return { ...step, acceptedTypeIds: [] as string[] };
          }
        })
      );
      const first = firstTypedStep(steps);
      return {
        id,
        name: def?.name || id,
        steps,
        firstAcceptedTypeIds: first?.acceptedTypeIds || [],
        limsAnalysisIds: steps
          .filter((s) => s.step_kind === 'lims_run' && s.analysis_id)
          .map((s) => s.analysis_id as string)
          .filter((aid, i, arr) => arr.indexOf(aid) === i),
        emergingTypeIds: Array.isArray(def?.emerging_sample_type_ids)
          ? def.emerging_sample_type_ids
          : first?.acceptedTypeIds || [],
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
        const types = typeNames(detail?.firstAcceptedTypeIds);
        const anals = analysisNames(detail?.limsAnalysisIds);
        return `${i + 1}. ${name} (types: ${types}; analyses: ${anals})`;
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

  const handoffOk = useMemo(() => {
    for (let i = 0; i < chainIds.length - 1; i += 1) {
      const emerging = definitionDetails[chainIds[i]]?.emergingTypeIds || [];
      const nextTypes = definitionDetails[chainIds[i + 1]]?.firstAcceptedTypeIds || [];
      if (!emerging.length || emerging.some((t) => !nextTypes.includes(t))) {
        return false;
      }
    }
    return true;
  }, [chainIds, definitionDetails]);

  const chainAnalysisIds = useMemo(() => {
    const ids: string[] = [];
    chainIds.forEach((id) => {
      (definitionDetails[id]?.limsAnalysisIds || []).forEach((aid) => {
        if (!ids.includes(aid)) ids.push(aid);
      });
    });
    return ids;
  }, [chainIds, definitionDetails]);

  const askedForSlotOptions = useMemo(() => {
    const options: { id: string; label: string }[] = [];
    chainIds.forEach((defId, defIdx) => {
      const detail = definitionDetails[defId];
      sortSteps(detail?.steps || []).forEach((step) => {
        if (step.step_kind !== 'lims_run' || !step.analysis_id || !step.id) return;
        const stepName = step.name?.trim() || kindLabel(step.step_kind);
        const analysis = nameOf(step.analysis_id, analyses);
        options.push({
          id: step.id,
          label: `Process ${defIdx + 1} · ${detail?.name || defId} · ${stepName} · ${analysis}`,
        });
      });
    });
    return options;
  }, [chainIds, definitionDetails, analyses]);

  useEffect(() => {
    if (askedForSlotOptions.length === 1) {
      setAskedForStepId(askedForSlotOptions[0].id);
      return;
    }
    if (!askedForSlotOptions.some((o) => o.id === askedForStepId)) {
      setAskedForStepId('');
    }
  }, [askedForSlotOptions, askedForStepId]);

  const handleCreate = async () => {
    if (!chainIds.length) return;
    setSaving(true);
    try {
      await apiService.createRoutingMap({
        tat_min: tatMin,
        tat_max: tatMax,
        process_definition_ids: chainIds,
        asked_for_step_id: askedForStepId || undefined,
      });
      setOpen(false);
      setChainIds([]);
      setAskedForStepId('');
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
      field: 'analysis_ids',
      headerName: 'LIMS Run analyses',
      flex: 1.2,
      minWidth: 180,
      valueGetter: (_v, row) => {
        const fromChain: string[] = [];
        (row.process_definition_ids || []).forEach((id: string) => {
          (definitionDetails[id]?.limsAnalysisIds || []).forEach((aid) => {
            if (!fromChain.includes(aid)) fromChain.push(aid);
          });
        });
        const ids = fromChain.length ? fromChain : row.analysis_ids || [];
        return ids.map((id: string) => nameOf(id, analyses)).join(', ') || '—';
      },
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
    chainIds.length > 0 &&
    tatMax >= tatMin &&
    firstTypeNames.length > 0 &&
    chainAnalysisIds.length > 0 &&
    Boolean(askedForStepId) &&
    handoffOk;
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
            A route is an ordered process chain plus TAT plus a named asked-for LIMS Run.
            Many routes may name the same analysis. Assignment uses first-step sample type,
            TAT, and that named slot — not “analysis anywhere in the chain.” Duplicate packs
            (same chain + overlapping TAT + overlapping first-step types) are refused.
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
        <DialogTitle>Add route</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
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
            Each process shows its allowed sample types and LIMS Run analyses. Name which
            LIMS Run is the asked-for assay. Other LIMS Runs are supporting QC.
          </Typography>
          {chainIds.map((id, idx) => {
            const detail = definitionDetails[id];
            const name = detail?.name || nameOf(id, definitions);
            const firstStep = detail ? firstTypedStep(detail.steps) : null;
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
                    label={idx === 0 ? 'gates sample type' : 'later process'}
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
                <Box sx={{ pl: 5, mt: 0.5 }}>
                  {(detail?.steps || []).map((s, i) => {
                    const analysis =
                      s.step_kind === 'lims_run' && s.analysis_id
                        ? nameOf(s.analysis_id, analyses)
                        : '';
                    const types = typeNames(s.acceptedTypeIds);
                    return (
                      <Typography key={s.id || i} variant="body2">
                        {stepLine(s, i)}
                        {firstStep && s.id === firstStep.id ? ' (first experiment / LIMS Run)' : ''}
                        {analysis ? ` — analysis: ${analysis}` : ''}
                        {` — sample types: ${types}`}
                      </Typography>
                    );
                  })}
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    Allowed sample types (first experiment / LIMS Run):{' '}
                    {typeNames(detail?.firstAcceptedTypeIds)}
                    {idx === 0 ? ' — used at Route' : ''}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    LIMS Run analyses: {analysisNames(detail?.limsAnalysisIds)}
                  </Typography>
                  <Typography variant="body2">
                    Emerging sample types (after last experiment / LIMS Run):{' '}
                    {typeNames(detail?.emergingTypeIds)}
                  </Typography>
                  {idx < chainIds.length - 1 &&
                    (() => {
                      const nextTypes =
                        definitionDetails[chainIds[idx + 1]]?.firstAcceptedTypeIds || [];
                      const emerging = detail?.emergingTypeIds || [];
                      const ok =
                        emerging.length > 0 &&
                        emerging.every((t) => nextTypes.includes(t));
                      return (
                        <Typography
                          variant="body2"
                          color={ok ? 'text.secondary' : 'error'}
                        >
                          {ok
                            ? `Process ${idx + 2} accepts these emerging types`
                            : `Process ${idx + 2} does not accept the type emerging from process ${idx + 1}`}
                        </Typography>
                      );
                    })()}
                </Box>
              </Box>
            );
          })}
          <Typography variant="body2">
            Sample types this route accepts at assignment:{' '}
            {firstTypeNames.length ? firstTypeNames.join(', ') : 'none — first process needs types'}
          </Typography>
          <FormControl fullWidth>
            <InputLabel>Asked-for LIMS Run</InputLabel>
            <Select
              label="Asked-for LIMS Run"
              value={askedForStepId}
              onChange={(e) => setAskedForStepId(String(e.target.value))}
            >
              {askedForSlotOptions.map((opt) => (
                <MenuItem key={opt.id} value={opt.id}>
                  {opt.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Typography variant="body2">
            LIMS Run analyses in this chain:{' '}
            {chainAnalysisIds.length
              ? analysisNames(chainAnalysisIds)
              : 'none — add a process with a LIMS Run analysis'}
          </Typography>
          <Box display="flex" gap={1} alignItems="flex-start">
            <FormControl fullWidth>
              <InputLabel>Add process</InputLabel>
              <Select
                label="Add process"
                value={addProcessId}
                onChange={(e) => setAddProcessId(e.target.value)}
                renderValue={(value) =>
                  value ? processPickerLabel(String(value)).split(' — ')[0] : ''
                }
              >
                {unusedDefinitions.map((d) => (
                  <MenuItem key={d.id} value={d.id} sx={{ whiteSpace: 'normal' }}>
                    <Box>
                      <Typography variant="body2">{d.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Sample types: {typeNames(definitionDetails[d.id]?.firstAcceptedTypeIds)}
                        {' · '}
                        Analyses: {analysisNames(definitionDetails[d.id]?.limsAnalysisIds)}
                      </Typography>
                    </Box>
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
