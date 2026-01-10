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
  Autocomplete,
  Tooltip,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
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

interface ClientProject {
  id: string;
  name: string;
  client_id: string;
}

interface Status {
  id: string;
  name: string;
  entry_value: string;
}

interface ProjectFormProps {
  open: boolean;
  project?: {
    id: string;
    name: string;
    description?: string;
    start_date: string;
    client_id: string;
    client_project_id?: string;
    status: string;
    custom_attributes?: Record<string, any>;
  } | null;
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
    start_date: string;
    client_id: string;
    client_project_id?: string;
    status: string;
    custom_attributes?: Record<string, any>;
  }) => Promise<void>;
  existingNames?: string[];
  clients: Client[];
  statuses: Status[];
}

const buildCustomAttributesValidation = (configs: CustomAttributeConfig[]): Record<string, any> => {
  const customAttrsSchema: Record<string, any> = {};
  
  configs.forEach((config) => {
    if (!config.active) return;
    
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
            if (originalValue === '' || originalValue === null || originalValue === undefined) {
              return null;
            }
            const parsed = typeof originalValue === 'string' ? parseFloat(originalValue) : originalValue;
            return isNaN(parsed) ? null : parsed;
          })
          .test('is-number', 'Must be a valid number', (value) => {
            if (value === null || value === undefined) return true;
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
        fieldSchema = yup.mixed()
          .nullable()
          .transform((value, originalValue) => {
            if (value instanceof Date) return value;
            if (typeof value === 'string' && value) {
              const date = new Date(value);
              return isNaN(date.getTime()) ? null : date;
            }
            return null;
          })
          .test('is-date', 'Must be a valid date', (value) => {
            if (value === null || value === undefined) return true;
            return value instanceof Date && !isNaN(value.getTime());
          });
        if (config.validation_rules?.min_date) {
          fieldSchema = fieldSchema.test(
            'min-date',
            `Date must be on or after ${config.validation_rules.min_date}`,
            function(value: any) {
              if (!value) return true;
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
              if (!value) return true;
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
  
  return {
    custom_attributes: yup.object().shape(customAttrsSchema).noUnknown(true).nullable()
  };
};

const ProjectForm: React.FC<ProjectFormProps> = ({
  open,
  project,
  onClose,
  onSubmit,
  existingNames = [],
  clients,
  statuses,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [clientProjects, setClientProjects] = useState<ClientProject[]>([]);
  const [loadingClientProjects, setLoadingClientProjects] = useState(false);
  const [customAttributeConfigs, setCustomAttributeConfigs] = useState<CustomAttributeConfig[]>([]);
  const [configsError, setConfigsError] = useState<string | null>(null);
  const [loadingConfigs, setLoadingConfigs] = useState(false);

  const loadCustomAttributeConfigs = async () => {
    try {
      setLoadingConfigs(true);
      setConfigsError(null);
      const response = await apiService.getCustomAttributeConfigs({
        entity_type: 'projects',
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

  const loadClientProjects = async (clientId: string) => {
    if (!clientId) {
      setClientProjects([]);
      return;
    }
    try {
      setLoadingClientProjects(true);
      const response = await apiService.getClientProjects({ client_id: clientId });
      // Handle both paginated and non-paginated responses
      const projects = response.client_projects || response || [];
      setClientProjects(projects);
    } catch (err: any) {
      console.error('Failed to load client projects:', err);
      setClientProjects([]);
    } finally {
      setLoadingClientProjects(false);
    }
  };

  const formik = useFormik({
    initialValues: {
      name: project?.name || '',
      description: project?.description || '',
      start_date: project?.start_date ? new Date(project.start_date) : new Date(),
      client_id: project?.client_id || '',
      client_project_id: project?.client_project_id || '',
      status: project?.status || '',
      custom_attributes: project?.custom_attributes || {},
    },
    validationSchema: useMemo(() => yup.object({
      name: yup
        .string()
        .required('Name is required')
        .min(1, 'Name must be at least 1 character')
        .max(255, 'Name must be at most 255 characters')
        .test('unique', 'Name already exists', (value) => {
          if (!value) return true;
          if (project && value === project.name) return true;
          return !existingNames.includes(value);
        }),
      description: yup.string().max(1000, 'Description must be at most 1000 characters'),
      start_date: yup.date().required('Start date is required'),
      client_id: yup.string().required('Client is required'),
      client_project_id: yup.string().nullable(),
      status: yup.string().required('Status is required'),
      ...buildCustomAttributesValidation(customAttributeConfigs),
    }), [project, existingNames, customAttributeConfigs]),
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
          start_date: values.start_date instanceof Date 
            ? values.start_date.toISOString() 
            : values.start_date,
          client_id: values.client_id,
          client_project_id: values.client_project_id || undefined,
          status: values.status,
          custom_attributes: Object.keys(values.custom_attributes || {}).length > 0 
            ? values.custom_attributes 
            : undefined,
        });
        formik.resetForm();
        onClose();
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to save project');
      } finally {
        setLoading(false);
      }
    },
  });

  useEffect(() => {
    if (open) {
      loadCustomAttributeConfigs();
      if (formik.values.client_id) {
        loadClientProjects(formik.values.client_id);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (formik.values.client_id && formik.values.client_id !== project?.client_id) {
      loadClientProjects(formik.values.client_id);
      // Reset client_project_id when client changes
      formik.setFieldValue('client_project_id', '');
    }
  }, [formik.values.client_id, project?.client_id]);

  const handleClose = () => {
    if (!loading) {
      formik.resetForm();
      setError(null);
      onClose();
    }
  };

  const selectedClient = clients.find((c) => c.id === formik.values.client_id);
  const selectedClientProject = clientProjects.find((cp) => cp.id === formik.values.client_project_id);

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
      <form onSubmit={formik.handleSubmit}>
        <DialogTitle>
          {project ? 'Edit Project' : 'Create Project'}
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

            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DatePicker
                label="Start Date"
                value={formik.values.start_date}
                onChange={(date) => {
                  formik.setFieldValue('start_date', date || new Date());
                  formik.setFieldTouched('start_date', true);
                }}
                slotProps={{
                  textField: {
                    fullWidth: true,
                    required: true,
                    error: formik.touched.start_date && Boolean(formik.errors.start_date),
                    helperText: formik.touched.start_date && formik.errors.start_date 
                      ? String(formik.errors.start_date) 
                      : undefined,
                    disabled: loading,
                  },
                }}
              />
            </LocalizationProvider>

            <FormControl
              fullWidth
              required
              error={formik.touched.client_id && Boolean(formik.errors.client_id)}
              disabled={loading}
            >
              <InputLabel>Client</InputLabel>
              <Select
                name="client_id"
                value={formik.values.client_id}
                onChange={formik.handleChange}
                onBlur={formik.handleBlur}
                label="Client"
              >
                {clients.map((client) => (
                  <MenuItem key={client.id} value={client.id}>
                    {client.name}
                  </MenuItem>
                ))}
              </Select>
              {formik.touched.client_id && formik.errors.client_id && (
                <Box sx={{ color: 'error.main', fontSize: '0.75rem', mt: 0.5, ml: 1.75 }}>
                  {formik.errors.client_id}
                </Box>
              )}
            </FormControl>

            <Tooltip title="Client Projects: Groupings for tracking multiple projects under client initiatives (US-25)">
              <FormControl
                fullWidth
                error={formik.touched.client_project_id && Boolean(formik.errors.client_project_id)}
                disabled={loading || loadingClientProjects || !formik.values.client_id}
              >
                <Autocomplete
                  options={clientProjects}
                  getOptionLabel={(option) => option.name}
                  value={selectedClientProject || null}
                  onChange={(_, newValue) => {
                    formik.setFieldValue('client_project_id', newValue?.id || '');
                    formik.setFieldTouched('client_project_id', true);
                  }}
                  onBlur={() => formik.setFieldTouched('client_project_id', true)}
                  loading={loadingClientProjects}
                  disabled={!formik.values.client_id}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Client Project (Optional)"
                      helperText={formik.touched.client_project_id && formik.errors.client_project_id}
                      error={formik.touched.client_project_id && Boolean(formik.errors.client_project_id)}
                    />
                  )}
                />
              </FormControl>
            </Tooltip>

            <FormControl
              fullWidth
              required
              error={formik.touched.status && Boolean(formik.errors.status)}
              disabled={loading}
            >
              <InputLabel>Status</InputLabel>
              <Select
                name="status"
                value={formik.values.status}
                onChange={formik.handleChange}
                onBlur={formik.handleBlur}
                label="Status"
              >
                {statuses.map((status) => (
                  <MenuItem key={status.id} value={status.id}>
                    {status.name}
                  </MenuItem>
                ))}
              </Select>
              {formik.touched.status && formik.errors.status && (
                <Box sx={{ color: 'error.main', fontSize: '0.75rem', mt: 0.5, ml: 1.75 }}>
                  {formik.errors.status}
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
            disabled={loading || loadingConfigs}
            startIcon={loading && <CircularProgress size={20} />}
          >
            {project ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default ProjectForm;
