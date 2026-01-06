import React, { useState, useEffect } from 'react';
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
} from '@mui/material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { useField } from 'formik';
import BulkUniquesTable from './BulkUniquesTable';
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
  const [nameField, nameMeta] = useField('name');
  const [nameVerificationField, nameVerificationMeta] = useField('name_verification');
  const [sampleTypeField, sampleTypeMeta] = useField('sample_type');
  const [sampleTypeVerificationField, sampleTypeVerificationMeta] = useField('sample_type_verification');
  const [containerTypeField, containerTypeMeta] = useField('container_type_id');
  const [containerNameField, containerNameMeta] = useField('container_name');
  const [customAttributeConfigs, setCustomAttributeConfigs] = useState<CustomAttributeConfig[]>([]);
  const [loadingConfigs, setLoadingConfigs] = useState(false);
  const [configsError, setConfigsError] = useState<string | null>(null);

  useEffect(() => {
    if (propsCustomAttributeConfigs) {
      setCustomAttributeConfigs(propsCustomAttributeConfigs);
    } else {
      loadCustomAttributeConfigs();
    }
  }, [propsCustomAttributeConfigs]);

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
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                {...nameField}
                label="Sample Name"
                fullWidth
                required
                error={nameMeta.touched && !!nameMeta.error}
                helperText={nameMeta.touched && nameMeta.error}
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
            <FormControl fullWidth>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                <InputLabel id="qc-type-label">QC Type</InputLabel>
                <Tooltip
                  title="QC: Blank—US-4. Quality control samples are used to ensure test accuracy. Blank samples contain no analyte and are used to verify the absence of contamination."
                  arrow
                  placement="top"
                >
                  <IconButton
                    size="small"
                    aria-label="QC Type help"
                    sx={{ p: 0.5 }}
                  >
                    <HelpOutlineIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
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
          </Grid>
          
          <Grid size={{ xs: 12, sm: 6 }}>
            <FormControl fullWidth required>
              <InputLabel>Project</InputLabel>
              <Select
                value={values.project_id}
                onChange={(e) => setFieldValue('project_id', e.target.value)}
              >
                {lookupData.projects.map((project) => (
                  <MenuItem key={project.id} value={project.id}>
                    {project.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          
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

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              name="container_concentration"
              label="Concentration"
              type="number"
              fullWidth
              value={values.container_concentration || ''}
              onChange={(e) => setFieldValue('container_concentration', e.target.value ? parseFloat(e.target.value) : null)}
              inputProps={{ min: 0, step: 0.01 }}
              helperText="Optional concentration value"
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <FormControl fullWidth>
              <InputLabel>Concentration Units</InputLabel>
              <Select
                value={values.container_concentration_units || ''}
                onChange={(e) => setFieldValue('container_concentration_units', e.target.value)}
              >
                <MenuItem value="">None</MenuItem>
                {lookupData.units
                  .filter((unit) => {
                    const unitType = unit.type?.name || unit.type;
                    return unitType === 'concentration';
                  })
                  .map((unit) => (
                    <MenuItem key={unit.id} value={unit.id}>
                      {unit.name}
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <TextField
              name="container_amount"
              label="Amount"
              type="number"
              fullWidth
              value={values.container_amount || ''}
              onChange={(e) => setFieldValue('container_amount', e.target.value ? parseFloat(e.target.value) : null)}
              inputProps={{ min: 0, step: 0.01 }}
              helperText="Optional amount value"
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6 }}>
            <FormControl fullWidth>
              <InputLabel>Amount Units</InputLabel>
              <Select
                value={values.container_amount_units || ''}
                onChange={(e) => setFieldValue('container_amount_units', e.target.value)}
              >
                <MenuItem value="">None</MenuItem>
                {lookupData.units
                  .filter((unit) => {
                    const unitType = unit.type?.name || unit.type;
                    return unitType === 'mass' || unitType === 'volume';
                  })
                  .map((unit) => (
                    <MenuItem key={unit.id} value={unit.id}>
                      {unit.name}
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
