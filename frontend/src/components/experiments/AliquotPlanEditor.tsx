/**
 * Entry-configured aliquot/pool plan editor.
 *
 * One concrete method controls the entry's mint operation and columns. Destination
 * sample type is a separate entry default with an optional per-line override.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  FormHelperText,
  IconButton,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import ScienceIcon from '@mui/icons-material/Science';
import {
  AliquotMethod,
  AliquotOperation,
  DestSampleTypeOptionsResponse,
  SampleTypeOption,
  apiService,
} from '../../services/apiService';

interface ApiError {
  response?: {
    data?: {
      detail?: unknown;
    };
  };
}

const apiErrorMsg = (err: unknown, fallback: string): string => {
  const detail = (err as ApiError)?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (typeof detail === 'object' && detail !== null && 'message' in detail) {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === 'string') return message;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (
      typeof first === 'object' &&
      first !== null &&
      'msg' in first &&
      typeof first.msg === 'string'
    ) {
      return first.msg;
    }
  }
  return fallback;
};

type NumericField =
  | 'volume'
  | 'target_amount'
  | 'target_volume'
  | 'target_concentration'
  | 'split_count';

interface MethodDefinition {
  value: AliquotMethod;
  label: string;
  operation: AliquotOperation;
  fields: readonly NumericField[];
}

const METHODS: readonly MethodDefinition[] = [
  {
    value: 'aliquot_by_volume',
    label: 'Aliquot — by volume',
    operation: 'aliquot',
    fields: ['volume'],
  },
  {
    value: 'aliquot_by_target_amount',
    label: 'Aliquot — by target amount',
    operation: 'aliquot',
    fields: ['target_amount'],
  },
  {
    value: 'aliquot_by_target_concentration',
    label: 'Aliquot — by target concentration (normalization)',
    operation: 'aliquot',
    fields: ['target_concentration', 'target_volume', 'target_amount'],
  },
  {
    value: 'aliquot_n_way_equal_split',
    label: 'Aliquot — N-way equal split',
    operation: 'aliquot',
    fields: ['split_count'],
  },
  {
    value: 'pool_by_volume_per_source',
    label: 'Pool — by volume per source',
    operation: 'pool',
    fields: ['volume'],
  },
  {
    value: 'pool_equal_volume_each',
    label: 'Pool — equal volume from each',
    operation: 'pool',
    fields: ['volume'],
  },
  {
    value: 'pool_by_target_amount_per_source',
    label: 'Pool — by target amount per source',
    operation: 'pool',
    fields: ['target_amount'],
  },
  {
    value: 'pool_consolidate_remaining',
    label: 'Pool — consolidate remaining',
    operation: 'pool',
    fields: [],
  },
] as const;

const ENTRY_DEFAULT = '__entry_default__';
const SAME_AS_PARENT = '__same_as_parent__';

interface PlanLine {
  line_id?: string;
  source_sample_id: string;
  source_container_id?: string;
  volume?: number | '';
  target_amount?: number | '';
  target_volume?: number | '';
  target_concentration?: number | '';
  split_count?: number | '';
  dest_container_type_id?: string;
  dest_container_name?: string;
  dest_sample_type?: string;
  inherit_entry_dest_sample_type: boolean;
  pool_group?: string;
}

interface CatalogState {
  loading: boolean;
  data?: DestSampleTypeOptionsResponse;
  error?: string;
}

interface AliquotPlanResponse {
  method: AliquotMethod;
  default_dest_sample_type?: string | null;
  lines?: PlanLine[];
  line_count: number;
}

interface AliquotPlanSaveResult {
  line_count: number;
}

interface AliquotPlanExecuteResult {
  success_count: number;
  error_count: number;
}

const methodDefinition = (method: AliquotMethod): MethodDefinition =>
  METHODS.find((candidate) => candidate.value === method) ?? METHODS[0];

const catalogKey = (sampleId: string, operation: AliquotOperation): string =>
  `${sampleId}:${operation}`;

const blankLine = (operation: AliquotOperation): PlanLine => ({
  source_sample_id: '',
  inherit_entry_dest_sample_type: true,
  pool_group: operation === 'pool' ? 'pool-1' : '',
});

export interface AliquotPlanEditorProps {
  entryId: string;
  canEdit?: boolean;
  sampleIds?: string[];
}

const AliquotPlanEditor: React.FC<AliquotPlanEditorProps> = ({
  entryId,
  canEdit = true,
  sampleIds = [],
}) => {
  const [method, setMethod] = useState<AliquotMethod>('aliquot_by_volume');
  const [defaultDestSampleType, setDefaultDestSampleType] = useState('');
  const [lines, setLines] = useState<PlanLine[]>([blankLine('aliquot')]);
  const [persistedLineCount, setPersistedLineCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [catalogs, setCatalogs] = useState<Record<string, CatalogState>>({});

  const methodConfig = useMemo(() => methodDefinition(method), [method]);
  const operation = methodConfig.operation;

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = (await apiService.getAliquotPlan(entryId)) as AliquotPlanResponse;
      const loadedMethod = response.method || 'aliquot_by_volume';
      const loadedOperation = methodDefinition(loadedMethod).operation;
      const raw = response.lines || [];
      setMethod(loadedMethod);
      setDefaultDestSampleType(response.default_dest_sample_type || '');
      setPersistedLineCount(response.line_count ?? raw.length);
      setLines(
        raw.length > 0
          ? raw.map((line) => ({
              line_id: line.line_id,
              source_sample_id: line.source_sample_id || '',
              source_container_id: line.source_container_id || '',
              volume: line.volume ?? '',
              target_amount: line.target_amount ?? '',
              target_volume: line.target_volume ?? '',
              target_concentration: line.target_concentration ?? '',
              split_count: line.split_count ?? '',
              dest_container_type_id: line.dest_container_type_id || '',
              dest_container_name: line.dest_container_name || '',
              dest_sample_type: line.dest_sample_type || '',
              inherit_entry_dest_sample_type:
                line.inherit_entry_dest_sample_type !== false,
              pool_group: line.pool_group || '',
            }))
          : [blankLine(loadedOperation)],
      );
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to load plan'));
    } finally {
      setLoading(false);
    }
  }, [entryId]);

  useEffect(() => {
    void load();
  }, [load]);

  const requiredCatalogKey = useMemo(() => {
    const keys = new Set<string>();
    lines.forEach((line) => {
      const sampleId = line.source_sample_id.trim();
      if (sampleId) keys.add(catalogKey(sampleId, operation));
    });
    return Array.from(keys).sort().join('|');
  }, [lines, operation]);

  useEffect(() => {
    if (!requiredCatalogKey) return;
    let active = true;
    const requests = requiredCatalogKey.split('|').map((key) => {
      const separator = key.lastIndexOf(':');
      const sampleId = key.slice(0, separator);
      const requestedOperation = key.slice(separator + 1) as AliquotOperation;
      setCatalogs((current) => ({ ...current, [key]: { loading: true } }));
      return apiService
        .getDestSampleTypes(sampleId, requestedOperation)
        .then((data) => {
          if (!active) return;
          setCatalogs((current) => ({
            ...current,
            [key]: { loading: false, data },
          }));
        })
        .catch((err) => {
          if (!active) return;
          setCatalogs((current) => ({
            ...current,
            [key]: {
              loading: false,
              error: apiErrorMsg(err, 'Could not load destination sample types'),
            },
          }));
        });
    });
    void Promise.all(requests);
    return () => {
      active = false;
    };
  }, [requiredCatalogKey]);

  const mixedPoolMessages = useMemo(() => {
    const messages = new Map<string, string>();
    if (operation !== 'pool') return messages;
    const groups = new Map<string, PlanLine[]>();
    lines.forEach((line) => {
      const group = line.pool_group?.trim();
      if (group) groups.set(group, [...(groups.get(group) || []), line]);
    });
    groups.forEach((groupLines, group) => {
      const sourceTypes = new Map<string, string>();
      let ready = true;
      groupLines.forEach((line) => {
        const sampleId = line.source_sample_id.trim();
        const catalog = catalogs[catalogKey(sampleId, 'pool')];
        if (!sampleId || !catalog?.data) {
          ready = false;
          return;
        }
        const sourceType = catalog.data.source_sample_type;
        sourceTypes.set(sourceType.id, sourceType.name);
      });
      if (ready && sourceTypes.size > 1) {
        messages.set(
          group,
          `Pool “${group}” has mixed source sample types (${Array.from(
            sourceTypes.values(),
          ).join(' and ')}). Use one source sample type per pool.`,
        );
      }
    });
    return messages;
  }, [catalogs, lines, operation]);

  const defaultOptions = useMemo<SampleTypeOption[]>(() => {
    const selectedSampleIds = Array.from(
      new Set(lines.map((line) => line.source_sample_id.trim()).filter(Boolean)),
    );
    if (selectedSampleIds.length === 0) return [];
    const optionLists = selectedSampleIds.map(
      (sampleId) => catalogs[catalogKey(sampleId, operation)]?.data?.options,
    );
    if (optionLists.some((options) => !options)) return [];
    const [first = [], ...rest] = optionLists as SampleTypeOption[][];
    return first.filter((option) =>
      rest.every((options) => options.some((candidate) => candidate.id === option.id)),
    );
  }, [catalogs, lines, operation]);

  const updateLine = (index: number, patch: Partial<PlanLine>) => {
    setLines((current) =>
      current.map((line, lineIndex) =>
        lineIndex === index ? { ...line, ...patch } : line,
      ),
    );
  };

  const toPayload = (list: PlanLine[]) =>
    list
      .filter((line) => line.source_sample_id.trim())
      .map((line) => {
        const numberOrUndefined = (value: number | '' | undefined) =>
          value === '' || value === undefined ? undefined : Number(value);
        return {
          line_id: line.line_id,
          source_sample_id: line.source_sample_id.trim(),
          source_container_id: line.source_container_id?.trim() || undefined,
          volume: numberOrUndefined(line.volume),
          target_amount: numberOrUndefined(line.target_amount),
          target_volume: numberOrUndefined(line.target_volume),
          target_concentration: numberOrUndefined(line.target_concentration),
          split_count: numberOrUndefined(line.split_count),
          dest_container_type_id: line.dest_container_type_id?.trim() || undefined,
          dest_container_name: line.dest_container_name?.trim() || undefined,
          dest_sample_type: line.dest_sample_type?.trim() || null,
          inherit_entry_dest_sample_type: line.inherit_entry_dest_sample_type,
          pool_group: operation === 'pool' ? line.pool_group?.trim() || undefined : undefined,
        };
      });

  const saveCurrentPlan = async (): Promise<AliquotPlanSaveResult> =>
    apiService.saveAliquotPlan(entryId, {
      method,
      default_dest_sample_type: defaultDestSampleType || null,
      lines: toPayload(lines),
    }) as Promise<AliquotPlanSaveResult>;

  const handleSave = async () => {
    if (mixedPoolMessages.size > 0) {
      setError(Array.from(mixedPoolMessages.values()).join(' '));
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const response = await saveCurrentPlan();
      setSuccess(`Saved ${response.line_count} plan line(s)`);
      await load();
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to save plan'));
    } finally {
      setSaving(false);
    }
  };

  const handleExecute = async (dryRun: boolean) => {
    if (mixedPoolMessages.size > 0) {
      setError(Array.from(mixedPoolMessages.values()).join(' '));
      return;
    }
    if (toPayload(lines).length === 0) {
      setError('Add at least one plan line with a source sample');
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await saveCurrentPlan();
      const response = (await apiService.executeAliquotPlan(entryId, {
        dry_run: dryRun,
      })) as AliquotPlanExecuteResult;
      setSuccess(
        `${dryRun ? 'Dry-run' : 'Execute'}: ${response.success_count} ok, ${
          response.error_count
        } error(s)`,
      );
      if (!dryRun) await load();
    } catch (err) {
      setError(apiErrorMsg(err, dryRun ? 'Dry-run failed' : 'Execute failed'));
    } finally {
      setSaving(false);
    }
  };

  const changeMethod = (nextMethod: AliquotMethod) => {
    const nextOperation = methodDefinition(nextMethod).operation;
    setMethod(nextMethod);
    setDefaultDestSampleType('');
    setLines((current) =>
      current.map((line) => ({
        ...line,
        dest_sample_type: '',
        inherit_entry_dest_sample_type: true,
        pool_group: nextOperation === 'pool' ? line.pool_group || 'pool-1' : '',
      })),
    );
  };

  if (loading) {
    return (
      <Box py={2} display="flex" justifyContent="center">
        <CircularProgress size={28} />
      </Box>
    );
  }

  const selectedSourceCount = new Set(
    lines.map((line) => line.source_sample_id.trim()).filter(Boolean),
  ).size;
  const catalogsLoading = requiredCatalogKey
    .split('|')
    .filter(Boolean)
    .some((key) => catalogs[key]?.loading);
  const defaultDisabled =
    !canEdit ||
    selectedSourceCount === 0 ||
    catalogsLoading ||
    mixedPoolMessages.size > 0;

  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="subtitle1" gutterBottom>
        Aliquot / pool plan
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        The entry method controls one mint operation and all line inputs. Destination type is a
        separate default that each line may inherit, clear to Same as parent, or override.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 1 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 1 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}
      {Array.from(mixedPoolMessages.values()).map((message) => (
        <Alert key={message} severity="warning" sx={{ mb: 1 }}>
          {message}
        </Alert>
      ))}

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1.5 }}>
        <FormControl
          size="small"
          sx={{ minWidth: 310 }}
          disabled={!canEdit || persistedLineCount > 0}
        >
          <InputLabel>Method</InputLabel>
          <Select
            label="Method"
            value={method}
            inputProps={{ 'aria-label': 'Aliquot or pool method' }}
            onChange={(event) => changeMethod(event.target.value as AliquotMethod)}
          >
            {METHODS.map((candidate) => (
              <MenuItem key={candidate.value} value={candidate.value}>
                {candidate.label}
              </MenuItem>
            ))}
          </Select>
          {persistedLineCount > 0 && (
            <FormHelperText>
              Method is locked after lines exist. Cancel the experiment to change it.
            </FormHelperText>
          )}
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 230 }} disabled={defaultDisabled}>
          <InputLabel>Default dest sample type</InputLabel>
          <Select
            label="Default dest sample type"
            value={defaultDestSampleType}
            inputProps={{ 'aria-label': 'Default dest sample type' }}
            onChange={(event) => setDefaultDestSampleType(event.target.value as string)}
          >
            <MenuItem value="">Same as parent.</MenuItem>
            {defaultOptions.map((option) => (
              <MenuItem key={option.id} value={option.id}>
                {option.name}
              </MenuItem>
            ))}
          </Select>
          {selectedSourceCount === 0 && (
            <FormHelperText>Select a source sample to load catalog options.</FormHelperText>
          )}
        </FormControl>
      </Box>

      {method === 'aliquot_by_target_concentration' && (
        <Alert severity="info" sx={{ mb: 1 }}>
          Normalization reads the source sample&apos;s prior concentration result. Concentration
          cannot be typed into this plan.
        </Alert>
      )}

      <TableContainer component={Paper} variant="outlined" sx={{ mb: 1, overflowX: 'auto' }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Source sample</TableCell>
              <TableCell>Dest sample type override</TableCell>
              <TableCell>Source container</TableCell>
              <TableCell>Method inputs</TableCell>
              <TableCell>Destination</TableCell>
              <TableCell width={48} />
            </TableRow>
          </TableHead>
          <TableBody>
            {lines.map((line, index) => {
              const sourceSampleId = line.source_sample_id.trim();
              const catalog = sourceSampleId
                ? catalogs[catalogKey(sourceSampleId, operation)]
                : undefined;
              const poolGroup = line.pool_group?.trim();
              const mixedPoolMessage =
                operation === 'pool' && poolGroup
                  ? mixedPoolMessages.get(poolGroup)
                  : undefined;
              const destTypeDisabled =
                !canEdit ||
                !sourceSampleId ||
                !catalog ||
                catalog.loading ||
                Boolean(catalog.error) ||
                Boolean(mixedPoolMessage);
              const destValue = line.inherit_entry_dest_sample_type
                ? ENTRY_DEFAULT
                : line.dest_sample_type || SAME_AS_PARENT;
              return (
                <TableRow key={line.line_id || index}>
                  <TableCell>
                    <FormControl size="small" sx={{ minWidth: 180 }} disabled={!canEdit}>
                      <Select
                        displayEmpty
                        value={line.source_sample_id}
                        inputProps={{ 'aria-label': `Source sample, line ${index + 1}` }}
                        onChange={(event) =>
                          updateLine(index, {
                            source_sample_id: event.target.value as string,
                            dest_sample_type: '',
                            inherit_entry_dest_sample_type: true,
                          })
                        }
                      >
                        <MenuItem value="">
                          <em>Select…</em>
                        </MenuItem>
                        {sampleIds.map((sampleId) => (
                          <MenuItem key={sampleId} value={sampleId}>
                            {sampleId.slice(0, 8)}…
                          </MenuItem>
                        ))}
                      </Select>
                      {sampleIds.length === 0 && (
                        <FormHelperText>No experiment cohort samples available.</FormHelperText>
                      )}
                    </FormControl>
                  </TableCell>
                  <TableCell>
                    <FormControl
                      size="small"
                      sx={{ minWidth: 210 }}
                      disabled={destTypeDisabled}
                      error={Boolean(catalog?.error || mixedPoolMessage)}
                    >
                      <InputLabel>Dest sample type</InputLabel>
                      <Select
                        label="Dest sample type"
                        inputProps={{
                          'aria-label': `Dest sample type, line ${index + 1}`,
                        }}
                        value={destValue}
                        onChange={(event) => {
                          const value = event.target.value as string;
                          if (value === ENTRY_DEFAULT) {
                            updateLine(index, {
                              inherit_entry_dest_sample_type: true,
                              dest_sample_type: '',
                            });
                          } else if (value === SAME_AS_PARENT) {
                            updateLine(index, {
                              inherit_entry_dest_sample_type: false,
                              dest_sample_type: '',
                            });
                          } else {
                            updateLine(index, {
                              inherit_entry_dest_sample_type: false,
                              dest_sample_type: value,
                            });
                          }
                        }}
                      >
                        <MenuItem value={ENTRY_DEFAULT}>Use entry default</MenuItem>
                        <MenuItem value={SAME_AS_PARENT}>Same as parent.</MenuItem>
                        {(catalog?.data?.options || []).map((option) => (
                          <MenuItem key={option.id} value={option.id}>
                            {option.name}
                          </MenuItem>
                        ))}
                      </Select>
                      {catalog?.loading && (
                        <FormHelperText>Loading allowed types…</FormHelperText>
                      )}
                      {!sourceSampleId && (
                        <FormHelperText>Select a source sample first.</FormHelperText>
                      )}
                      {catalog?.error && <FormHelperText>{catalog.error}</FormHelperText>}
                      {mixedPoolMessage && (
                        <FormHelperText>Mixed source types cannot be pooled.</FormHelperText>
                      )}
                    </FormControl>
                  </TableCell>
                  <TableCell>
                    <TextField
                      size="small"
                      placeholder="Optional container UUID"
                      value={line.source_container_id || ''}
                      disabled={!canEdit}
                      onChange={(event) =>
                        updateLine(index, { source_container_id: event.target.value })
                      }
                      sx={{ minWidth: 160 }}
                    />
                  </TableCell>
                  <TableCell>
                    <Box display="flex" gap={0.5} flexWrap="wrap">
                      {methodConfig.fields.map((field) => (
                        <TextField
                          key={field}
                          size="small"
                          type="number"
                          label={field.replace(/_/g, ' ')}
                          value={line[field] ?? ''}
                          disabled={!canEdit}
                          inputProps={field === 'split_count' ? { min: 2, step: 1 } : { min: 0 }}
                          onChange={(event) =>
                            updateLine(index, {
                              [field]:
                                event.target.value === '' ? '' : Number(event.target.value),
                            })
                          }
                          sx={{ width: 125 }}
                        />
                      ))}
                      {methodConfig.fields.length === 0 && (
                        <Typography variant="body2" color="text.secondary">
                          Uses all remaining tracked amount.
                        </Typography>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Box display="flex" flexDirection="column" gap={0.5}>
                      <TextField
                        size="small"
                        placeholder="Dest container name"
                        value={line.dest_container_name || ''}
                        disabled={!canEdit}
                        onChange={(event) =>
                          updateLine(index, { dest_container_name: event.target.value })
                        }
                      />
                      {operation === 'pool' && (
                        <TextField
                          size="small"
                          required
                          label="Pool group"
                          value={line.pool_group || ''}
                          disabled={!canEdit}
                          onChange={(event) =>
                            updateLine(index, {
                              pool_group: event.target.value,
                              dest_sample_type: '',
                              inherit_entry_dest_sample_type: true,
                            })
                          }
                        />
                      )}
                      <TextField
                        size="small"
                        placeholder="Dest container type UUID"
                        value={line.dest_container_type_id || ''}
                        disabled={!canEdit}
                        onChange={(event) =>
                          updateLine(index, { dest_container_type_id: event.target.value })
                        }
                      />
                    </Box>
                  </TableCell>
                  <TableCell>
                    {canEdit && (
                      <IconButton
                        size="small"
                        color="error"
                        aria-label={`Delete line ${index + 1}`}
                        onClick={() =>
                          setLines((current) =>
                            current.filter((_, lineIndex) => lineIndex !== index),
                          )
                        }
                        disabled={lines.length <= 1}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>

      {canEdit && (
        <Box display="flex" gap={1} flexWrap="wrap">
          <Button
            size="small"
            startIcon={<AddIcon />}
            onClick={() => setLines((current) => [...current, blankLine(operation)])}
          >
            Add line
          </Button>
          <Button
            size="small"
            variant="outlined"
            disabled={saving}
            onClick={() => void handleSave()}
          >
            {saving ? 'Saving…' : 'Save plan'}
          </Button>
          <Button
            size="small"
            variant="outlined"
            startIcon={<ScienceIcon />}
            disabled={saving}
            onClick={() => void handleExecute(true)}
          >
            Dry-run
          </Button>
          <Button
            size="small"
            variant="contained"
            color="warning"
            startIcon={
              saving ? <CircularProgress size={14} color="inherit" /> : <PlayArrowIcon />
            }
            disabled={saving}
            onClick={() => void handleExecute(false)}
          >
            Execute
          </Button>
        </Box>
      )}
    </Box>
  );
};

export default AliquotPlanEditor;
