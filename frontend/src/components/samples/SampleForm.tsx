import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  Typography,
  Divider,
  Tooltip,
  IconButton,
  Alert,
  CircularProgress,
} from '@mui/material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import CustomAttributeField from '../common/CustomAttributeField';
import { apiService } from '../../services/apiService';
import { useUser } from '../../contexts/UserContext';

interface CustomAttributeConfig {
  id: string;
  entity_type: string;
  attr_name: string;
  data_type: 'text' | 'number' | 'date' | 'boolean' | 'select';
  validation_rules: Record<string, any>;
  description?: string;
  active: boolean;
}

interface SampleFormProps {
  sample?: any;
  lookupData: {
    sampleTypes: any[];
    statuses: any[];
    matrices: any[];
    qcTypes: any[];
    projects: any[];
  };
  onSubmit: (data: any) => Promise<void>;
  onCancel: () => void;
}

const buildCustomAttributesValidation = (configs: CustomAttributeConfig[]): Record<string, any> => {
  const customAttrsSchema: Record<string, any> = {};
  
  configs.forEach((config) => {
    if (!config.active) return;
    
    const fieldPath = `custom_attributes.${config.attr_name}`;
    let fieldSchema: any = null;
    
    switch (config.data_type) {
      case 'text':
        fieldSchema = Yup.string().nullable();
        if (config.validation_rules?.max_length) {
          fieldSchema = fieldSchema.max(config.validation_rules.max_length);
        }
        if (config.validation_rules?.min_length) {
          fieldSchema = fieldSchema.min(config.validation_rules.min_length);
        }
        break;
      
      case 'number':
        fieldSchema = Yup.number().nullable();
        if (config.validation_rules?.min !== undefined) {
          fieldSchema = fieldSchema.min(config.validation_rules.min);
        }
        if (config.validation_rules?.max !== undefined) {
          fieldSchema = fieldSchema.max(config.validation_rules.max);
        }
        break;
      
      case 'date':
        fieldSchema = Yup.date().nullable();
        break;
      
      case 'boolean':
        fieldSchema = Yup.boolean().nullable();
        break;
      
      case 'select':
        const options = config.validation_rules?.options || [];
        fieldSchema = Yup.string().oneOf([...options, ''], `Must be one of: ${options.join(', ')}`).nullable();
        break;
      
      default:
        fieldSchema = Yup.mixed().nullable();
    }
    
    if (fieldSchema) {
      customAttrsSchema[fieldPath] = fieldSchema;
    }
  });
  
  return customAttrsSchema;
};

const SampleForm: React.FC<SampleFormProps> = ({
  sample,
  lookupData,
  onSubmit,
  onCancel,
}) => {
  const { hasPermission } = useUser();
  const [loading, setLoading] = useState(false);
  const [customAttributeConfigs, setCustomAttributeConfigs] = useState<CustomAttributeConfig[]>([]);
  const [configsError, setConfigsError] = useState<string | null>(null);
  const [loadingConfigs, setLoadingConfigs] = useState(false);
  const isEditMode = !!sample;
  const canUpdate = hasPermission('sample:update');

  useEffect(() => {
    loadCustomAttributeConfigs();
  }, []);

  const loadCustomAttributeConfigs = async () => {
    try {
      setLoadingConfigs(true);
      setConfigsError(null);
      const response = await apiService.getCustomAttributeConfigs({
        entity_type: 'samples',
        active: true,
      });
      setCustomAttributeConfigs(response.configs || []);
    } catch (err: any) {
      setConfigsError(err.response?.data?.detail || 'Failed to load custom fields');
      console.error('Error loading custom attribute configs:', err);
    } finally {
      setLoadingConfigs(false);
    }
  };

  const validationSchema = Yup.object({
    name: Yup.string().min(1, 'Sample name is required').max(255, 'Name must be less than 255 characters'),
    description: Yup.string().nullable(),
    due_date: Yup.date().nullable().max(new Date(), 'Due date cannot be in the future'),
    received_date: Yup.date().nullable().max(new Date(), 'Received date cannot be in the future'),
    report_date: Yup.date().nullable().max(new Date(), 'Report date cannot be in the future'),
    sample_type: Yup.string().nullable(),
    status: Yup.string().nullable(),
    matrix: Yup.string().nullable(),
    temperature: Yup.number().nullable().min(-273.15, 'Temperature must be at least -273.15°C').max(1000, 'Temperature must be at most 1000°C'),
    qc_type: Yup.string().nullable(),
    ...buildCustomAttributesValidation(customAttributeConfigs),
  });

  const initialValues = {
    name: sample?.name || '',
    description: sample?.description || '',
    due_date: sample?.due_date || null,
    received_date: sample?.received_date || null,
    report_date: sample?.report_date || null,
    sample_type: sample?.sample_type || '',
    status: sample?.status || '',
    matrix: sample?.matrix || '',
    temperature: sample?.temperature || null,
    qc_type: sample?.qc_type || '',
    custom_attributes: sample?.custom_attributes || {},
  };

  const handleSubmit = async (values: any) => {
    setLoading(true);
    try {
      // Prepare update data (only include fields that are set)
      const updateData: any = {};
      if (values.name !== undefined) updateData.name = values.name;
      if (values.description !== undefined) updateData.description = values.description;
      if (values.due_date !== null && values.due_date !== undefined) updateData.due_date = values.due_date;
      if (values.received_date !== null && values.received_date !== undefined) updateData.received_date = values.received_date;
      if (values.report_date !== null && values.report_date !== undefined) updateData.report_date = values.report_date;
      if (values.sample_type) updateData.sample_type = values.sample_type;
      if (values.status) updateData.status = values.status;
      if (values.matrix) updateData.matrix = values.matrix;
      if (values.temperature !== null && values.temperature !== undefined) updateData.temperature = values.temperature;
      if (values.qc_type) updateData.qc_type = values.qc_type;
      if (Object.keys(values.custom_attributes || {}).length > 0) {
        updateData.custom_attributes = values.custom_attributes;
      }

      await onSubmit(updateData);
    } catch (error) {
      // Error handling is done in parent component
      throw error;
    } finally {
      setLoading(false);
    }
  };

  if (loadingConfigs) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      {!canUpdate && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          You do not have permission to update samples. Contact your administrator.
        </Alert>
      )}

      {configsError && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {configsError}
        </Alert>
      )}

      <Formik
        initialValues={initialValues}
        validationSchema={validationSchema}
        onSubmit={handleSubmit}
        enableReinitialize
      >
        {({ values, errors, touched, setFieldValue, isValid }) => (
          <Form>
            <Grid container spacing={3}>
              <Grid size={12}>
                <Typography variant="h6" gutterBottom>
                  Sample Information
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <Field name="name">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Sample Name"
                      fullWidth
                      required
                      error={meta.touched && !!meta.error}
                      helperText={meta.touched && meta.error}
                      disabled={!canUpdate}
                    />
                  )}
                </Field>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <Field name="description">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Description"
                      fullWidth
                      multiline
                      rows={2}
                      error={meta.touched && !!meta.error}
                      helperText={meta.touched && meta.error}
                      disabled={!canUpdate}
                    />
                  )}
                </Field>
              </Grid>

              <Grid size={{ xs: 12, sm: 4 }}>
                <LocalizationProvider dateAdapter={AdapterDateFns}>
                  <DatePicker
                    label="Due Date"
                    value={values.due_date ? new Date(values.due_date) : null}
                    onChange={(date) => setFieldValue('due_date', date ? date.toISOString() : null)}
                    slotProps={{
                      textField: {
                        fullWidth: true,
                        error: touched.due_date && !!errors.due_date,
                        helperText: touched.due_date && errors.due_date ? String(errors.due_date) : undefined,
                        disabled: !canUpdate,
                      },
                    }}
                  />
                </LocalizationProvider>
              </Grid>

              <Grid size={{ xs: 12, sm: 4 }}>
                <LocalizationProvider dateAdapter={AdapterDateFns}>
                  <DatePicker
                    label="Received Date"
                    value={values.received_date ? new Date(values.received_date) : null}
                    onChange={(date) => setFieldValue('received_date', date ? date.toISOString() : null)}
                    slotProps={{
                      textField: {
                        fullWidth: true,
                        error: touched.received_date && !!errors.received_date,
                        helperText: touched.received_date && errors.received_date ? String(errors.received_date) : undefined,
                        disabled: !canUpdate,
                      },
                    }}
                  />
                </LocalizationProvider>
              </Grid>

              <Grid size={{ xs: 12, sm: 4 }}>
                <LocalizationProvider dateAdapter={AdapterDateFns}>
                  <DatePicker
                    label="Report Date"
                    value={values.report_date ? new Date(values.report_date) : null}
                    onChange={(date) => setFieldValue('report_date', date ? date.toISOString() : null)}
                    slotProps={{
                      textField: {
                        fullWidth: true,
                        error: touched.report_date && !!errors.report_date,
                        helperText: touched.report_date && errors.report_date ? String(errors.report_date) : undefined,
                        disabled: !canUpdate,
                      },
                    }}
                  />
                </LocalizationProvider>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth>
                  <InputLabel>Sample Type</InputLabel>
                  <Select
                    value={values.sample_type || ''}
                    onChange={(e) => setFieldValue('sample_type', e.target.value)}
                    error={touched.sample_type && !!errors.sample_type}
                    disabled={!canUpdate}
                  >
                    <MenuItem value="">None</MenuItem>
                    {lookupData.sampleTypes.map((type) => (
                      <MenuItem key={type.id} value={type.id}>
                        {type.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth>
                  <InputLabel>Status</InputLabel>
                  <Select
                    value={values.status || ''}
                    onChange={(e) => setFieldValue('status', e.target.value)}
                    error={touched.status && !!errors.status}
                    disabled={!canUpdate}
                  >
                    <MenuItem value="">None</MenuItem>
                    {lookupData.statuses.map((status) => (
                      <MenuItem key={status.id} value={status.id}>
                        {status.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <Tooltip title="Edit status: Requires sample:update permission" arrow>
                  <IconButton size="small" sx={{ ml: 1, mt: -1 }}>
                    <HelpOutlineIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth>
                  <InputLabel>Matrix</InputLabel>
                  <Select
                    value={values.matrix || ''}
                    onChange={(e) => setFieldValue('matrix', e.target.value)}
                    error={touched.matrix && !!errors.matrix}
                    disabled={!canUpdate}
                  >
                    <MenuItem value="">None</MenuItem>
                    {lookupData.matrices.map((matrix) => (
                      <MenuItem key={matrix.id} value={matrix.id}>
                        {matrix.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <Field name="temperature">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Temperature (°C)"
                      type="number"
                      fullWidth
                      error={meta.touched && !!meta.error}
                      helperText={meta.touched && meta.error}
                      disabled={!canUpdate}
                    />
                  )}
                </Field>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth>
                  <InputLabel>QC Type</InputLabel>
                  <Select
                    value={values.qc_type || ''}
                    onChange={(e) => setFieldValue('qc_type', e.target.value || null)}
                    error={touched.qc_type && !!errors.qc_type}
                    disabled={!canUpdate}
                  >
                    <MenuItem value="">None</MenuItem>
                    {lookupData.qcTypes.map((qcType) => (
                      <MenuItem key={qcType.id} value={qcType.id}>
                        {qcType.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              {/* Custom Attributes */}
              {customAttributeConfigs.length > 0 && (
                <>
                  <Grid size={12}>
                    <Divider sx={{ my: 2 }} />
                    <Typography variant="h6" gutterBottom>
                      Custom Attributes
                    </Typography>
                  </Grid>
                  {customAttributeConfigs.map((config) => {
                    const fieldError = errors?.custom_attributes && typeof errors.custom_attributes === 'object' && !Array.isArray(errors.custom_attributes)
                      ? (errors.custom_attributes as Record<string, any>)[config.attr_name]
                      : undefined;
                    const fieldTouched = touched?.custom_attributes && typeof touched.custom_attributes === 'object' && !Array.isArray(touched.custom_attributes)
                      ? (touched.custom_attributes as Record<string, any>)[config.attr_name]
                      : false;

                    return (
                      <Grid size={{ xs: 12, sm: 6 }} key={config.id}>
                        <CustomAttributeField
                          config={config}
                          value={values.custom_attributes?.[config.attr_name]}
                          onChange={(value) => {
                            const newCustomAttrs = { ...values.custom_attributes };
                            if (value === null || value === undefined || value === '') {
                              delete newCustomAttrs[config.attr_name];
                            } else {
                              newCustomAttrs[config.attr_name] = value;
                            }
                            setFieldValue('custom_attributes', newCustomAttrs);
                          }}
                          error={fieldTouched && !!fieldError}
                          helperText={fieldTouched && fieldError ? String(fieldError) : undefined}
                        />
                      </Grid>
                    );
                  })}
                </>
              )}
            </Grid>

            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 3 }}>
              <Button onClick={onCancel} disabled={loading}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="contained"
                disabled={!isValid || loading || !canUpdate}
                aria-label={isEditMode ? 'Update sample' : 'Create sample'}
              >
                {loading ? 'Saving...' : isEditMode ? 'Update' : 'Create'}
              </Button>
            </Box>
          </Form>
        )}
      </Formik>
    </Box>
  );
};

export default SampleForm;

