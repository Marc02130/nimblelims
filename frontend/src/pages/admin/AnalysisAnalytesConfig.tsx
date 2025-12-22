import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  TextField,
  InputAdornment,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Chip,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Search,
  Clear,
  ArrowBack,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';
import AnalyteRuleForm from './AnalyteRuleForm';

interface AnalyteRule {
  analyte_id: string;
  analyte_name: string;
  data_type?: string;
  high_value?: number;
  low_value?: number;
  significant_figures?: number;
  is_required: boolean;
  reported_name?: string;
  calculation?: string;
  default_value?: string;
}

interface Analysis {
  id: string;
  name: string;
}

const AnalysisAnalytesConfig: React.FC = () => {
  const { analysisId } = useParams<{ analysisId: string }>();
  const navigate = useNavigate();
  const { user, hasPermission } = useUser();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [rules, setRules] = useState<AnalyteRule[]>([]);
  const [dataTypes, setDataTypes] = useState<Array<{ id: string; name: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [formOpen, setFormOpen] = useState(false);
  const [selectedRule, setSelectedRule] = useState<AnalyteRule | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<AnalyteRule | null>(null);

  const canEdit = hasPermission('config:edit') || hasPermission('test:configure');

  useEffect(() => {
    if (analysisId) {
      loadData();
    }
  }, [analysisId]);

  const loadData = async () => {
    if (!analysisId) return;
    
    try {
      setLoading(true);
      setError(null);
      
      const [analysesData, rulesData, dataTypesData] = await Promise.all([
        apiService.getAnalyses(),
        apiService.getAnalysisAnalyteRules(analysisId).catch(() => []),
        apiService.getListEntries('data_types').catch(() => {
          // Fallback to common data types if list doesn't exist
          return [
            { id: '1', name: 'numeric' },
            { id: '2', name: 'text' },
            { id: '3', name: 'boolean' },
          ];
        }),
      ]);

      const foundAnalysis = analysesData.find((a: Analysis) => a.id === analysisId);
      if (!foundAnalysis) {
        setError('Analysis not found');
        return;
      }

      setAnalysis(foundAnalysis);
      setRules(rulesData || []);
      setDataTypes(dataTypesData || []);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view analysis-analytes configuration');
      } else {
        setError(err.response?.data?.detail || 'Failed to load configuration');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredRules = React.useMemo(() => {
    if (!searchTerm) return rules;
    const term = searchTerm.toLowerCase();
    return rules.filter(
      (rule) =>
        rule.analyte_name.toLowerCase().includes(term) ||
        rule.data_type?.toLowerCase().includes(term) ||
        rule.reported_name?.toLowerCase().includes(term)
    );
  }, [rules, searchTerm]);

  const handleCreate = async (data: {
    analyte_id: string;
    data_type?: string;
    list_id?: string;
    high_value?: number;
    low_value?: number;
    significant_figures?: number;
    calculation?: string;
    reported_name?: string;
    is_required: boolean;
    default_value?: string;
  }) => {
    if (!analysisId) return;
    await apiService.createAnalysisAnalyteRule(analysisId, data);
    await loadData();
  };

  const handleUpdate = async (data: {
    analyte_id: string;
    data_type?: string;
    list_id?: string;
    high_value?: number;
    low_value?: number;
    significant_figures?: number;
    calculation?: string;
    reported_name?: string;
    is_required: boolean;
    default_value?: string;
  }) => {
    if (!analysisId || !selectedRule) return;
    await apiService.updateAnalysisAnalyteRule(analysisId, selectedRule.analyte_id, data);
    await loadData();
    setSelectedRule(null);
  };

  const handleDelete = async () => {
    if (!analysisId || !deleteTarget) return;
    try {
      await apiService.deleteAnalysisAnalyteRule(analysisId, deleteTarget.analyte_id);
      await loadData();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete analyte rule');
      setDeleteDialogOpen(false);
    }
  };

  const formatRange = (low?: number, high?: number) => {
    if (low === undefined && high === undefined) return 'N/A';
    if (low === undefined) return `≤ ${high}`;
    if (high === undefined) return `≥ ${low}`;
    return `${low} - ${high}`;
  };

  const columns: GridColDef[] = [
    {
      field: 'analyte_name',
      headerName: 'Analyte',
      width: 200,
      flex: 1,
    },
    {
      field: 'data_type',
      headerName: 'Data Type',
      width: 120,
      valueGetter: (value) => value || 'N/A',
    },
    {
      field: 'range',
      headerName: 'Range',
      width: 150,
      valueGetter: (value, row) => formatRange((row as AnalyteRule).low_value, (row as AnalyteRule).high_value),
    },
    {
      field: 'significant_figures',
      headerName: 'Sig Figs',
      width: 100,
      valueGetter: (value) => value || 'N/A',
    },
    {
      field: 'is_required',
      headerName: 'Required',
      width: 100,
      renderCell: (params) => (
        <Chip
          label={params.value ? 'Yes' : 'No'}
          size="small"
          color={params.value ? 'primary' : 'default'}
        />
      ),
    },
    {
      field: 'reported_name',
      headerName: 'Reported Name',
      width: 150,
      valueGetter: (value) => value || 'N/A',
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 120,
      getActions: (params: GridRowParams) => {
        const rule = params.row as AnalyteRule;
        const actions = [];

        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedRule(rule);
                setFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget(rule);
                setDeleteDialogOpen(true);
              }}
            />
          );
        }

        return actions;
      },
    },
  ];

  if (!canEdit && !hasPermission('sample:read')) {
    return (
      <Box>
        <Alert severity="warning">
          You do not have permission to view analysis-analytes configuration.
        </Alert>
      </Box>
    );
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!analysis) {
    return (
      <Box>
        <Alert severity="error">Analysis not found</Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate('/admin/analyses')}
            sx={{ mb: 1 }}
          >
            Back to Analyses
          </Button>
          <Typography variant="h4">
            Configure Analytes: {analysis.name}
          </Typography>
        </Box>
        {canEdit && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setSelectedRule(null);
              setFormOpen(true);
            }}
          >
            Add Analyte Rule
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ mb: 2 }}>
        <TextField
          fullWidth
          placeholder="Search analytes, data types, or reported names..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
            endAdornment: searchTerm && (
              <InputAdornment position="end">
                <IconButton size="small" onClick={() => setSearchTerm('')}>
                  <Clear />
                </IconButton>
              </InputAdornment>
            ),
          }}
        />
      </Box>

      <Box sx={{ height: 600, width: '100%' }}>
        <DataGrid
          rows={filteredRules}
          columns={columns}
          getRowId={(row) => row.analyte_id}
          pageSizeOptions={[10, 25, 50]}
          initialState={{
            pagination: {
              paginationModel: { page: 0, pageSize: 10 },
            },
          }}
          disableRowSelectionOnClick
          slots={{
            noRowsOverlay: () => (
              <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                <Typography>No analyte rules configured</Typography>
              </Box>
            ),
          }}
        />
      </Box>

      {/* Analyte Rule Form Dialog */}
      <AnalyteRuleForm
        open={formOpen}
        analysisId={analysisId || ''}
        rule={selectedRule}
        existingAnalyteIds={rules.map((r) => r.analyte_id)}
        dataTypes={dataTypes}
        onClose={() => {
          setFormOpen(false);
          setSelectedRule(null);
        }}
        onSubmit={selectedRule ? handleUpdate : handleCreate}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to remove the analyte rule for <strong>{deleteTarget?.analyte_name}</strong>?
            <Box component="span" sx={{ display: 'block', mt: 1, color: 'warning.main' }}>
              This will remove all validation rules for this analyte in this analysis.
            </Box>
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AnalysisAnalytesConfig;

