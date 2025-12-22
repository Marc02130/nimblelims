import React, { useState, useEffect, useMemo } from 'react';
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
  Tooltip,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Search,
  Clear,
  ExpandMore,
  ExpandLess,
  Settings,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';
import { useNavigate } from 'react-router-dom';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';
import AnalysisFormDialog from './AnalysisFormDialog';

interface Analyte {
  id: string;
  name: string;
  description?: string;
}

interface Analysis {
  id: string;
  name: string;
  description?: string;
  method?: string;
  turnaround_time?: number;
  cost?: number;
  active: boolean;
  created_at: string;
  modified_at: string;
  analytes?: Analyte[];
  analytes_count?: number;
}

const AnalysesManagement: React.FC = () => {
  const navigate = useNavigate();
  const { user, hasPermission } = useUser();
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [formOpen, setFormOpen] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState<Analysis | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Analysis | null>(null);

  const canEdit = hasPermission('config:edit') || hasPermission('test:configure');

  useEffect(() => {
    loadAnalyses();
  }, []);

  const loadAnalyses = async () => {
    try {
      setLoading(true);
      setError(null);
      const analysesData = await apiService.getAnalyses();
      
      // Load analytes for each analysis
      const analysesWithAnalytes = await Promise.all(
        (analysesData || []).map(async (analysis: Analysis) => {
          try {
            const analytes = await apiService.getAnalysisAnalytes(analysis.id);
            return {
              ...analysis,
              analytes: analytes || [],
              analytes_count: analytes?.length || 0,
            };
          } catch {
            // If endpoint doesn't exist, use analytes from analysis if available
            return {
              ...analysis,
              analytes: analysis.analytes || [],
              analytes_count: analysis.analytes?.length || 0,
            };
          }
        })
      );
      
      setAnalyses(analysesWithAnalytes);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view analyses management');
      } else {
        setError(err.response?.data?.detail || 'Failed to load analyses');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredAnalyses = useMemo(() => {
    if (!searchTerm) return analyses;
    const term = searchTerm.toLowerCase();
    return analyses.filter(
      (analysis) =>
        analysis.name.toLowerCase().includes(term) ||
        analysis.description?.toLowerCase().includes(term) ||
        analysis.method?.toLowerCase().includes(term) ||
        analysis.analytes?.some((a) =>
          a.name.toLowerCase().includes(term) ||
          a.description?.toLowerCase().includes(term)
        )
    );
  }, [analyses, searchTerm]);

  const handleCreate = async (data: {
    name: string;
    description?: string;
    method?: string;
    turnaround_time?: number;
    cost?: number;
    analyte_ids: string[];
  }) => {
    const { analyte_ids, ...analysisData } = data;
    const analysis = await apiService.createAnalysis(analysisData);
    
    // Assign analytes
    if (analyte_ids.length > 0) {
      await apiService.updateAnalysisAnalytes(analysis.id, analyte_ids);
    }
    
    await loadAnalyses();
  };

  const handleUpdate = async (data: {
    name: string;
    description?: string;
    method?: string;
    turnaround_time?: number;
    cost?: number;
    analyte_ids: string[];
  }) => {
    if (!selectedAnalysis) return;
    
    const { analyte_ids, ...analysisData } = data;
    await apiService.updateAnalysis(selectedAnalysis.id, analysisData);
    
    // Update analytes
    await apiService.updateAnalysisAnalytes(selectedAnalysis.id, analyte_ids);
    
    await loadAnalyses();
    setSelectedAnalysis(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteAnalysis(deleteTarget.id);
      await loadAnalyses();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      if (err.response?.status === 400) {
        setError(err.response?.data?.detail || 'Cannot delete analysis that is referenced in tests');
      } else {
        setError(err.response?.data?.detail || 'Failed to delete analysis');
      }
      setDeleteDialogOpen(false);
    }
  };

  const toggleRowExpansion = (analysisId: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(analysisId)) {
      newExpanded.delete(analysisId);
    } else {
      newExpanded.add(analysisId);
    }
    setExpandedRows(newExpanded);
  };

  const formatCurrency = (value?: number | string) => {
    if (value === null || value === undefined) return 'N/A';
    // Convert to number if it's a string (from API Decimal/Numeric types)
    const numValue = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(numValue)) return 'N/A';
    return `$${numValue.toFixed(2)}`;
  };

  const columns: GridColDef[] = [
    {
      field: 'expand',
      headerName: '',
      width: 60,
      sortable: false,
      filterable: false,
      renderCell: (params) => {
        const analysis = params.row as Analysis;
        const isExpanded = expandedRows.has(analysis.id);
        const hasAnalytes = (analysis.analytes_count || 0) > 0;
        
        if (!hasAnalytes && !isExpanded) return null;
        
        return (
          <Tooltip title={isExpanded ? 'Collapse analytes' : 'Expand analytes'}>
            <IconButton
              size="small"
              onClick={(e) => {
                e.stopPropagation();
                toggleRowExpansion(analysis.id);
              }}
            >
              {isExpanded ? <ExpandLess /> : <ExpandMore />}
            </IconButton>
          </Tooltip>
        );
      },
    },
    {
      field: 'name',
      headerName: 'Analysis Name',
      width: 200,
      flex: 1,
    },
    {
      field: 'method',
      headerName: 'Method',
      width: 150,
      flex: 1,
    },
    {
      field: 'turnaround_time',
      headerName: 'Turnaround (days)',
      width: 150,
      valueGetter: (value, row) => (row as Analysis).turnaround_time || 'N/A',
    },
    {
      field: 'cost',
      headerName: 'Cost',
      width: 120,
      valueGetter: (value, row) => formatCurrency((row as Analysis).cost),
    },
    {
      field: 'analytes_count',
      headerName: 'Analytes',
      width: 100,
      valueGetter: (value, row) => (row as Analysis).analytes_count || 0,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={params.value === 0 ? 'default' : 'primary'}
        />
      ),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 180,
      getActions: (params: GridRowParams) => {
        const analysis = params.row as Analysis;
        const actions = [];

        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedAnalysis(analysis);
                setFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Settings />}
              label="Configure Analytes"
              onClick={() => {
                navigate(`/admin/analyses/${analysis.id}/analytes`);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget(analysis);
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
          You do not have permission to view analyses management.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Analyses Management</Typography>
        {canEdit && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setSelectedAnalysis(null);
              setFormOpen(true);
            }}
          >
            Create Analysis
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
          placeholder="Search analyses, methods, or analytes..."
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

      {loading ? (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <CircularProgress />
        </Box>
      ) : (
        <>
          <Box sx={{ height: 600, width: '100%', mb: 2 }}>
            <DataGrid
              rows={filteredAnalyses}
              columns={columns}
              getRowId={(row) => row.id}
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
                    <Typography>No analyses found</Typography>
                  </Box>
                ),
              }}
            />
          </Box>

          {/* Expanded rows for analytes */}
          {Array.from(expandedRows).map((analysisId) => {
            const analysis = analyses.find((a) => a.id === analysisId);
            if (!analysis) return null;

            return (
              <Box
                key={`analytes-${analysisId}`}
                sx={{
                  mt: 2,
                  mb: 3,
                  p: 2,
                  bgcolor: 'background.paper',
                  borderRadius: 1,
                  border: 1,
                  borderColor: 'divider',
                }}
              >
                <Typography variant="h6" gutterBottom>
                  Analytes for {analysis.name}
                </Typography>
                {analysis.analytes && analysis.analytes.length > 0 ? (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                    {analysis.analytes.map((analyte) => (
                      <Chip
                        key={analyte.id}
                        label={analyte.name}
                        size="small"
                        color="primary"
                        variant="outlined"
                        title={analyte.description}
                      />
                    ))}
                  </Box>
                ) : (
                  <Typography color="text.secondary">
                    No analytes assigned to this analysis
                  </Typography>
                )}
              </Box>
            );
          })}
        </>
      )}

      {/* Analysis Form Dialog */}
      <AnalysisFormDialog
        open={formOpen}
        analysis={selectedAnalysis}
        existingNames={analyses.map((a) => a.name)}
        onClose={() => {
          setFormOpen(false);
          setSelectedAnalysis(null);
        }}
        onSubmit={selectedAnalysis ? handleUpdate : handleCreate}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete analysis <strong>{deleteTarget?.name}</strong>?
            <Box component="span" sx={{ display: 'block', mt: 1, color: 'warning.main' }}>
              This action cannot be undone. If this analysis is referenced in any tests, the deletion will fail.
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

export default AnalysesManagement;

