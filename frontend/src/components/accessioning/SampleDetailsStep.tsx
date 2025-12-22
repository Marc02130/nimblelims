import React from 'react';
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
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { useField } from 'formik';

interface SampleDetailsStepProps {
  values: any;
  setFieldValue: (field: string, value: any) => void;
  lookupData: {
    sampleTypes: any[];
    statuses: any[];
    matrices: any[];
    qcTypes: any[];
    projects: any[];
    containerTypes: any[];
    units: any[];
  };
}

const SampleDetailsStep: React.FC<SampleDetailsStepProps> = ({
  values,
  setFieldValue,
  lookupData,
}) => {
  const [nameField, nameMeta] = useField('name');
  const [nameVerificationField, nameVerificationMeta] = useField('name_verification');
  const [sampleTypeField, sampleTypeMeta] = useField('sample_type');
  const [sampleTypeVerificationField, sampleTypeVerificationMeta] = useField('sample_type_verification');
  const [containerTypeField, containerTypeMeta] = useField('container_type_id');
  const [containerNameField, containerNameMeta] = useField('container_name');

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
          Sample Information
        </Typography>
        
        <Grid container spacing={3}>
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
          
          <Grid size={{ xs: 12, sm: 6 }}>
            <FormControl fullWidth>
              <InputLabel>QC Type</InputLabel>
              <Select
                value={values.qc_type}
                onChange={(e) => setFieldValue('qc_type', e.target.value)}
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

        <Divider sx={{ my: 3 }} />

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
      </Box>
    </LocalizationProvider>
  );
};

export default SampleDetailsStep;
