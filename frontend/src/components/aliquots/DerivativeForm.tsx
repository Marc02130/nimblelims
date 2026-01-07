import React, { useState, useEffect } from 'react';
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
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { apiService } from '../../services/apiService';

interface DerivativeFormProps {
  parentSampleId: string;
  onSuccess: (derivative: any) => void;
  onCancel: () => void;
}

interface DerivativeFormData {
  name: string;
  description: string;
  sample_type: string;
  matrix: string;
  temperature: number;
  concentration: number;
  concentration_units: string;
  amount: number;
  amount_units: string;
  container_type: string;
  due_date: Date | null;
}

const DerivativeForm: React.FC<DerivativeFormProps> = ({ parentSampleId, onSuccess, onCancel }) => {
  const [formData, setFormData] = useState<DerivativeFormData>({
    name: '',
    description: '',
    sample_type: '',
    matrix: '',
    temperature: 0,
    concentration: 0,
    concentration_units: '',
    amount: 0,
    amount_units: '',
    container_type: '',
    due_date: null,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listEntries, setListEntries] = useState<any>({});
  const [units, setUnits] = useState<any[]>([]);
  const [containerTypes, setContainerTypes] = useState<any[]>([]);

  useEffect(() => {
    const loadData = async () => {
      try {
          const [sampleTypes, matrices, unitsData, containerTypesData] = await Promise.all([
          apiService.getListEntries('sample_types'),  // Use normalized slug format
          apiService.getListEntries('matrix_types'),  // Use normalized slug format
          apiService.getUnits(),
          apiService.getContainerTypes(),
        ]);

        setListEntries({
          sample_types: sampleTypes,
          matrices: matrices,
        });
        setUnits(unitsData);
        setContainerTypes(containerTypesData);
      } catch (err) {
        setError('Failed to load form data');
      }
    };

    loadData();
  }, []);

  const handleInputChange = (field: keyof DerivativeFormData, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const derivativeData = {
        parent_sample_id: parentSampleId,
        name: formData.name,
        description: formData.description,
        sample_type: formData.sample_type,
        matrix: formData.matrix,
        temperature: formData.temperature,
        concentration: formData.concentration,
        concentration_units: formData.concentration_units,
        amount: formData.amount,
        amount_units: formData.amount_units,
        container_type: formData.container_type,
        due_date: formData.due_date?.toISOString(),
      };

      const result = await apiService.createDerivative(derivativeData);
      onSuccess(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create derivative');
    } finally {
      setLoading(false);
    }
  };

  const concentrationUnits = units.filter(unit => unit.type_name === 'concentration');
  const amountUnits = units.filter(unit => unit.type_name === 'mass' || unit.type_name === 'volume');

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Create Derivative
          </Typography>
          <Divider sx={{ mb: 2 }} />

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <form onSubmit={handleSubmit}>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Derivative Name"
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
                <FormControl fullWidth required>
                  <InputLabel>Sample Type</InputLabel>
                  <Select
                    value={formData.sample_type}
                    onChange={(e) => handleInputChange('sample_type', e.target.value)}
                  >
                    {listEntries.sample_types?.map((entry: any) => (
                      <MenuItem key={entry.id} value={entry.id}>
                        {entry.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth required>
                  <InputLabel>Matrix</InputLabel>
                  <Select
                    value={formData.matrix}
                    onChange={(e) => handleInputChange('matrix', e.target.value)}
                  >
                    {listEntries.matrices?.map((entry: any) => (
                      <MenuItem key={entry.id} value={entry.id}>
                        {entry.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Temperature"
                  type="number"
                  value={formData.temperature}
                  onChange={(e) => handleInputChange('temperature', parseFloat(e.target.value))}
                />
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <DatePicker
                  label="Due Date"
                  value={formData.due_date}
                  onChange={(date) => handleInputChange('due_date', date)}
                  slotProps={{ textField: { fullWidth: true } }}
                />
              </Grid>

              <Grid size={12}>
                <Typography variant="subtitle1" sx={{ mt: 2, mb: 1 }}>
                  Container Information
                </Typography>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth required>
                  <InputLabel>Container Type</InputLabel>
                  <Select
                    value={formData.container_type}
                    onChange={(e) => handleInputChange('container_type', e.target.value)}
                  >
                    {containerTypes.map((type) => (
                      <MenuItem key={type.id} value={type.id}>
                        {type.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={{ xs: 12, sm: 3 }}>
                <TextField
                  fullWidth
                  label="Concentration"
                  type="number"
                  value={formData.concentration}
                  onChange={(e) => handleInputChange('concentration', parseFloat(e.target.value))}
                />
              </Grid>

              <Grid size={{ xs: 12, sm: 3 }}>
                <FormControl fullWidth>
                  <InputLabel>Concentration Units</InputLabel>
                  <Select
                    value={formData.concentration_units}
                    onChange={(e) => handleInputChange('concentration_units', e.target.value)}
                  >
                    {concentrationUnits.map((unit) => (
                      <MenuItem key={unit.id} value={unit.id}>
                        {unit.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={{ xs: 12, sm: 3 }}>
                <TextField
                  fullWidth
                  label="Amount"
                  type="number"
                  value={formData.amount}
                  onChange={(e) => handleInputChange('amount', parseFloat(e.target.value))}
                />
              </Grid>

              <Grid size={{ xs: 12, sm: 3 }}>
                <FormControl fullWidth>
                  <InputLabel>Amount Units</InputLabel>
                  <Select
                    value={formData.amount_units}
                    onChange={(e) => handleInputChange('amount_units', e.target.value)}
                  >
                    {amountUnits.map((unit) => (
                      <MenuItem key={unit.id} value={unit.id}>
                        {unit.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={12}>
                <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end', mt: 2 }}>
                  <Button onClick={onCancel} disabled={loading}>
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="contained"
                    disabled={loading}
                    startIcon={loading && <CircularProgress size={20} />}
                  >
                    Create Derivative
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </form>
        </CardContent>
      </Card>
    </LocalizationProvider>
  );
};

export default DerivativeForm;
