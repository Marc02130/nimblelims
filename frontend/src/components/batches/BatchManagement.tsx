import React, { useState, useEffect } from 'react';
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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import BatchList from './BatchList';
import BatchForm from './BatchForm';
import BatchFormEnhanced from './BatchFormEnhanced';
import ContainerGrid from './ContainerGrid';
import { apiService } from '../../services/apiService';
import { useUser } from '../../contexts/UserContext';

interface Batch {
  id: string;
  name: string;
  description: string;
  type: string;
  status: string;
  start_date: string;
  end_date: string;
  created_at: string;
  containers?: any[];
}

interface BatchManagementProps {
  onBack?: () => void;
}

const BatchManagement: React.FC<BatchManagementProps> = ({ onBack }) => {
  const { hasPermission } = useUser();
  const [view, setView] = useState<'list' | 'create' | 'edit' | 'details'>('list');
  const [selectedBatch, setSelectedBatch] = useState<Batch | null>(null);
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [listEntries, setListEntries] = useState<any>({});
  const [workflowTemplates, setWorkflowTemplates] = useState<{ id: string; name: string }[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  const [applyTemplateLoading, setApplyTemplateLoading] = useState(false);
  const [applyTemplateError, setApplyTemplateError] = useState<string | null>(null);
  const [applyTemplateSuccess, setApplyTemplateSuccess] = useState<string | null>(null);

  const canExecuteWorkflow = hasPermission('workflow:execute');

  useEffect(() => {
    const loadListEntries = async () => {
      try {
        const [batchStatuses, batchTypes] = await Promise.all([
          apiService.getListEntries('batch_status'),
          apiService.getListEntries('batch_types').catch(() => []),
        ]);
        setListEntries({
          batch_statuses: batchStatuses,
          batch_types: batchTypes,
        });
      } catch (err) {
        console.error('Failed to load list entries:', err);
      }
    };
    loadListEntries();
  }, []);

  useEffect(() => {
    if (canExecuteWorkflow) {
      apiService.getWorkflowTemplates({ active: true })
        .then((list) => setWorkflowTemplates(Array.isArray(list) ? list : []))
        .catch((err) => console.error('Failed to load workflow templates:', err));
    }
  }, [canExecuteWorkflow]);

  const handleApplyTemplate = async () => {
    if (!selectedBatch || !selectedTemplateId || !canExecuteWorkflow) return;
    setApplyTemplateLoading(true);
    setApplyTemplateError(null);
    setApplyTemplateSuccess(null);
    try {
      await apiService.executeWorkflow(selectedTemplateId, {
        context: { batch_id: selectedBatch.id },
      });
      setApplyTemplateSuccess('Workflow executed successfully.');
      setSelectedTemplateId('');
      await handleViewBatch(selectedBatch.id);
    } catch (err: any) {
      setApplyTemplateError(err.response?.data?.detail || err.message || 'Failed to execute workflow');
    } finally {
      setApplyTemplateLoading(false);
    }
  };

  const getTypeName = (typeId: string) => {
    if (!typeId) return 'Not set';
    return listEntries.batch_types?.find((t: any) => t.id === typeId)?.name || typeId;
  };

  const getStatusName = (statusId: string) => {
    if (!statusId) return 'Not set';
    return listEntries.batch_statuses?.find((s: any) => s.id === statusId)?.name || statusId;
  };

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
            <BatchFormEnhanced
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
              <Typography variant="h5">Edit Batch: {selectedBatch.name}</Typography>
              <Button onClick={handleBackToList}>Back to List</Button>
            </Box>
            <BatchForm
              batch={selectedBatch}
              onSuccess={handleBatchUpdated}
              onCancel={handleBackToList}
            />
          </CardContent>
        </Card>
      )}

      {view === 'details' && selectedBatch && (
        <Card>
          <CardContent>
            {applyTemplateError && (
              <Alert severity="error" sx={{ mb: 2 }} onClose={() => setApplyTemplateError(null)}>
                {applyTemplateError}
              </Alert>
            )}
            {applyTemplateSuccess && (
              <Alert severity="success" sx={{ mb: 2 }} onClose={() => setApplyTemplateSuccess(null)}>
                {applyTemplateSuccess}
              </Alert>
            )}
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2, mb: 2 }}>
              <Typography variant="h5">{selectedBatch.name}</Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                {canExecuteWorkflow && workflowTemplates.length > 0 && (
                  <>
                    <FormControl size="small" sx={{ minWidth: 200 }}>
                      <InputLabel id="batch-apply-template-label">Apply Template</InputLabel>
                      <Select
                        labelId="batch-apply-template-label"
                        value={selectedTemplateId}
                        label="Apply Template"
                        onChange={(e) => setSelectedTemplateId(e.target.value)}
                        disabled={applyTemplateLoading}
                      >
                        <MenuItem value="">
                          <em>Select workflow...</em>
                        </MenuItem>
                        {workflowTemplates.map((t) => (
                          <MenuItem key={t.id} value={t.id}>
                            {t.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                    <Button
                      variant="outlined"
                      onClick={handleApplyTemplate}
                      disabled={!selectedTemplateId || applyTemplateLoading}
                      startIcon={applyTemplateLoading ? <CircularProgress size={18} /> : null}
                    >
                      {applyTemplateLoading ? 'Running...' : 'Apply'}
                    </Button>
                  </>
                )}
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
                containers={selectedBatch.containers || []}
                onContainersChange={(updatedContainers) => {
                  setSelectedBatch(prev => prev ? { ...prev, containers: updatedContainers } : null);
                }}
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
                    <strong>Type:</strong> {getTypeName(selectedBatch.type)}
                  </Typography>
                  <Typography variant="body2">
                    <strong>Status:</strong> {getStatusName(selectedBatch.status)}
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
