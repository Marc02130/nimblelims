import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
  Alert,
  CircularProgress,
  Divider,
  Chip,
  Autocomplete,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  Checkbox,
  FormControlLabel,
  IconButton,
} from '@mui/material';
import {
  Delete as DeleteIcon,
  Add as AddIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { apiService } from '../../services/apiService';
import { useUser } from '../../contexts/UserContext';

interface BatchFormEnhancedProps {
  onSuccess: (batch: any) => void;
  onCancel: () => void;
}

interface Container {
  id: string;
  name: string;
  type_id?: string;
  type?: {
    name: string;
  };
  sample?: {
    id: string;
    name: string;
    project_id: string;
    project?: {
      name: string;
    };
  };
}

interface Project {
  id: string;
  name: string;
}

interface QCAddition {
  qc_type: string;
  notes?: string;
}

interface BatchFormData {
  name: string;
  description: string;
  type: string;
  status: string;
  start_date: Date | null;
  end_date: Date | null;
  container_ids: string[];
  cross_project: boolean;
  divergent_analyses: string[];
  qc_additions: QCAddition[];
}

interface CompatibilityResult {
  compatible: boolean;
  error?: string;
  details?: {
    projects: string[];
    analyses: string[];
    suggestion?: string;
  };
}

const BatchFormEnhanced: React.FC<BatchFormEnhancedProps> = ({ onSuccess, onCancel }) => {
  const { user } = useUser();
  const [formData, setFormData] = useState<BatchFormData>({
    name: '',
    description: '',
    type: '',
    status: '',
    start_date: null,
    end_date: null,
    container_ids: [],
    cross_project: false,
    divergent_analyses: [],
    qc_additions: [],
  });

  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [compatibilityResult, setCompatibilityResult] = useState<CompatibilityResult | null>(null);
  
  const [listEntries, setListEntries] = useState<any>({});
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjects, setSelectedProjects] = useState<string[]>([]);
  const [containers, setContainers] = useState<Container[]>([]);
  const [selectedContainers, setSelectedContainers] = useState<Container[]>([]);
  const [containerSearchTerm, setContainerSearchTerm] = useState('');
  const [subBatchDialogOpen, setSubBatchDialogOpen] = useState(false);
  const [analyses, setAnalyses] = useState<any[]>([]);
  const [selectedDivergentAnalyses, setSelectedDivergentAnalyses] = useState<string[]>([]);
  const [qcTypes, setQcTypes] = useState<any[]>([]);
  const [qcRequired, setQcRequired] = useState(false);
  const [requireQcForBatchTypes, setRequireQcForBatchTypes] = useState<string[]>([]);

  // Load accessible projects from UserContext
  useEffect(() => {
    const loadProjects = async () => {
      try {
        const projectsResponse = await apiService.getProjects();
        // Extract projects array from paginated response
        const projectsArray = projectsResponse.projects || projectsResponse || [];
        setProjects(Array.isArray(projectsArray) ? projectsArray : []);
        // Auto-select all accessible projects for cross-project batching
        if (projectsArray && Array.isArray(projectsArray) && projectsArray.length > 0) {
          setSelectedProjects(projectsArray.map((p: Project) => p.id));
        }
      } catch (err) {
        console.error('Failed to load projects:', err);
      }
    };
    loadProjects();
  }, []);

  // Load containers when projects are selected
  useEffect(() => {
    const loadContainers = async () => {
      if (selectedProjects.length === 0) {
        setContainers([]);
        return;
      }

      try {
        const containersData = await apiService.getContainers({
          project_ids: selectedProjects,
        });
        setContainers(containersData || []);
      } catch (err) {
        console.error('Failed to load containers:', err);
      }
    };

    loadContainers();
  }, [selectedProjects]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [batchStatuses, batchTypes, analysesData, qcTypesData] = await Promise.all([
          apiService.getListEntries('batch_status'),
          apiService.getListEntries('batch_types').catch(() => []),
          apiService.getAnalyses().catch(() => []),
          apiService.getListEntries('qc_types').catch(() => []),
        ]);

        setListEntries({
          batch_statuses: batchStatuses,
          batch_types: batchTypes,
        });
        setAnalyses(analysesData || []);
        setQcTypes(qcTypesData || []);

        // Load QC requirement config from environment or API
        // For now, check if REQUIRE_QC_FOR_BATCH_TYPES env var is set
        // In production, this would come from a config endpoint
        const requireQcEnv = process.env.REACT_APP_REQUIRE_QC_FOR_BATCH_TYPES;
        if (requireQcEnv) {
          const requiredTypes = requireQcEnv.split(',').map(t => t.trim());
          setRequireQcForBatchTypes(requiredTypes);
        }

        // Set default status to 'Created'
        const createdStatus = batchStatuses.find((status: any) => status.name === 'Created');
        if (createdStatus) {
          setFormData(prev => ({ ...prev, status: createdStatus.id }));
        }
      } catch (err) {
        setError('Failed to load form data');
      }
    };

    loadData();
  }, []);

  // Auto-detect cross-project if containers from multiple projects
  useEffect(() => {
    if (selectedContainers.length > 0) {
      const projectIds = new Set(
        selectedContainers
          .map(c => c.sample?.project_id)
          .filter(Boolean)
      );
      setFormData(prev => ({
        ...prev,
        cross_project: projectIds.size > 1,
        container_ids: selectedContainers.map(c => c.id),
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        cross_project: false,
        container_ids: [],
      }));
    }
  }, [selectedContainers]);

  // Check if QC is required for selected batch type
  useEffect(() => {
    if (formData.type && requireQcForBatchTypes.length > 0) {
      const isRequired = requireQcForBatchTypes.includes(formData.type);
      setQcRequired(isRequired);
      
      // If QC becomes required and no QC additions exist, show warning
      if (isRequired && formData.qc_additions.length === 0) {
        setValidationError('QC samples are required for this batch type');
      } else if (!isRequired) {
        setValidationError(null);
      }
    } else {
      setQcRequired(false);
    }
  }, [formData.type, requireQcForBatchTypes, formData.qc_additions.length]);

  // Suggest QC based on batch size and type
  const suggestQC = () => {
    const containerCount = selectedContainers.length;
    const suggestions: QCAddition[] = [];

    // Suggest QC based on batch size
    if (containerCount >= 10) {
      // Large batches: suggest Blank, Blank Spike, Matrix Spike
      const blankType = qcTypes.find(qt => qt.name.toLowerCase().includes('blank') && !qt.name.toLowerCase().includes('spike'));
      const blankSpikeType = qcTypes.find(qt => qt.name.toLowerCase().includes('blank spike'));
      const matrixSpikeType = qcTypes.find(qt => qt.name.toLowerCase().includes('matrix spike'));

      if (blankType) suggestions.push({ qc_type: blankType.id, notes: 'Auto-suggested for large batch' });
      if (blankSpikeType) suggestions.push({ qc_type: blankSpikeType.id, notes: 'Auto-suggested for large batch' });
      if (matrixSpikeType) suggestions.push({ qc_type: matrixSpikeType.id, notes: 'Auto-suggested for large batch' });
    } else if (containerCount >= 5) {
      // Medium batches: suggest Blank and Matrix Spike
      const blankType = qcTypes.find(qt => qt.name.toLowerCase().includes('blank') && !qt.name.toLowerCase().includes('spike'));
      const matrixSpikeType = qcTypes.find(qt => qt.name.toLowerCase().includes('matrix spike'));

      if (blankType) suggestions.push({ qc_type: blankType.id, notes: 'Auto-suggested for medium batch' });
      if (matrixSpikeType) suggestions.push({ qc_type: matrixSpikeType.id, notes: 'Auto-suggested for medium batch' });
    } else if (containerCount >= 2) {
      // Small batches: suggest Blank
      const blankType = qcTypes.find(qt => qt.name.toLowerCase().includes('blank') && !qt.name.toLowerCase().includes('spike'));
      if (blankType) suggestions.push({ qc_type: blankType.id, notes: 'Auto-suggested for small batch' });
    }

    // Add suggestions if not already present
    if (suggestions.length > 0 && formData.qc_additions.length === 0) {
      setFormData(prev => ({
        ...prev,
        qc_additions: suggestions,
      }));
    }
  };

  // Auto-suggest QC when containers are added
  useEffect(() => {
    if (selectedContainers.length >= 2 && formData.qc_additions.length === 0 && qcTypes.length > 0) {
      // Only suggest if user hasn't manually added QC
      // This is a one-time suggestion
      const shouldSuggest = !localStorage.getItem(`qc_suggested_${formData.name || 'new'}`);
      if (shouldSuggest && selectedContainers.length >= 2) {
        suggestQC();
        localStorage.setItem(`qc_suggested_${formData.name || 'new'}`, 'true');
      }
    }
  }, [selectedContainers.length, qcTypes.length]);

  const handleInputChange = (field: keyof BatchFormData, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleValidateCompatibility = async () => {
    if (selectedContainers.length < 2) {
      setValidationError('Please select at least 2 containers to validate compatibility');
      return;
    }

    setValidating(true);
    setValidationError(null);
    setCompatibilityResult(null);

    try {
      const result = await apiService.validateBatchCompatibility({
        container_ids: selectedContainers.map(c => c.id),
      });
      setCompatibilityResult(result);
      if (!result.compatible) {
        setValidationError(result.error || 'Containers are not compatible for cross-project batching');
      }
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      setValidationError(
        typeof errorDetail === 'string'
          ? errorDetail
          : errorDetail?.error || 'Failed to validate compatibility'
      );
      setCompatibilityResult({
        compatible: false,
        error: errorDetail?.error || 'Validation failed',
        details: errorDetail?.details,
      });
    } finally {
      setValidating(false);
    }
  };

  const handleAddContainer = (container: Container) => {
    if (!selectedContainers.find(c => c.id === container.id)) {
      setSelectedContainers(prev => [...prev, container]);
      setContainerSearchTerm('');
    }
  };

  const handleRemoveContainer = (containerId: string) => {
    setSelectedContainers(prev => prev.filter(c => c.id !== containerId));
    setCompatibilityResult(null);
    setValidationError(null);
  };

  const handleOpenSubBatchDialog = () => {
    setSubBatchDialogOpen(true);
  };

  const handleCloseSubBatchDialog = () => {
    setSubBatchDialogOpen(false);
  };

  const handleCreateSubBatches = () => {
    setFormData(prev => ({
      ...prev,
      divergent_analyses: selectedDivergentAnalyses,
    }));
    handleCloseSubBatchDialog();
  };

  const handleAddQC = () => {
    setFormData(prev => ({
      ...prev,
      qc_additions: [...prev.qc_additions, { qc_type: '', notes: '' }],
    }));
  };

  const handleRemoveQC = (index: number) => {
    setFormData(prev => ({
      ...prev,
      qc_additions: prev.qc_additions.filter((_, i) => i !== index),
    }));
  };

  const handleQCChange = (index: number, field: keyof QCAddition, value: string) => {
    setFormData(prev => ({
      ...prev,
      qc_additions: prev.qc_additions.map((qc, i) =>
        i === index ? { ...qc, [field]: value } : qc
      ),
    }));
  };

  const filteredContainers = useMemo(() => {
    if (!containerSearchTerm) return containers;
    const term = containerSearchTerm.toLowerCase();
    return containers.filter(
      c =>
        c.name.toLowerCase().includes(term) ||
        c.sample?.name.toLowerCase().includes(term) ||
        c.sample?.project?.name.toLowerCase().includes(term)
    );
  }, [containers, containerSearchTerm]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    // Validate QC requirement
    if (qcRequired && formData.qc_additions.length === 0) {
      setError('QC samples are required for this batch type. Please add at least one QC sample.');
      setLoading(false);
      return;
    }

    // Validate QC additions have qc_type
    const invalidQC = formData.qc_additions.some(qc => !qc.qc_type);
    if (formData.qc_additions.length > 0 && invalidQC) {
      setError('All QC additions must have a QC type selected.');
      setLoading(false);
      return;
    }

    try {
      const batchData = {
        name: formData.name,
        description: formData.description,
        type: formData.type || undefined,
        status: formData.status,
        start_date: formData.start_date?.toISOString(),
        end_date: formData.end_date?.toISOString(),
        container_ids: formData.container_ids.length > 0 ? formData.container_ids : undefined,
        cross_project: formData.cross_project,
        divergent_analyses: formData.divergent_analyses.length > 0 ? formData.divergent_analyses : undefined,
        qc_additions: formData.qc_additions.length > 0 ? formData.qc_additions.map(qc => ({
          qc_type: qc.qc_type,
          notes: qc.notes || undefined,
        })) : undefined,
      };

      const result = await apiService.createBatch(batchData);
      onSuccess(result);
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      setError(
        typeof errorDetail === 'string'
          ? errorDetail
          : errorDetail?.error || 'Failed to create batch'
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Create New Batch
          </Typography>
          <Divider sx={{ mb: 2 }} />

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <Grid container spacing={3}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Batch Name"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  required
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Description"
                  value={formData.description}
                  onChange={(e) => handleInputChange('description', e.target.value)}
                />
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth>
                  <InputLabel>Batch Type</InputLabel>
                  <Select
                    value={formData.type}
                    onChange={(e) => handleInputChange('type', e.target.value)}
                  >
                    {listEntries.batch_types?.map((entry: any) => (
                      <MenuItem key={entry.id} value={entry.id}>
                        {entry.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth required>
                  <InputLabel>Status</InputLabel>
                  <Select
                    value={formData.status}
                    onChange={(e) => handleInputChange('status', e.target.value)}
                  >
                    {listEntries.batch_statuses?.map((entry: any) => (
                      <MenuItem key={entry.id} value={entry.id}>
                        {entry.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <DatePicker
                  label="Start Date"
                  value={formData.start_date}
                  onChange={(date) => handleInputChange('start_date', date)}
                  slotProps={{ textField: { fullWidth: true } }}
                />
              </Grid>

              {/* End date is not available when creating a batch - only set when batch is completed */}
              {/* <Grid size={{ xs: 12, sm: 6 }}>
                <DatePicker
                  label="End Date"
                  value={formData.end_date}
                  onChange={(date) => handleInputChange('end_date', date)}
                  slotProps={{ textField: { fullWidth: true } }}
                />
              </Grid> */}

              <Grid size={12}>
                <Divider sx={{ my: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Cross-Project Container Selection
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Select containers from multiple projects for cross-project batching. Containers must share compatible analyses.
                </Typography>
              </Grid>

              <Grid size={12}>
                <FormControl fullWidth>
                  <InputLabel>Filter by Projects</InputLabel>
                  <Select
                    multiple
                    value={selectedProjects}
                    onChange={(e) => setSelectedProjects(e.target.value as string[])}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {(selected as string[]).map((projectId) => {
                          const project = projects.find(p => p.id === projectId);
                          return <Chip key={projectId} label={project?.name || projectId} size="small" />;
                        })}
                      </Box>
                    )}
                  >
                    {projects.map((project) => (
                      <MenuItem key={project.id} value={project.id}>
                        <Checkbox checked={selectedProjects.includes(project.id)} />
                        {project.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={12}>
                <Autocomplete
                  options={filteredContainers}
                  getOptionLabel={(option) =>
                    `${option.name}${option.sample ? ` - ${option.sample.name} (${option.sample.project?.name || 'Unknown Project'})` : ''}`
                  }
                  value={null}
                  inputValue={containerSearchTerm}
                  onInputChange={(_, newValue) => setContainerSearchTerm(newValue)}
                  onChange={(_, newValue) => {
                    if (newValue) {
                      handleAddContainer(newValue);
                    }
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Search and Add Containers"
                      placeholder="Type to search containers..."
                    />
                  )}
                  renderOption={(props, option) => (
                    <li {...props} key={option.id}>
                      <Box>
                        <Typography variant="body1">{option.name}</Typography>
                        {option.sample && (
                          <Typography variant="body2" color="text.secondary">
                            Sample: {option.sample.name} | Project: {option.sample.project?.name || 'Unknown'}
                          </Typography>
                        )}
                      </Box>
                    </li>
                  )}
                />
              </Grid>

              {selectedContainers.length > 0 && (
                <Grid size={12}>
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Selected Containers ({selectedContainers.length})
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {selectedContainers.map((container) => (
                        <Chip
                          key={container.id}
                          label={`${container.name}${container.sample ? ` (${container.sample.project?.name})` : ''}`}
                          onDelete={() => handleRemoveContainer(container.id)}
                          deleteIcon={<DeleteIcon />}
                        />
                      ))}
                    </Box>
                  </Box>

                  {formData.cross_project && (
                    <Alert severity="info" sx={{ mb: 2 }}>
                      Cross-project batch detected: Containers from multiple projects selected.
                    </Alert>
                  )}

                  <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                    <Button
                      variant="outlined"
                      onClick={handleValidateCompatibility}
                      disabled={validating || selectedContainers.length < 2}
                      startIcon={validating ? <CircularProgress size={20} /> : <CheckCircleIcon />}
                    >
                      Validate Compatibility
                    </Button>
                    <Button
                      variant="outlined"
                      onClick={handleOpenSubBatchDialog}
                      startIcon={<AddIcon />}
                    >
                      Create Sub-Batches
                    </Button>
                  </Box>

                  {compatibilityResult && (
                    <Alert
                      severity={compatibilityResult.compatible ? 'success' : 'warning'}
                      icon={compatibilityResult.compatible ? <CheckCircleIcon /> : <WarningIcon />}
                      sx={{ mb: 2 }}
                    >
                      {compatibilityResult.compatible ? (
                        'Containers are compatible for cross-project batching'
                      ) : (
                        <Box>
                          <Typography variant="body2" fontWeight="bold">
                            {compatibilityResult.error || 'Containers are not compatible'}
                          </Typography>
                          {compatibilityResult.details && (
                            <Box sx={{ mt: 1 }}>
                              {compatibilityResult.details.projects && (
                                <Typography variant="body2">
                                  Projects: {compatibilityResult.details.projects.join(', ')}
                                </Typography>
                              )}
                              {compatibilityResult.details.analyses && (
                                <Typography variant="body2">
                                  Analyses: {compatibilityResult.details.analyses.join(', ')}
                                </Typography>
                              )}
                              {compatibilityResult.details.suggestion && (
                                <Typography variant="body2" sx={{ mt: 1, fontStyle: 'italic' }}>
                                  {compatibilityResult.details.suggestion}
                                </Typography>
                              )}
                            </Box>
                          )}
                        </Box>
                      )}
                    </Alert>
                  )}

                  {validationError && !compatibilityResult && (
                    <Alert severity="error" sx={{ mb: 2 }}>
                      {validationError}
                    </Alert>
                  )}
                </Grid>
              )}

              {formData.divergent_analyses.length > 0 && (
                <Grid size={12}>
                  <Alert severity="info" sx={{ mb: 2 }}>
                    Sub-batches will be created for divergent analyses: {formData.divergent_analyses.length} selected
                  </Alert>
                </Grid>
              )}

              <Grid size={12}>
                <Divider sx={{ my: 2 }} />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" gutterBottom>
                    QC Samples
                  </Typography>
                  <Button
                    variant="outlined"
                    size="small"
                    startIcon={<AddIcon />}
                    onClick={handleAddQC}
                  >
                    Add QC
                  </Button>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Add QC samples to be auto-generated with this batch. QC samples will inherit properties from the first sample in the batch.
                  {selectedContainers.length >= 2 && (
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={suggestQC}
                      sx={{ ml: 2 }}
                      startIcon={<AddIcon />}
                    >
                      Suggest QC ({selectedContainers.length} containers)
                    </Button>
                  )}
                </Typography>

                {qcRequired && formData.qc_additions.length === 0 && (
                  <Alert severity="warning" sx={{ mb: 2 }}>
                    QC samples are required for batch type "{listEntries.batch_types?.find((t: any) => t.id === formData.type)?.name || formData.type}". Please add at least one QC sample.
                  </Alert>
                )}

                {formData.qc_additions.map((qc, index) => (
                  <Box
                    key={index}
                    sx={{
                      p: 2,
                      mb: 2,
                      border: '1px solid',
                      borderColor: 'divider',
                      borderRadius: 1,
                      bgcolor: 'background.paper',
                    }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                      <Typography variant="subtitle2">
                        QC Sample {index + 1}
                      </Typography>
                      <IconButton
                        size="small"
                        onClick={() => handleRemoveQC(index)}
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                    <Grid container spacing={2}>
                      <Grid size={{ xs: 12, sm: 6 }}>
                        <FormControl fullWidth required>
                          <InputLabel>QC Type</InputLabel>
                          <Select
                            value={qc.qc_type}
                            onChange={(e) => handleQCChange(index, 'qc_type', e.target.value)}
                            label="QC Type"
                          >
                            {qcTypes.map((qcType) => (
                              <MenuItem key={qcType.id} value={qcType.id}>
                                {qcType.name}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Grid>
                      <Grid size={{ xs: 12, sm: 6 }}>
                        <TextField
                          fullWidth
                          label="Notes (Optional)"
                          value={qc.notes || ''}
                          onChange={(e) => handleQCChange(index, 'notes', e.target.value)}
                          placeholder="Additional notes for this QC sample"
                        />
                      </Grid>
                    </Grid>
                  </Box>
                ))}

                {formData.qc_additions.length === 0 && !qcRequired && (
                  <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                    No QC samples added. Click "Add QC" to add QC samples to this batch.
                  </Typography>
                )}
              </Grid>

              <Grid size={12}>
                <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end', mt: 2 }}>
                  <Button onClick={onCancel} disabled={loading}>
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="contained"
                    disabled={loading || !formData.name || !formData.status}
                    startIcon={loading && <CircularProgress size={20} />}
                  >
                    Create Batch
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </form>

          {/* Sub-Batch Creation Dialog */}
          <Dialog open={subBatchDialogOpen} onClose={handleCloseSubBatchDialog} maxWidth="sm" fullWidth>
            <DialogTitle>Create Sub-Batches for Divergent Analyses</DialogTitle>
            <DialogContent>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Select analyses that require separate sub-batches due to divergent processing steps.
              </Typography>
              <List>
                {analyses.map((analysis) => (
                  <ListItem key={analysis.id}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={selectedDivergentAnalyses.includes(analysis.id)}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setSelectedDivergentAnalyses(prev => [...prev, analysis.id]);
                            } else {
                              setSelectedDivergentAnalyses(prev => prev.filter(id => id !== analysis.id));
                            }
                          }}
                        />
                      }
                      label={
                        <Box>
                          <Typography variant="body1">{analysis.name}</Typography>
                          {analysis.method && (
                            <Typography variant="body2" color="text.secondary">
                              Method: {analysis.method}
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </DialogContent>
            <DialogActions>
              <Button onClick={handleCloseSubBatchDialog}>Cancel</Button>
              <Button onClick={handleCreateSubBatches} variant="contained">
                Apply
              </Button>
            </DialogActions>
          </Dialog>
        </CardContent>
      </Card>
    </LocalizationProvider>
  );
};

export default BatchFormEnhanced;

