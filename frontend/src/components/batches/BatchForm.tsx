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

interface BatchFormProps {
  onSuccess: (batch: any) => void;
  onCancel: () => void;
}

interface BatchFormData {
  name: string;
  description: string;
  type: string;
  status: string;
  start_date: Date | null;
  end_date: Date | null;
}

const BatchForm: React.FC<BatchFormProps> = ({ onSuccess, onCancel }) => {
  const [formData, setFormData] = useState<BatchFormData>({
    name: '',
    description: '',
    type: '',
    status: '',
    start_date: null,
    end_date: null,
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listEntries, setListEntries] = useState<any>({});

  useEffect(() => {
    const loadData = async () => {
      try {
        const [batchStatuses] = await Promise.all([
          apiService.getListEntries('batch_status'),  // Use normalized slug format
        ]);

        setListEntries({
          batch_statuses: batchStatuses,
        });

        // Set default status to 'Created'
        const createdStatus = batchStatuses.find((status: any) => status.name === 'Created');
        if (createdStatus) {
          setFormData(prev => ({ ...prev, status: createdStatus.id }));
        }
      } catch (err) {
        setError('Failed to load form data');
      }
    };

    loadData();
  }, []);

  const handleInputChange = (field: keyof BatchFormData, value: any) => {
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
      const batchData = {
        name: formData.name,
        description: formData.description,
        type: formData.type,
        status: formData.status,
        start_date: formData.start_date?.toISOString(),
        end_date: formData.end_date?.toISOString(),
      };

      const result = await apiService.createBatch(batchData);
      onSuccess(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create batch');
    } finally {
      setLoading(false);
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Create New Batch
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
                  label="Batch Name"
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
                <FormControl fullWidth>
                  <InputLabel>Batch Type</InputLabel>
                  <Select
                    value={formData.type}
                    onChange={(e) => handleInputChange('type', e.target.value)}
                  >
                    {listEntries.batch_types?.map((entry: any) => (
                      <MenuItem key={entry.id} value={entry.id}>
                        {entry.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth required>
                  <InputLabel>Status</InputLabel>
                  <Select
                    value={formData.status}
                    onChange={(e) => handleInputChange('status', e.target.value)}
                  >
                    {listEntries.batch_statuses?.map((entry: any) => (
                      <MenuItem key={entry.id} value={entry.id}>
                        {entry.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <DatePicker
                  label="Start Date"
                  value={formData.start_date}
                  onChange={(date) => handleInputChange('start_date', date)}
                  slotProps={{ textField: { fullWidth: true } }}
                />
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <DatePicker
                  label="End Date"
                  value={formData.end_date}
                  onChange={(date) => handleInputChange('end_date', date)}
                  slotProps={{ textField: { fullWidth: true } }}
                />
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
                    Create Batch
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

export default BatchForm;
