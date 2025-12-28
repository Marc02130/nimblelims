import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
} from '@mui/icons-material';
import { apiService } from '../../services/apiService';

interface Container {
  id: string;
  name: string;
  type: string;
  type_id?: string;
  row: number;
  column: number;
  concentration?: number;
  concentration_units?: string;
  amount?: number;
  amount_units?: string;
  samples?: any[];
  contents?: Array<{
    sample_id: string;
    sample?: {
      id: string;
      name: string;
      qc_type?: string;
      qc_type_info?: {
        id: string;
        name: string;
      };
    };
  }>;
}

interface ContainerGridProps {
  batchId: string;
  containers: Container[];
  onContainersChange: (containers: Container[]) => void;
}

const ContainerGrid: React.FC<ContainerGridProps> = ({
  batchId,
  containers,
  onContainersChange,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedContainer, setSelectedContainer] = useState<Container | null>(null);
  const [containerTypes, setContainerTypes] = useState<any[]>([]);
  const [units, setUnits] = useState<any[]>([]);
  const [formData, setFormData] = useState<any>({});
  const [batchContainers, setBatchContainers] = useState<Container[]>(containers);
  const [qcTypes, setQcTypes] = useState<any[]>([]);

  useEffect(() => {
    loadData();
    loadBatchContainers();
  }, [batchId]);

  useEffect(() => {
    setBatchContainers(containers);
  }, [containers]);

  const loadBatchContainers = async () => {
    if (!batchId) return;
    try {
      const batch = await apiService.getBatch(batchId);
      if (batch.containers) {
        setBatchContainers(batch.containers.map((bc: any) => bc.container || bc));
        onContainersChange(batch.containers.map((bc: any) => bc.container || bc));
      }
    } catch (err: any) {
      console.error('Failed to load batch containers:', err);
    }
  };

  const loadData = async () => {
    try {
      const [types, unitsData, qcTypesData] = await Promise.all([
        apiService.getContainerTypes(),
        apiService.getUnits(),
        apiService.getListEntries('qc_types').catch(() => []),
      ]);
      setContainerTypes(types);
      setUnits(unitsData);
      setQcTypes(qcTypesData || []);
    } catch (err) {
      setError('Failed to load container data');
    }
  };

  const isQCContainer = (container: Container): boolean => {
    if (!container.contents || container.contents.length === 0) return false;
    return container.contents.some(content => content.sample?.qc_type);
  };

  const getQCTypes = (container: Container): string[] => {
    if (!container.contents) return [];
    return container.contents
      .filter(content => content.sample?.qc_type)
      .map(content => {
        const qcType = qcTypes.find(qt => qt.id === content.sample?.qc_type);
        return qcType?.name || 'QC';
      });
  };

  const handleAddContainer = async () => {
    try {
      setLoading(true);
      const result = await apiService.addContainerToBatch(batchId, formData);
      const updatedContainers = [...batchContainers, result];
      setBatchContainers(updatedContainers);
      onContainersChange(updatedContainers);
      setAddDialogOpen(false);
      setFormData({});
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add container');
    } finally {
      setLoading(false);
    }
  };

  const handleEditContainer = async () => {
    if (!selectedContainer) return;

    try {
      setLoading(true);
      const result = await apiService.updateContainer(selectedContainer.id, formData);
      const updatedContainers = batchContainers.map(c => 
        c.id === selectedContainer.id ? result : c
      );
      setBatchContainers(updatedContainers);
      onContainersChange(updatedContainers);
      setEditDialogOpen(false);
      setSelectedContainer(null);
      setFormData({});
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update container');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveContainer = async (containerId: string) => {
    try {
      setLoading(true);
      await apiService.removeContainerFromBatch(batchId, containerId);
      const updatedContainers = batchContainers.filter(c => c.id !== containerId);
      setBatchContainers(updatedContainers);
      onContainersChange(updatedContainers);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to remove container');
    } finally {
      setLoading(false);
    }
  };

  const openEditDialog = (container: Container) => {
    setSelectedContainer(container);
    setFormData({
      name: container.name,
      type_id: container.type_id || container.type,
      row: container.row,
      column: container.column,
      concentration: container.concentration,
      concentration_units: container.concentration_units,
      amount: container.amount,
      amount_units: container.amount_units,
    });
    setEditDialogOpen(true);
  };

  const getContainerTypeName = (typeId: string | undefined) => {
    if (!typeId) return 'Unknown';
    return containerTypes.find(t => t.id === typeId)?.name || typeId;
  };

  const getUnitName = (unitId: string | undefined) => {
    if (!unitId) return '';
    return units.find(u => u.id === unitId)?.name || unitId;
  };

  const concentrationUnits = units.filter(unit => unit.type === 'concentration');
  const amountUnits = units.filter(unit => unit.type === 'mass' || unit.type === 'volume');

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Containers ({batchContainers.length})
          {batchContainers.filter(c => isQCContainer(c)).length > 0 && (
            <Chip
              label={`${batchContainers.filter(c => isQCContainer(c)).length} QC`}
              size="small"
              color="warning"
              sx={{ ml: 1 }}
            />
          )}
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setAddDialogOpen(true)}
        >
          Add Container
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={2}>
        {batchContainers.map((container) => {
          const isQC = isQCContainer(container);
          const qcTypeNames = getQCTypes(container);
          
          return (
          <Grid size={{ xs: 12, sm: 6, md: 4 }} key={container.id}>
              <Card
                sx={{
                  border: isQC ? '2px solid' : '1px solid',
                  borderColor: isQC ? 'warning.main' : 'divider',
                  bgcolor: isQC ? 'warning.light' : 'background.paper',
                }}
              >
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Box>
                  <Typography variant="h6">{container.name}</Typography>
                      {isQC && (
                        <Chip
                          label={`QC: ${qcTypeNames.join(', ')}`}
                          size="small"
                          color="warning"
                          sx={{ mt: 0.5 }}
                        />
                      )}
                    </Box>
                  <Box>
                    <IconButton
                      size="small"
                      onClick={() => openEditDialog(container)}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleRemoveContainer(container.id)}
                      disabled={loading}
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                </Box>
                
                <Typography variant="body2" color="text.secondary" gutterBottom>
                    {getContainerTypeName(container.type_id || container.type)}
                </Typography>

                <Box sx={{ mb: 1 }}>
                  <Chip
                    label={`Row: ${container.row}, Col: ${container.column}`}
                    size="small"
                    variant="outlined"
                  />
                </Box>

                  {container.concentration && container.concentration > 0 && (
                  <Typography variant="body2">
                    Concentration: {container.concentration} {getUnitName(container.concentration_units)}
                  </Typography>
                )}

                  {container.amount && container.amount > 0 && (
                  <Typography variant="body2">
                    Amount: {container.amount} {getUnitName(container.amount_units)}
                  </Typography>
                )}

                  {container.contents && container.contents.length > 0 && (
                    <Box sx={{ mt: 1 }}>
                      {container.contents.map((content, idx) => (
                        <Typography
                          key={idx}
                          variant="body2"
                          color={content.sample?.qc_type ? 'warning.main' : 'primary'}
                          fontWeight={content.sample?.qc_type ? 'bold' : 'normal'}
                        >
                          {content.sample?.name || `Sample ${idx + 1}`}
                          {content.sample?.qc_type && (
                            <Chip
                              label={qcTypeNames[idx] || 'QC'}
                              size="small"
                              color="warning"
                              sx={{ ml: 1 }}
                            />
                          )}
                        </Typography>
                      ))}
                    </Box>
                  )}

                {container.samples && container.samples.length > 0 && (
                  <Typography variant="body2" color="primary">
                    {container.samples.length} sample(s)
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
          );
        })}
      </Grid>

      {/* Add Container Dialog */}
      <Dialog open={addDialogOpen} onClose={() => setAddDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add Container to Batch</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <TextField
              fullWidth
              label="Container Name"
              value={formData.name || ''}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              sx={{ mb: 2 }}
            />

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Container Type</InputLabel>
              <Select
                value={formData.type_id || ''}
                onChange={(e) => setFormData({ ...formData, type_id: e.target.value })}
              >
                {containerTypes.map((type) => (
                  <MenuItem key={type.id} value={type.id}>
                    {type.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                label="Row"
                type="number"
                value={formData.row || ''}
                onChange={(e) => setFormData({ ...formData, row: parseInt(e.target.value) })}
              />
              <TextField
                label="Column"
                type="number"
                value={formData.column || ''}
                onChange={(e) => setFormData({ ...formData, column: parseInt(e.target.value) })}
              />
            </Box>

            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                label="Concentration"
                type="number"
                value={formData.concentration || ''}
                onChange={(e) => setFormData({ ...formData, concentration: parseFloat(e.target.value) })}
              />
              <FormControl sx={{ minWidth: 120 }}>
                <InputLabel>Units</InputLabel>
                <Select
                  value={formData.concentration_units || ''}
                  onChange={(e) => setFormData({ ...formData, concentration_units: e.target.value })}
                >
                  {concentrationUnits.map((unit) => (
                    <MenuItem key={unit.id} value={unit.id}>
                      {unit.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="Amount"
                type="number"
                value={formData.amount || ''}
                onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) })}
              />
              <FormControl sx={{ minWidth: 120 }}>
                <InputLabel>Units</InputLabel>
                <Select
                  value={formData.amount_units || ''}
                  onChange={(e) => setFormData({ ...formData, amount_units: e.target.value })}
                >
                  {amountUnits.map((unit) => (
                    <MenuItem key={unit.id} value={unit.id}>
                      {unit.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleAddContainer}
            variant="contained"
            disabled={loading}
            startIcon={loading && <CircularProgress size={20} />}
          >
            Add Container
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Container Dialog */}
      <Dialog open={editDialogOpen} onClose={() => setEditDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit Container</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <TextField
              fullWidth
              label="Container Name"
              value={formData.name || ''}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              sx={{ mb: 2 }}
            />

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Container Type</InputLabel>
              <Select
                value={formData.type_id || ''}
                onChange={(e) => setFormData({ ...formData, type_id: e.target.value })}
              >
                {containerTypes.map((type) => (
                  <MenuItem key={type.id} value={type.id}>
                    {type.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                label="Row"
                type="number"
                value={formData.row || ''}
                onChange={(e) => setFormData({ ...formData, row: parseInt(e.target.value) })}
              />
              <TextField
                label="Column"
                type="number"
                value={formData.column || ''}
                onChange={(e) => setFormData({ ...formData, column: parseInt(e.target.value) })}
              />
            </Box>

            <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
              <TextField
                label="Concentration"
                type="number"
                value={formData.concentration || ''}
                onChange={(e) => setFormData({ ...formData, concentration: parseFloat(e.target.value) })}
              />
              <FormControl sx={{ minWidth: 120 }}>
                <InputLabel>Units</InputLabel>
                <Select
                  value={formData.concentration_units || ''}
                  onChange={(e) => setFormData({ ...formData, concentration_units: e.target.value })}
                >
                  {concentrationUnits.map((unit) => (
                    <MenuItem key={unit.id} value={unit.id}>
                      {unit.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="Amount"
                type="number"
                value={formData.amount || ''}
                onChange={(e) => setFormData({ ...formData, amount: parseFloat(e.target.value) })}
              />
              <FormControl sx={{ minWidth: 120 }}>
                <InputLabel>Units</InputLabel>
                <Select
                  value={formData.amount_units || ''}
                  onChange={(e) => setFormData({ ...formData, amount_units: e.target.value })}
                >
                  {amountUnits.map((unit) => (
                    <MenuItem key={unit.id} value={unit.id}>
                      {unit.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleEditContainer}
            variant="contained"
            disabled={loading}
            startIcon={loading && <CircularProgress size={20} />}
          >
            Update Container
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ContainerGrid;
