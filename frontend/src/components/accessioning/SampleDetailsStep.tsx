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
