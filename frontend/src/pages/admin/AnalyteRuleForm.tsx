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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Checkbox,
  Grid,
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { apiService } from '../../services/apiService';

interface Analyte {
  id: string;
  name: string;
  description?: string;
}

interface AnalyteRuleFormProps {
  open: boolean;
  analysisId: string;
  rule?: {
    analyte_id: string;
    analyte_name?: string;
    data_type?: string;
    list_id?: string;
    high_value?: number;
    low_value?: number;
    significant_figures?: number;
    calculation?: string;
    reported_name?: string;
    is_required?: boolean;
    default_value?: string;
  } | null;
  existingAnalyteIds: string[];
  dataTypes: Array<{ id: string; name: string }>;
  onClose: () => void;
  onSubmit: (data: {
    analyte_id: string;
    data_type?: string;
    list_id?: string;
    high_value?: number;
    low_value?: number;
    significant_figures?: number;
    calculation?: string;
    reported_name?: string;
    is_required: boolean;
    default_value?: string;
  }) => Promise<void>;
}

const createValidationSchema = (isEdit: boolean) => Yup.object({
  analyte_id: isEdit
    ? Yup.string().notRequired()
    : Yup.string().required('Analyte is required'),
  data_type: Yup.string().nullable(),
  high_value: Yup.number().nullable(),
  low_value: Yup.number().nullable(),
  significant_figures: Yup.number()
    .integer('Significant figures must be an integer')
    .min(1, 'Significant figures must be at least 1')
    .nullable(),
  calculation: Yup.string().nullable(),
  reported_name: Yup.string().max(255, 'Reported name must be less than 255 characters').nullable(),
  is_required: Yup.boolean().required(),
  default_value: Yup.string().max(255, 'Default value must be less than 255 characters').nullable(),
}).test('low-high-range', 'Low value must be less than or equal to high value', function (values) {
  const { low_value, high_value } = values;
  if (low_value !== null && low_value !== undefined && high_value !== null && high_value !== undefined) {
    return low_value <= high_value;
  }
  return true;
});

const AnalyteRuleForm: React.FC<AnalyteRuleFormProps> = ({
  open,
  analysisId,
  rule,
  existingAnalyteIds,
  dataTypes,
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = useState(false);
  const [loadingAnalytes, setLoadingAnalytes] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [allAnalytes, setAllAnalytes] = useState<Analyte[]>([]);

  const isEdit = !!rule;

  useEffect(() => {
    if (open) {
      loadAnalytes();
    }
  }, [open]);

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

  const initialValues = {
    analyte_id: rule?.analyte_id || '',
    data_type: rule?.data_type || '',
    list_id: rule?.list_id || '',
    high_value: rule?.high_value || null,
    low_value: rule?.low_value || null,
    significant_figures: rule?.significant_figures || null,
    calculation: rule?.calculation || '',
    reported_name: rule?.reported_name || '',
    is_required: rule?.is_required || false,
    default_value: rule?.default_value || '',
  };

  const handleSubmit = async (values: {
    analyte_id: string;
    data_type?: string;
    list_id?: string;
    high_value?: number | null;
    low_value?: number | null;
    significant_figures?: number | null;
    calculation?: string;
    reported_name?: string;
    is_required: boolean;
    default_value?: string;
  }) => {
    setLoading(true);
    setError(null);

    try {
      // Check for uniqueness (excluding current rule if editing)
      if (!isEdit && existingAnalyteIds.includes(values.analyte_id)) {
        setError('This analyte is already configured for this analysis');
        setLoading(false);
        return;
      }

      const submitData: any = {
        analyte_id: values.analyte_id,
        is_required: values.is_required,
      };

      if (values.data_type) submitData.data_type = values.data_type;
      if (values.list_id) submitData.list_id = values.list_id;
      if (values.high_value !== null && values.high_value !== undefined) submitData.high_value = values.high_value;
      if (values.low_value !== null && values.low_value !== undefined) submitData.low_value = values.low_value;
      if (values.significant_figures !== null && values.significant_figures !== undefined) {
        submitData.significant_figures = values.significant_figures;
      }
      if (values.calculation) submitData.calculation = values.calculation;
      if (values.reported_name) submitData.reported_name = values.reported_name;
      if (values.default_value) submitData.default_value = values.default_value;

      await onSubmit(submitData);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save analyte rule');
    } finally {
      setLoading(false);
    }
  };

  // Filter out already assigned analytes (for create mode)
  const availableAnalytes = isEdit
    ? allAnalytes
    : allAnalytes.filter((a) => !existingAnalyteIds.includes(a.id));

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <Formik
        initialValues={initialValues}
        validationSchema={createValidationSchema(isEdit)}
        onSubmit={handleSubmit}
        enableReinitialize
      >
        {({ values, errors, touched, setFieldValue, isValid }) => (
          <Form>
            <DialogTitle>{isEdit ? 'Edit Analyte Rule' : 'Add Analyte Rule'}</DialogTitle>
            <DialogContent>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              <Box sx={{ pt: 2 }}>
                <Grid container spacing={2} sx={{ mt: 0 }}>
                  <Grid size={12}>
                    <FormControl fullWidth required={!isEdit} margin="normal" disabled={isEdit}>
                      <InputLabel>Analyte</InputLabel>
                      <Select
                        value={values.analyte_id}
                        onChange={(e) => setFieldValue('analyte_id', e.target.value)}
                        error={touched.analyte_id && !!errors.analyte_id}
                      >
                        {availableAnalytes.map((analyte) => (
                          <MenuItem key={analyte.id} value={analyte.id}>
                            {analyte.name}
                            {analyte.description && (
                              <Box component="span" sx={{ ml: 1, color: 'text.secondary', fontSize: '0.875rem' }}>
                                - {analyte.description}
                              </Box>
                            )}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <FormControl fullWidth margin="normal">
                      <InputLabel>Data Type</InputLabel>
                      <Select
                        value={values.data_type || ''}
                        onChange={(e) => setFieldValue('data_type', e.target.value || null)}
                      >
                        <MenuItem value="">None</MenuItem>
                        {dataTypes.map((dt) => (
                          <MenuItem key={dt.id} value={dt.name}>
                            {dt.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Field name="reported_name">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Reported Name"
                          fullWidth
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Optional custom name for reporting'}
                          error={meta.touched && !!meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Field name="low_value">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Low Value"
                          type="number"
                          fullWidth
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Minimum acceptable value'}
                          error={meta.touched && !!meta.error}
                          onChange={(e) => {
                            const value = e.target.value === '' ? null : parseFloat(e.target.value);
                            setFieldValue('low_value', value);
                          }}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Field name="high_value">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="High Value"
                          type="number"
                          fullWidth
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Maximum acceptable value'}
                          error={meta.touched && !!meta.error}
                          onChange={(e) => {
                            const value = e.target.value === '' ? null : parseFloat(e.target.value);
                            setFieldValue('high_value', value);
                          }}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Field name="significant_figures">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Significant Figures"
                          type="number"
                          fullWidth
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Number of significant figures'}
                          error={meta.touched && !!meta.error}
                          onChange={(e) => {
                            const value = e.target.value === '' ? null : parseInt(e.target.value, 10);
                            setFieldValue('significant_figures', value);
                          }}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Field name="default_value">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Default Value"
                          fullWidth
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Optional default value'}
                          error={meta.touched && !!meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={12}>
                    <Field name="calculation">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Calculation Formula"
                          fullWidth
                          multiline
                          rows={2}
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Optional calculation formula'}
                          error={meta.touched && !!meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={12}>
                    <FormControlLabel
                      control={
                        <Checkbox
                          checked={values.is_required}
                          onChange={(e) => setFieldValue('is_required', e.target.checked)}
                        />
                      }
                      label="Required"
                    />
                  </Grid>
                </Grid>
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={onClose} disabled={loading}>
                Cancel
              </Button>
              <Button type="submit" variant="contained" disabled={loading || !isValid}>
                {loading ? 'Saving...' : isEdit ? 'Update' : 'Add'}
              </Button>
            </DialogActions>
          </Form>
        )}
      </Formik>
    </Dialog>
  );
};

export default AnalyteRuleForm;

