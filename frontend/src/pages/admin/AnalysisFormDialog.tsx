import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Alert,
  Typography,
  Divider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  OutlinedInput,
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { apiService } from '../../services/apiService';

interface Analyte {
  id: string;
  name: string;
  description?: string;
}

interface AnalysisFormDialogProps {
  open: boolean;
  analysis?: {
    id: string;
    name: string;
    description?: string;
    method?: string;
    turnaround_time?: number;
    cost?: number;
    analytes?: Analyte[];
  } | null;
  existingNames: string[];
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
    method?: string;
    turnaround_time?: number;
    cost?: number;
    analyte_ids: string[];
  }) => Promise<void>;
}

const validationSchema = Yup.object({
  name: Yup.string()
    .required('Analysis name is required')
    .min(2, 'Analysis name must be at least 2 characters')
    .max(255, 'Analysis name must be less than 255 characters'),
  description: Yup.string().max(500, 'Description must be less than 500 characters'),
  method: Yup.string().max(255, 'Method must be less than 255 characters'),
  turnaround_time: Yup.number()
    .integer('Turnaround time must be an integer')
    .min(1, 'Turnaround time must be at least 1 day')
    .nullable(),
  cost: Yup.number()
    .min(0, 'Cost must be greater than or equal to 0')
    .nullable(),
});

const AnalysisFormDialog: React.FC<AnalysisFormDialogProps> = ({
  open,
  analysis,
  existingNames,
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = useState(false);
  const [loadingAnalytes, setLoadingAnalytes] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [allAnalytes, setAllAnalytes] = useState<Analyte[]>([]);
  const [selectedAnalyteIds, setSelectedAnalyteIds] = useState<string[]>([]);

  const isEdit = !!analysis;

  useEffect(() => {
    if (open) {
      loadAnalytes();
      if (isEdit && analysis) {
        loadAnalysisAnalytes();
      } else {
        setSelectedAnalyteIds([]);
      }
    }
  }, [open, isEdit, analysis]);

  const loadAnalytes = async () => {
    try {
      setLoadingAnalytes(true);
      const analytes = await apiService.getAnalytes();
      setAllAnalytes(analytes || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load analytes');
    } finally {
      setLoadingAnalytes(false);
    }
  };

  const loadAnalysisAnalytes = async () => {
    if (!analysis) return;
    try {
      const analysisAnalytes = await apiService.getAnalysisAnalytes(analysis.id);
      setSelectedAnalyteIds(analysisAnalytes.map((a: Analyte) => a.id));
    } catch (err: any) {
      // If endpoint doesn't exist yet, use analytes from analysis object if available
      if (analysis.analytes) {
        setSelectedAnalyteIds(analysis.analytes.map((a) => a.id));
      }
    }
  };

  const initialValues = {
    name: analysis?.name || '',
    description: analysis?.description || '',
    method: analysis?.method || '',
    turnaround_time: analysis?.turnaround_time || null,
    // Convert cost to number if it's a string (from API Decimal/Numeric types)
    cost: analysis?.cost !== undefined && analysis?.cost !== null
      ? (typeof analysis.cost === 'string' ? parseFloat(analysis.cost) : analysis.cost)
      : null,
  };

  const handleSubmit = async (values: {
    name: string;
    description?: string;
    method?: string;
    turnaround_time?: number | null;
    cost?: number | null;
  }) => {
    setLoading(true);
    setError(null);

    try {
      // Check for uniqueness (excluding current analysis if editing)
      if (existingNames.includes(values.name) && (!isEdit || values.name !== analysis.name)) {
        setError('An analysis with this name already exists');
        setLoading(false);
        return;
      }

      await onSubmit({
        name: values.name,
        description: values.description || undefined,
        method: values.method || undefined,
        turnaround_time: values.turnaround_time || undefined,
        cost: values.cost || undefined,
        analyte_ids: selectedAnalyteIds,
      });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save analysis');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <Formik
        initialValues={initialValues}
        validationSchema={validationSchema}
        onSubmit={handleSubmit}
        enableReinitialize
      >
        {({ values, errors, touched, setFieldValue, isValid }) => (
          <Form>
            <DialogTitle>{isEdit ? 'Edit Analysis' : 'Create New Analysis'}</DialogTitle>
            <DialogContent>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              <Box sx={{ pt: 2 }}>
                <Field name="name">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Analysis Name"
                      fullWidth
                      required
                      margin="normal"
                      helperText={meta.touched && meta.error ? meta.error : 'Unique identifier for this analysis'}
                      error={meta.touched && !!meta.error}
                    />
                  )}
                </Field>

                <Field name="description">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Description"
                      fullWidth
                      multiline
                      rows={2}
                      margin="normal"
                      helperText={meta.touched && meta.error ? meta.error : 'Optional description for this analysis'}
                      error={meta.touched && !!meta.error}
                    />
                  )}
                </Field>

                <Field name="method">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Method"
                      fullWidth
                      margin="normal"
                      helperText={meta.touched && meta.error ? meta.error : 'Testing method (e.g., EPA 8080)'}
                      error={meta.touched && !!meta.error}
                    />
                  )}
                </Field>

                <Box sx={{ display: 'flex', gap: 2 }}>
                  <Field name="turnaround_time">
                    {({ field, meta }: any) => (
                      <TextField
                        {...field}
                        label="Turnaround Time (days)"
                        type="number"
                        fullWidth
                        margin="normal"
                        helperText={meta.touched && meta.error ? meta.error : 'Days required for completion'}
                        error={meta.touched && !!meta.error}
                        onChange={(e) => {
                          const value = e.target.value === '' ? null : parseInt(e.target.value, 10);
                          setFieldValue('turnaround_time', value);
                        }}
                      />
                    )}
                  </Field>

                  <Field name="cost">
                    {({ field, meta }: any) => (
                      <TextField
                        {...field}
                        label="Cost"
                        type="number"
                        fullWidth
                        margin="normal"
                        helperText={meta.touched && meta.error ? meta.error : 'Cost in dollars'}
                        error={meta.touched && !!meta.error}
                        onChange={(e) => {
                          const value = e.target.value === '' ? null : parseFloat(e.target.value);
                          setFieldValue('cost', value);
                        }}
                      />
                    )}
                  </Field>
                </Box>

                <Divider sx={{ my: 3 }} />

                <Typography variant="h6" gutterBottom>
                  Analytes
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Select the analytes to include in this analysis. Changes will be saved when you submit the form.
                </Typography>

                {loadingAnalytes ? (
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <Typography>Loading analytes...</Typography>
                  </Box>
                ) : (
                  <FormControl fullWidth margin="normal">
                    <InputLabel>Analytes</InputLabel>
                    <Select
                      multiple
                      value={selectedAnalyteIds}
                      onChange={(e) => setSelectedAnalyteIds(e.target.value as string[])}
                      input={<OutlinedInput label="Analytes" />}
                      renderValue={(selected) => (
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                          {(selected as string[]).map((analyteId) => {
                            const analyte = allAnalytes.find((a) => a.id === analyteId);
                            return (
                              <Chip
                                key={analyteId}
                                label={analyte?.name || analyteId}
                                size="small"
                              />
                            );
                          })}
                        </Box>
                      )}
                    >
                      {allAnalytes.map((analyte) => (
                        <MenuItem key={analyte.id} value={analyte.id}>
                          {analyte.name}
                          {analyte.description && (
                            <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                              - {analyte.description}
                            </Typography>
                          )}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={onClose} disabled={loading}>
                Cancel
              </Button>
              <Button type="submit" variant="contained" disabled={loading || !isValid}>
                {loading ? 'Saving...' : isEdit ? 'Update' : 'Create'}
              </Button>
            </DialogActions>
          </Form>
        )}
      </Formik>
    </Dialog>
  );
};

export default AnalysisFormDialog;

