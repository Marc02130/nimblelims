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
  FormHelperText,
} from '@mui/material';
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
  temperature: number;
  concentration: number;
  concentration_units: string;
  amount: number;
  amount_units: string;
  container_id: string;
  source_container_id: string;
}

function asRows(data: any): Array<{ id: string; name: string }> {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.containers)) return data.containers;
  return [];
}

function apiErrorMessage(err: any, fallback: string): string {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail.message === 'string') return detail.message;
  return fallback;
}

const DerivativeForm: React.FC<DerivativeFormProps> = ({ parentSampleId, onSuccess, onCancel }) => {
  const [formData, setFormData] = useState<DerivativeFormData>({
    name: '',
    description: '',
    sample_type: '',
    temperature: 0,
    concentration: 0,
    concentration_units: '',
    amount: 0,
    amount_units: '',
    container_id: '',
    source_container_id: '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listEntries, setListEntries] = useState<any>({});
  const [units, setUnits] = useState<any[]>([]);
  const [containers, setContainers] = useState<Array<{ id: string; name: string }>>([]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [sampleTypes, unitsData, containersData] = await Promise.all([
          apiService.getListEntries('sample_types'),
          apiService.getUnits(),
          apiService.getContainers(),
        ]);

        setListEntries({ sample_types: sampleTypes });
        setUnits(unitsData);
        setContainers(asRows(containersData));
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

    if (!formData.sample_type) {
      setError('Choose a sample type that is different from the parent.');
      setLoading(false);
      return;
    }
    if (!formData.container_id) {
      setError('Choose a destination container.');
      setLoading(false);
      return;
    }
    if (!(formData.amount > 0)) {
      setError('Enter an amount greater than zero.');
      setLoading(false);
      return;
    }

    try {
      const derivativeData: Record<string, unknown> = {
        parent_sample_id: parentSampleId,
        name: formData.name || 'derivative',
        sample_type: formData.sample_type,
        container_id: formData.container_id,
        amount: formData.amount,
      };
      if (formData.description) derivativeData.description = formData.description;
      if (formData.temperature) derivativeData.temperature = formData.temperature;
      if (formData.source_container_id) derivativeData.source_container_id = formData.source_container_id;
      if (formData.concentration) derivativeData.concentration = formData.concentration;
      if (formData.concentration_units) derivativeData.concentration_units = formData.concentration_units;
      if (formData.amount_units) derivativeData.amount_units = formData.amount_units;

      const result = await apiService.createDerivative(derivativeData);
      onSuccess(result);
    } catch (err: any) {
      setError(apiErrorMessage(err, 'Failed to create derivative'));
    } finally {
      setLoading(false);
    }
  };

  const concentrationUnits = units.filter(unit => unit.type_name === 'concentration');
  const amountUnits = units.filter(unit => unit.type_name === 'mass' || unit.type_name === 'volume');

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Create Derivative
        </Typography>
        <Divider sx={{ mb: 2 }} />

        <Alert severity="info" sx={{ mb: 2 }}>
          A derivative changes the sample type and creates a child sample. The child is named
          parent-DER-token. The source vessel amount is reduced by the amount you move.
        </Alert>

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
                label="Label"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                helperText="Stored as the description when Description is empty. The sample name is assigned on the server."
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
                <InputLabel id="derivative-sample-type-label">Sample Type</InputLabel>
                <Select
                  labelId="derivative-sample-type-label"
                  label="Sample Type"
                  value={formData.sample_type}
                  onChange={(e) => handleInputChange('sample_type', e.target.value)}
                >
                  {listEntries.sample_types?.map((entry: any) => (
                    <MenuItem key={entry.id} value={entry.id}>
                      {entry.name}
                    </MenuItem>
                  ))}
                </Select>
                <FormHelperText>Must be an allowed derivative transition for this client.</FormHelperText>
              </FormControl>
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                label="Temperature"
                type="number"
                value={formData.temperature}
                onChange={(e) => handleInputChange('temperature', parseFloat(e.target.value))}
                helperText="Leave 0 to keep the parent's temperature."
              />
            </Grid>

            <Grid size={12}>
              <Typography variant="subtitle1" sx={{ mt: 2, mb: 1 }}>
                Container Information
              </Typography>
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth required>
                <InputLabel id="derivative-destination-container-label">Destination container</InputLabel>
                <Select
                  labelId="derivative-destination-container-label"
                  label="Destination container"
                  value={formData.container_id}
                  onChange={(e) => handleInputChange('container_id', e.target.value)}
                >
                  {containers.map((row) => (
                    <MenuItem key={row.id} value={row.id}>
                      {row.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>

            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel id="derivative-source-container-label">Source container</InputLabel>
                <Select
                  labelId="derivative-source-container-label"
                  label="Source container"
                  value={formData.source_container_id}
                  onChange={(e) => handleInputChange('source_container_id', e.target.value)}
                >
                  <MenuItem value="">Only vessel</MenuItem>
                  {containers.map((row) => (
                    <MenuItem key={row.id} value={row.id}>
                      {row.name}
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
                <InputLabel id="derivative-concentration-units-label">Concentration Units</InputLabel>
                <Select
                  labelId="derivative-concentration-units-label"
                  label="Concentration Units"
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
                required
                label="Amount"
                type="number"
                value={formData.amount}
                onChange={(e) => handleInputChange('amount', parseFloat(e.target.value))}
                inputProps={{ min: 0, step: 'any' }}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 3 }}>
              <FormControl fullWidth>
                <InputLabel id="derivative-amount-units-label">Amount Units</InputLabel>
                <Select
                  labelId="derivative-amount-units-label"
                  label="Amount Units"
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
  );
};

export default DerivativeForm;
