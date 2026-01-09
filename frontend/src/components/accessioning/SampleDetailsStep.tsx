import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Typography,
  Divider,
  Alert,
  CircularProgress,
  Tooltip,
  IconButton,
  Paper,
  Autocomplete,
} from '@mui/material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { useField } from 'formik';
import BulkUniquesTable from './BulkUniquesTable';
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

interface SampleDetailsStepProps {
  values: any;
  setFieldValue: (field: string, value: any) => void;
  setFieldTouched?: (field: string, touched: boolean) => void;
  validateField?: (field: string) => void;
  lookupData: {
    sampleTypes: any[];
    statuses: any[];
    matrices: any[];
    qcTypes: any[];
    projects: any[];
    clients: any[];
    clientProjects: any[];
    containerTypes: any[];
    units: any[];
  };
  bulkMode?: boolean;
  errors?: any;
  touched?: any;
  customAttributeConfigs?: CustomAttributeConfig[];
}

const SampleDetailsStep: React.FC<SampleDetailsStepProps> = ({
  values,
  setFieldValue,
  setFieldTouched,
  validateField,
  lookupData,
  bulkMode = false,
  errors,
  touched,
  customAttributeConfigs: propsCustomAttributeConfigs,
}) => {
  const { user } = useUser();
  const [nameField, nameMeta] = useField('name');
  const [nameVerificationField, nameVerificationMeta] = useField('name_verification');
  const [sampleTypeField, sampleTypeMeta] = useField('sample_type');
  const [sampleTypeVerificationField, sampleTypeVerificationMeta] = useField('sample_type_verification');
  const [containerTypeField, containerTypeMeta] = useField('container_type_id');
  const [containerNameField, containerNameMeta] = useField('container_name');
  const [customAttributeConfigs, setCustomAttributeConfigs] = useState<CustomAttributeConfig[]>([]);
  const [loadingConfigs, setLoadingConfigs] = useState(false);
  const [configsError, setConfigsError] = useState<string | null>(null);
  const [nameTemplate, setNameTemplate] = useState<any>(null);
  const [loadingTemplate, setLoadingTemplate] = useState(false);
  const [autoGenerateNameField] = useField('auto_generate_name');
  const [clientProjects, setClientProjects] = useState<any[]>([]);
  const [loadingClientProjects, setLoadingClientProjects] = useState(false);
  const [projectPreview, setProjectPreview] = useState<string | null>(null);
  const [loadingProjectPreview, setLoadingProjectPreview] = useState(false);

  // Pre-select client_id from user context if available
  useEffect(() => {
    if (user?.client_id && !values.client_id) {
      setFieldValue('client_id', user.client_id);
    }
  }, [user?.client_id, values.client_id, setFieldValue]);

  useEffect(() => {
    if (propsCustomAttributeConfigs) {
      setCustomAttributeConfigs(propsCustomAttributeConfigs);
    } else {
      loadCustomAttributeConfigs();
    }
  }, [propsCustomAttributeConfigs]);

  useEffect(() => {
    if (!bulkMode && autoGenerateNameField.value) {
      loadNameTemplate();
    }
  }, [bulkMode, autoGenerateNameField.value]);

  // Load client projects when client_id changes
  useEffect(() => {
    if (values.client_id) {
      loadClientProjects(values.client_id);
      // Clear client_project_id when client changes
      if (values.client_project_id) {
        const currentClientProject = clientProjects.find(cp => cp.id === values.client_project_id);
        if (!currentClientProject || currentClientProject.client_id !== values.client_id) {
          setFieldValue('client_project_id', '');
        }
      }
    } else {
      setClientProjects([]);
      setFieldValue('client_project_id', '');
    }
  }, [values.client_id]);

  // Load project name preview when client_id or received_date changes
  useEffect(() => {
    if (values.client_id && values.received_date) {
      loadProjectPreview();
    } else {
      setProjectPreview(null);
    }
  }, [values.client_id, values.received_date]);

  const loadClientProjects = async (clientId: string) => {
    try {
      setLoadingClientProjects(true);
      const response = await apiService.getClientProjects({ client_id: clientId });
      const projects = response.client_projects || response || [];
      setClientProjects(Array.isArray(projects) ? projects : []);
    } catch (err: any) {
      console.error('Error loading client projects:', err);
      setClientProjects([]);
    } finally {
      setLoadingClientProjects(false);
    }
  };

  const loadProjectPreview = async () => {
    try {
      setLoadingProjectPreview(true);
      // Format date as YYYY-MM-DD if it's a Date object
      let dateStr = values.received_date;
      if (dateStr instanceof Date) {
        dateStr = dateStr.toISOString().split('T')[0];
      } else if (dateStr && typeof dateStr === 'string') {
        // Ensure it's in YYYY-MM-DD format
        const date = new Date(dateStr);
        if (!isNaN(date.getTime())) {
          dateStr = date.toISOString().split('T')[0];
        }
      }
      // Fetch project name preview from API
      const response = await apiService.getGeneratedNamePreview('project', values.client_id, dateStr);
      setProjectPreview(response || null);
    } catch (err: any) {
      console.error('Error loading project preview:', err);
      setProjectPreview(null);
    } finally {
      setLoadingProjectPreview(false);
    }
  };

  const loadNameTemplate = async () => {
    try {
      setLoadingTemplate(true);
      const response = await apiService.getNameTemplates({
        entity_type: 'sample',
        active: true,
      });
      if (response.templates && response.templates.length > 0) {
        setNameTemplate(response.templates[0]);
      } else {
        setNameTemplate(null);
      }
    } catch (err: any) {
      console.error('Error loading name template:', err);
      setNameTemplate(null);
    } finally {
      setLoadingTemplate(false);
    }
  };

  const generateNamePreview = useMemo(() => {
    if (!nameTemplate || !autoGenerateNameField.value) return null;
    
    let preview = nameTemplate.template;
    // Use received_date if available, otherwise use current date
    const dateToUse = values.received_date ? new Date(values.received_date) : new Date();
    
    // Replace date placeholders
    preview = preview.replace(/{YYYY}/g, String(dateToUse.getFullYear()));
    preview = preview.replace(/{MM}/g, String(dateToUse.getMonth() + 1).padStart(2, '0'));
    preview = preview.replace(/{DD}/g, String(dateToUse.getDate()).padStart(2, '0'));
    preview = preview.replace(/{YYYYMMDD}/g, dateToUse.toISOString().split('T')[0].replace(/-/g, ''));
    
    // Replace CLIENT placeholder if client is selected
    if (values.client_id && lookupData.clients) {
      const client = lookupData.clients.find((c: any) => c.id === values.client_id);
      if (client) {
        const clientName = client.name || 'UNKNOWN';
        const clientCode = clientName.toUpperCase().replace(/[^A-Z0-9]/g, '').substring(0, 10);
        preview = preview.replace(/{CLIENT}/g, clientCode);
      } else {
        preview = preview.replace(/{CLIENT}/g, 'UNKNOWN');
      }
    } else {
      preview = preview.replace(/{CLIENT}/g, 'UNKNOWN');
    }
    
    // Replace SEQ with example
    preview = preview.replace(/{SEQ}/g, '001');
    
    return preview;
  }, [nameTemplate, autoGenerateNameField.value, values.client_id, values.received_date, lookupData.clients]);

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

  const handleCustomAttributeChange = (attrName: string, value: any) => {
    const currentAttrs = values.custom_attributes || {};
    const newAttrs = {
      ...currentAttrs,
      [attrName]: value,
    };
    // Remove the key if value is null/undefined/empty
    if (value === null || value === undefined || value === '') {
      delete newAttrs[attrName];
    }
    setFieldValue('custom_attributes', newAttrs);
    // Mark field as touched to trigger validation
    if (setFieldTouched) {
      const fieldPath = `custom_attributes.${attrName}`;
      setFieldTouched(fieldPath, true);
      // Trigger validation immediately
      if (validateField) {
        setTimeout(() => {
          validateField(fieldPath);
        }, 0);
      }
    }
  };

  const handleCustomAttributeBlur = (attrName: string) => {
    if (setFieldTouched && validateField) {
      const fieldPath = `custom_attributes.${attrName}`;
      setFieldTouched(fieldPath, true);
      validateField(fieldPath);
    }
  };

  const handleDoubleEntryToggle = (event: React.ChangeEvent<HTMLInputElement>) => {
    const enabled = event.target.checked;
    setFieldValue('double_entry_enabled', enabled);
    if (!enabled) {
      setFieldValue('name_verification', '');
      setFieldValue('sample_type_verification', '');
    }
  };

  const handleClientChange = (clientId: string) => {
    setFieldValue('client_id', clientId);
    setFieldValue('client_project_id', ''); // Clear client project when client changes
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box>
        <Typography variant="h6" gutterBottom>
          {bulkMode ? 'Common Sample Information' : 'Sample Information'}
        </Typography>
        {bulkMode && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            These fields will be applied to all samples. Unique fields per sample are configured in the table below.
          </Typography>
        )}
        
        <Grid container spacing={3}>
          {!bulkMode && (
            <Grid size={{ xs: 12 }}>
              <Box sx={{ mb: 2 }}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={autoGenerateNameField.value}
                      onChange={(e) => {
                        setFieldValue('auto_generate_name', e.target.checked);
                        if (!e.target.checked) {
                          setFieldValue('name', '');
                        }
                      }}
                    />
                  }
                  label="Auto-Generate Name"
                />
                {autoGenerateNameField.value && nameTemplate && (
                  <Box sx={{ mt: 1 }}>
                    <Paper sx={{ p: 1.5, bgcolor: 'info.light', border: '1px solid', borderColor: 'info.main' }}>
                      <Typography variant="caption" component="div">
                        <strong>Preview:</strong> {generateNamePreview || 'Loading...'}
                      </Typography>
                      {loadingTemplate && (
                        <CircularProgress size={16} sx={{ ml: 1 }} />
                      )}
                    </Paper>
                  </Box>
                )}
              </Box>
            </Grid>
          )}
          {!bulkMode && (
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                {...nameField}
                label="Sample Name"
                fullWidth
                required={!autoGenerateNameField.value}
                disabled={autoGenerateNameField.value}
                error={nameMeta.touched && !!nameMeta.error}
                helperText={
                  autoGenerateNameField.value
                    ? 'Name will be auto-generated based on template'
                    : nameMeta.touched && nameMeta.error
                    ? nameMeta.error
                    : 'Enter a custom sample name'
                }
              />
            </Grid>
          )}
          
          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              name="description"
              label="Description"
              fullWidth
              value={values.description}
              onChange={(e) => setFieldValue('description', e.target.value)}
            />
          </Grid>
          
          <Grid size={{ xs: 12, sm: 6 }}>
            <DatePicker
              label="Due Date"
              value={values.due_date ? new Date(values.due_date) : null}
              onChange={(date) => setFieldValue('due_date', date?.toISOString().split('T')[0] || '')}
              slotProps={{
                textField: {
                  fullWidth: true,
                  required: true,
                },
              }}
            />
          </Grid>
          
          <Grid size={{ xs: 12, sm: 6 }}>
            <DatePicker
              label="Received Date"
              value={values.received_date ? new Date(values.received_date) : null}
              onChange={(date) => setFieldValue('received_date', date?.toISOString().split('T')[0] || '')}
              slotProps={{
                textField: {
                  fullWidth: true,
                  required: true,
                },
              }}
            />
          </Grid>
          
          <Grid size={{ xs: 12, sm: 6 }}>
            <FormControl fullWidth required>
              <InputLabel>Sample Type</InputLabel>
              <Select
                value={values.sample_type}
                onChange={(e) => setFieldValue('sample_type', e.target.value)}
                error={sampleTypeMeta.touched && !!sampleTypeMeta.error}
              >
                {lookupData.sampleTypes.map((type) => (
                  <MenuItem key={type.id} value={type.id}>
                    {type.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid size={{ xs: 12, sm: 6 }}>
            <FormControl fullWidth required>
              <InputLabel>Status</InputLabel>
              <Select
                value={values.status}
                onChange={(e) => setFieldValue('status', e.target.value)}
              >
                {lookupData.statuses.map((status) => (
                  <MenuItem key={status.id} value={status.id}>
                    {status.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          <Grid size={{ xs: 12, sm: 6 }}>
            <FormControl fullWidth required>
              <InputLabel>Matrix</InputLabel>
              <Select
                value={values.matrix}
                onChange={(e) => setFieldValue('matrix', e.target.value)}
              >
                {lookupData.matrices.map((matrix) => (
                  <MenuItem key={matrix.id} value={matrix.id}>
                    {matrix.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
          {!bulkMode && (
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                name="temperature"
                label="Temperature (°C)"
                type="number"
                fullWidth
                required
                value={values.temperature}
                onChange={(e) => setFieldValue('temperature', parseFloat(e.target.value) || 0)}
              />
            </Grid>
          )}
          
          <Grid size={{ xs: 12, sm: 6 }}>
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
            <FormControl fullWidth>
                <InputLabel id="qc-type-label">QC Type</InputLabel>
              <Select
                value={values.qc_type || ''}
                onChange={(e) => setFieldValue('qc_type', e.target.value)}
                labelId="qc-type-label"
                label="QC Type"
              >
                <MenuItem value="">None</MenuItem>
                {lookupData.qcTypes.map((qcType) => (
                  <MenuItem key={qcType.id} value={qcType.id}>
                    {qcType.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
              <Tooltip
                title="QC: Blank—US-4. Quality control samples are used to ensure test accuracy. Blank samples contain no analyte and are used to verify the absence of contamination."
                arrow
                placement="top"
              >
                <IconButton
                  size="small"
                  aria-label="QC Type help"
                  sx={{ mt: 1.5, p: 0.5 }}
                >
                  <HelpOutlineIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          </Grid>
          
          {/* Client Selection - Required */}
          <Grid size={{ xs: 12, sm: 6 }}>
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
              <FormControl fullWidth required error={touched?.client_id && !!errors?.client_id}>
              <InputLabel>Client</InputLabel>
              <Select
                value={values.client_id || ''}
                  onChange={(e) => handleClientChange(e.target.value)}
                label="Client"
                  disabled={user?.role === 'Client' && !!user?.client_id} // Disable only for Client role users with a pre-selected client_id
              >
                {lookupData.clients && lookupData.clients.length > 0 ? (
                  lookupData.clients.map((client: any) => (
                    <MenuItem key={client.id} value={client.id}>
                      {client.name}
                    </MenuItem>
                  ))
                ) : (
                  <MenuItem disabled>No clients available</MenuItem>
                )}
              </Select>
            </FormControl>
              <Tooltip
                title="Select a client to create a project for. The project will be auto-created during accessioning."
                arrow
                placement="top"
              >
                <IconButton
                  size="small"
                  aria-label="Client help"
                  sx={{ mt: 1.5, p: 0.5 }}
                >
                  <HelpOutlineIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          </Grid>
          
          {/* Client Project Selection - Optional, cascades from client */}
          <Grid size={{ xs: 12, sm: 6 }}>
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
            <FormControl fullWidth>
                <InputLabel>Client Project (Optional)</InputLabel>
              <Select
                value={values.client_project_id || ''}
                onChange={(e) => setFieldValue('client_project_id', e.target.value || undefined)}
                  label="Client Project (Optional)"
                  disabled={!values.client_id || loadingClientProjects}
              >
                <MenuItem value="">None</MenuItem>
                  {loadingClientProjects ? (
                    <MenuItem disabled>Loading...</MenuItem>
                  ) : clientProjects.length > 0 ? (
                    clientProjects.map((clientProject: any) => (
                      <MenuItem key={clientProject.id} value={clientProject.id}>
                        {clientProject.name}
                      </MenuItem>
                    ))
                ) : (
                  <MenuItem disabled>
                    {!values.client_id ? 'Select a client first' : 'No client projects available'}
                  </MenuItem>
                )}
              </Select>
            </FormControl>
              <Tooltip
                title="Optionally select a client project to group related samples. This filters based on the selected client."
                arrow
                placement="top"
              >
                <IconButton
                  size="small"
                  aria-label="Client Project help"
                  sx={{ mt: 1.5, p: 0.5 }}
                >
                  <HelpOutlineIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          </Grid>

          {/* Project Auto-Creation Preview */}
          {values.client_id && (
            <Grid size={{ xs: 12 }}>
              <Paper sx={{ p: 2, bgcolor: 'info.light', border: '1px solid', borderColor: 'info.main' }}>
                <Typography variant="body2" component="div">
                  <strong>Project:</strong> Will be auto-created
                  {projectPreview && (
                    <>
                      {' '}
                      <Typography component="span" variant="body2" sx={{ fontStyle: 'italic' }}>
                        (Preview: {projectPreview})
                      </Typography>
                    </>
                  )}
                  {loadingProjectPreview && <CircularProgress size={14} sx={{ ml: 1 }} />}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                  A new project will be automatically created for this client during accessioning.
                </Typography>
              </Paper>
            </Grid>
          )}
          
          <Grid size={12}>
            <TextField
              name="anomalies"
              label="Anomalies/Notes"
              multiline
              rows={3}
              fullWidth
              value={values.anomalies}
              onChange={(e) => setFieldValue('anomalies', e.target.value)}
            />
          </Grid>
        </Grid>

        {/* Custom Fields Section */}
        {customAttributeConfigs.length > 0 && (
          <>
            <Divider sx={{ my: 3 }} />
            <Typography variant="h6" gutterBottom>
              Custom Fields
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Additional custom attributes for this sample.
            </Typography>
            {configsError && (
              <Alert severity="warning" sx={{ mb: 2 }} onClose={() => setConfigsError(null)}>
                {configsError}
              </Alert>
            )}
            {loadingConfigs ? (
              <Box display="flex" justifyContent="center" p={2}>
                <CircularProgress size={24} />
              </Box>
            ) : (
              <Grid container spacing={3}>
                {customAttributeConfigs.map((config) => {
                  const fieldPath = `custom_attributes.${config.attr_name}`;
                  const fieldValue = values.custom_attributes?.[config.attr_name];
                  const fieldError = errors?.custom_attributes?.[config.attr_name];
                  const fieldTouched = touched?.custom_attributes?.[config.attr_name];

                  return (
                    <Grid key={config.id} size={{ xs: 12, sm: 6 }}>
                      <CustomAttributeField
                        config={config}
                        value={fieldValue}
                        onChange={(value) => handleCustomAttributeChange(config.attr_name, value)}
                        onBlur={() => handleCustomAttributeBlur(config.attr_name)}
                        error={fieldTouched && !!fieldError}
                        helperText={fieldTouched && fieldError ? String(fieldError) : undefined}
                      />
                    </Grid>
                  );
                })}
              </Grid>
            )}
          </>
        )}

        <Divider sx={{ my: 3 }} />

        {!bulkMode && (
          <>
            <Typography variant="h6" gutterBottom>
              Container Information
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Specify the container in which this sample is received. A new container instance will be created.
            </Typography>

            <Grid container spacing={3}>
          <Grid size={{ xs: 12, sm: 6 }}>
            <FormControl fullWidth required error={containerTypeMeta.touched && !!containerTypeMeta.error}>
              <InputLabel>Container Type</InputLabel>
              <Select
                {...containerTypeField}
                value={containerTypeField.value || ''}
                onChange={(e) => {
                  containerTypeField.onChange(e);
                  setFieldValue('container_type_id', e.target.value);
                }}
              >
                {lookupData.containerTypes.map((type) => (
                  <MenuItem key={type.id} value={type.id}>
                    {type.name} {type.dimensions ? `(${type.dimensions})` : ''}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              {...containerNameField}
              label="Container Name/Barcode"
              fullWidth
              required
              error={containerNameMeta.touched && !!containerNameMeta.error}
              helperText={containerNameMeta.touched && containerNameMeta.error ? containerNameMeta.error : 'Unique identifier for this container instance'}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              name="container_row"
              label="Row"
              type="number"
              fullWidth
              value={values.container_row || 1}
              onChange={(e) => setFieldValue('container_row', parseInt(e.target.value) || 1)}
              inputProps={{ min: 1 }}
              helperText="Row position for plate-based containers (default: 1)"
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              name="container_column"
              label="Column"
              type="number"
              fullWidth
              value={values.container_column || 1}
              onChange={(e) => setFieldValue('container_column', parseInt(e.target.value) || 1)}
              inputProps={{ min: 1 }}
              helperText="Column position for plate-based containers (default: 1)"
            />
          </Grid>

        </Grid>
          </>
        )}

        {bulkMode && (
          <>
            <Typography variant="h6" gutterBottom>
              Container Type (Common)
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Select the container type that will be used for all samples in this batch.
            </Typography>
            <Grid container spacing={3}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth required error={containerTypeMeta.touched && !!containerTypeMeta.error}>
                  <InputLabel>Container Type</InputLabel>
                  <Select
                    {...containerTypeField}
                    value={containerTypeField.value || ''}
                    onChange={(e) => {
                      containerTypeField.onChange(e);
                      setFieldValue('container_type_id', e.target.value);
                    }}
                  >
                    {lookupData.containerTypes.map((type) => (
                      <MenuItem key={type.id} value={type.id}>
                        {type.name} {type.dimensions ? `(${type.dimensions})` : ''}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </>
        )}

        {bulkMode && (
          <>
            <Divider sx={{ my: 3 }} />
            <Typography variant="h6" gutterBottom>
              Unique Fields per Sample
            </Typography>
            <BulkUniquesTable
              uniques={values.bulk_uniques || []}
              onAdd={() => {
                const newId = String((values.bulk_uniques?.length || 0) + 1);
                setFieldValue('bulk_uniques', [
                  ...(values.bulk_uniques || []),
                  { id: newId, container_name: '', custom_attributes: {} }
                ]);
              }}
              onRemove={(id) => {
                setFieldValue('bulk_uniques', 
                  (values.bulk_uniques || []).filter((u: any) => u.id !== id)
                );
              }}
              onUpdate={(id, field, value) => {
                if (field.startsWith('custom_attributes.')) {
                  // Handle custom attributes nested update
                  const attrName = field.replace('custom_attributes.', '');
                  setFieldValue('bulk_uniques',
                    (values.bulk_uniques || []).map((u: any) => {
                      if (u.id === id) {
                        const customAttrs = u.custom_attributes || {};
                        return {
                          ...u,
                          custom_attributes: {
                            ...customAttrs,
                            [attrName]: value,
                          },
                        };
                      }
                      return u;
                    })
                  );
                } else {
                  setFieldValue('bulk_uniques',
                    (values.bulk_uniques || []).map((u: any) =>
                      u.id === id ? { ...u, [field]: value } : u
                    )
                  );
                }
              }}
              autoNamePrefix={values.auto_name_prefix}
              autoNameStart={values.auto_name_start}
              onAutoNameChange={(prefix, start) => {
                setFieldValue('auto_name_prefix', prefix || '');
                setFieldValue('auto_name_start', start || 1);
              }}
              customAttributeConfigs={customAttributeConfigs}
            />
          </>
        )}

        {!bulkMode && (
          <>
            <Divider sx={{ my: 3 }} />

            <Box>
              <FormControlLabel
                control={
                  <Switch
                    checked={values.double_entry_enabled}
                    onChange={handleDoubleEntryToggle}
                  />
                }
                label="Enable Double Entry Validation"
              />
              
              {values.double_entry_enabled && (
                <Grid container spacing={3} sx={{ mt: 2 }}>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <TextField
                      {...nameVerificationField}
                      label="Verify Sample Name"
                      fullWidth
                      required
                      error={nameVerificationMeta.touched && !!nameVerificationMeta.error}
                      helperText={nameVerificationMeta.touched && nameVerificationMeta.error}
                    />
                  </Grid>
                  
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <FormControl fullWidth required>
                      <InputLabel>Verify Sample Type</InputLabel>
                      <Select
                        {...sampleTypeVerificationField}
                        error={sampleTypeVerificationMeta.touched && !!sampleTypeVerificationMeta.error}
                      >
                        {lookupData.sampleTypes.map((type) => (
                          <MenuItem key={type.id} value={type.id}>
                            {type.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
              )}
            </Box>
          </>
        )}
      </Box>
    </LocalizationProvider>
  );
};

export default SampleDetailsStep;
