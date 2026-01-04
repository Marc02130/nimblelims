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

  const validationSchema = Yup.object({
    status: Yup.string().required('Status is required'),
    technician_id: Yup.string().nullable(),
    test_date: Yup.date().nullable().max(new Date(), 'Test date cannot be in the future'),
    review_date: Yup.date().nullable().max(new Date(), 'Review date cannot be in the future'),
    ...buildCustomAttributesValidation(customAttributeConfigs),
  });

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
      >
        {({ values, errors, touched, setFieldValue, isValid }) => (
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
                    value={values.test_date ? new Date(values.test_date) : null}
                    onChange={(date) => setFieldValue('test_date', date ? date.toISOString() : null)}
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

