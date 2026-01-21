import React, { useState, useEffect, useMemo, useCallback } from 'react';
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
  Tooltip,
  Stepper,
  Step,
  StepLabel,
  Paper,
} from '@mui/material';
import {
  Delete as DeleteIcon,
  Add as AddIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  ArrowForward as ArrowForwardIcon,
  ArrowBack as ArrowBackIcon,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridRenderCellParams, GridSortModel, GridRowSelectionModel } from '@mui/x-data-grid';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { apiService, EligibleSample, BatchCompatibilityResult, BatchCompatibilityWarning } from '../../services/apiService';
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
  container_type_id: string;
  matrix_id: string;
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

const STEPS = ['Batch Details', 'Select Eligible Samples', 'QC Samples', 'Review & Create'];

const BatchFormEnhanced: React.FC<BatchFormEnhancedProps> = ({ onSuccess, onCancel }) => {
  const { user } = useUser();
  const [activeStep, setActiveStep] = useState(0);
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
  const [compatibilityResult, setCompatibilityResult] = useState<BatchCompatibilityResult | null>(null);
  const [compatibilityWarnings, setCompatibilityWarnings] = useState<BatchCompatibilityWarning[]>([]);
  
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
  const [containerTypes, setContainerTypes] = useState<any[]>([]);
  const [matrixTypes, setMatrixTypes] = useState<any[]>([]);
  const [qcRequired, setQcRequired] = useState(false);
  const [requireQcForBatchTypes, setRequireQcForBatchTypes] = useState<string[]>([]);
  
  // Eligible samples state for Step 2
  const [eligibleSamples, setEligibleSamples] = useState<EligibleSample[]>([]);
  const [eligibleSamplesLoading, setEligibleSamplesLoading] = useState(false);
  const [eligibleSamplesWarnings, setEligibleSamplesWarnings] = useState<string[]>([]);
  const [selectedSampleIds, setSelectedSampleIds] = useState<GridRowSelectionModel>({ type: 'include', ids: new Set() });
  const [includeExpired, setIncludeExpired] = useState(false);
  const [selectedAnalysisIds, setSelectedAnalysisIds] = useState<string[]>([]);
  const [sortModel, setSortModel] = useState<GridSortModel>([
    { field: 'days_until_expiration', sort: 'asc' },
    { field: 'days_until_due', sort: 'asc' },
  ]);

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
        const [batchStatuses, batchTypes, analysesResponse, qcTypesData, containerTypesData, matrixTypesData] = await Promise.all([
          apiService.getListEntries('batch_status'),
          apiService.getListEntries('batch_types').catch(() => []),
          apiService.getAnalyses().catch(() => ({ analyses: [] })),
          apiService.getListEntries('qc_types').catch(() => []),
          apiService.getContainerTypes().catch(() => []),
          apiService.getListEntries('matrix_types').catch(() => []),
        ]);

        setListEntries({
          batch_statuses: batchStatuses,
          batch_types: batchTypes,
        });
        // API returns paginated response {analyses, total, page, size, pages}
        setAnalyses(analysesResponse?.analyses || []);
        setQcTypes(qcTypesData || []);
        // Container types may also be paginated
        setContainerTypes(containerTypesData?.container_types || containerTypesData || []);
        setMatrixTypes(matrixTypesData || []);

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

  // Load eligible samples when entering Step 2
  const loadEligibleSamples = useCallback(async () => {
    setEligibleSamplesLoading(true);
    try {
      // Only fetch samples that have the selected analyses/tests assigned
      const testIds = selectedAnalysisIds.length > 0 ? selectedAnalysisIds.join(',') : undefined;
      
      const response = await apiService.getEligibleSamples({
        test_ids: testIds,
        project_id: selectedProjects.length === 1 ? selectedProjects[0] : undefined,
        include_expired: includeExpired,
        size: 100, // Load more for better selection
      });
      
      setEligibleSamples(response.samples);
      setEligibleSamplesWarnings(response.warnings);
    } catch (err) {
      console.error('Failed to load eligible samples:', err);
      setError('Failed to load eligible samples');
    } finally {
      setEligibleSamplesLoading(false);
    }
  }, [selectedProjects, includeExpired, selectedAnalysisIds]);

  // Load eligible samples when step changes to Step 2 and analyses are selected
  useEffect(() => {
    if (activeStep === 1 && selectedAnalysisIds.length > 0) {
      loadEligibleSamples();
    } else if (activeStep === 1 && selectedAnalysisIds.length === 0) {
      // Clear samples when no analyses selected
      setEligibleSamples([]);
      setEligibleSamplesWarnings([]);
    }
  }, [activeStep, selectedAnalysisIds, loadEligibleSamples]);

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

  // Validate compatibility when moving to next step after sample selection
  const handleValidateOnStepChange = async () => {
    if (selectedContainers.length < 2) {
      return; // Skip validation if less than 2 containers
    }

    setValidating(true);
    setCompatibilityWarnings([]);

    try {
      const result = await apiService.validateBatchCompatibility({
        container_ids: selectedContainers.map(c => c.id),
      });
      setCompatibilityResult(result);
      
      // Handle warnings for expired/expiring samples
      if (result.warnings && result.warnings.length > 0) {
        setCompatibilityWarnings(result.warnings);
      }
      
      if (!result.compatible) {
        setValidationError(result.error || 'Containers are not compatible for cross-project batching');
        return false;
      }
      return true;
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      setValidationError(
        typeof errorDetail === 'string'
          ? errorDetail
          : errorDetail?.error || 'Failed to validate compatibility'
      );
      return false;
    } finally {
      setValidating(false);
    }
  };

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

      if (blankType) suggestions.push({ qc_type: blankType.id, container_type_id: '', matrix_id: '', notes: 'Auto-suggested for large batch' });
      if (blankSpikeType) suggestions.push({ qc_type: blankSpikeType.id, container_type_id: '', matrix_id: '', notes: 'Auto-suggested for large batch' });
      if (matrixSpikeType) suggestions.push({ qc_type: matrixSpikeType.id, container_type_id: '', matrix_id: '', notes: 'Auto-suggested for large batch' });
    } else if (containerCount >= 5) {
      // Medium batches: suggest Blank and Matrix Spike
      const blankType = qcTypes.find(qt => qt.name.toLowerCase().includes('blank') && !qt.name.toLowerCase().includes('spike'));
      const matrixSpikeType = qcTypes.find(qt => qt.name.toLowerCase().includes('matrix spike'));

      if (blankType) suggestions.push({ qc_type: blankType.id, container_type_id: '', matrix_id: '', notes: 'Auto-suggested for medium batch' });
      if (matrixSpikeType) suggestions.push({ qc_type: matrixSpikeType.id, container_type_id: '', matrix_id: '', notes: 'Auto-suggested for medium batch' });
    } else if (containerCount >= 2) {
      // Small batches: suggest Blank
      const blankType = qcTypes.find(qt => qt.name.toLowerCase().includes('blank') && !qt.name.toLowerCase().includes('spike'));
      if (blankType) suggestions.push({ qc_type: blankType.id, container_type_id: '', matrix_id: '', notes: 'Auto-suggested for small batch' });
    }

    // Add suggestions if not already present
    if (suggestions.length > 0 && formData.qc_additions.length === 0) {
      setFormData(prev => ({
        ...prev,
        qc_additions: suggestions,
      }));
    }
  };

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
    setCompatibilityWarnings([]);

    try {
      const result = await apiService.validateBatchCompatibility({
        container_ids: selectedContainers.map(c => c.id),
      });
      setCompatibilityResult(result);
      
      // Handle warnings for expired/expiring samples
      if (result.warnings && result.warnings.length > 0) {
        setCompatibilityWarnings(result.warnings);
      }
      
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
    setCompatibilityWarnings([]);
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
      qc_additions: [...prev.qc_additions, { qc_type: '', container_type_id: '', matrix_id: '', notes: '' }],
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

  // DataGrid columns for eligible samples with prioritization
  const eligibleSamplesColumns: GridColDef[] = useMemo(() => [
    {
      field: 'name',
      headerName: 'Sample Name',
      flex: 1,
      minWidth: 150,
    },
    {
      field: 'project_name',
      headerName: 'Project',
      flex: 1,
      minWidth: 120,
    },
    {
      field: 'days_until_expiration',
      headerName: 'Days to Expiration',
      width: 150,
      type: 'number',
      sortable: true,
      renderHeader: () => (
        <Tooltip title="Days until sample expires based on date_sampled + shelf_life. Sorted by expiration priority.">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }} aria-label="Sorted by expiration priority">
            <ScheduleIcon fontSize="small" />
            <span>Days to Expiration</span>
          </Box>
        </Tooltip>
      ),
      renderCell: (params: GridRenderCellParams) => {
        const days = params.value as number | null;
        const isExpired = params.row.is_expired;
        
        if (days === null || days === undefined) {
          return <Typography color="text.secondary">—</Typography>;
        }
        
        const isNegative = days < 0;
        const isUrgent = days <= 3 && days >= 0;
        
        return (
          <Tooltip 
            title={isExpired ? 'Expired: Testing invalid' : (isUrgent ? 'Expiring soon' : '')}
            aria-label={isExpired ? 'Sample expired - testing invalid' : (isUrgent ? 'Sample expiring soon' : `${days} days until expiration`)}
          >
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.5,
                color: isNegative ? 'error.main' : (isUrgent ? 'warning.main' : 'text.primary'),
                fontWeight: isNegative || isUrgent ? 'bold' : 'normal',
                bgcolor: isNegative ? 'error.light' : (isUrgent ? 'warning.light' : 'transparent'),
                px: 1,
                py: 0.5,
                borderRadius: 1,
              }}
            >
              {isNegative && <ErrorIcon fontSize="small" />}
              {isUrgent && !isNegative && <WarningIcon fontSize="small" />}
              <span>{days}</span>
            </Box>
          </Tooltip>
        );
      },
    },
    {
      field: 'days_until_due',
      headerName: 'Days to Due',
      width: 130,
      type: 'number',
      sortable: true,
      renderHeader: () => (
        <Tooltip title="Days until due date (sample or project). Negative means overdue.">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }} aria-label="Days until due date">
            <ScheduleIcon fontSize="small" />
            <span>Days to Due</span>
          </Box>
        </Tooltip>
      ),
      renderCell: (params: GridRenderCellParams) => {
        const days = params.value as number | null;
        const isOverdue = params.row.is_overdue;
        
        if (days === null || days === undefined) {
          return <Typography color="text.secondary">—</Typography>;
        }
        
        const isNegative = days < 0;
        const isUrgent = days <= 3 && days >= 0;
        
        return (
          <Tooltip 
            title={isOverdue ? 'Overdue' : (isUrgent ? 'Due soon' : '')}
            aria-label={isOverdue ? 'Sample overdue' : (isUrgent ? 'Sample due soon' : `${days} days until due`)}
          >
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.5,
                color: isNegative ? 'error.main' : (isUrgent ? 'warning.main' : 'text.primary'),
                fontWeight: isNegative || isUrgent ? 'bold' : 'normal',
                bgcolor: isNegative ? 'error.light' : (isUrgent ? 'warning.light' : 'transparent'),
                px: 1,
                py: 0.5,
                borderRadius: 1,
              }}
            >
              {isNegative && <ErrorIcon fontSize="small" />}
              {isUrgent && !isNegative && <WarningIcon fontSize="small" />}
              <span>{days}</span>
            </Box>
          </Tooltip>
        );
      },
    },
    {
      field: 'analysis_name',
      headerName: 'Analysis',
      flex: 1,
      minWidth: 120,
      renderCell: (params: GridRenderCellParams) => params.value || '—',
    },
    {
      field: 'shelf_life',
      headerName: 'Shelf Life (days)',
      width: 120,
      type: 'number',
      renderCell: (params: GridRenderCellParams) => params.value ?? '—',
    },
    {
      field: 'expiration_warning',
      headerName: 'Warning',
      width: 180,
      renderCell: (params: GridRenderCellParams) => {
        const warning = params.value as string | null;
        if (!warning) return null;
        
        const isExpired = params.row.is_expired;
        return (
          <Chip
            size="small"
            icon={isExpired ? <ErrorIcon /> : <WarningIcon />}
            label={warning}
            color={isExpired ? 'error' : 'warning'}
            sx={{ maxWidth: '100%' }}
          />
        );
      },
    },
  ], []);

  const handleNext = async () => {
    // Validate on step 1 -> 2 transition if containers are selected
    if (activeStep === 1 && selectedContainers.length >= 2) {
      const isValid = await handleValidateOnStepChange();
      if (!isValid) {
        // Show validation error but don't prevent navigation if compatible
        // User can still proceed with warnings
      }
    }
    
    setActiveStep(prev => Math.min(prev + 1, STEPS.length - 1));
  };

  const handleBack = () => {
    setActiveStep(prev => Math.max(prev - 1, 0));
  };

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

    // Validate QC additions have qc_type and container_id
    const invalidQCType = formData.qc_additions.some(qc => !qc.qc_type);
    if (formData.qc_additions.length > 0 && invalidQCType) {
      setError('All QC additions must have a QC type selected.');
      setLoading(false);
      return;
    }

    const invalidQCContainerType = formData.qc_additions.some(qc => !qc.container_type_id);
    if (formData.qc_additions.length > 0 && invalidQCContainerType) {
      setError('All QC additions must have a container type selected.');
      setLoading(false);
      return;
    }

    const invalidQCMatrix = formData.qc_additions.some(qc => !qc.matrix_id);
    if (formData.qc_additions.length > 0 && invalidQCMatrix) {
      setError('All QC additions must have a matrix selected.');
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
          container_type_id: qc.container_type_id,
          matrix_id: qc.matrix_id,
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

  // Render step content
  const renderStepContent = (step: number) => {
    switch (step) {
      case 0: // Batch Details
        return (
          <Grid container spacing={3}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                label="Batch Name"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                required
                inputProps={{ 'aria-label': 'Batch name' }}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                label="Description"
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                inputProps={{ 'aria-label': 'Batch description' }}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel id="batch-type-label">Batch Type</InputLabel>
                <Select
                  labelId="batch-type-label"
                  value={formData.type}
                  onChange={(e) => handleInputChange('type', e.target.value)}
                  label="Batch Type"
                  inputProps={{ 'aria-label': 'Batch type' }}
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
                <InputLabel id="batch-status-label">Status</InputLabel>
                <Select
                  labelId="batch-status-label"
                  value={formData.status}
                  onChange={(e) => handleInputChange('status', e.target.value)}
                  label="Status"
                  inputProps={{ 'aria-label': 'Batch status' }}
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
                slotProps={{ textField: { fullWidth: true, inputProps: { 'aria-label': 'Start date' } } }}
              />
            </Grid>
          </Grid>
        );

      case 1: // Select Eligible Samples
        return (
          <Box>
            <Typography variant="h6" gutterBottom>
              Eligible Samples
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Select the test(s)/analysis(es) to batch, then choose samples that have those tests assigned.
              Samples are sorted by expiration priority (most urgent first), then by due date.
            </Typography>

            {/* Analysis/Test Filter */}
            <Box sx={{ mb: 3 }}>
              <Autocomplete
                multiple
                id="analysis-filter"
                options={analyses}
                getOptionLabel={(option) => option.name || ''}
                value={analyses.filter(a => selectedAnalysisIds.includes(a.id))}
                onChange={(_, newValue) => {
                  setSelectedAnalysisIds(newValue.map(a => a.id));
                }}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Filter by Test/Analysis"
                    placeholder="Select tests to batch..."
                    helperText={selectedAnalysisIds.length === 0 
                      ? "Select one or more tests to see samples with those tests assigned" 
                      : `Showing samples with ${selectedAnalysisIds.length} selected test(s)`}
                  />
                )}
                renderTags={(value, getTagProps) =>
                  value.map((option, index) => (
                    <Chip
                      label={option.name}
                      {...getTagProps({ index })}
                      key={option.id}
                      color="primary"
                      size="small"
                    />
                  ))
                }
                sx={{ minWidth: 300 }}
              />
            </Box>

            {/* Info message when no analyses selected */}
            {selectedAnalysisIds.length === 0 && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Please select at least one test/analysis above to view eligible samples.
              </Alert>
            )}

            {/* Warnings for expired/overdue samples */}
            {eligibleSamplesWarnings.length > 0 && (
              <Box sx={{ mb: 2 }}>
                {eligibleSamplesWarnings.map((warning, idx) => (
                  <Alert key={idx} severity="warning" sx={{ mb: 1 }} icon={<WarningIcon />}>
                    {warning}
                  </Alert>
                ))}
              </Box>
            )}

            {/* Compatibility warnings */}
            {compatibilityWarnings.length > 0 && (
              <Box sx={{ mb: 2 }}>
                {compatibilityWarnings.map((warning, idx) => (
                  <Alert
                    key={idx}
                    severity={warning.type === 'expired_samples' ? 'error' : 'warning'}
                    sx={{ mb: 1 }}
                    icon={warning.type === 'expired_samples' ? <ErrorIcon /> : <WarningIcon />}
                  >
                    <Typography variant="subtitle2">{warning.message}</Typography>
                    {warning.samples && warning.samples.length > 0 && (
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="body2">
                          Affected samples: {warning.samples.map((s: any) => s.sample_name).join(', ')}
                        </Typography>
                      </Box>
                    )}
                  </Alert>
                ))}
              </Box>
            )}

            <Box sx={{ mb: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={includeExpired}
                    onChange={(e) => setIncludeExpired(e.target.checked)}
                    inputProps={{ 'aria-label': 'Include expired samples' }}
                  />
                }
                label="Include expired samples"
              />
              <Button
                variant="outlined"
                size="small"
                onClick={loadEligibleSamples}
                disabled={eligibleSamplesLoading || selectedAnalysisIds.length === 0}
              >
                Refresh
              </Button>
            </Box>

            <Paper sx={{ height: 400, width: '100%' }}>
              <DataGrid
                rows={eligibleSamples}
                columns={eligibleSamplesColumns}
                loading={eligibleSamplesLoading}
                checkboxSelection
                disableRowSelectionOnClick
                rowSelectionModel={selectedSampleIds}
                onRowSelectionModelChange={(newSelection) => {
                  setSelectedSampleIds(newSelection);
                }}
                sortModel={sortModel}
                onSortModelChange={(model) => setSortModel(model)}
                initialState={{
                  sorting: {
                    sortModel: [
                      { field: 'days_until_expiration', sort: 'asc' },
                    ],
                  },
                }}
                pageSizeOptions={[10, 25, 50]}
                getRowClassName={(params) => {
                  if (params.row.is_expired) return 'expired-row';
                  if (params.row.is_overdue) return 'overdue-row';
                  return '';
                }}
                sx={{
                  '& .expired-row': {
                    bgcolor: 'error.light',
                    '&:hover': {
                      bgcolor: 'error.main',
                    },
                  },
                  '& .overdue-row': {
                    bgcolor: 'warning.light',
                    '&:hover': {
                      bgcolor: 'warning.main',
                    },
                  },
                }}
                aria-label="Eligible samples grid sorted by expiration priority"
              />
            </Paper>

            <Divider sx={{ my: 3 }} />

            <Typography variant="h6" gutterBottom>
              Cross-Project Container Selection
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Select containers from multiple projects for cross-project batching. Containers must share compatible analyses.
            </Typography>

            <Grid container spacing={2}>
              <Grid size={12}>
                <FormControl fullWidth>
                  <InputLabel id="filter-projects-label">Filter by Projects</InputLabel>
                  <Select
                    labelId="filter-projects-label"
                    multiple
                    value={selectedProjects}
                    onChange={(e) => setSelectedProjects(e.target.value as string[])}
                    label="Filter by Projects"
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
                      inputProps={{
                        ...params.inputProps,
                        'aria-label': 'Search containers',
                      }}
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
            </Grid>

            {selectedContainers.length > 0 && (
              <Box sx={{ mt: 2 }}>
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

                {formData.cross_project && (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    Cross-project batch detected: Containers from multiple projects selected.
                  </Alert>
                )}

                <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
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

                {compatibilityResult && !compatibilityWarnings.length && (
                  <Alert
                    severity={compatibilityResult.compatible ? 'success' : 'warning'}
                    icon={compatibilityResult.compatible ? <CheckCircleIcon /> : <WarningIcon />}
                    sx={{ mt: 2 }}
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
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {validationError}
                  </Alert>
                )}
              </Box>
            )}

            {formData.divergent_analyses.length > 0 && (
              <Alert severity="info" sx={{ mt: 2 }}>
                Sub-batches will be created for divergent analyses: {formData.divergent_analyses.length} selected
              </Alert>
            )}
          </Box>
        );

      case 2: // QC Samples
        return (
          <Box>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h6">QC Samples</Typography>
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

            {formData.qc_additions.length > 0 && (
              <Alert severity="info" sx={{ mb: 2 }}>
                QC samples will be assigned to the system "Laboratory QC" project and shared across all samples in this batch.
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
                  <Typography variant="subtitle2">QC Sample {index + 1}</Typography>
                  <IconButton size="small" onClick={() => handleRemoveQC(index)} color="error" aria-label={`Remove QC sample ${index + 1}`}>
                    <DeleteIcon />
                  </IconButton>
                </Box>
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, sm: 4 }}>
                    <FormControl fullWidth required>
                      <InputLabel id={`qc-type-label-${index}`}>QC Type</InputLabel>
                      <Select
                        labelId={`qc-type-label-${index}`}
                        value={qc.qc_type}
                        onChange={(e) => handleQCChange(index, 'qc_type', e.target.value)}
                        label="QC Type"
                        inputProps={{ 'aria-label': `QC type for sample ${index + 1}` }}
                      >
                        {qcTypes.map((qcType) => (
                          <MenuItem key={qcType.id} value={qcType.id}>
                            {qcType.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 4 }}>
                    <FormControl fullWidth required>
                      <InputLabel id={`qc-container-type-label-${index}`}>Container Type</InputLabel>
                      <Select
                        labelId={`qc-container-type-label-${index}`}
                        value={qc.container_type_id}
                        onChange={(e) => handleQCChange(index, 'container_type_id', e.target.value)}
                        label="Container Type"
                        inputProps={{ 'aria-label': `Container type for QC sample ${index + 1}` }}
                      >
                        {containerTypes.map((containerType: any) => (
                          <MenuItem key={containerType.id} value={containerType.id}>
                            {containerType.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 4 }}>
                    <FormControl fullWidth required>
                      <InputLabel id={`qc-matrix-label-${index}`}>Matrix</InputLabel>
                      <Select
                        labelId={`qc-matrix-label-${index}`}
                        value={qc.matrix_id}
                        onChange={(e) => handleQCChange(index, 'matrix_id', e.target.value)}
                        label="Matrix"
                        inputProps={{ 'aria-label': `Matrix for QC sample ${index + 1}` }}
                      >
                        {matrixTypes.map((matrix: any) => (
                          <MenuItem key={matrix.id} value={matrix.id}>
                            {matrix.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 4 }}>
                    <TextField
                      fullWidth
                      label="Notes (Optional)"
                      value={qc.notes || ''}
                      onChange={(e) => handleQCChange(index, 'notes', e.target.value)}
                      placeholder="Additional notes for this QC sample"
                      inputProps={{ 'aria-label': `Notes for QC sample ${index + 1}` }}
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
          </Box>
        );

      case 3: // Review & Create
        return (
          <Box>
            <Typography variant="h6" gutterBottom>Review Batch</Typography>
            
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="subtitle2" color="text.secondary">Batch Details</Typography>
              <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid size={{ xs: 6 }}>
                  <Typography variant="body2"><strong>Name:</strong> {formData.name || '—'}</Typography>
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <Typography variant="body2"><strong>Status:</strong> {listEntries.batch_statuses?.find((s: any) => s.id === formData.status)?.name || '—'}</Typography>
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <Typography variant="body2"><strong>Type:</strong> {listEntries.batch_types?.find((t: any) => t.id === formData.type)?.name || '—'}</Typography>
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <Typography variant="body2"><strong>Start Date:</strong> {formData.start_date?.toLocaleDateString() || '—'}</Typography>
                </Grid>
              </Grid>
            </Paper>

            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="subtitle2" color="text.secondary">Containers ({selectedContainers.length})</Typography>
              {selectedContainers.length > 0 ? (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                  {selectedContainers.map((c) => (
                    <Chip key={c.id} label={c.name} size="small" />
                  ))}
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>No containers selected</Typography>
              )}
              {formData.cross_project && (
                <Alert severity="info" sx={{ mt: 1 }} icon={<CheckCircleIcon />}>
                  Cross-project batch
                </Alert>
              )}
            </Paper>

            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="subtitle2" color="text.secondary">QC Samples ({formData.qc_additions.length})</Typography>
              {formData.qc_additions.length > 0 ? (
                <Box sx={{ mt: 1 }}>
                  {formData.qc_additions.map((qc, idx) => {
                    const qcTypeName = qcTypes.find((t) => t.id === qc.qc_type)?.name || 'Unknown';
                    return (
                      <Chip key={idx} label={`${qcTypeName}${qc.notes ? `: ${qc.notes}` : ''}`} size="small" sx={{ mr: 1, mb: 1 }} />
                    );
                  })}
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>No QC samples</Typography>
              )}
            </Paper>

            {/* Show any compatibility warnings in review */}
            {compatibilityWarnings.length > 0 && (
              <Box sx={{ mb: 2 }}>
                {compatibilityWarnings.map((warning, idx) => (
                  <Alert
                    key={idx}
                    severity={warning.type === 'expired_samples' ? 'error' : 'warning'}
                    sx={{ mb: 1 }}
                  >
                    <Typography variant="subtitle2">{warning.message}</Typography>
                  </Alert>
                ))}
              </Box>
            )}
          </Box>
        );

      default:
        return null;
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Create New Batch
          </Typography>
          
          <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
            {STEPS.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          <Divider sx={{ mb: 3 }} />

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            {renderStepContent(activeStep)}

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'space-between', mt: 4 }}>
              <Box>
                <Button onClick={onCancel} disabled={loading}>
                  Cancel
                </Button>
              </Box>
              <Box sx={{ display: 'flex', gap: 2 }}>
                {activeStep > 0 && (
                  <Button
                    onClick={handleBack}
                    disabled={loading}
                    startIcon={<ArrowBackIcon />}
                  >
                    Back
                  </Button>
                )}
                {activeStep < STEPS.length - 1 ? (
                  <Button
                    variant="contained"
                    onClick={handleNext}
                    disabled={loading || (activeStep === 0 && (!formData.name || !formData.status))}
                    endIcon={<ArrowForwardIcon />}
                  >
                    Next
                  </Button>
                ) : (
                  <Button
                    type="submit"
                    variant="contained"
                    disabled={loading || !formData.name || !formData.status}
                    startIcon={loading && <CircularProgress size={20} />}
                  >
                    Create Batch
                  </Button>
                )}
              </Box>
            </Box>
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
