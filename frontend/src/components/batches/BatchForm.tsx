import React, { useState, useEffect, useMemo } from 'react';
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
import { Formik, Form } from 'formik';
import * as Yup from 'yup';
import CustomAttributeField from '../common/CustomAttributeField';
import { apiService } from '../../services/apiService';

interface CustomAttributeConfig {
  id: string;
  entity_type: string;
  attr_name: string;
  data_type: 'text' | 'number' | 'date' | 'boolean' | 'select';
  validation_rules: Record<string, any>;
  description?: string;
  active: boolean;
}

interface BatchFormProps {
  onSuccess: (batch: any) => void;
  onCancel: () => void;
}

const buildCustomAttributesValidation = (configs: CustomAttributeConfig[]): Record<string, any> => {
  const customAttrsSchema: Record<string, any> = {};
  
  configs.forEach((config) => {
    if (!config.active) return;
    
    // Use the attribute name directly (not the full path)
    const fieldName = config.attr_name;
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
        fieldSchema = Yup.number()
          .nullable()
          .transform((value, originalValue) => {
            // Handle empty strings
            if (originalValue === '' || originalValue === null || originalValue === undefined) {
              return null;
            }
            // Parse number
            const parsed = typeof originalValue === 'string' ? parseFloat(originalValue) : originalValue;
            // Return null for NaN instead of NaN
            return isNaN(parsed) ? null : parsed;
          })
          .test('is-number', 'Must be a valid number', (value) => {
            if (value === null || value === undefined) return true; // Allow null/undefined
            return typeof value === 'number' && !isNaN(value);
          });
        if (config.validation_rules?.min !== undefined) {
          fieldSchema = fieldSchema.min(
            config.validation_rules.min,
            `Value must be at least ${config.validation_rules.min}`
          );
        }
        if (config.validation_rules?.max !== undefined) {
          fieldSchema = fieldSchema.max(
            config.validation_rules.max,
            `Value must be at most ${config.validation_rules.max}`
          );
        }
        break;
      
      case 'date':
        // Date values come as ISO strings, so we need to transform them
        fieldSchema = Yup.mixed()
          .nullable()
          .transform((value, originalValue) => {
            // If it's already a Date, return it
            if (value instanceof Date) return value;
            // If it's a string (ISO format), convert to Date
            if (typeof value === 'string' && value) {
              const date = new Date(value);
              return isNaN(date.getTime()) ? null : date;
            }
            return null;
          })
          .test('is-date', 'Must be a valid date', (value) => {
            if (value === null || value === undefined) return true; // Allow null/undefined
            return value instanceof Date && !isNaN(value.getTime());
          });
        if (config.validation_rules?.min_date) {
          fieldSchema = fieldSchema.test(
            'min-date',
            `Date must be on or after ${config.validation_rules.min_date}`,
            function(value: any) {
              if (!value) return true; // Allow null/undefined
              const minDate = new Date(config.validation_rules.min_date);
              return value >= minDate;
            }
          );
        }
        if (config.validation_rules?.max_date) {
          fieldSchema = fieldSchema.test(
            'max-date',
            `Date must be on or before ${config.validation_rules.max_date}`,
            function(value: any) {
              if (!value) return true; // Allow null/undefined
              const maxDate = new Date(config.validation_rules.max_date);
              return value <= maxDate;
            }
          );
        }
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
      customAttrsSchema[fieldName] = fieldSchema;
    }
  });
  
  // Return as a nested object structure for custom_attributes
  // Use noUnknown(true) to allow fields not in the schema (e.g., inactive fields)
  return {
    custom_attributes: Yup.object().shape(customAttrsSchema).noUnknown(true).nullable()
  };
};

const BatchForm: React.FC<BatchFormProps> = ({ onSuccess, onCancel }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [listEntries, setListEntries] = useState<any>({});
  const [customAttributeConfigs, setCustomAttributeConfigs] = useState<CustomAttributeConfig[]>([]);
  const [configsError, setConfigsError] = useState<string | null>(null);
  const [loadingConfigs, setLoadingConfigs] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [batchStatuses, batchTypes] = await Promise.all([
          apiService.getListEntries('batch_status'),
          apiService.getListEntries('batch_types').catch(() => []), // Handle 404 if not seeded yet
        ]);

        setListEntries({
          batch_statuses: batchStatuses,
          batch_types: batchTypes,
        });
      } catch (err) {
        setError('Failed to load form data');
      }
    };

    loadData();
    loadCustomAttributeConfigs();
  }, []);

  const loadCustomAttributeConfigs = async () => {
    try {
      setLoadingConfigs(true);
      setConfigsError(null);
      const response = await apiService.getCustomAttributeConfigs({
        entity_type: 'batches',
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

  const validationSchema = useMemo(() => Yup.object({
    name: Yup.string().required('Batch name is required').max(255, 'Name must be less than 255 characters'),
    description: Yup.string().nullable(),
    type: Yup.string().nullable(),
    status: Yup.string().required('Status is required'),
    start_date: Yup.date().nullable(),
    end_date: Yup.date().nullable(),
    ...buildCustomAttributesValidation(customAttributeConfigs),
  }), [customAttributeConfigs]);

  const getInitialValues = () => ({
    name: '',
    description: '',
    type: '',
    status: listEntries.batch_statuses?.find((s: any) => s.name === 'Created')?.id || '',
    start_date: null as Date | null,
    end_date: null as Date | null,
    custom_attributes: {} as Record<string, any>,
  });

  const handleSubmit = async (values: any) => {
    setLoading(true);
    setError(null);

    try {
      const batchData = {
        name: values.name,
        description: values.description,
        type: values.type,
        status: values.status,
        start_date: values.start_date?.toISOString(),
        end_date: values.end_date?.toISOString(),
        custom_attributes: values.custom_attributes,
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

          <Formik
            initialValues={getInitialValues()}
            validationSchema={validationSchema}
            onSubmit={handleSubmit}
            enableReinitialize
            validateOnChange={true}
            validateOnBlur={true}
          >
            {({ values, errors, touched, setFieldValue, setFieldTouched, validateField, isValid }) => (
              <Form>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Batch Name"
                      name="name"
                      value={values.name}
                      onChange={(e) => setFieldValue('name', e.target.value)}
                      onBlur={() => setFieldTouched('name', true)}
                      error={touched.name && !!errors.name}
                      helperText={touched.name && errors.name}
                  required
                      disabled={loading}
                />
              </Grid>
              <Grid size={{ xs: 12, sm: 6 }}>
                <TextField
                  fullWidth
                  label="Description"
                      name="description"
                      value={values.description}
                      onChange={(e) => setFieldValue('description', e.target.value)}
                      onBlur={() => setFieldTouched('description', true)}
                      error={touched.description && !!errors.description}
                      helperText={touched.description && errors.description}
                      disabled={loading}
                />
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                    <FormControl fullWidth error={touched.type && !!errors.type}>
                  <InputLabel>Batch Type</InputLabel>
                  <Select
                        name="type"
                        value={values.type}
                        onChange={(e) => setFieldValue('type', e.target.value)}
                        onBlur={() => setFieldTouched('type', true)}
                        label="Batch Type"
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
                    <FormControl fullWidth required error={touched.status && !!errors.status}>
                  <InputLabel>Status</InputLabel>
                  <Select
                        name="status"
                        value={values.status}
                        onChange={(e) => setFieldValue('status', e.target.value)}
                        onBlur={() => setFieldTouched('status', true)}
                        label="Status"
                  >
                    {listEntries.batch_statuses?.map((entry: any) => (
                      <MenuItem key={entry.id} value={entry.id}>
                        {entry.name}
                      </MenuItem>
                    ))}
                  </Select>
                      {touched.status && errors.status && (
                        <Box sx={{ color: 'error.main', fontSize: '0.75rem', mt: 0.5, ml: 1.75 }}>
                          {String(errors.status)}
                        </Box>
                      )}
                </FormControl>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <DatePicker
                  label="Start Date"
                      value={values.start_date}
                      onChange={(date) => {
                        setFieldValue('start_date', date);
                        setFieldTouched('start_date', true);
                      }}
                      slotProps={{
                        textField: {
                          fullWidth: true,
                          error: touched.start_date && !!errors.start_date,
                          helperText: touched.start_date && errors.start_date,
                        },
                      }}
                />
              </Grid>

              {/* End date is not available when creating a batch - only set when batch is completed */}
              {/* <Grid size={{ xs: 12, sm: 6 }}>
                <DatePicker
                  label="End Date"
                      value={values.end_date}
                      onChange={(date) => {
                        setFieldValue('end_date', date);
                        setFieldTouched('end_date', true);
                      }}
                      slotProps={{
                        textField: {
                          fullWidth: true,
                          error: touched.end_date && !!errors.end_date,
                          helperText: touched.end_date && errors.end_date,
                        },
                      }}
                />
              </Grid> */}

                  {/* Custom Attributes */}
                  {customAttributeConfigs.length > 0 && (
                    <>
                      <Grid size={12}>
                        <Divider sx={{ my: 2 }} />
                        <Typography variant="h6" gutterBottom>
                          Custom Attributes
                        </Typography>
                      </Grid>
                      {configsError && (
                        <Grid size={12}>
                          <Alert severity="error" sx={{ mb: 2 }}>
                            {configsError}
                          </Alert>
                        </Grid>
                      )}
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
                                const fieldPath = `custom_attributes.${config.attr_name}`;
                                setFieldValue('custom_attributes', newCustomAttrs);
                                setFieldTouched(fieldPath, true);
                                setTimeout(() => {
                                  validateField(fieldPath);
                                }, 0);
                              }}
                              onBlur={() => {
                                const fieldPath = `custom_attributes.${config.attr_name}`;
                                setFieldTouched(fieldPath, true);
                                validateField(fieldPath);
                              }}
                              error={fieldTouched && !!fieldError}
                              helperText={fieldTouched && fieldError ? String(fieldError) : config.description}
                            />
                          </Grid>
                        );
                      })}
                    </>
                  )}

              <Grid size={12}>
                <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end', mt: 2 }}>
                  <Button onClick={onCancel} disabled={loading}>
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="contained"
                        disabled={loading || !isValid}
                    startIcon={loading && <CircularProgress size={20} />}
                  >
                    Create Batch
                  </Button>
                </Box>
              </Grid>
            </Grid>
              </Form>
            )}
          </Formik>
        </CardContent>
      </Card>
    </LocalizationProvider>
  );
};

export default BatchForm;
