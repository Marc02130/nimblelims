import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Divider,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import BatchList from './BatchList';
import BatchForm from './BatchForm';
import ContainerGrid from './ContainerGrid';
import { apiService } from '../../services/apiService';

interface Batch {
  id: string;
  name: string;
  description: string;
  type: string;
  status: string;
  start_date: string;
  end_date: string;
  created_at: string;
}

interface BatchManagementProps {
  onBack?: () => void;
}

const BatchManagement: React.FC<BatchManagementProps> = ({ onBack }) => {
  const [view, setView] = useState<'list' | 'create' | 'edit' | 'details'>('list');
  const [selectedBatch, setSelectedBatch] = useState<Batch | null>(null);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);

  const handleCreateBatch = () => {
    setView('create');
    setSelectedBatch(null);
  };

  const handleEditBatch = (batch: Batch) => {
    setSelectedBatch(batch);
    setView('edit');
  };

  const handleViewBatch = async (batchId: string) => {
    try {
      setLoading(true);
      const batch = await apiService.getBatch(batchId);
      setSelectedBatch(batch);
      setView('details');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load batch details');
    } finally {
      setLoading(false);
    }
  };

  const handleBatchCreated = (batch: Batch) => {
    setBatches(prev => [batch, ...prev]);
    setView('list');
  };

  const handleBatchUpdated = (updatedBatch: Batch) => {
    setBatches(prev => prev.map(b => b.id === updatedBatch.id ? updatedBatch : b));
    setView('list');
  };

  const handleBackToList = () => {
    setView('list');
    setSelectedBatch(null);
    setActiveTab(0);
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
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
        <BatchList
          onViewBatch={handleViewBatch}
          onEditBatch={handleEditBatch}
          onCreateBatch={handleCreateBatch}
        />
      )}

      {view === 'create' && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h5">Create New Batch</Typography>
              <Button onClick={handleBackToList}>Back to List</Button>
            </Box>
            <BatchForm
              onSuccess={handleBatchCreated}
              onCancel={handleBackToList}
            />
          </CardContent>
        </Card>
      )}

      {view === 'edit' && selectedBatch && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h5">Edit Batch</Typography>
              <Button onClick={handleBackToList}>Back to List</Button>
            </Box>
            <BatchForm
              onSuccess={handleBatchUpdated}
              onCancel={handleBackToList}
            />
          </CardContent>
        </Card>
      )}

      {view === 'details' && selectedBatch && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h5">{selectedBatch.name}</Typography>
              <Box>
                <Button
                  startIcon={<EditIcon />}
                  onClick={() => setView('edit')}
                  sx={{ mr: 1 }}
                >
                  Edit
                </Button>
                <Button onClick={handleBackToList}>Back to List</Button>
              </Box>
            </Box>

            <Typography variant="body1" sx={{ mb: 2 }}>
              {selectedBatch.description}
            </Typography>

            <Divider sx={{ mb: 2 }} />

            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={activeTab} onChange={handleTabChange}>
                <Tab label="Containers" />
                <Tab label="Results" />
                <Tab label="Details" />
              </Tabs>
            </Box>

            {activeTab === 0 && (
              <ContainerGrid
                batchId={selectedBatch.id}
                containers={[]} // This would be loaded from the API
                onContainersChange={() => {}} // This would update the containers
              />
            )}

            {activeTab === 1 && (
              <Box sx={{ p: 2 }}>
                <Typography variant="h6">Results Entry</Typography>
                <Typography variant="body2" color="text.secondary">
                  Results entry functionality will be implemented in the results components.
                </Typography>
              </Box>
            )}

            {activeTab === 2 && (
              <Box sx={{ p: 2 }}>
                <Typography variant="h6">Batch Details</Typography>
                <Box sx={{ mt: 2 }}>
                  <Typography variant="body2">
                    <strong>Type:</strong> {selectedBatch.type}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Status:</strong> {selectedBatch.status}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Start Date:</strong> {selectedBatch.start_date ? new Date(selectedBatch.start_date).toLocaleDateString() : 'Not set'}
                  </Typography>
                  <Typography variant="body2">
                    <strong>End Date:</strong> {selectedBatch.end_date ? new Date(selectedBatch.end_date).toLocaleDateString() : 'Not set'}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Created:</strong> {new Date(selectedBatch.created_at).toLocaleDateString()}
                  </Typography>
                </Box>
              </Box>
            )}
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default BatchManagement;
