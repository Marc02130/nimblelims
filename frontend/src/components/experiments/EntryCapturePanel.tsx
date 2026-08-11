/**
 * Entry capture UI for an Experiment (P0 foundation).
 * Kinds: experiment_sample_data | experiment_data | predefined_action | display_table
 * (legacy sample_data / experiment_detail still accepted).
 * Save = entry values only; Submit = mark complete + Sample write-back.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
  Paper,
  Tooltip,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SaveIcon from '@mui/icons-material/Save';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import RefreshIcon from '@mui/icons-material/Refresh';
import PlaylistAddIcon from '@mui/icons-material/PlaylistAdd';
import SyncAltIcon from '@mui/icons-material/SyncAlt';
import { apiService } from '../../services/apiService';

const apiErrorMsg = (err: any, fallback: string): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) return detail[0]?.msg || fallback;
  return fallback;
};

interface FieldLink {
  field_definition_id: string;
  sort_order: number;
  visible: boolean;
  write_back_target?: string | null;
}

interface EntryValue {
  id: string;
  field_definition_id: string;
  sample_id?: string | null;
  value_text?: string | null;
  value_number?: number | null;
  value_list_entry_id?: string | null;
  value_date?: string | null;
  value_boolean?: boolean | null;
  value_json?: unknown;
  write_back_at?: string | null;
  write_back_previous?: { column?: string; value?: unknown } | null;
}

interface Entry {
  id: string;
  experiment_id: string;
  entry_type: string;
  name: string;
  description?: string | null;
  predefined_entry_key?: string | null;
  sort_order: number;
  active: boolean;
  config?: { status?: string; submitted_at?: string; sample_columns?: string[] } | null;
  field_definition_links: FieldLink[];
  values: EntryValue[];
}

/** Canonical + legacy aliases for sample-oriented rows (one per experiment sample). */
const isSampleScoped = (entryType: string) =>
  entryType === 'experiment_sample_data' || entryType === 'sample_data';

/** Experiment-level / purpose table (rows not auto from full cohort). */
const isExperimentScoped = (entryType: string) =>
  entryType === 'experiment_data' || entryType === 'experiment_detail';

const isWritableEntry = (entryType: string) =>
  isSampleScoped(entryType) || isExperimentScoped(entryType) || entryType === 'predefined_action';

const typeLabel = (entryType: string): string => {
  if (entryType === 'sample_data') return 'experiment_sample_data';
  if (entryType === 'experiment_detail') return 'experiment_data';
  return entryType;
};

interface FieldDef {
  id: string;
  name: string;
  display_name?: string | null;
  data_type: string;
  source_list_id?: string | null;
  is_required?: boolean;
}

interface ListOption {
  id: string;
  name: string;
}

interface SampleExecution {
  sample_id: string;
  replicate_number?: number;
}

export interface EntryCapturePanelProps {
  experimentId: string;
  sampleExecutions?: SampleExecution[];
  canEdit?: boolean;
}

type DraftKey = string; // `${fieldId}::${sampleId || ''}`

const draftKey = (fieldId: string, sampleId?: string | null) =>
  `${fieldId}::${sampleId || ''}`;

const TYPE_COLORS: Record<string, 'default' | 'primary' | 'secondary' | 'info' | 'warning' | 'success'> = {
  experiment_sample_data: 'primary',
  experiment_data: 'info',
  sample_data: 'primary',
  experiment_detail: 'info',
  predefined_action: 'warning',
  display_table: 'default',
};

const EntryCapturePanel: React.FC<EntryCapturePanelProps> = ({
  experimentId,
  sampleExecutions = [],
  canEdit = true,
}) => {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [fieldMap, setFieldMap] = useState<Record<string, FieldDef>>({});
  const [listOptions, setListOptions] = useState<Record<string, ListOption[]>>({}); // by field_definition_id
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<DraftKey, any>>({});
  const [dirty, setDirty] = useState<Record<string, boolean>>({}); // entry_id
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [instantiating, setInstantiating] = useState(false);

  const sampleIds = useMemo(
    () => Array.from(new Set(sampleExecutions.map((s) => s.sample_id).filter(Boolean))),
    [sampleExecutions],
  );

  const valueFromRow = (v: EntryValue | undefined, dataType: string): any => {
    if (!v) return dataType === 'boolean' ? false : '';
    switch (dataType) {
      case 'number':
        return v.value_number ?? '';
      case 'boolean':
        return Boolean(v.value_boolean);
      case 'list':
      case 'lookup':
        return v.value_list_entry_id ?? '';
      case 'date':
        return v.value_date ? String(v.value_date).slice(0, 10) : '';
      default:
        return v.value_text ?? '';
    }
  };

  const buildDraftsFromEntries = (list: Entry[], fmap: Record<string, FieldDef>) => {
    const next: Record<DraftKey, any> = {};
    for (const entry of list) {
      const links = (entry.field_definition_links || [])
        .filter((l) => l.visible !== false)
        .sort((a, b) => a.sort_order - b.sort_order);
      for (const link of links) {
        const fd = fmap[link.field_definition_id];
        const dt = fd?.data_type || 'text';
        if (isSampleScoped(entry.entry_type)) {
          for (const sid of sampleIds) {
            const existing = (entry.values || []).find(
              (v) => v.field_definition_id === link.field_definition_id && v.sample_id === sid,
            );
            next[draftKey(link.field_definition_id, sid)] = valueFromRow(existing, dt);
          }
        } else {
          const existing = (entry.values || []).find(
            (v) => v.field_definition_id === link.field_definition_id && !v.sample_id,
          );
          next[draftKey(link.field_definition_id)] = valueFromRow(existing, dt);
        }
      }
    }
    setDrafts(next);
    setDirty({});
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [entriesRes, fieldsRes, listsRes] = await Promise.all([
        apiService.getExperimentEntries(experimentId, {
          active: true,
          include_values: true,
        }),
        apiService.getFieldDefinitions({ active: true, page: 1, size: 200 }),
        apiService.getLists().catch(() => []),
      ]);

      const entryList: Entry[] = entriesRes?.entries ?? [];
      const fieldItems: FieldDef[] = fieldsRes?.items ?? fieldsRes?.field_definitions ?? [];
      const fmap: Record<string, FieldDef> = {};
      for (const f of fieldItems) fmap[f.id] = f;

      // Fetch any missing field defs by id
      const neededIds = new Set<string>();
      for (const e of entryList) {
        for (const l of e.field_definition_links || []) {
          neededIds.add(l.field_definition_id);
        }
      }
      for (const fid of neededIds) {
        if (!fmap[fid]) {
          try {
            const one = await apiService.getFieldDefinition(fid);
            fmap[fid] = one;
          } catch {
            // ignore missing
          }
        }
      }
      setFieldMap(fmap);

      // Resolve list options for list/lookup fields (getLists includes nested entries)
      const lists: Array<{ id: string; name: string; entries?: ListOption[] }> = Array.isArray(
        listsRes,
      )
        ? listsRes
        : listsRes?.lists ?? [];
      const entriesByListId: Record<string, ListOption[]> = {};
      for (const l of lists) {
        entriesByListId[l.id] = (l.entries || []).map((o: any) => ({
          id: o.id,
          name: o.name,
        }));
      }

      const optionsByField: Record<string, ListOption[]> = {};
      for (const fid of neededIds) {
        const fd = fmap[fid];
        if (!fd || !['list', 'lookup'].includes(fd.data_type) || !fd.source_list_id) continue;
        optionsByField[fid] = entriesByListId[fd.source_list_id] || [];
      }
      setListOptions(optionsByField);
      setEntries(entryList.sort((a, b) => a.sort_order - b.sort_order));
      buildDraftsFromEntries(entryList, fmap);
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to load entries'));
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }, [experimentId, sampleIds.join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    load();
  }, [load]);

  const setDraft = (entryId: string, fieldId: string, sampleId: string | null | undefined, val: any) => {
    const key = draftKey(fieldId, sampleId);
    setDrafts((d) => ({ ...d, [key]: val }));
    setDirty((x) => ({ ...x, [entryId]: true }));
  };

  const toUpsertPayload = (
    fieldId: string,
    dataType: string,
    raw: any,
    sampleId?: string | null,
  ) => {
    // Save path: entry values only — write-back runs on submit
    const base: any = {
      field_definition_id: fieldId,
      apply_write_back: false,
    };
    if (sampleId) base.sample_id = sampleId;

    if (raw === '' || raw === undefined || raw === null) {
      // clear typed columns
      base.value_text = null;
      base.value_number = null;
      base.value_list_entry_id = null;
      base.value_date = null;
      base.value_boolean = null;
      return base;
    }

    switch (dataType) {
      case 'number':
        base.value_number = Number(raw);
        break;
      case 'boolean':
        base.value_boolean = Boolean(raw);
        break;
      case 'list':
      case 'lookup':
        base.value_list_entry_id = raw;
        break;
      case 'date':
        base.value_date = raw; // YYYY-MM-DD
        break;
      default:
        base.value_text = String(raw);
    }
    return base;
  };

  const saveEntry = async (entry: Entry) => {
    setSaving((s) => ({ ...s, [entry.id]: true }));
    setError(null);
    setSuccess(null);
    try {
      const links = (entry.field_definition_links || []).filter((l) => l.visible !== false);
      const values: any[] = [];

      if (isSampleScoped(entry.entry_type)) {
        if (sampleIds.length === 0) {
          setError(
            'Select samples for this experiment (queue at start / sample executions) before capturing sample data.',
          );
          return;
        }
        for (const link of links) {
          const fd = fieldMap[link.field_definition_id];
          const dt = fd?.data_type || 'text';
          for (const sid of sampleIds) {
            const key = draftKey(link.field_definition_id, sid);
            values.push(toUpsertPayload(link.field_definition_id, dt, drafts[key], sid));
          }
        }
      } else if (isExperimentScoped(entry.entry_type) || entry.entry_type === 'predefined_action') {
        for (const link of links) {
          const fd = fieldMap[link.field_definition_id];
          const dt = fd?.data_type || 'text';
          const key = draftKey(link.field_definition_id);
          values.push(toUpsertPayload(link.field_definition_id, dt, drafts[key]));
        }
      } else {
        // display_table is read-only
        return;
      }

      if (values.length === 0) {
        setError('No fields to save on this entry.');
        return;
      }

      await apiService.upsertEntryValues(entry.id, values);
      setDirty((d) => ({ ...d, [entry.id]: false }));
      setSuccess(`Saved “${entry.name}” (draft — use Submit to write back to samples)`);
      await load();
    } catch (err) {
      setError(apiErrorMsg(err, `Failed to save ${entry.name}`));
    } finally {
      setSaving((s) => ({ ...s, [entry.id]: false }));
    }
  };

  const submitEntry = async (entry: Entry) => {
    setSaving((s) => ({ ...s, [entry.id]: true }));
    setError(null);
    setSuccess(null);
    try {
      // Persist unsaved drafts first (still no write-back until submit)
      if (dirty[entry.id] && isWritableEntry(entry.entry_type)) {
        const links = (entry.field_definition_links || []).filter((l) => l.visible !== false);
        const values: any[] = [];
        if (isSampleScoped(entry.entry_type)) {
          for (const link of links) {
            const fd = fieldMap[link.field_definition_id];
            const dt = fd?.data_type || 'text';
            for (const sid of sampleIds) {
              values.push(
                toUpsertPayload(
                  link.field_definition_id,
                  dt,
                  drafts[draftKey(link.field_definition_id, sid)],
                  sid,
                ),
              );
            }
          }
        } else {
          for (const link of links) {
            const fd = fieldMap[link.field_definition_id];
            const dt = fd?.data_type || 'text';
            values.push(
              toUpsertPayload(
                link.field_definition_id,
                dt,
                drafts[draftKey(link.field_definition_id)],
              ),
            );
          }
        }
        if (values.length > 0) {
          await apiService.upsertEntryValues(entry.id, values);
        }
      }

      const res: any = await apiService.submitEntry(entry.id);
      const n = res?.write_backs_applied ?? 0;
      setDirty((d) => ({ ...d, [entry.id]: false }));
      setSuccess(
        n > 0
          ? `Submitted “${entry.name}” (${n} sample write-back${n === 1 ? '' : 's'})`
          : `Submitted “${entry.name}”`,
      );
      await load();
    } catch (err) {
      setError(apiErrorMsg(err, `Failed to submit ${entry.name}`));
    } finally {
      setSaving((s) => ({ ...s, [entry.id]: false }));
    }
  };

  const handleInstantiate = async () => {
    setInstantiating(true);
    setError(null);
    try {
      const res: any = await apiService.instantiateExperimentEntries(experimentId, {
        skip_if_exists: true,
      });
      const n = res?.total ?? res?.entries?.length ?? 0;
      setSuccess(
        n > 0
          ? `Entries ready (${n})`
          : 'No entries declared on the template (template_definition.entries is empty)',
      );
      await load();
    } catch (err) {
      setError(apiErrorMsg(err, 'Failed to instantiate entries from template'));
    } finally {
      setInstantiating(false);
    }
  };

  const renderFieldInput = (
    entry: Entry,
    link: FieldLink,
    sampleId?: string | null,
  ) => {
    const fd = fieldMap[link.field_definition_id];
    const label = fd?.display_name || fd?.name || link.field_definition_id.slice(0, 8);
    const dt = fd?.data_type || 'text';
    const key = draftKey(link.field_definition_id, sampleId);
    const val = drafts[key];
    const readOnly = !canEdit || entry.entry_type === 'display_table';
    const writeBack = link.write_back_target;

    const existing = (entry.values || []).find(
      (v) =>
        v.field_definition_id === link.field_definition_id &&
        (sampleId ? v.sample_id === sampleId : !v.sample_id),
    );

    const adornment = writeBack ? (
      <Tooltip
        title={
          existing?.write_back_at
            ? `Last write-back to Sample.${writeBack} at ${new Date(existing.write_back_at).toLocaleString()}`
            : `Writes back to Sample.${writeBack} on Submit (not Save)`
        }
      >
        <SyncAltIcon fontSize="small" color="action" sx={{ ml: 0.5 }} />
      </Tooltip>
    ) : null;

    if (dt === 'boolean') {
      return (
        <Box key={key} display="flex" alignItems="center" gap={0.5}>
          <FormControlLabel
            control={
              <Switch
                checked={Boolean(val)}
                disabled={readOnly}
                onChange={(e) => setDraft(entry.id, link.field_definition_id, sampleId, e.target.checked)}
              />
            }
            label={label}
          />
          {adornment}
        </Box>
      );
    }

    if (dt === 'list' || dt === 'lookup') {
      const opts = listOptions[link.field_definition_id] || [];
      return (
        <FormControl key={key} fullWidth size="small" margin="dense" disabled={readOnly}>
          <InputLabel>
            {label}
            {writeBack ? ' ⇄' : ''}
          </InputLabel>
          <Select
            label={`${label}${writeBack ? ' ⇄' : ''}`}
            value={val || ''}
            onChange={(e) => setDraft(entry.id, link.field_definition_id, sampleId, e.target.value)}
          >
            <MenuItem value="">
              <em>—</em>
            </MenuItem>
            {opts.map((o) => (
              <MenuItem key={o.id} value={o.id}>
                {o.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      );
    }

    return (
      <TextField
        key={key}
        fullWidth
        size="small"
        margin="dense"
        label={label}
        type={dt === 'number' ? 'number' : dt === 'date' ? 'date' : 'text'}
        InputLabelProps={dt === 'date' ? { shrink: true } : undefined}
        value={val ?? ''}
        disabled={readOnly}
        onChange={(e) =>
          setDraft(
            entry.id,
            link.field_definition_id,
            sampleId,
            dt === 'number' ? e.target.value : e.target.value,
          )
        }
        InputProps={{
          endAdornment: adornment,
        }}
      />
    );
  };

  if (loading) {
    return (
      <Box sx={{ py: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} flexWrap="wrap" gap={1}>
        <Typography variant="h6">Entries</Typography>
        <Box display="flex" gap={1}>
          <Button size="small" startIcon={<RefreshIcon />} onClick={() => load()}>
            Refresh
          </Button>
          {canEdit && (
            <Button
              size="small"
              variant="outlined"
              startIcon={<PlaylistAddIcon />}
              disabled={instantiating}
              onClick={handleInstantiate}
            >
              {instantiating ? 'Instantiating…' : 'Instantiate from template'}
            </Button>
          )}
        </Box>
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Structured data capture for this experiment. Sample-oriented entries use the experiment
        cohort (queue at start / sample executions). <strong>Save</strong> stores draft values only;{' '}
        <strong>Submit</strong> completes the entry and applies Sample write-backs (⇄, last write
        wins). You can edit again after submit until the experiment is done.
      </Typography>

      {entries.length === 0 ? (
        <Alert severity="info">
          No entries yet. If the experiment template defines{' '}
          <code>template_definition.entries</code>, use <strong>Instantiate from template</strong>.
          You can also add entries via the API.
        </Alert>
      ) : (
        entries.map((entry) => {
          const links = (entry.field_definition_links || [])
            .filter((l) => l.visible !== false)
            .sort((a, b) => a.sort_order - b.sort_order);
          const isDirty = Boolean(dirty[entry.id]);
          const isSaving = Boolean(saving[entry.id]);
          const entryStatus = entry.config?.status || 'draft';
          const isSubmitted = entryStatus === 'submitted';

          return (
            <Accordion key={entry.id} defaultExpanded={entries.length <= 3}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
                  <Typography fontWeight={600}>{entry.name}</Typography>
                  <Chip
                    size="small"
                    label={typeLabel(entry.entry_type)}
                    color={TYPE_COLORS[entry.entry_type] || 'default'}
                  />
                  {entry.predefined_entry_key && (
                    <Chip size="small" variant="outlined" label={entry.predefined_entry_key} />
                  )}
                  <Chip
                    size="small"
                    variant="outlined"
                    color={isSubmitted ? 'success' : 'default'}
                    label={isSubmitted ? 'Submitted' : 'Draft'}
                  />
                  {isDirty && <Chip size="small" color="warning" label="Unsaved" />}
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                {entry.description && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    {entry.description}
                  </Typography>
                )}

                {entry.entry_type === 'display_table' && (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Read-only display entry.
                  </Typography>
                )}

                {entry.entry_type === 'predefined_action' && (
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Predefined action <strong>{entry.predefined_entry_key || entry.name}</strong>.
                    Configurable parameters (if any) can be saved below. Full action execution is a
                    later phase.
                  </Alert>
                )}

                {isSampleScoped(entry.entry_type) ? (
                  sampleIds.length === 0 ? (
                    <Alert severity="warning">
                      No samples on this experiment yet. Select the cohort at start (queue / scan),
                      then capture per-sample data here.
                    </Alert>
                  ) : links.length === 0 ? (
                    <Typography color="text.secondary">No fields configured on this entry.</Typography>
                  ) : (
                    <TableContainer component={Paper} variant="outlined">
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell>Sample</TableCell>
                            {links.map((link) => {
                              const fd = fieldMap[link.field_definition_id];
                              return (
                                <TableCell key={link.field_definition_id}>
                                  {fd?.display_name || fd?.name || 'Field'}
                                  {link.write_back_target && (
                                    <Tooltip
                                      title={`Write-back on Submit: Sample.${link.write_back_target}`}
                                    >
                                      <SyncAltIcon
                                        sx={{ fontSize: 14, ml: 0.5, verticalAlign: 'middle' }}
                                      />
                                    </Tooltip>
                                  )}
                                </TableCell>
                              );
                            })}
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {sampleIds.map((sid) => (
                            <TableRow key={sid}>
                              <TableCell>
                                <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                                  {sid.slice(0, 8)}…
                                </Typography>
                              </TableCell>
                              {links.map((link) => (
                                <TableCell
                                  key={`${sid}-${link.field_definition_id}`}
                                  sx={{ minWidth: 140 }}
                                >
                                  {renderFieldInput(entry, link, sid)}
                                </TableCell>
                              ))}
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  )
                ) : links.length === 0 ? (
                  <Typography color="text.secondary">No fields configured on this entry.</Typography>
                ) : (
                  <Box display="flex" flexDirection="column" gap={0.5} maxWidth={480}>
                    {links.map((link) => renderFieldInput(entry, link))}
                  </Box>
                )}

                {canEdit && isWritableEntry(entry.entry_type) && links.length > 0 && (
                  <Box mt={2} display="flex" gap={1} flexWrap="wrap">
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={
                        isSaving ? <CircularProgress size={16} color="inherit" /> : <SaveIcon />
                      }
                      disabled={isSaving || (!isDirty && !isSampleScoped(entry.entry_type))}
                      onClick={() => saveEntry(entry)}
                    >
                      {isSaving ? 'Saving…' : 'Save'}
                    </Button>
                    <Button
                      variant="contained"
                      size="small"
                      color="success"
                      startIcon={
                        isSaving ? (
                          <CircularProgress size={16} color="inherit" />
                        ) : (
                          <CheckCircleOutlineIcon />
                        )
                      }
                      disabled={isSaving}
                      onClick={() => submitEntry(entry)}
                    >
                      {isSubmitted ? 'Re-submit' : 'Submit'}
                    </Button>
                  </Box>
                )}
              </AccordionDetails>
            </Accordion>
          );
        })
      )}
    </Box>
  );
};

export default EntryCapturePanel;
