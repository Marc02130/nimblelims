import React, { useState, useEffect, useMemo } from 'react';
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

interface TestFormProps {
  test?: any;
  sampleId?: string;
  lookupData: {
    statuses: any[];
    users?: any[];
    analyses?: any[];
  };
  onSubmit: (data: any) => Promise<void>;
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

const TestForm: React.FC<TestFormProps> = ({
  test,
  sampleId,
  lookupData,
  onSubmit,
  onCancel,
}) => {
  const { hasPermission } = useUser();
  const [loading, setLoading] = useState(false);
  const [customAttributeConfigs, setCustomAttributeConfigs] = useState<CustomAttributeConfig[]>([]);
  const [configsError, setConfigsError] = useState<string | null>(null);
  const isEditMode = !!test;
  const canUpdate = hasPermission('test:update');

  useEffect(() => {
    loadCustomAttributeConfigs();
  }, []);

  const loadCustomAttributeConfigs = async () => {
    try {
      setConfigsError(null);
      const response = await apiService.getCustomAttributeConfigs({
        entity_type: 'tests',
        active: true,
      });
      setCustomAttributeConfigs(response.configs || []);
    } catch (err: any) {
      setConfigsError(err.response?.data?.detail || 'Failed to load custom fields');
      console.error('Error loading custom attribute configs:', err);
    }
  };

  const validationSchema = useMemo(() => Yup.object({
    status: Yup.string().required('Status is required'),
    technician_id: Yup.string().nullable(),
    test_date: Yup.date().nullable().max(new Date(), 'Test date cannot be in the future'),
    review_date: Yup.date().nullable().max(new Date(), 'Review date cannot be in the future'),
    ...buildCustomAttributesValidation(customAttributeConfigs),
  }), [customAttributeConfigs]);

  const initialValues = {
    name: test?.name || '',
    description: test?.description || '',
    status: test?.status || '',
    technician_id: test?.technician_id || '',
    test_date: test?.test_date || null,
    review_date: test?.review_date || null,
    custom_attributes: test?.custom_attributes || {},
  };

  const handleSubmit = async (values: any) => {
    setLoading(true);
    try {
      // Prepare update data (only include fields that are set)
      const updateData: any = {};
      if (values.status) updateData.status = values.status;
      if (values.technician_id) updateData.technician_id = values.technician_id;
      if (values.test_date) updateData.test_date = values.test_date;
      if (values.review_date) updateData.review_date = values.review_date;
      if (values.description !== undefined) updateData.description = values.description;
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

  return (
    <Box sx={{ p: 2 }}>
      {!canUpdate && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          You do not have permission to update tests. Contact your administrator.
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
        validateOnChange={true}
        validateOnBlur={true}
      >
        {({ values, errors, touched, setFieldValue, setFieldTouched, validateField, isValid }) => (
          <Form>
            <Grid container spacing={3}>
              <Grid size={12}>
                <Typography variant="h6" gutterBottom>
                  Test Information
                </Typography>
                <Divider sx={{ mb: 2 }} />
              </Grid>

              {!isEditMode && (
                <>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <TextField
                      label="Test Name"
                      value={values.name}
                      fullWidth
                      disabled
                      helperText="Auto-generated from sample and analysis"
                    />
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <TextField
                      label="Description"
                      value={values.description || ''}
                      onChange={(e) => setFieldValue('description', e.target.value)}
                      fullWidth
                      multiline
                      rows={2}
                      error={touched.description && !!errors.description}
                      helperText={touched.description && errors.description ? String(errors.description) : undefined}
                    />
                  </Grid>
                </>
              )}

              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth required>
                  <InputLabel>Status</InputLabel>
                  <Select
                    value={values.status}
                    onChange={(e) => setFieldValue('status', e.target.value)}
                    error={touched.status && !!errors.status}
                    disabled={!canUpdate}
                  >
                    {lookupData.statuses.map((status) => (
                      <MenuItem key={status.id} value={status.id}>
                        {status.name}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <Tooltip title="Edit status: Requires test:update permission" arrow>
                  <IconButton size="small" sx={{ ml: 1, mt: -1 }}>
                    <HelpOutlineIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth>
                  <InputLabel>Technician</InputLabel>
                  <Select
                    value={values.technician_id || ''}
                    onChange={(e) => setFieldValue('technician_id', e.target.value || null)}
                    error={touched.technician_id && !!errors.technician_id}
                    disabled={!canUpdate}
                  >
                    <MenuItem value="">None</MenuItem>
                    {lookupData.users?.map((user) => (
                      <MenuItem key={user.id} value={user.id}>
                        {user.name || user.username}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <Tooltip title="Assign technician to this test" arrow>
                  <IconButton size="small" sx={{ ml: 1, mt: -1 }}>
                    <HelpOutlineIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <LocalizationProvider dateAdapter={AdapterDateFns}>
                  <DatePicker
                    label="Test Date"
                    value={values.test_date ? (() => {
                      // Parse date string in local timezone (YYYY-MM-DD format)
                      const dateStr = values.test_date;
                      if (dateStr && typeof dateStr === 'string' && dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
                        const [year, month, day] = dateStr.split('-').map(Number);
                        return new Date(year, month - 1, day);
                      }
                      return new Date(dateStr);
                    })() : null}
                    onChange={(date) => {
                      if (date) {
                        // Format date in local timezone as YYYY-MM-DD
                        const year = date.getFullYear();
                        const month = String(date.getMonth() + 1).padStart(2, '0');
                        const day = String(date.getDate()).padStart(2, '0');
                        setFieldValue('test_date', `${year}-${month}-${day}`);
                      } else {
                        setFieldValue('test_date', null);
                      }
                    }}
                    slotProps={{
                      textField: {
                        fullWidth: true,
                        error: touched.test_date && !!errors.test_date,
                        helperText: touched.test_date && errors.test_date ? String(errors.test_date) : undefined,
                        disabled: !canUpdate,
                      },
                    }}
                  />
                </LocalizationProvider>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <LocalizationProvider dateAdapter={AdapterDateFns}>
                  <DatePicker
                    label="Review Date"
                    value={values.review_date ? new Date(values.review_date) : null}
                    onChange={(date) => setFieldValue('review_date', date ? date.toISOString() : null)}
                    slotProps={{
                      textField: {
                        fullWidth: true,
                        error: touched.review_date && !!errors.review_date,
                        helperText: touched.review_date && errors.review_date ? String(errors.review_date) : undefined,
                        disabled: !canUpdate,
                      },
                    }}
                  />
                </LocalizationProvider>
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
                            const fieldPath = `custom_attributes.${config.attr_name}`;
                            setFieldValue('custom_attributes', newCustomAttrs);
                            // Mark field as touched and trigger validation
                            setFieldTouched(fieldPath, true);
                            // Trigger validation immediately
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
            </Grid>

            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 3 }}>
              <Button onClick={onCancel} disabled={loading}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="contained"
                disabled={!isValid || loading || !canUpdate}
                aria-label={isEditMode ? 'Update test' : 'Create test'}
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

export default TestForm;

