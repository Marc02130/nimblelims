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
} from '@mui/material';
import {
  MoreVert as MoreVertIcon,
  Add as AddIcon,
  Visibility as ViewIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { apiService, addClientFilterIfNeeded } from '../../services/apiService';
import { useUser } from '../../contexts/UserContext';

interface BatchContainer {
  batch_id: string;
  container_id: string;
  position?: string;
  notes?: string;
}

interface Batch {
  id: string;
  name: string;
  description: string;
  type: string;
  status: string;
  start_date: string;
  end_date: string;
  created_at: string;
  containers?: BatchContainer[];
}

interface BatchListProps {
  onViewBatch: (batchId: string) => void;
  onEditBatch: (batch: Batch) => void;
  onCreateBatch: () => void;
}

const BatchList: React.FC<BatchListProps> = ({ onViewBatch, onEditBatch, onCreateBatch }) => {
  const { user, isSystemClient, isAdmin } = useUser();
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedBatch, setSelectedBatch] = useState<Batch | null>(null);
  const [listEntries, setListEntries] = useState<any>({});

  useEffect(() => {
    loadBatches();
    loadListEntries();
  }, [statusFilter, typeFilter]);

  const loadBatches = async () => {
    try {
      setLoading(true);
      const filters: Record<string, string | undefined> = {};
      if (statusFilter) filters.status = statusFilter;
      if (typeFilter) filters.type = typeFilter;

      // Add client_id filter for non-System clients (though RLS will also enforce this)
      const filteredFilters = addClientFilterIfNeeded(
        filters,
        user?.client_id,
        user?.role
      );

      const data = await apiService.getBatches(filteredFilters);
      setBatches(data);
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('Access denied: You do not have permission to view these batches. Client users can only view batches containing samples from their own client\'s projects.');
      } else if (err.response?.status === 404) {
        setError('No batches found. This may be due to access restrictions.');
      } else {
        setError(err.response?.data?.detail || 'Failed to load batches');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadListEntries = async () => {
    try {
      const [batchStatuses, batchTypes] = await Promise.all([
        apiService.getListEntries('batch_status'),
        apiService.getListEntries('batch_types'),
      ]);

      setListEntries({
        batch_statuses: batchStatuses,
        batch_types: batchTypes,
      });
    } catch (err) {
      console.error('Failed to load list entries:', err);
    }
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, batch: Batch) => {
    setAnchorEl(event.currentTarget);
    setSelectedBatch(batch);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedBatch(null);
  };

  const handleViewBatch = () => {
    if (selectedBatch) {
      onViewBatch(selectedBatch.id);
    }
    handleMenuClose();
  };

  const handleEditBatch = () => {
    if (selectedBatch) {
      onEditBatch(selectedBatch);
    }
    handleMenuClose();
  };

  const handleDeleteBatch = async () => {
    if (selectedBatch) {
      try {
        await apiService.updateBatch(selectedBatch.id, { active: false });
        await loadBatches();
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to delete batch');
      }
    }
    handleMenuClose();
  };

  const getStatusColor = (status: string) => {
    const statusName = listEntries.batch_statuses?.find((s: any) => s.id === status)?.name;
    switch (statusName) {
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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5">Batches</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={onCreateBatch}
        >
          Create Batch
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Card>
        <CardContent>
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Filter by Status</InputLabel>
                <Select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                >
                  <MenuItem value="">All Statuses</MenuItem>
                  {listEntries.batch_statuses?.map((entry: any) => (
                    <MenuItem key={entry.id} value={entry.id}>
                      {entry.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Filter by Type</InputLabel>
                <Select
                  value={typeFilter}
                  onChange={(e) => setTypeFilter(e.target.value)}
                >
                  <MenuItem value="">All Types</MenuItem>
                  {listEntries.batch_types?.map((entry: any) => (
                    <MenuItem key={entry.id} value={entry.id}>
                      {entry.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>

          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Start Date</TableCell>
                  <TableCell>End Date</TableCell>
                  <TableCell>Containers</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {batches.map((batch) => (
                  <TableRow key={batch.id}>
                    <TableCell>{batch.name}</TableCell>
                    <TableCell>{batch.description}</TableCell>
                    <TableCell>
                      {listEntries.batch_types?.find((t: any) => t.id === batch.type)?.name || batch.type}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={listEntries.batch_statuses?.find((s: any) => s.id === batch.status)?.name || batch.status}
                        color={getStatusColor(batch.status) as any}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>{batch.start_date ? formatDate(batch.start_date) : '-'}</TableCell>
                    <TableCell>{batch.end_date ? formatDate(batch.end_date) : '-'}</TableCell>
                    <TableCell>{batch.containers?.length || 0}</TableCell>
                    <TableCell align="right">
                      <IconButton
                        onClick={(e) => handleMenuOpen(e, batch)}
                        size="small"
                      >
                        <MoreVertIcon />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
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

      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleViewBatch}>
          <ViewIcon sx={{ mr: 1 }} />
          View Details
        </MenuItem>
        <MenuItem onClick={handleEditBatch}>
          <EditIcon sx={{ mr: 1 }} />
          Edit
        </MenuItem>
        <MenuItem onClick={handleDeleteBatch}>
          <DeleteIcon sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default BatchList;
