import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Grid,
  Typography,
  Divider,
} from '@mui/material';
import { useFormik } from 'formik';
import * as yup from 'yup';
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

interface Client {
  id: string;
  name: string;
  description?: string;
}

interface ClientProjectFormProps {
  open: boolean;
  clientProject?: {
    id: string;
    name: string;
    description?: string;
    client_id: string;
    active: boolean;
  } | null;
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
    client_id: string;
    custom_attributes?: Record<string, any>;
  }) => Promise<void>;
  existingNames?: string[];
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
        fieldSchema = yup.string().nullable();
        if (config.validation_rules?.max_length) {
          fieldSchema = fieldSchema.max(config.validation_rules.max_length);
        }
        if (config.validation_rules?.min_length) {
          fieldSchema = fieldSchema.min(config.validation_rules.min_length);
        }
        break;
      
      case 'number':
        fieldSchema = yup.number()
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
        fieldSchema = yup.mixed()
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
        fieldSchema = yup.boolean().nullable();
        break;
      
      case 'select':
        const options = config.validation_rules?.options || [];
        fieldSchema = yup.string().oneOf([...options, ''], `Must be one of: ${options.join(', ')}`).nullable();
        break;
      
      default:
        fieldSchema = yup.mixed().nullable();
    }
    
    if (fieldSchema) {
      customAttrsSchema[fieldName] = fieldSchema;
    }
  });
  
  // Return as a nested object structure for custom_attributes
  // Use noUnknown(true) to allow fields not in the schema (e.g., inactive fields)
  return {
    custom_attributes: yup.object().shape(customAttrsSchema).noUnknown(true).nullable()
  };
};

const ClientProjectForm: React.FC<ClientProjectFormProps> = ({
  open,
  clientProject,
  onClose,
  onSubmit,
  existingNames = [],
}) => {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingClients, setLoadingClients] = useState(true);
  const [customAttributeConfigs, setCustomAttributeConfigs] = useState<CustomAttributeConfig[]>([]);
  const [configsError, setConfigsError] = useState<string | null>(null);
  const [loadingConfigs, setLoadingConfigs] = useState(false);

  useEffect(() => {
    if (open) {
      loadClients();
      loadCustomAttributeConfigs();
    }
  }, [open]);

  const loadCustomAttributeConfigs = async () => {
    try {
      setLoadingConfigs(true);
      setConfigsError(null);
      const response = await apiService.getCustomAttributeConfigs({
        entity_type: 'client_projects',
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

  const loadClients = async () => {
    try {
      setLoadingClients(true);
      const clientsData = await apiService.getClients();
      setClients(clientsData || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load clients');
    } finally {
      setLoadingClients(false);
    }
  };

  const formik = useFormik({
    initialValues: {
      name: clientProject?.name || '',
      description: clientProject?.description || '',
      client_id: clientProject?.client_id || '',
      custom_attributes: (clientProject as any)?.custom_attributes || {},
    },
    validationSchema: useMemo(() => yup.object({
      name: yup
        .string()
        .required('Name is required')
        .min(1, 'Name must be at least 1 character')
        .max(255, 'Name must be at most 255 characters')
        .test('unique', 'Name already exists', (value) => {
          if (!value) return true;
          if (clientProject && value === clientProject.name) return true;
          return !existingNames.includes(value);
        }),
      description: yup.string().max(1000, 'Description must be at most 1000 characters'),
      client_id: yup.string().required('Client is required'),
      ...buildCustomAttributesValidation(customAttributeConfigs),
    }), [clientProject, existingNames, customAttributeConfigs]),
    enableReinitialize: true,
    validateOnChange: true,
    validateOnBlur: true,
    onSubmit: async (values) => {
      setLoading(true);
      setError(null);
      try {
        await onSubmit({
          name: values.name,
          description: values.description || undefined,
          client_id: values.client_id,
          custom_attributes: Object.keys(values.custom_attributes || {}).length > 0 ? values.custom_attributes : undefined,
        });
        formik.resetForm();
        onClose();
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to save client project');
      } finally {
        setLoading(false);
      }
    },
  });

  const handleClose = () => {
    if (!loading) {
      formik.resetForm();
      setError(null);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <form onSubmit={formik.handleSubmit}>
        <DialogTitle>
          {clientProject ? 'Edit Client Project' : 'Create Client Project'}
        </DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              fullWidth
              label="Name"
              name="name"
              value={formik.values.name}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
              error={formik.touched.name && Boolean(formik.errors.name)}
              helperText={formik.touched.name && formik.errors.name}
              required
              disabled={loading}
            />

            <TextField
              fullWidth
              label="Description"
              name="description"
              value={formik.values.description}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
              error={formik.touched.description && Boolean(formik.errors.description)}
              helperText={formik.touched.description && formik.errors.description}
              multiline
              rows={3}
              disabled={loading}
            />

            <FormControl
              fullWidth
              required
              error={formik.touched.client_id && Boolean(formik.errors.client_id)}
              disabled={loading || loadingClients}
            >
              <InputLabel>Client</InputLabel>
              <Select
                name="client_id"
                value={formik.values.client_id}
                onChange={formik.handleChange}
                onBlur={formik.handleBlur}
                label="Client"
              >
                {loadingClients ? (
                  <MenuItem disabled>
                    <CircularProgress size={20} sx={{ mr: 1 }} />
                    Loading clients...
                  </MenuItem>
                ) : (
                  clients.map((client) => (
                    <MenuItem key={client.id} value={client.id}>
                      {client.name}
                    </MenuItem>
                  ))
                )}
              </Select>
              {formik.touched.client_id && formik.errors.client_id && (
                <Box sx={{ color: 'error.main', fontSize: '0.75rem', mt: 0.5, ml: 1.75 }}>
                  {formik.errors.client_id}
                </Box>
              )}
            </FormControl>

            {/* Custom Attributes */}
            {customAttributeConfigs.length > 0 && (
              <>
                <Divider sx={{ my: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Custom Attributes
                </Typography>
                {configsError && (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    {configsError}
                  </Alert>
                )}
                <Grid container spacing={2}>
                  {customAttributeConfigs.map((config) => {
                    const fieldError = formik.errors?.custom_attributes && typeof formik.errors.custom_attributes === 'object' && !Array.isArray(formik.errors.custom_attributes)
                      ? (formik.errors.custom_attributes as Record<string, any>)[config.attr_name]
                      : undefined;
                    const fieldTouched = formik.touched?.custom_attributes && typeof formik.touched.custom_attributes === 'object' && !Array.isArray(formik.touched.custom_attributes)
                      ? (formik.touched.custom_attributes as Record<string, any>)[config.attr_name]
                      : false;

                    return (
                      <Grid key={config.id} size={{ xs: 12, sm: 6 }}>
                        <CustomAttributeField
                          config={config}
                          value={(formik.values.custom_attributes as Record<string, any>)?.[config.attr_name]}
                          onChange={(value) => {
                            const newCustomAttrs = { ...(formik.values.custom_attributes as Record<string, any>) };
                            if (value === null || value === undefined || value === '') {
                              delete newCustomAttrs[config.attr_name];
                            } else {
                              newCustomAttrs[config.attr_name] = value;
                            }
                            formik.setFieldValue('custom_attributes', newCustomAttrs);
                            const fieldPath = `custom_attributes.${config.attr_name}`;
                            formik.setFieldTouched(fieldPath, true);
                            setTimeout(() => {
                              formik.validateField(fieldPath);
                            }, 0);
                          }}
                          onBlur={() => {
                            const fieldPath = `custom_attributes.${config.attr_name}`;
                            formik.setFieldTouched(fieldPath, true);
                            formik.validateField(fieldPath);
                          }}
                          error={fieldTouched && !!fieldError}
                          helperText={fieldTouched && fieldError ? String(fieldError) : config.description}
                        />
                      </Grid>
                    );
                  })}
                </Grid>
              </>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={loading || loadingClients}
            startIcon={loading && <CircularProgress size={20} />}
          >
            {clientProject ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default ClientProjectForm;

