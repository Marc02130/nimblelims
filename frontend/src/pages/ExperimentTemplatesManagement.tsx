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
  Tooltip,
} from '@mui/material';
import { Add, Edit, Delete, RateReview } from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../contexts/UserContext';
import { apiService } from '../services/apiService';

// ─── Types ────────────────────────────────────────────────────────────────────

interface TransferStep {
  step: number;
  source_plate?: string;
  source_well?: string;
  dest_plate?: string;
  dest_well?: string;
  volume_ul?: number;
  mandatory_review: boolean;
}

interface TemplateDefinition {
  experiment_name: string;
  description?: string;
  protocol_steps: string[];
  plate_layout?: '96-well' | '384-well' | null;
  transfer_steps: TransferStep[];
  result_columns: Record<string, unknown>[];
  acceptance_criteria?: string;
  mandatory_review_count: number;
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

const blankDefinition = (): TemplateDefinition => ({
  experiment_name: '',
  description: '',
  protocol_steps: [],
  plate_layout: null,
  transfer_steps: [],
  result_columns: [],
  acceptance_criteria: '',
  mandatory_review_count: 0,
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
  const [tabErrors, setTabErrors] = useState<boolean[]>([false, false, false, false]);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Form fields — outer
  const [formName, setFormName] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formActive, setFormActive] = useState(true);

  // Form fields — template_definition
  const [formDef, setFormDef] = useState<TemplateDefinition>(blankDefinition());

  // Delete dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ExperimentTemplateRow | null>(null);
  const [deleteSubmitting, setDeleteSubmitting] = useState(false);

  // Sign-off dialog state
  const [signoffOpen, setSignoffOpen] = useState(false);
  const [signoffTemplate, setSignoffTemplate] = useState<ExperimentTemplateRow | null>(null);
  const [signoffConfirmed, setSignoffConfirmed] = useState<Set<number>>(new Set());
  const [signoffSubmitting, setSignoffSubmitting] = useState(false);
  const [signoffCloseWarning, setSignoffCloseWarning] = useState(false);

  // ── Data loading ─────────────────────────────────────────────────────────

  const loadTemplates = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getExperimentTemplates();
      setRows(Array.isArray(data) ? data : (data?.items ?? []));
    } catch (err: unknown) {
      const e = err as { response?: { status?: number; data?: { detail?: string } }; message?: string };
      if (e.response?.status === 403) {
        setError('You do not have permission to view experiment templates.');
      } else {
        setError(e.response?.data?.detail || 'Failed to load experiment templates');
      }
      setRows([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  // ── Form helpers ─────────────────────────────────────────────────────────

  const openCreate = () => {
    setSelectedTemplate(null);
    setFormName('');
    setFormDescription('');
    setFormActive(true);
    setFormDef(blankDefinition());
    setActiveTab(0);
    setTabErrors([false, false, false, false]);
    setFormError(null);
    setFormOpen(true);
  };

  const openEdit = (row: ExperimentTemplateRow) => {
    setSelectedTemplate(row);
    setFormName(row.name);
    setFormDescription(row.description ?? '');
    setFormActive(row.active);
    setFormDef({
      ...blankDefinition(),
      ...row.template_definition,
    });
    setActiveTab(0);
    setTabErrors([false, false, false, false]);
    setFormError(null);
    setFormOpen(true);
  };

  const validateForm = (): { valid: boolean; tabErrors: boolean[] } => {
    const errors = [false, false, false, false];
    if (!formName.trim() || !formDef.experiment_name.trim()) {
      errors[0] = true;
    }
    return { valid: !errors.some(Boolean), tabErrors: errors };
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
      const payload = {
        name: formName.trim(),
        description: formDescription.trim() || undefined,
        template_definition: {
          ...formDef,
          mandatory_review_count: formDef.transfer_steps.filter((s) => s.mandatory_review).length,
        } as unknown as Record<string, unknown>,
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
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setFormError(e.response?.data?.detail || e.message || 'Failed to save template');
    } finally {
      setFormSubmitting(false);
    }
  };

  // ── Transfer step helpers ─────────────────────────────────────────────────

  const addTransferStep = () => {
    const nextStep = formDef.transfer_steps.length + 1;
    setFormDef((d) => ({
      ...d,
      transfer_steps: [...d.transfer_steps, { step: nextStep, mandatory_review: true }],
    }));
  };

  const updateTransferStep = (index: number, patch: Partial<TransferStep>) => {
    setFormDef((d) => {
      const updated = [...d.transfer_steps];
      updated[index] = { ...updated[index], ...patch };
      return { ...d, transfer_steps: updated };
    });
  };

  const removeTransferStep = (index: number) => {
    setFormDef((d) => {
      const updated = d.transfer_steps.filter((_, i) => i !== index).map((s, i) => ({ ...s, step: i + 1 }));
      return { ...d, transfer_steps: updated };
    });
  };

  // ── Protocol step helpers ─────────────────────────────────────────────────

  const addProtocolStep = () => {
    setFormDef((d) => ({ ...d, protocol_steps: [...d.protocol_steps, ''] }));
  };

  const updateProtocolStep = (index: number, value: string) => {
    setFormDef((d) => {
      const updated = [...d.protocol_steps];
      updated[index] = value;
      return { ...d, protocol_steps: updated };
    });
  };

  const removeProtocolStep = (index: number) => {
    setFormDef((d) => ({ ...d, protocol_steps: d.protocol_steps.filter((_, i) => i !== index) }));
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
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail || 'Failed to delete template');
      setDeleteDialogOpen(false);
    } finally {
      setDeleteSubmitting(false);
    }
  };

  // ── Sign-off ──────────────────────────────────────────────────────────────

  const openSignoff = (row: ExperimentTemplateRow) => {
    setSignoffTemplate(row);
    setSignoffConfirmed(new Set());
    setSignoffCloseWarning(false);
    setSignoffOpen(true);
  };

  const handleSignoffClose = () => {
    const pendingSteps = (signoffTemplate?.template_definition.transfer_steps ?? [])
      .filter((s) => s.mandatory_review && !signoffConfirmed.has(s.step));
    if (pendingSteps.length > 0 && !signoffCloseWarning) {
      setSignoffCloseWarning(true);
      return;
    }
    setSignoffOpen(false);
    setSignoffCloseWarning(false);
  };

  const confirmStep = (step: number) => {
    setSignoffConfirmed((prev) => new Set([...prev, step]));
    setSignoffCloseWarning(false);
  };

  const handleSignoffComplete = async () => {
    if (!signoffTemplate) return;
    setSignoffSubmitting(true);
    try {
      const updatedSteps = signoffTemplate.template_definition.transfer_steps.map((s) =>
        s.mandatory_review ? { ...s, mandatory_review: false } : s
      );
      const updatedDef: TemplateDefinition = {
        ...signoffTemplate.template_definition,
        transfer_steps: updatedSteps,
        mandatory_review_count: 0,
      };
      await apiService.updateExperimentTemplate(String(signoffTemplate.id), {
        template_definition: updatedDef as unknown as Record<string, unknown>,
      });
      await loadTemplates();
      setSignoffOpen(false);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(e.response?.data?.detail || e.message || 'Failed to complete sign-off');
    } finally {
      setSignoffSubmitting(false);
    }
  };

  const handleActivationToggle = async (row: ExperimentTemplateRow) => {
    try {
      await apiService.updateExperimentTemplate(String(row.id), { active: !row.active });
      await loadTemplates();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e.response?.data?.detail || 'Failed to update template status');
    }
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
      field: 'plate_layout',
      headerName: 'Plate',
      width: 100,
      valueGetter: (_: unknown, row: ExperimentTemplateRow) =>
        row.template_definition?.plate_layout ?? '—',
    },
    {
      field: 'status',
      headerName: 'Status',
      width: 170,
      renderCell: (params) => {
        const row = params.row as ExperimentTemplateRow;
        const count = row.template_definition?.mandatory_review_count ?? 0;
        if (count > 0) {
          return (
            <Chip
              label={`${count} pending sign-off${count !== 1 ? 's' : ''}`}
              size="small"
              color="warning"
              variant="filled"
              sx={{ cursor: 'pointer' }}
              onClick={() => openSignoff(row)}
            />
          );
        }
        return <Chip label="Ready" size="small" color="success" variant="outlined" />;
      },
    },
    {
      field: 'active',
      headerName: 'Active',
      width: 90,
      renderCell: (params) => {
        const row = params.row as ExperimentTemplateRow;
        const needsSignoff = (row.template_definition?.mandatory_review_count ?? 0) > 0;
        const toggle = (
          <Switch
            size="small"
            checked={row.active}
            onChange={() => handleActivationToggle(row)}
            disabled={needsSignoff || !canManage}
            color="success"
          />
        );
        if (needsSignoff) {
          return (
            <Tooltip title="Sign-off required before activating this template">
              <span>{toggle}</span>
            </Tooltip>
          );
        }
        return toggle;
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
        const pendingSignoffs = (row.template_definition?.mandatory_review_count ?? 0) > 0;
        const actions: React.ReactElement[] = [];
        if (pendingSignoffs) {
          actions.push(
            <GridActionsCellItem
              key="signoff"
              icon={<RateReview />}
              label="Review Sign-offs"
              onClick={() => openSignoff(row)}
            />
          );
        }
        if (canManage) {
          actions.push(
            <GridActionsCellItem key="edit" icon={<Edit />} label="Edit" onClick={() => openEdit(row)} />,
            <GridActionsCellItem
              key="delete"
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget(row);
                setDeleteDialogOpen(true);
              }}
            />
          );
        }
        return actions;
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

  const pendingReviewSteps = signoffTemplate?.template_definition.transfer_steps.filter(
    (s) => s.mandatory_review
  ) ?? [];
  const allConfirmed =
    pendingReviewSteps.length > 0 && pendingReviewSteps.every((s) => signoffConfirmed.has(s.step));

  return (
    <Box sx={{ p: 2 }}>
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: 2,
          mb: 2,
        }}
      >
        <Typography variant="h5">Experiment Templates</Typography>
        {canManage && (
          <Button variant="contained" startIcon={<Add />} onClick={openCreate}>
            New Template
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* List */}
      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
          <CircularProgress />
        </Box>
      ) : (
        <Box sx={{ height: rows.length === 0 ? 'auto' : 600, minHeight: 220, width: '100%', mb: 2 }}>
          <DataGrid
            rows={rows}
            columns={columns}
            getRowId={(row) => row.id}
            pageSizeOptions={[10, 25, 50]}
            initialState={{ pagination: { paginationModel: { pageSize: 25 } } }}
            disableRowSelectionOnClick
            autoHeight={rows.length === 0}
            slots={{
              noRowsOverlay: () => (
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    height: '100%',
                    minHeight: 160,
                  }}
                >
                  <Typography>No experiment templates yet. Create one to get started.</Typography>
                </Box>
              ),
            }}
            sx={{ '& .MuiDataGrid-cell': { fontSize: theme.typography.body2.fontSize } }}
          />
        </Box>
      )}

      {/* ── Create/Edit Dialog ───────────────────────────────────────────── */}
      <Dialog open={formOpen} onClose={() => setFormOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle>
          {selectedTemplate ? `Edit Template: ${selectedTemplate.name}` : 'Create Experiment Template'}
        </DialogTitle>
        <DialogContent>
          {/* Tab-level error summary */}
          {tabErrors.some(Boolean) && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {tabErrors[0] && <div>Tab 1 (Basic Info): Name and Experiment Name are required.</div>}
              {tabErrors[1] && <div>Tab 2 (Protocol Steps): Check for empty steps.</div>}
              {tabErrors[2] && <div>Tab 3 (Transfer Steps): Check step entries.</div>}
              {tabErrors[3] && <div>Tab 4 (Result Columns): Check column entries.</div>}
            </Alert>
          )}

          <Tabs
            value={activeTab}
            onChange={(_, v) => setActiveTab(v)}
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab
              label="Basic Info"
              sx={{ color: tabErrors[0] ? 'error.main' : undefined }}
              icon={tabErrors[0] ? <span style={{ color: 'red', fontSize: 10 }}>●</span> : undefined}
              iconPosition="end"
            />
            <Tab label="Protocol Steps" />
            <Tab label="Transfer Steps" />
            <Tab label="Result Columns" />
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

          {/* Tab 2: Protocol Steps */}
          <TabPanel value={activeTab} index={1}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {formDef.protocol_steps.map((step, i) => (
                <Box key={i} sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                  <Typography variant="body2" sx={{ minWidth: 24, color: 'text.secondary' }}>
                    {i + 1}.
                  </Typography>
                  <TextField
                    fullWidth
                    size="small"
                    value={step}
                    onChange={(e) => updateProtocolStep(i, e.target.value)}
                    placeholder={`Step ${i + 1}`}
                  />
                  <IconButton size="small" onClick={() => removeProtocolStep(i)} color="error">
                    <Delete fontSize="small" />
                  </IconButton>
                </Box>
              ))}
              <Button
                startIcon={<Add />}
                onClick={addProtocolStep}
                variant="outlined"
                size="small"
                sx={{ alignSelf: 'flex-start', mt: 1 }}
              >
                Add Step
              </Button>
            </Box>
          </TabPanel>

          {/* Tab 3: Transfer Steps */}
          <TabPanel value={activeTab} index={2}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell width={40}>#</TableCell>
                  <TableCell>Source Plate</TableCell>
                  <TableCell>Source Well</TableCell>
                  <TableCell>Dest Plate</TableCell>
                  <TableCell>Dest Well</TableCell>
                  <TableCell width={90}>Vol (µL)</TableCell>
                  <TableCell>
                    <Tooltip title="When checked, a lab manager must review this step before the template can be activated">
                      <span>Requires sign-off</span>
                    </Tooltip>
                  </TableCell>
                  <TableCell width={48} />
                </TableRow>
              </TableHead>
              <TableBody>
                {formDef.transfer_steps.map((s, i) => (
                  <TableRow key={i}>
                    <TableCell>{s.step}</TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        value={s.source_plate ?? ''}
                        onChange={(e) => updateTransferStep(i, { source_plate: e.target.value })}
                        sx={{ width: 100 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        value={s.source_well ?? ''}
                        onChange={(e) => updateTransferStep(i, { source_well: e.target.value })}
                        sx={{ width: 80 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        value={s.dest_plate ?? ''}
                        onChange={(e) => updateTransferStep(i, { dest_plate: e.target.value })}
                        sx={{ width: 100 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        value={s.dest_well ?? ''}
                        onChange={(e) => updateTransferStep(i, { dest_well: e.target.value })}
                        sx={{ width: 80 }}
                      />
                    </TableCell>
                    <TableCell>
                      <TextField
                        size="small"
                        type="number"
                        value={s.volume_ul ?? ''}
                        onChange={(e) =>
                          updateTransferStep(i, {
                            volume_ul: e.target.value ? parseFloat(e.target.value) : undefined,
                          })
                        }
                        sx={{ width: 80 }}
                      />
                    </TableCell>
                    <TableCell>
                      <Switch
                        size="small"
                        checked={s.mandatory_review}
                        onChange={(e) => updateTransferStep(i, { mandatory_review: e.target.checked })}
                        color="warning"
                      />
                    </TableCell>
                    <TableCell>
                      <IconButton size="small" onClick={() => removeTransferStep(i)} color="error">
                        <Delete fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Button
              startIcon={<Add />}
              onClick={addTransferStep}
              variant="outlined"
              size="small"
              sx={{ mt: 2 }}
            >
              Add Transfer Step
            </Button>
          </TabPanel>

          {/* Tab 4: Result Columns */}
          <TabPanel value={activeTab} index={3}>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {formDef.result_columns.map((col, i) => (
                <Box key={i} sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                  <TextField
                    size="small"
                    label="Column name"
                    value={(col.name as string) ?? ''}
                    onChange={(e) => {
                      const updated = [...formDef.result_columns];
                      updated[i] = { ...updated[i], name: e.target.value };
                      setFormDef((d) => ({ ...d, result_columns: updated }));
                    }}
                    sx={{ flex: 1 }}
                  />
                  <TextField
                    size="small"
                    label="Type / unit"
                    value={(col.type as string) ?? ''}
                    onChange={(e) => {
                      const updated = [...formDef.result_columns];
                      updated[i] = { ...updated[i], type: e.target.value };
                      setFormDef((d) => ({ ...d, result_columns: updated }));
                    }}
                    sx={{ flex: 1 }}
                  />
                  <IconButton
                    size="small"
                    onClick={() =>
                      setFormDef((d) => ({
                        ...d,
                        result_columns: d.result_columns.filter((_, j) => j !== i),
                      }))
                    }
                    color="error"
                  >
                    <Delete fontSize="small" />
                  </IconButton>
                </Box>
              ))}
              <Button
                startIcon={<Add />}
                onClick={() =>
                  setFormDef((d) => ({ ...d, result_columns: [...d.result_columns, { name: '', type: '' }] }))
                }
                variant="outlined"
                size="small"
                sx={{ alignSelf: 'flex-start', mt: 1 }}
              >
                Add Column
              </Button>
            </Box>
          </TabPanel>

          {formError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {formError}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setFormOpen(false)} disabled={formSubmitting}>
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

      {/* ── Sign-off Dialog ──────────────────────────────────────────────── */}
      <Dialog open={signoffOpen} onClose={handleSignoffClose} maxWidth="md" fullWidth>
        <DialogTitle>
          Review Sign-offs — {signoffTemplate?.name}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Review each robot-affecting transfer step below. Confirm each step individually before
            this template can be activated.
          </Typography>

          {signoffCloseWarning && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              You have {pendingReviewSteps.filter((s) => !signoffConfirmed.has(s.step)).length} unconfirmed
              step(s). Progress will not be saved if you close now.
            </Alert>
          )}

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell width={40}>#</TableCell>
                <TableCell>Source</TableCell>
                <TableCell>Destination</TableCell>
                <TableCell width={90}>Volume</TableCell>
                <TableCell width={120}>Action</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {pendingReviewSteps.map((s) => {
                const confirmed = signoffConfirmed.has(s.step);
                return (
                  <TableRow
                    key={s.step}
                    sx={{ backgroundColor: confirmed ? 'success.light' : undefined, opacity: confirmed ? 0.7 : 1 }}
                  >
                    <TableCell>{s.step}</TableCell>
                    <TableCell>
                      {s.source_plate && s.source_well
                        ? `${s.source_plate}, ${s.source_well}`
                        : s.source_plate || s.source_well || '—'}
                    </TableCell>
                    <TableCell>
                      {s.dest_plate && s.dest_well
                        ? `${s.dest_plate}, ${s.dest_well}`
                        : s.dest_plate || s.dest_well || '—'}
                    </TableCell>
                    <TableCell>{s.volume_ul != null ? `${s.volume_ul} µL` : '—'}</TableCell>
                    <TableCell>
                      {confirmed ? (
                        <Chip label="Confirmed" size="small" color="success" />
                      ) : (
                        <Button size="small" variant="outlined" color="success" onClick={() => confirmStep(s.step)}>
                          Confirm
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleSignoffClose}>
            {signoffCloseWarning ? 'Close Anyway' : 'Close'}
          </Button>
          <Button
            variant="contained"
            color="success"
            onClick={handleSignoffComplete}
            disabled={!allConfirmed || signoffSubmitting}
          >
            {signoffSubmitting ? 'Saving...' : 'Complete Sign-off'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ExperimentTemplatesManagement;
