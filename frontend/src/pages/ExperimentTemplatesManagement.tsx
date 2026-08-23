import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  TextField,
  Chip,
  FormControlLabel,
  Switch,
  Tab,
  Tabs,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import { Add, Edit, Delete, Upload } from '@mui/icons-material';
import LinearProgress from '@mui/material/LinearProgress';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../contexts/UserContext';
import { apiService } from '../services/apiService';
import { FillHeightPage, FillHeightTable } from '../components/common/FillHeightPage';

const apiErrorMsg = (err: any, fallback: string): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) return detail[0]?.msg || fallback;
  return fallback;
};

// ─── Types ────────────────────────────────────────────────────────────────────

/** Declared on template_definition.entries — instantiated on experiment create. */
interface TemplateEntryField {
  field_definition_id: string;
  sort_order?: number;
  visible?: boolean;
  write_back_target?: string | null;
}

interface TemplateEntryDeclaration {
  entry_type:
    | 'experiment_sample_data'
    | 'experiment_data'
    | 'predefined_action'
    | 'display_table'
    | 'sample_data'
    | 'experiment_detail';
  name: string;
  description?: string;
  predefined_entry_key?: string;
  sort_order?: number;
  /** Names or predefined keys that must be submitted before this entry */
  depends_on?: string[];
  config?: {
    sample_columns?: string[];
    status?: string;
    depends_on?: string[];
    [key: string]: unknown;
  };
  fields?: TemplateEntryField[];
}

interface FieldDefOption {
  id: string;
  name: string;
  display_name?: string | null;
  data_type: string;
  entity_type?: string;
}

const ENTRY_TYPE_OPTIONS: {
  value: TemplateEntryDeclaration['entry_type'];
  label: string;
  helper: string;
}[] = [
  {
    value: 'experiment_sample_data',
    label: 'Experiment sample data',
    helper: 'Table: one row per sample in the experiment cohort',
  },
  {
    value: 'experiment_data',
    label: 'Experiment data',
    helper: 'Table: multi-row free records (not a form)',
  },
  {
    value: 'predefined_action',
    label: 'Aliquot / pool (predefined)',
    helper: 'Plan + execute aliquot/pool (not FieldDefinition columns)',
  },
];

/** FieldDefinitions used as entry columns (not Custom Fields for Sample/Test tables). */
const ENTRY_FIELD_ENTITY_TYPES = {
  experiment_sample_data: 'experiment_sample_data',
  experiment_data: 'experiment_data',
  sample_data: 'experiment_sample_data',
  experiment_detail: 'experiment_data',
} as const;

const fieldEntityTypeForEntry = (entryType: string): string | null => {
  if (entryType === 'experiment_sample_data' || entryType === 'sample_data') {
    return ENTRY_FIELD_ENTITY_TYPES.experiment_sample_data;
  }
  if (entryType === 'experiment_data' || entryType === 'experiment_detail') {
    return ENTRY_FIELD_ENTITY_TYPES.experiment_data;
  }
  return null;
};

const SAMPLE_COLUMN_OPTIONS = [
  { key: 'client_sample_id', label: 'Client Sample ID' },
  { key: 'received_date', label: 'Received date' },
  { key: 'date_sampled', label: 'Date sampled' },
  { key: 'specimen_biotype_id', label: 'Biotype' },
  { key: 'sample_type', label: 'Sample type' },
  { key: 'status', label: 'Status' },
  { key: 'matrix', label: 'Matrix' },
  { key: 'temperature', label: 'Temperature' },
];

/** Config-eligible Sample columns for write-back on Submit only. */
const WRITE_BACK_TARGETS = [
  { value: '', label: 'None' },
  { value: 'specimen_biotype_id', label: 'Sample.specimen_biotype_id' },
  { value: 'temperature', label: 'Sample.temperature' },
  { value: 'due_date', label: 'Sample.due_date' },
  { value: 'report_date', label: 'Sample.report_date' },
];

const ALIQUOT_POOL_METHOD_OPTIONS = [
  { value: 'aliquot_by_volume', label: 'Aliquot — by volume' },
  { value: 'aliquot_by_target_amount', label: 'Aliquot — by target amount' },
  {
    value: 'aliquot_by_target_concentration',
    label: 'Aliquot — by target concentration (normalization)',
  },
  { value: 'aliquot_n_way_equal_split', label: 'Aliquot — N-way equal split' },
  { value: 'pool_by_volume_per_source', label: 'Pool — by volume per source' },
  { value: 'pool_equal_volume_each', label: 'Pool — equal volume from each' },
  {
    value: 'pool_by_target_amount_per_source',
    label: 'Pool — by target amount per source',
  },
  { value: 'pool_consolidate_remaining', label: 'Pool — consolidate remaining' },
] as const;

interface TemplateDefinition {
  experiment_name: string;
  description?: string;
  plate_layout?: '96-well' | '384-well' | null;
  acceptance_criteria?: string;
  /** Ordered capture places — the reusable template body (instantiated on experiment create). */
  entries?: TemplateEntryDeclaration[];
}

interface ExperimentTemplateRow {
  id: number;
  name: string;
  description?: string;
  active: boolean;
  template_definition: TemplateDefinition;
  custom_attributes?: Record<string, unknown>;
  created_at: string;
  modified_at?: string;
  created_by?: string;
  modified_by?: string;
  lifecycle_type?: 'standard' | 'cro';
}

// ─── Tab panel helper ─────────────────────────────────────────────────────────

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel({ children, value, index }: TabPanelProps) {
  return (
    <Box role="tabpanel" hidden={value !== index} sx={{ pt: 2 }}>
      {value === index && children}
    </Box>
  );
}

// ─── Blank form state ─────────────────────────────────────────────────────────

const blankEntry = (sortOrder = 0): TemplateEntryDeclaration => ({
  entry_type: 'experiment_sample_data',
  name: '',
  description: '',
  sort_order: sortOrder,
  config: { sample_columns: ['client_sample_id'] },
  fields: [],
});

const PREDEFINED_PRESETS: {
  key: string;
  label: string;
  entry: Omit<TemplateEntryDeclaration, 'sort_order'>;
}[] = [
  {
    key: 'experiment_header',
    label: 'Header',
    entry: {
      entry_type: 'experiment_data',
      name: 'Experiment header',
      description: 'Start context for the experiment',
      predefined_entry_key: 'experiment_header',
      fields: [],
    },
  },
  {
    key: 'samples',
    label: 'Samples',
    entry: {
      entry_type: 'experiment_sample_data',
      name: 'Samples',
      description: 'Cohort selected at experiment start (queue / scan)',
      predefined_entry_key: 'samples',
      config: {
        sample_columns: [
          'client_sample_id',
          'specimen_biotype_id',
          'received_date',
          'sample_type',
          'status',
        ],
      },
      fields: [],
    },
  },
  {
    key: 'aliquot_pool_plan',
    label: 'Aliquot/pool plan',
    entry: {
      entry_type: 'experiment_data',
      name: 'Aliquot / pool plan',
      description: 'Plan amounts; execute creates dest samples (methods in v1)',
      predefined_entry_key: 'aliquot_pool_plan',
      config: {
        method: 'aliquot_by_volume',
        default_dest_sample_type: null,
      },
      fields: [],
    },
  },
  {
    key: 'aliquots_pools',
    label: 'Aliquots/pools results',
    entry: {
      entry_type: 'experiment_sample_data',
      name: 'Aliquots / pools',
      description: 'Post-execute view of resulting samples',
      predefined_entry_key: 'aliquots_pools',
      config: {
        sample_columns: ['client_sample_id', 'sample_type'],
        minted_sample_ids: [],
        populated_after_execute: false,
      },
      fields: [],
    },
  },
];

/** New templates start with Header + Samples so create always yields a reusable entry spine. */
const defaultEntries = (): TemplateEntryDeclaration[] => [
  { ...PREDEFINED_PRESETS[0].entry, sort_order: 0 },
  { ...PREDEFINED_PRESETS[1].entry, sort_order: 1 },
];

const blankDefinition = (): TemplateDefinition => ({
  experiment_name: '',
  description: '',
  plate_layout: null,
  acceptance_criteria: '',
  entries: defaultEntries(),
});

// ─── Component ────────────────────────────────────────────────────────────────

const ExperimentTemplatesManagement: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const { hasPermission } = useUser();
  const canManage = hasPermission('experiment:manage');

  // List state
  const [rows, setRows] = useState<ExperimentTemplateRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create/Edit dialog state
  const [formOpen, setFormOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<ExperimentTemplateRow | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  /** Index 0 = Basic Info, 1 = Tables & forms */
  const [tabErrors, setTabErrors] = useState<boolean[]>([false, false]);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Form fields — outer
  const [formName, setFormName] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formActive, setFormActive] = useState(true);
  const [formLifecycleType, setFormLifecycleType] = useState<'standard' | 'cro'>('standard');

  // Form fields — template_definition
  const [formDef, setFormDef] = useState<TemplateDefinition>(blankDefinition());
  const [fieldDefOptions, setFieldDefOptions] = useState<FieldDefOption[]>([]);

  // Create FieldDefinition (entry columns — not Custom Fields for Sample/Test)
  const [createFieldOpen, setCreateFieldOpen] = useState(false);
  const [createFieldEntryIndex, setCreateFieldEntryIndex] = useState<number | null>(null);
  const [createFieldName, setCreateFieldName] = useState('');
  const [createFieldDisplay, setCreateFieldDisplay] = useState('');
  const [createFieldDataType, setCreateFieldDataType] = useState<
    'text' | 'number' | 'date' | 'boolean' | 'list'
  >('text');
  const [createFieldListId, setCreateFieldListId] = useState('');
  const [createFieldLists, setCreateFieldLists] = useState<{ id: string; name: string }[]>([]);
  const [createFieldSubmitting, setCreateFieldSubmitting] = useState(false);
  const [createFieldError, setCreateFieldError] = useState<string | null>(null);

  // Delete dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ExperimentTemplateRow | null>(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  // SOP upload dialog state
  const [sopUploadOpen, setSopUploadOpen] = useState(false);
  const [sopFile, setSopFile] = useState<File | null>(null);
  const [instrumentFile, setInstrumentFile] = useState<File | null>(null);
  const [sopUploadError, setSopUploadError] = useState<string | null>(null);
  const [sopJobId, setSopJobId] = useState<string | null>(null);
  // phase: 'idle' | 'uploading' | 'polling' | 'applying' | 'done' | 'timeout'
  const [sopPhase, setSopPhase] = useState<'idle' | 'uploading' | 'polling' | 'applying' | 'done' | 'timeout'>('idle');
  const [sopElapsedSeconds, setSopElapsedSeconds] = useState(0);
  const [sopFromExtraction, setSopFromExtraction] = useState(false);

  // ── Data loading ─────────────────────────────────────────────────────────

  const loadTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getExperimentTemplates();
      setRows(Array.isArray(data) ? data : (data?.templates ?? data?.items ?? []));
    } catch (err: unknown) {
      const e = err as { response?: { status?: number; data?: { detail?: string } }; message?: string };
      if (e.response?.status === 403) {
        setError('You do not have permission to view experiment templates.');
      } else {
        setError(apiErrorMsg(e, 'Failed to load experiment templates'));
      }
      setRows([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  const loadFieldDefinitions = async () => {
    try {
      // Entry column catalogs for both kinds (+ keep sample entity for future RO display if needed)
      const [esd, ed] = await Promise.all([
        apiService.getFieldDefinitions({
          entity_type: 'experiment_sample_data',
          active: true,
          page: 1,
          size: 200,
        }),
        apiService.getFieldDefinitions({
          entity_type: 'experiment_data',
          active: true,
          page: 1,
          size: 200,
        }),
      ]);
      const a: FieldDefOption[] = esd?.items ?? esd?.field_definitions ?? (Array.isArray(esd) ? esd : []);
      const b: FieldDefOption[] = ed?.items ?? ed?.field_definitions ?? (Array.isArray(ed) ? ed : []);
      const byId = new Map<string, FieldDefOption>();
      for (const f of [...a, ...b]) byId.set(f.id, f);
      setFieldDefOptions(Array.from(byId.values()));
    } catch {
      setFieldDefOptions([]);
    }
  };

  // ── Form helpers ─────────────────────────────────────────────────────────

  const openCreate = () => {
    setSelectedTemplate(null);
    setFormName('');
    setFormDescription('');
    setFormActive(true);
    setFormLifecycleType('standard');
    setFormDef(blankDefinition());
    setActiveTab(0);
    setTabErrors([false, false]);
    setFormError(null);
    setFormOpen(true);
    void loadFieldDefinitions();
  };

  const openEdit = (row: ExperimentTemplateRow) => {
    setSelectedTemplate(row);
    setFormName(row.name);
    setFormDescription(row.description ?? '');
    setFormActive(row.active);
    setFormLifecycleType(row.lifecycle_type ?? 'standard');
    const existingEntries = row.template_definition?.entries;
    setFormDef({
      experiment_name: row.template_definition?.experiment_name ?? '',
      description: row.template_definition?.description,
      plate_layout: (row.template_definition?.plate_layout as TemplateDefinition['plate_layout']) ?? null,
      acceptance_criteria: row.template_definition?.acceptance_criteria ?? '',
      // Prefer declared entries; empty legacy templates get the default spine for re-save
      entries:
        existingEntries && existingEntries.length > 0 ? existingEntries : defaultEntries(),
    });
    setActiveTab(existingEntries && existingEntries.length > 0 ? 1 : 0);
    setTabErrors([false, false]);
    setFormError(null);
    setFormOpen(true);
    void loadFieldDefinitions();
  };

  const validateForm = (): { valid: boolean; tabErrors: boolean[] } => {
    const errors = [false, false];
    if (!formName.trim() || !formDef.experiment_name.trim()) {
      errors[0] = true;
    }
    const entries = formDef.entries ?? [];
    if (entries.length === 0) {
      errors[1] = true;
    }
    for (const e of entries) {
      if (!e.name?.trim() || !e.entry_type) {
        errors[1] = true;
        break;
      }
    }
    return { valid: !errors.some(Boolean), tabErrors: errors };
  };

  // ── Entry (Tables & forms) helpers ───────────────────────────────────────

  const entriesList = formDef.entries ?? [];

  const setEntries = (entries: TemplateEntryDeclaration[]) => {
    setFormDef((d) => ({
      ...d,
      entries: entries.map((e, i) => ({ ...e, sort_order: e.sort_order ?? i })),
    }));
  };

  const addEntry = () => {
    setEntries([...entriesList, blankEntry(entriesList.length)]);
  };

  const updateEntry = (index: number, patch: Partial<TemplateEntryDeclaration>) => {
    const updated = entriesList.map((e, i) => (i === index ? { ...e, ...patch } : e));
    setEntries(updated);
  };

  const removeEntry = (index: number) => {
    setEntries(entriesList.filter((_, i) => i !== index));
  };

  const addEntryField = (entryIndex: number, fieldDefinitionId: string) => {
    if (!fieldDefinitionId) return;
    const entry = entriesList[entryIndex];
    const fields = [...(entry.fields || [])];
    if (fields.some((f) => f.field_definition_id === fieldDefinitionId)) return;
    fields.push({
      field_definition_id: fieldDefinitionId,
      sort_order: fields.length,
      visible: true,
      write_back_target: null,
    });
    updateEntry(entryIndex, { fields });
  };

  const openCreateField = async (entryIndex: number) => {
    setCreateFieldEntryIndex(entryIndex);
    setCreateFieldName('');
    setCreateFieldDisplay('');
    setCreateFieldDataType('text');
    setCreateFieldListId('');
    setCreateFieldError(null);
    setCreateFieldOpen(true);
    try {
      const lists = await apiService.getLists();
      const arr = Array.isArray(lists) ? lists : lists?.lists ?? [];
      setCreateFieldLists(arr.map((l: any) => ({ id: l.id, name: l.name })));
    } catch {
      setCreateFieldLists([]);
    }
  };

  const handleCreateField = async () => {
    if (createFieldEntryIndex == null) return;
    const entry = entriesList[createFieldEntryIndex];
    const entityType = fieldEntityTypeForEntry(entry?.entry_type || '');
    if (!entityType) {
      setCreateFieldError('This entry type does not use field definition columns.');
      return;
    }
    const name = createFieldName.trim().toLowerCase().replace(/\s+/g, '_');
    if (!name) {
      setCreateFieldError('Internal name is required (e.g. elution_volume).');
      return;
    }
    if (createFieldDataType === 'list' && !createFieldListId) {
      setCreateFieldError('List-backed fields require a source list.');
      return;
    }
    setCreateFieldSubmitting(true);
    setCreateFieldError(null);
    try {
      const created = await apiService.createFieldDefinition({
        entity_type: entityType,
        name,
        display_name: createFieldDisplay.trim() || name,
        data_type: createFieldDataType,
        source_list_id: createFieldDataType === 'list' ? createFieldListId : undefined,
        is_required: false,
        active: true,
        is_materialized_column: false,
      });
      await loadFieldDefinitions();
      if (created?.id) {
        addEntryField(createFieldEntryIndex, created.id);
      }
      setCreateFieldOpen(false);
    } catch (err: unknown) {
      setCreateFieldError(apiErrorMsg(err, 'Failed to create field definition'));
    } finally {
      setCreateFieldSubmitting(false);
    }
  };

  const updateEntryField = (
    entryIndex: number,
    fieldIndex: number,
    patch: Partial<TemplateEntryField>,
  ) => {
    const entry = entriesList[entryIndex];
    const fields = (entry.fields || []).map((f, i) => (i === fieldIndex ? { ...f, ...patch } : f));
    updateEntry(entryIndex, { fields });
  };

  const removeEntryField = (entryIndex: number, fieldIndex: number) => {
    const entry = entriesList[entryIndex];
    const fields = (entry.fields || []).filter((_, i) => i !== fieldIndex);
    updateEntry(entryIndex, { fields });
  };

  const toggleSampleColumn = (entryIndex: number, key: string) => {
    const entry = entriesList[entryIndex];
    const current = entry.config?.sample_columns || [];
    const next = current.includes(key) ? current.filter((k) => k !== key) : [...current, key];
    updateEntry(entryIndex, {
      config: { ...(entry.config || {}), sample_columns: next },
    });
  };

  const fieldLabel = (id: string) => {
    const fd = fieldDefOptions.find((f) => f.id === id);
    return fd?.display_name || fd?.name || id.slice(0, 8);
  };

  const handleSave = async () => {
    const { valid, tabErrors: errs } = validateForm();
    setTabErrors(errs);
    if (!valid) {
      const firstErrorTab = errs.findIndex(Boolean);
      setActiveTab(firstErrorTab);
      return;
    }
    setFormSubmitting(true);
    setFormError(null);
    try {
      // Persist entry-based definition only. Clear legacy protocol/transfer/result
      // and sign-off counters so activation is never blocked by unused formats.
      const template_definition: Record<string, unknown> = {
        experiment_name: formDef.experiment_name.trim(),
        description: formDef.description || undefined,
        plate_layout: formDef.plate_layout || null,
        acceptance_criteria: formDef.acceptance_criteria || undefined,
        entries: (formDef.entries ?? []).map((e, i) => ({
          ...e,
          sort_order: e.sort_order ?? i,
        })),
        protocol_steps: [],
        transfer_steps: [],
        result_columns: [],
        mandatory_review_count: 0,
      };
      const payload = {
        name: formName.trim(),
        description: formDescription.trim() || undefined,
        lifecycle_type: formLifecycleType,
        template_definition,
      };
      if (selectedTemplate) {
        await apiService.updateExperimentTemplate(String(selectedTemplate.id), {
          ...payload,
          active: formActive,
        });
      } else {
        await apiService.createExperimentTemplate(payload);
      }
      await loadTemplates();
      setFormOpen(false);
    } catch (err: unknown) {
      setFormError(apiErrorMsg(err, (err as any)?.message || 'Failed to save template'));
    } finally {
      setFormSubmitting(false);
    }
  };

  // ── Delete ────────────────────────────────────────────────────────────────

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setDeleteSubmitting(true);
    try {
      await apiService.deleteExperimentTemplate(String(deleteTarget.id));
      await loadTemplates();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: unknown) {
      setError(apiErrorMsg(err, 'Failed to delete template'));
      setDeleteDialogOpen(false);
    } finally {
      setDeleteSubmitting(false);
    }
  };

  const handleActivationToggle = async (row: ExperimentTemplateRow) => {
    try {
      await apiService.updateExperimentTemplate(String(row.id), { active: !row.active });
      await loadTemplates();
    } catch (err: unknown) {
      setError(apiErrorMsg(err, 'Failed to update template status'));
    }
  };

  // ── SOP upload ────────────────────────────────────────────────────────────

  const openSopUpload = () => {
    setSopFile(null);
    setInstrumentFile(null);
    setSopUploadError(null);
    setSopJobId(null);
    setSopPhase('idle');
    setSopElapsedSeconds(0);
    setSopUploadOpen(true);
  };

  const handleSopSubmit = async () => {
    if (!sopFile || !instrumentFile) {
      setSopUploadError('Both files are required.');
      return;
    }
    setSopUploadError(null);
    setSopPhase('uploading');

    let jobId: string;
    try {
      const job = await apiService.createSopParseJob(sopFile, instrumentFile);
      jobId = job.id;
      setSopJobId(jobId);
    } catch (err: unknown) {
      setSopUploadError(apiErrorMsg(err, (err as any)?.message || 'Upload failed'));
      setSopPhase('idle');
      return;
    }

    // Poll
    setSopPhase('polling');
    let elapsed = 0;
    const MAX_WAIT = 120;
    const POLL_INTERVAL = 2000;

    const poll = async (): Promise<void> => {
      elapsed += POLL_INTERVAL / 1000;
      setSopElapsedSeconds(elapsed);

      if (elapsed >= MAX_WAIT) {
        setSopPhase('timeout');
        return;
      }

      try {
        const job = await apiService.getSopParseJob(jobId);
        if (job.status === 'complete') {
          setSopPhase('applying');
          try {
            const applied = await apiService.applySopParseJob(jobId);
            await loadTemplates();
            // Fetch the newly created template and open edit dialog for review
            const newTemplate = await apiService.getExperimentTemplate(applied.experiment_template_id);
            setSopUploadOpen(false);
            setSopFromExtraction(true);
            openEdit(newTemplate as ExperimentTemplateRow);
          } catch (applyErr: unknown) {
            const e = applyErr as { response?: { status?: number; data?: { detail?: string } }; message?: string };
            if (e.response?.status === 409) {
              // Already applied — just reload and close
              await loadTemplates();
              setSopUploadOpen(false);
            } else {
              setSopUploadError(apiErrorMsg(applyErr, (applyErr as any)?.message || 'Apply failed'));
              setSopPhase('idle');
            }
          }
          return;
        }
        if (job.status === 'failed') {
          setSopUploadError('SOP extraction failed. Please fill in the template manually.');
          setSopPhase('idle');
          return;
        }
        // Still pending/processing — keep polling
        setTimeout(poll, POLL_INTERVAL);
      } catch {
        setSopUploadError('Lost connection while polling. Please try again.');
        setSopPhase('idle');
      }
    };

    setTimeout(poll, POLL_INTERVAL);
  };

  const handleSopKeepWaiting = () => {
    setSopPhase('polling');
    setSopElapsedSeconds(0);
    if (sopJobId) {
      // Resume polling from current job
      const poll = async (): Promise<void> => {
        setSopElapsedSeconds((s) => s + 2);
        if (!sopJobId) return;
        try {
          const job = await apiService.getSopParseJob(sopJobId);
          if (job.status === 'complete') {
            setSopPhase('applying');
            const applied = await apiService.applySopParseJob(sopJobId);
            await loadTemplates();
            const newTemplate = await apiService.getExperimentTemplate(applied.experiment_template_id);
            setSopUploadOpen(false);
            setSopFromExtraction(true);
            openEdit(newTemplate as ExperimentTemplateRow);
            return;
          }
          if (job.status === 'failed') {
            setSopUploadError('SOP extraction failed.');
            setSopPhase('idle');
            return;
          }
          setTimeout(poll, 2000);
        } catch {
          setSopUploadError('Connection lost.');
          setSopPhase('idle');
        }
      };
      setTimeout(poll, 2000);
    }
  };

  const handleSopFillManually = () => {
    setSopUploadOpen(false);
    openCreate();
  };

  // ── DataGrid columns ──────────────────────────────────────────────────────

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', width: 200, flex: isMobile ? 0 : 1 },
    {
      field: 'description',
      headerName: 'Description',
      width: 200,
      flex: isMobile ? 0 : 1,
      valueGetter: (_: unknown, row: ExperimentTemplateRow) => row.description ?? '—',
    },
    {
      field: 'lifecycle_type',
      headerName: 'Lifecycle',
      width: 100,
      valueGetter: (_: unknown, row: ExperimentTemplateRow) =>
        row.lifecycle_type === 'cro' ? 'CRO' : 'Standard',
    },
    {
      field: 'plate_layout',
      headerName: 'Plate',
      width: 100,
      valueGetter: (_: unknown, row: ExperimentTemplateRow) =>
        row.template_definition?.plate_layout ?? '—',
    },
    {
      field: 'entries',
      headerName: 'Tables & forms',
      width: 130,
      valueGetter: (_: unknown, row: ExperimentTemplateRow) => {
        const n = row.template_definition?.entries?.length ?? 0;
        return n === 0 ? '—' : `${n}`;
      },
    },
    {
      field: 'active',
      headerName: 'Active',
      width: 90,
      renderCell: (params) => {
        const row = params.row as ExperimentTemplateRow;
        return (
          <Switch
            size="small"
            checked={row.active}
            onChange={() => handleActivationToggle(row)}
            disabled={!canManage}
            color="success"
          />
        );
      },
    },
    {
      field: 'modified_at',
      headerName: 'Last Modified',
      width: 160,
      valueFormatter: (value: unknown) => (value ? new Date(value as string).toLocaleString() : '—'),
    },
    {
      field: 'modified_by',
      headerName: 'Modified By',
      width: 130,
      valueGetter: (_: unknown, row: ExperimentTemplateRow) => row.modified_by ?? '—',
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 120,
      getActions: (params: GridRowParams) => {
        const row = params.row as ExperimentTemplateRow;
        if (!canManage) return [];
        return [
          <GridActionsCellItem key="edit" icon={<Edit />} label="Edit" onClick={() => openEdit(row)} />,
          <GridActionsCellItem
            key="delete"
            icon={<Delete />}
            label="Delete"
            onClick={() => {
              setDeleteTarget(row);
              setDeleteDialogOpen(true);
            }}
          />,
        ];
      },
    },
  ];

  // ── Permission guard ──────────────────────────────────────────────────────

  if (!canManage) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="warning">
          You do not have permission to view experiment templates. Requires{' '}
          <strong>experiment:manage</strong> permission.
        </Alert>
      </Box>
    );
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <FillHeightPage
      header={
        <>
          <Box
            sx={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: 2,
            }}
          >
            <Typography variant="h5">Experiment Templates</Typography>
            {canManage && (
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button variant="contained" startIcon={<Upload />} onClick={openSopUpload}>
                  Upload SOP
                </Button>
                <Button variant="outlined" startIcon={<Add />} onClick={openCreate}>
                  New Template
                </Button>
              </Box>
            )}
          </Box>

          {error && (
            <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
        </>
      }
    >
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" flex={1}>
          <CircularProgress />
        </Box>
      ) : (
        <FillHeightTable>
          <DataGrid
            rows={rows}
            columns={columns}
            getRowId={(row) => row.id}
            pageSizeOptions={[10, 25, 50]}
            initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
            disableRowSelectionOnClick
            slots={{
              noRowsOverlay: () => (
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    height: '100%',
                  }}
                >
                  <Typography>No experiment templates yet. Create one to get started.</Typography>
                </Box>
              ),
            }}
            sx={{ '& .MuiDataGrid-cell': { fontSize: theme.typography.body2.fontSize } }}
          />
        </FillHeightTable>
      )}

      {/* ── Create/Edit Dialog ───────────────────────────────────────────── */}
      <Dialog open={formOpen} onClose={() => { setFormOpen(false); setSopFromExtraction(false); }} maxWidth="lg" fullWidth>
        <DialogTitle>
          {selectedTemplate ? `Edit Template: ${selectedTemplate.name}` : 'Create Experiment Template'}
        </DialogTitle>
        <DialogContent>
          {/* SOP extraction banner */}
          {sopFromExtraction && (
            <Alert severity="info" sx={{ mb: 2 }} onClose={() => setSopFromExtraction(false)}>
              This template was filled from your SOP. Review all fields before activating.
            </Alert>
          )}
          {/* Tab-level error summary */}
          {tabErrors.some(Boolean) && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {tabErrors[0] && <div>Basic Info: Template name and experiment name are required.</div>}
              {tabErrors[1] && (
                <div>
                  Tables &amp; forms: Add at least one entry; each needs a name and type. These are the
                  reusable capture places instantiated when an experiment is created from this template.
                </div>
              )}
            </Alert>
          )}

          <Tabs
            value={activeTab}
            onChange={(_, v) => setActiveTab(v)}
            variant="scrollable"
            scrollButtons="auto"
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab
              label="Basic Info"
              sx={{ color: tabErrors[0] ? 'error.main' : undefined }}
              icon={tabErrors[0] ? <span style={{ color: 'red', fontSize: 10 }}>●</span> : undefined}
              iconPosition="end"
            />
            <Tab
              label="Tables & forms"
              sx={{ color: tabErrors[1] ? 'error.main' : undefined }}
              icon={tabErrors[1] ? <span style={{ color: 'red', fontSize: 10 }}>●</span> : undefined}
              iconPosition="end"
            />
          </Tabs>

          {/* Tab 1: Basic Info */}
          <TabPanel value={activeTab} index={0}>
            <TextField
              fullWidth
              required
              label="Template Name"
              helperText="Public display name for this template"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              error={tabErrors[0] && !formName.trim()}
              margin="normal"
            />
            <TextField
              fullWidth
              required
              label="Experiment Name"
              helperText="Internal experiment identifier used when running this template"
              value={formDef.experiment_name}
              onChange={(e) => setFormDef((d) => ({ ...d, experiment_name: e.target.value }))}
              error={tabErrors[0] && !formDef.experiment_name.trim()}
              margin="normal"
            />
            <TextField
              fullWidth
              label="Description"
              value={formDescription}
              onChange={(e) => setFormDescription(e.target.value)}
              multiline
              rows={2}
              margin="normal"
            />
            <FormControl fullWidth margin="normal">
              <InputLabel>Plate Layout</InputLabel>
              <Select
                value={formDef.plate_layout ?? ''}
                label="Plate Layout"
                onChange={(e) =>
                  setFormDef((d) => ({
                    ...d,
                    plate_layout: (e.target.value as '96-well' | '384-well') || null,
                  }))
                }
              >
                <MenuItem value="">None</MenuItem>
                <MenuItem value="96-well">96-well</MenuItem>
                <MenuItem value="384-well">384-well</MenuItem>
              </Select>
            </FormControl>
            <TextField
              fullWidth
              label="Acceptance Criteria"
              value={formDef.acceptance_criteria ?? ''}
              onChange={(e) => setFormDef((d) => ({ ...d, acceptance_criteria: e.target.value }))}
              multiline
              rows={3}
              margin="normal"
              placeholder="e.g. All results must be within 10% of control values"
            />
            <FormControl fullWidth margin="normal">
              <InputLabel>Lifecycle Type</InputLabel>
              <Select
                value={formLifecycleType}
                label="Lifecycle Type"
                onChange={(e) => setFormLifecycleType(e.target.value as 'standard' | 'cro')}
              >
                <MenuItem value="standard">Standard</MenuItem>
                <MenuItem value="cro">CRO</MenuItem>
              </Select>
            </FormControl>
            {selectedTemplate && (
              <FormControlLabel
                control={
                  <Switch checked={formActive} onChange={(e) => setFormActive(e.target.checked)} color="success" />
                }
                label="Active"
                sx={{ mt: 1 }}
              />
            )}
          </TabPanel>

          {/* Tab 2: Tables & forms (ELN entries — reusable template body) */}
          <TabPanel value={activeTab} index={1}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              These <strong>entries</strong> are the reusable template. They are instantiated
              automatically when an experiment is created from this template.{' '}
              <strong>Sample data</strong> = one row per cohort sample;{' '}
              <strong>Experiment data</strong> = purpose table/form (plans, headers). Write-back
              targets apply on <strong>Submit</strong> only (not Save).
            </Typography>

            {(formDef.entries ?? []).length === 0 && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                Add at least one table or form (or use a preset below). Empty templates cannot be saved.
              </Alert>
            )}

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {(formDef.entries ?? []).map((entry, ei) => {
                const isSample =
                  entry.entry_type === 'experiment_sample_data' || entry.entry_type === 'sample_data';
                const isDataTable =
                  isSample ||
                  entry.entry_type === 'experiment_data' ||
                  entry.entry_type === 'experiment_detail';
                const fieldEntity = fieldEntityTypeForEntry(entry.entry_type);
                const usedFieldIds = new Set((entry.fields || []).map((f) => f.field_definition_id));
                const availableFields = fieldDefOptions.filter(
                  (f) =>
                    !usedFieldIds.has(f.id) &&
                    fieldEntity != null &&
                    (f.entity_type || '').toLowerCase() === fieldEntity,
                );

                return (
                  <Box
                    key={ei}
                    sx={{
                      border: 1,
                      borderColor: 'divider',
                      borderRadius: 1,
                      p: 2,
                    }}
                  >
                    <Box
                      sx={{
                        display: 'flex',
                        gap: 1,
                        flexWrap: 'wrap',
                        alignItems: 'flex-start',
                        mb: 1,
                      }}
                    >
                      <TextField
                        size="small"
                        required
                        label="Entry name"
                        value={entry.name}
                        onChange={(e) => updateEntry(ei, { name: e.target.value })}
                        error={tabErrors[1] && !entry.name.trim()}
                        sx={{ minWidth: 180, flex: 1 }}
                      />
                      <FormControl size="small" sx={{ minWidth: 200 }}>
                        <InputLabel>Type</InputLabel>
                        <Select
                          label="Type"
                          value={entry.entry_type}
                          onChange={(e) =>
                            updateEntry(ei, {
                              entry_type: e.target.value as TemplateEntryDeclaration['entry_type'],
                            })
                          }
                        >
                          {ENTRY_TYPE_OPTIONS.map((opt) => (
                            <MenuItem key={opt.value} value={opt.value}>
                              {opt.label}
                            </MenuItem>
                          ))}
                        </Select>
                      </FormControl>
                      {entry.entry_type === 'predefined_action' && (
                        <TextField
                          size="small"
                          label="Predefined key"
                          placeholder="e.g. aliquot_pool"
                          value={entry.predefined_entry_key ?? ''}
                          onChange={(e) =>
                            updateEntry(ei, { predefined_entry_key: e.target.value || undefined })
                          }
                          sx={{ minWidth: 160 }}
                        />
                      )}
                      <IconButton size="small" color="error" onClick={() => removeEntry(ei)}>
                        <Delete fontSize="small" />
                      </IconButton>
                    </Box>

                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                      {ENTRY_TYPE_OPTIONS.find((o) => o.value === entry.entry_type)?.helper ||
                        entry.entry_type}
                    </Typography>

                    {entry.predefined_entry_key === 'aliquot_pool_plan' && (
                      <Box sx={{ mb: 1.5 }}>
                        <FormControl size="small" sx={{ minWidth: 360 }}>
                          <InputLabel>Plan method</InputLabel>
                          <Select
                            label="Plan method"
                            value={String(entry.config?.method || 'aliquot_by_volume')}
                            onChange={(event) =>
                              updateEntry(ei, {
                                config: {
                                  ...(entry.config || {}),
                                  method: event.target.value,
                                  default_dest_sample_type:
                                    entry.config?.default_dest_sample_type ?? null,
                                },
                              })
                            }
                          >
                            {ALIQUOT_POOL_METHOD_OPTIONS.map((option) => (
                              <MenuItem key={option.value} value={option.value}>
                                {option.label}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          display="block"
                          sx={{ mt: 0.5 }}
                        >
                          One concrete method fixes aliquot or pool for the entry. The catalog-limited
                          default destination type is selected from source samples in the runtime plan.
                        </Typography>
                      </Box>
                    )}

                    <TextField
                      size="small"
                      fullWidth
                      label="Description"
                      value={entry.description ?? ''}
                      onChange={(e) => updateEntry(ei, { description: e.target.value })}
                      sx={{ mb: 1.5 }}
                    />

                    <FormControl size="small" fullWidth sx={{ mb: 1.5 }}>
                      <InputLabel>Depends on (submit first)</InputLabel>
                      <Select
                        multiple
                        label="Depends on (submit first)"
                        value={entry.depends_on || entry.config?.depends_on || []}
                        onChange={(e) => {
                          const v = e.target.value;
                          const deps = typeof v === 'string' ? v.split(',') : (v as string[]);
                          updateEntry(ei, { depends_on: deps });
                        }}
                        renderValue={(selected) => (selected as string[]).join(', ') || 'None'}
                      >
                        {(formDef.entries ?? [])
                          .filter((_, j) => j !== ei)
                          .map((other) => {
                            const key = other.predefined_entry_key || other.name;
                            if (!key) return null;
                            return (
                              <MenuItem key={key} value={key}>
                                {other.name || key}
                                {other.predefined_entry_key
                                  ? ` (${other.predefined_entry_key})`
                                  : ''}
                              </MenuItem>
                            );
                          })}
                      </Select>
                    </FormControl>
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1.5 }}>
                      Submit is blocked until each dependency is submitted (template SOP control).
                    </Typography>

                    {isSample && (
                      <Box sx={{ mb: 1.5 }}>
                        <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                          Read-only sample columns
                        </Typography>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {SAMPLE_COLUMN_OPTIONS.map((opt) => {
                            const selected = (entry.config?.sample_columns || []).includes(opt.key);
                            return (
                              <Chip
                                key={opt.key}
                                size="small"
                                label={opt.label}
                                color={selected ? 'primary' : 'default'}
                                variant={selected ? 'filled' : 'outlined'}
                                onClick={() => toggleSampleColumn(ei, opt.key)}
                              />
                            );
                          })}
                        </Box>
                      </Box>
                    )}

                    {isDataTable && (
                      <>
                        <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
                          Table columns (entry field definitions)
                        </Typography>
                        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                          Not Custom Fields on Sample/Test. Entity type:{' '}
                          <code>{fieldEntity || '—'}</code>. These columns appear as the entry table.
                        </Typography>
                        {(entry.fields || []).length === 0 ? (
                          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                            No columns yet — create a field or add an existing one below.
                          </Typography>
                        ) : (
                          <Table size="small" sx={{ mb: 1 }}>
                            <TableHead>
                              <TableRow>
                                <TableCell>Field</TableCell>
                                <TableCell width={200}>Write-back (on Submit)</TableCell>
                                <TableCell width={48} />
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {(entry.fields || []).map((f, fi) => (
                                <TableRow key={f.field_definition_id}>
                                  <TableCell>
                                    <Typography variant="body2">
                                      {fieldLabel(f.field_definition_id)}
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                      {f.field_definition_id.slice(0, 8)}…
                                    </Typography>
                                  </TableCell>
                                  <TableCell>
                                    <FormControl size="small" fullWidth disabled={!isSample}>
                                      <Select
                                        displayEmpty
                                        value={f.write_back_target ?? ''}
                                        onChange={(e) =>
                                          updateEntryField(ei, fi, {
                                            write_back_target: e.target.value || null,
                                          })
                                        }
                                      >
                                        {WRITE_BACK_TARGETS.map((t) => (
                                          <MenuItem key={t.value || 'none'} value={t.value}>
                                            {t.label}
                                          </MenuItem>
                                        ))}
                                      </Select>
                                    </FormControl>
                                  </TableCell>
                                  <TableCell>
                                    <IconButton
                                      size="small"
                                      color="error"
                                      onClick={() => removeEntryField(ei, fi)}
                                    >
                                      <Delete fontSize="small" />
                                    </IconButton>
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        )}

                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
                          <FormControl size="small" sx={{ minWidth: 280 }}>
                            <InputLabel>Add existing field</InputLabel>
                            <Select
                              label="Add existing field"
                              value=""
                              onChange={(e) => addEntryField(ei, String(e.target.value))}
                              disabled={availableFields.length === 0}
                            >
                              {availableFields.length === 0 ? (
                                <MenuItem value="" disabled>
                                  No fields for {fieldEntity} — create one
                                </MenuItem>
                              ) : (
                                availableFields.map((fd) => (
                                  <MenuItem key={fd.id} value={fd.id}>
                                    {fd.display_name || fd.name} ({fd.data_type})
                                  </MenuItem>
                                ))
                              )}
                            </Select>
                          </FormControl>
                          <Button
                            size="small"
                            variant="outlined"
                            startIcon={<Add />}
                            onClick={() => openCreateField(ei)}
                          >
                            Create field
                          </Button>
                        </Box>
                      </>
                    )}
                    {!isDataTable && entry.entry_type === 'predefined_action' && (
                      <Typography variant="body2" color="text.secondary">
                        Aliquot/pool uses the plan editor at runtime — no table columns here. Set
                        predefined key to <code>aliquot_pool_plan</code> if needed.
                      </Typography>
                    )}
                  </Box>
                );
              })}
            </Box>

            <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
              <Button startIcon={<Add />} onClick={addEntry} variant="outlined" size="small">
                Add table / form
              </Button>
              <Typography variant="body2" color="text.secondary" sx={{ mx: 0.5 }}>
                Presets:
              </Typography>
              {PREDEFINED_PRESETS.map((p) => {
                const already = (formDef.entries ?? []).some(
                  (e) => e.predefined_entry_key === p.key,
                );
                return (
                  <Button
                    key={p.key}
                    size="small"
                    variant="text"
                    disabled={already}
                    onClick={() =>
                      setEntries([
                        ...(formDef.entries ?? []),
                        { ...p.entry, sort_order: (formDef.entries ?? []).length },
                      ])
                    }
                  >
                    + {p.label}
                  </Button>
                );
              })}
            </Box>
          </TabPanel>

          {formError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {formError}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setFormOpen(false); setSopFromExtraction(false); }} disabled={formSubmitting}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={formSubmitting || !formName.trim()}
          >
            {formSubmitting ? 'Saving...' : selectedTemplate ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── SOP Upload Dialog ───────────────────────────────────────────── */}
      <Dialog
        open={sopUploadOpen}
        onClose={() => { if (sopPhase !== 'uploading' && sopPhase !== 'polling' && sopPhase !== 'applying') setSopUploadOpen(false); }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Upload SOP to Create Template</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Upload your SOP document and an example instrument CSV. Extraction may pre-fill basic
            fields; review and author <strong>Tables &amp; forms</strong> (entries) before activating.
            Legacy protocol/transfer lists are no longer used.
          </Typography>

          {sopUploadError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setSopUploadError(null)}>
              {sopUploadError}
            </Alert>
          )}

          {/* Idle / file selection */}
          {(sopPhase === 'idle') && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Box>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
                  SOP Document (PDF, DOCX, or TXT) *
                </Typography>
                <Button variant="outlined" component="label" fullWidth>
                  {sopFile ? sopFile.name : 'Choose SOP file...'}
                  <input
                    type="file"
                    hidden
                    accept=".pdf,.docx,.txt,.doc"
                    onChange={(e) => setSopFile(e.target.files?.[0] ?? null)}
                  />
                </Button>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
                  Instrument CSV (example output from the instrument) *
                </Typography>
                <Button variant="outlined" component="label" fullWidth>
                  {instrumentFile ? instrumentFile.name : 'Choose instrument CSV...'}
                  <input
                    type="file"
                    hidden
                    accept=".csv,.txt"
                    onChange={(e) => setInstrumentFile(e.target.files?.[0] ?? null)}
                  />
                </Button>
              </Box>
            </Box>
          )}

          {/* Uploading */}
          {sopPhase === 'uploading' && (
            <Box sx={{ textAlign: 'center', py: 3 }}>
              <CircularProgress size={40} />
              <Typography variant="body2" sx={{ mt: 2 }}>Uploading files...</Typography>
            </Box>
          )}

          {/* Polling */}
          {sopPhase === 'polling' && (
            <Box sx={{ py: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                <CircularProgress size={24} />
                <Typography variant="body2">
                  Claude is reading your SOP... {sopElapsedSeconds}s
                </Typography>
              </Box>
              <LinearProgress variant="determinate" value={Math.min((sopElapsedSeconds / 120) * 100, 99)} />
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Usually takes 15–60 seconds for most SOPs.
              </Typography>
            </Box>
          )}

          {/* Applying */}
          {sopPhase === 'applying' && (
            <Box sx={{ textAlign: 'center', py: 3 }}>
              <CircularProgress size={40} />
              <Typography variant="body2" sx={{ mt: 2 }}>Creating template from extraction...</Typography>
            </Box>
          )}

          {/* Timeout */}
          {sopPhase === 'timeout' && (
            <Box sx={{ py: 2 }}>
              <Alert severity="warning" sx={{ mb: 2 }}>
                This is taking longer than expected ({sopElapsedSeconds}s). The extraction may still be running.
              </Alert>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          {/* Close only when not actively processing */}
          {(sopPhase === 'idle' || sopPhase === 'timeout') && (
            <Button onClick={() => setSopUploadOpen(false)}>Cancel</Button>
          )}
          {sopPhase === 'timeout' && (
            <>
              <Button onClick={handleSopKeepWaiting} variant="outlined">Keep Waiting</Button>
              <Button onClick={handleSopFillManually} variant="outlined">Fill in Manually</Button>
            </>
          )}
          {sopPhase === 'idle' && (
            <Button
              variant="contained"
              onClick={handleSopSubmit}
              disabled={!sopFile || !instrumentFile}
            >
              Extract from SOP
            </Button>
          )}
        </DialogActions>
      </Dialog>

      {/* ── Delete Dialog ────────────────────────────────────────────────── */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Template</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Permanently delete <strong>{deleteTarget?.name}</strong>? This cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deleteSubmitting}>
            Cancel
          </Button>
          <Button onClick={handleDeleteConfirm} color="error" variant="contained" disabled={deleteSubmitting}>
            {deleteSubmitting ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* ── Create entry FieldDefinition ─────────────────────────────────── */}
      <Dialog
        open={createFieldOpen}
        onClose={() => !createFieldSubmitting && setCreateFieldOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Create entry field</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Defines a column for this entry table (stored as a FieldDefinition with entity type{' '}
            <code>
              {createFieldEntryIndex != null
                ? fieldEntityTypeForEntry(entriesList[createFieldEntryIndex]?.entry_type || '') ||
                  '—'
                : '—'}
            </code>
            ). This is <strong>not</strong> a Custom Field on Sample/Test database tables.
          </Typography>
          {createFieldError && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setCreateFieldError(null)}>
              {createFieldError}
            </Alert>
          )}
          <TextField
            fullWidth
            required
            label="Internal name"
            helperText="snake_case, unique per entity type"
            value={createFieldName}
            onChange={(e) => setCreateFieldName(e.target.value)}
            margin="normal"
            placeholder="elution_volume"
          />
          <TextField
            fullWidth
            label="Display name"
            value={createFieldDisplay}
            onChange={(e) => setCreateFieldDisplay(e.target.value)}
            margin="normal"
            placeholder="Elution volume"
          />
          <FormControl fullWidth margin="normal">
            <InputLabel>Data type</InputLabel>
            <Select
              label="Data type"
              value={createFieldDataType}
              onChange={(e) =>
                setCreateFieldDataType(e.target.value as typeof createFieldDataType)
              }
            >
              <MenuItem value="text">Text</MenuItem>
              <MenuItem value="number">Number</MenuItem>
              <MenuItem value="date">Date</MenuItem>
              <MenuItem value="boolean">Boolean</MenuItem>
              <MenuItem value="list">List</MenuItem>
            </Select>
          </FormControl>
          {createFieldDataType === 'list' && (
            <FormControl fullWidth margin="normal">
              <InputLabel>Source list</InputLabel>
              <Select
                label="Source list"
                value={createFieldListId}
                onChange={(e) => setCreateFieldListId(e.target.value)}
              >
                {createFieldLists.map((l) => (
                  <MenuItem key={l.id} value={l.id}>
                    {l.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateFieldOpen(false)} disabled={createFieldSubmitting}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleCreateField}
            disabled={createFieldSubmitting || !createFieldName.trim()}
          >
            {createFieldSubmitting ? 'Creating…' : 'Create & add to entry'}
          </Button>
        </DialogActions>
      </Dialog>
    </FillHeightPage>
  );
};

export default ExperimentTemplatesManagement;
