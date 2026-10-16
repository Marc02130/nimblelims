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
import { apiService } from '../../services/apiService';

interface AliquotFormProps {
  parentSampleId: string;
  onSuccess: (aliquot: any) => void;
  onCancel: () => void;
}

interface AliquotFormData {
  container_id: string;
  source_container_id: string;
  concentration: number | '';
  concentration_units: string;
  amount: number;
  amount_units: string;
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

const AliquotForm: React.FC<AliquotFormProps> = ({ parentSampleId, onSuccess, onCancel }) => {
  const [formData, setFormData] = useState<AliquotFormData>({
    container_id: '',
    source_container_id: '',
    concentration: '',
    concentration_units: '',
    amount: 0,
    amount_units: '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [units, setUnits] = useState<any[]>([]);
  const [containers, setContainers] = useState<Array<{ id: string; name: string }>>([]);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [unitsData, containersData] = await Promise.all([
          apiService.getUnits(),
          apiService.getContainers(),
        ]);
        setUnits(unitsData);
        setContainers(asRows(containersData));
      } catch (err) {
        setError('Failed to load form data');
      }
    };

    loadData();
  }, []);

  const handleInputChange = (field: keyof AliquotFormData, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

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
      const aliquotData: Record<string, unknown> = {
        parent_sample_id: parentSampleId,
        container_id: formData.container_id,
        amount: formData.amount,
      };
      if (formData.source_container_id) {
        aliquotData.source_container_id = formData.source_container_id;
      }
      if (formData.amount_units) {
        aliquotData.amount_units = formData.amount_units;
      }
      if (formData.concentration !== '' && !Number.isNaN(formData.concentration)) {
        aliquotData.concentration = formData.concentration;
      }
      if (formData.concentration_units) {
        aliquotData.concentration_units = formData.concentration_units;
      }

      const result = await apiService.createAliquot(aliquotData);
      onSuccess(result);
    } catch (err: any) {
      setError(apiErrorMessage(err, 'Failed to create aliquot'));
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
          Create Aliquot
        </Typography>
        <Divider sx={{ mb: 2 }} />

        <Alert severity="info" sx={{ mb: 2 }}>
          An aliquot is this same sample in another container. It does not create a new sample.
        </Alert>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth required>
                <InputLabel id="aliquot-destination-container-label">Destination container</InputLabel>
                <Select
                  labelId="aliquot-destination-container-label"
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
                <InputLabel id="aliquot-source-container-label">Source container</InputLabel>
                <Select
                  labelId="aliquot-source-container-label"
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
                label="Amount"
                type="number"
                value={formData.amount}
                onChange={(e) => handleInputChange('amount', parseFloat(e.target.value))}
                required
                inputProps={{ min: 0, step: 'any' }}
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 3 }}>
              <FormControl fullWidth>
                <InputLabel id="aliquot-amount-units-label">Amount Units</InputLabel>
                <Select
                  labelId="aliquot-amount-units-label"
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

            <Grid size={{ xs: 12, sm: 3 }}>
              <TextField
                fullWidth
                label="Concentration"
                type="number"
                value={formData.concentration}
                onChange={(e) =>
                  handleInputChange(
                    'concentration',
                    e.target.value === '' ? '' : parseFloat(e.target.value),
                  )
                }
              />
            </Grid>

            <Grid size={{ xs: 12, sm: 3 }}>
              <FormControl fullWidth>
                <InputLabel id="aliquot-concentration-units-label">Concentration Units</InputLabel>
                <Select
                  labelId="aliquot-concentration-units-label"
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
                  Create Aliquot
                </Button>
              </Box>
            </Grid>
          </Grid>
        </form>
      </CardContent>
    </Card>
  );
};

export default AliquotForm;
