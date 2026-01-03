import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  Alert,
  CircularProgress,
  Grid,
  FormControl,
  InputLabel,
  Select,
  Tooltip,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  PlayArrow as PlayArrowIcon,
  Visibility as ViewIcon,
  Edit as EditIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import BatchResultsView from './BatchResultsView';
import { apiService } from '../../services/apiService';
import { useUser } from '../../contexts/UserContext';

interface Batch {
  id: string;
  name: string;
  description: string;
  status: string;
  container_count: number;
  created_at: string;
  containers?: Array<{
    container_id: string;
    container?: {
      contents?: Array<{
        sample?: {
          qc_type?: string;
        };
      }>;
    };
  }>;
}

interface ResultsManagementProps {
  onBack?: () => void;
}

const ResultsManagement: React.FC<ResultsManagementProps> = ({ onBack }) => {
  const { user } = useUser();
  const isClient = user?.role === 'Client';
  const [view, setView] = useState<'list' | 'entry'>('list');
  const [batches, setBatches] = useState<Batch[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<Batch | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [batchStatuses, setBatchStatuses] = useState<any[]>([]);
  const [qcTypes, setQcTypes] = useState<any[]>([]);

  useEffect(() => {
    loadBatches();
    loadListEntries();
    loadQCTypes();
  }, [statusFilter]);

  const loadListEntries = async () => {
    try {
      const statuses = await apiService.getListEntries('batch_status');
      setBatchStatuses(statuses);
    } catch (err) {
      console.error('Failed to load list entries:', err);
    }
  };

  const loadQCTypes = async () => {
    try {
      const types = await apiService.getListEntries('qc_types');
      setQcTypes(types || []);
    } catch (err) {
      console.error('Failed to load QC types:', err);
    }
  };

  // Check if batch has QC samples
  const hasQCSamples = (batch: Batch): boolean => {
    if (!batch.containers) return false;
    return batch.containers.some(bc => {
      const container = bc.container;
      if (!container?.contents) return false;
      return container.contents.some(content => content.sample?.qc_type);
    });
  };

  // Get QC type names for a batch
  const getQCTypesForBatch = (batch: Batch): string[] => {
    if (!batch.containers) return [];
    const qcTypeIds = new Set<string>();
    batch.containers.forEach(bc => {
      const container = bc.container;
      if (container?.contents) {
        container.contents.forEach(content => {
          if (content.sample?.qc_type) {
            qcTypeIds.add(content.sample.qc_type);
          }
        });
      }
    });
    return Array.from(qcTypeIds)
      .map(id => qcTypes.find(qt => qt.id === id)?.name)
      .filter(Boolean) as string[];
  };

  const loadBatches = async () => {
    try {
      setLoading(true);
      const filters: any = {};
      if (statusFilter) filters.status = statusFilter;

      const data = await apiService.getBatches(filters);
      setBatches(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load batches');
    } finally {
      setLoading(false);
    }
  };

  const handleViewBatch = (batch: Batch) => {
    setSelectedBatch(batch);
    setView('entry');
  };

  const handleBackToList = () => {
    setView('list');
    setSelectedBatch(null);
    loadBatches(); // Refresh batches to show updated statuses
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Created':
        return 'default';
      case 'In Process':
        return 'primary';
      case 'Completed':
        return 'success';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={3}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      {onBack && (
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={onBack}
          sx={{ mb: 2 }}
        >
          Back
        </Button>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {view === 'list' && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Tooltip
              title={isClient ? 'This shows your test results. Contact your lab for questions about specific results or if you need assistance.' : ''}
              arrow
            >
            <Typography variant="h5">Results Management</Typography>
            </Tooltip>
          </Box>

          <Card sx={{ mb: 2 }}>
            <CardContent>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <FormControl fullWidth>
                    <InputLabel>Filter by Status</InputLabel>
                    <Select
                      value={statusFilter}
                      onChange={(e) => setStatusFilter(e.target.value)}
                    >
                      <MenuItem value="">All Statuses</MenuItem>
                      {batchStatuses.map((entry: any) => (
                        <MenuItem key={entry.id} value={entry.id}>
                          {entry.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Grid>
              </Grid>
            </CardContent>
          </Card>

          <Card>
            <CardContent>
              <TableContainer component={Paper}>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Batch Name</TableCell>
                      <TableCell>Description</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Containers</TableCell>
                      <TableCell>QC Samples</TableCell>
                      <TableCell>Created</TableCell>
                      <TableCell align="right">Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {batches.map((batch) => {
                      const hasQC = hasQCSamples(batch);
                      const qcTypeNames = getQCTypesForBatch(batch);
                      return (
                      <TableRow key={batch.id}>
                        <TableCell>{batch.name}</TableCell>
                        <TableCell>{batch.description}</TableCell>
                        <TableCell>
                          <Chip
                            label={batch.status}
                            color={getStatusColor(batch.status) as any}
                            size="small"
                          />
                        </TableCell>
                          <TableCell>{batch.container_count || batch.containers?.length || 0}</TableCell>
                          <TableCell>
                            {hasQC ? (
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                                <WarningIcon color="warning" fontSize="small" />
                                <Chip
                                  label={qcTypeNames.length > 0 ? qcTypeNames.join(', ') : 'QC'}
                                  size="small"
                                  color="warning"
                                  variant="outlined"
                                />
                              </Box>
                            ) : (
                              <Typography variant="body2" color="text.secondary">None</Typography>
                            )}
                          </TableCell>
                        <TableCell>{formatDate(batch.created_at)}</TableCell>
                        <TableCell align="right">
                          <Button
                            variant="contained"
                            startIcon={<PlayArrowIcon />}
                            onClick={() => handleViewBatch(batch)}
                            size="small"
                          >
                            Enter Results
                          </Button>
                        </TableCell>
                      </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>

              {batches.length === 0 && (
                <Box textAlign="center" py={4}>
                  <Typography variant="body1" color="text.secondary">
                    No batches found
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Box>
      )}

      {view === 'entry' && selectedBatch && (
        <BatchResultsView
          batchId={selectedBatch.id}
          onBack={handleBackToList}
        />
      )}
    </Box>
  );
};

export default ResultsManagement;
