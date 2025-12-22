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
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Search,
  Clear,
  ExpandMore,
  ExpandLess,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams, GridRenderCellParams } from '@mui/x-data-grid';
import { useUser } from '../../contexts/UserContext';
import { apiService } from '../../services/apiService';
import BatteryFormDialog from './BatteryFormDialog';

interface BatteryAnalysis {
  analysis_id: string;
  analysis_name: string;
  analysis_method?: string;
  sequence: number;
  optional: boolean;
}

interface TestBattery {
  id: string;
  name: string;
  description?: string;
  active: boolean;
  created_at: string;
  modified_at: string;
  analyses_count?: number;
  analyses?: BatteryAnalysis[];
}

const TestBatteriesManagement: React.FC = () => {
  const { user, hasPermission } = useUser();
  const [batteries, setBatteries] = useState<TestBattery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [formOpen, setFormOpen] = useState(false);
  const [selectedBattery, setSelectedBattery] = useState<TestBattery | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<TestBattery | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const canEdit = hasPermission('config:edit') || hasPermission('test:configure');

  useEffect(() => {
    loadBatteries();
  }, []);

  const loadBatteries = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiService.getTestBatteries({ name: searchTerm || undefined });
      const batteriesData = response.batteries || response || [];
      
      // Load analyses for each battery
      const batteriesWithAnalyses = await Promise.all(
        batteriesData.map(async (battery: TestBattery) => {
          try {
            const analyses = await apiService.getBatteryAnalyses(battery.id);
            return {
              ...battery,
              analyses: analyses || [],
              analyses_count: analyses?.length || 0,
            };
          } catch {
            return {
              ...battery,
              analyses: battery.analyses || [],
              analyses_count: battery.analyses_count || 0,
            };
          }
        })
      );
      
      setBatteries(batteriesWithAnalyses);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to view test batteries management');
      } else {
        setError(err.response?.data?.detail || 'Failed to load test batteries');
      }
    } finally {
      setLoading(false);
    }
  };

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (!loading) {
        loadBatteries();
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const filteredBatteries = useMemo(() => {
    if (!searchTerm) return batteries;
    const term = searchTerm.toLowerCase();
    return batteries.filter(
      (battery) =>
        battery.name.toLowerCase().includes(term) ||
        battery.description?.toLowerCase().includes(term)
    );
  }, [batteries, searchTerm]);

  const handleCreate = async (data: {
    name: string;
    description?: string;
    analyses: BatteryAnalysis[];
  }) => {
    // Create battery first
    const battery = await apiService.createTestBattery({
      name: data.name,
      description: data.description,
    });
    
    // Add analyses to battery
    for (const analysis of data.analyses) {
      await apiService.addAnalysisToBattery(battery.id, {
        analysis_id: analysis.analysis_id,
        sequence: analysis.sequence,
        optional: analysis.optional,
      });
    }
    
    await loadBatteries();
  };

  const handleUpdate = async (data: {
    name: string;
    description?: string;
    analyses: BatteryAnalysis[];
  }) => {
    if (!selectedBattery) return;
    
    // Update battery
    await apiService.updateTestBattery(selectedBattery.id, {
      name: data.name,
      description: data.description,
    });
    
    // Get current analyses
    const currentAnalyses = await apiService.getBatteryAnalyses(selectedBattery.id);
    const currentIds = new Set(currentAnalyses.map((a: BatteryAnalysis) => a.analysis_id));
    const newIds = new Set(data.analyses.map(a => a.analysis_id));
    
    // Remove analyses that are no longer in the list
    for (const currentAnalysis of currentAnalyses) {
      if (!newIds.has(currentAnalysis.analysis_id)) {
        await apiService.removeAnalysisFromBattery(
          selectedBattery.id,
          currentAnalysis.analysis_id
        );
      }
    }
    
    // Add or update analyses
    for (const analysis of data.analyses) {
      if (currentIds.has(analysis.analysis_id)) {
        // Update existing
        await apiService.updateBatteryAnalysis(
          selectedBattery.id,
          analysis.analysis_id,
          {
            sequence: analysis.sequence,
            optional: analysis.optional,
          }
        );
      } else {
        // Add new
        await apiService.addAnalysisToBattery(selectedBattery.id, {
          analysis_id: analysis.analysis_id,
          sequence: analysis.sequence,
          optional: analysis.optional,
        });
      }
    }
    
    await loadBatteries();
    setSelectedBattery(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    
    try {
      setDeleteError(null);
      await apiService.deleteTestBattery(deleteTarget.id);
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
      await loadBatteries();
    } catch (err: any) {
      if (err.response?.status === 409) {
        setDeleteError(err.response?.data?.detail || 'Cannot delete: battery is referenced by tests');
      } else {
        setDeleteError(err.response?.data?.detail || 'Failed to delete battery');
      }
    }
  };

  const toggleExpand = (batteryId: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(batteryId)) {
      newExpanded.delete(batteryId);
    } else {
      newExpanded.add(batteryId);
    }
    setExpandedRows(newExpanded);
  };

  const existingNames = batteries
    .filter(b => !selectedBattery || b.id !== selectedBattery.id)
    .map(b => b.name);

  const columns: GridColDef[] = [
    {
      field: 'expand',
      headerName: '',
      width: 60,
      sortable: false,
      renderCell: (params: GridRenderCellParams) => {
        const battery = params.row as TestBattery;
        const isExpanded = expandedRows.has(battery.id);
        return (
          <IconButton
            size="small"
            onClick={() => toggleExpand(battery.id)}
            disabled={!battery.analyses || battery.analyses.length === 0}
          >
            {isExpanded ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
        );
      },
    },
    {
      field: 'name',
      headerName: 'Name',
      width: 250,
      flex: 1,
    },
    {
      field: 'description',
      headerName: 'Description',
      width: 300,
      flex: 1,
      valueGetter: (value) => value || '',
    },
    {
      field: 'analyses_count',
      headerName: 'Analyses',
      width: 120,
      valueGetter: (value, row) => (row as TestBattery).analyses_count || 0,
      renderCell: (params) => (
        <Chip
          label={params.value}
          size="small"
          color={params.value === 0 ? 'default' : 'primary'}
        />
      ),
    },
    {
      field: 'active',
      headerName: 'Status',
      width: 100,
      renderCell: (params) => (
        <Chip
          label={params.value ? 'Active' : 'Inactive'}
          size="small"
          color={params.value ? 'success' : 'default'}
        />
      ),
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 180,
      getActions: (params: GridRowParams) => {
        const battery = params.row as TestBattery;
        const actions = [];

        if (canEdit) {
          actions.push(
            <GridActionsCellItem
              icon={<Edit />}
              label="Edit"
              onClick={() => {
                setSelectedBattery(battery);
                setFormOpen(true);
              }}
            />,
            <GridActionsCellItem
              icon={<Delete />}
              label="Delete"
              onClick={() => {
                setDeleteTarget(battery);
                setDeleteDialogOpen(true);
                setDeleteError(null);
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
          You do not have permission to view test batteries management.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Test Batteries Management</Typography>
        {canEdit && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setSelectedBattery(null);
              setFormOpen(true);
            }}
          >
            Create Battery
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box mb={2}>
        <TextField
          fullWidth
          size="small"
          placeholder="Search batteries by name or description..."
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
        <Box display="flex" justifyContent="center" p={3}>
          <CircularProgress />
        </Box>
      ) : (
        <Box>
          <DataGrid
            rows={filteredBatteries}
            columns={columns}
            getRowId={(row) => row.id}
            autoHeight
            disableRowSelectionOnClick
            initialState={{
              pagination: {
                paginationModel: { page: 0, pageSize: 10 },
              },
            }}
            pageSizeOptions={[10, 25, 50]}
            sx={{
              '& .MuiDataGrid-cell': {
                display: 'flex',
                alignItems: 'center',
              },
            }}
          />

          {/* Expanded rows showing analyses */}
          {filteredBatteries
            .filter((battery) => expandedRows.has(battery.id))
            .map((battery) => (
              <Paper key={battery.id} variant="outlined" sx={{ mt: 2, p: 2 }}>
                <Typography variant="h6" gutterBottom>
                  Analyses in {battery.name}
                </Typography>
                {battery.analyses && battery.analyses.length > 0 ? (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Sequence</TableCell>
                          <TableCell>Analysis Name</TableCell>
                          <TableCell>Method</TableCell>
                          <TableCell>Optional</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {battery.analyses
                          .sort((a, b) => a.sequence - b.sequence)
                          .map((analysis) => (
                            <TableRow key={analysis.analysis_id}>
                              <TableCell>{analysis.sequence}</TableCell>
                              <TableCell>{analysis.analysis_name}</TableCell>
                              <TableCell>{analysis.analysis_method || '-'}</TableCell>
                              <TableCell>
                                <Chip
                                  label={analysis.optional ? 'Yes' : 'No'}
                                  size="small"
                                  color={analysis.optional ? 'warning' : 'default'}
                                />
                              </TableCell>
                            </TableRow>
                          ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Typography variant="body2" color="textSecondary">
                    No analyses assigned to this battery.
                  </Typography>
                )}
              </Paper>
            ))}
        </Box>
      )}

      <BatteryFormDialog
        open={formOpen}
        battery={selectedBattery}
        existingNames={existingNames}
        onClose={() => {
          setFormOpen(false);
          setSelectedBattery(null);
        }}
        onSubmit={selectedBattery ? handleUpdate : handleCreate}
      />

      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Test Battery</DialogTitle>
        <DialogContent>
          {deleteError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {deleteError}
            </Alert>
          )}
          <DialogContentText>
            Are you sure you want to delete "{deleteTarget?.name}"? This action cannot be undone.
            {deleteError && (
              <Typography variant="body2" color="error" sx={{ mt: 1 }}>
                {deleteError}
              </Typography>
            )}
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

export default TestBatteriesManagement;

