import React, { useState } from 'react';
import {
  Box,
  Grid,
  Typography,
  Card,
  CardContent,
  Button,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Divider,
} from '@mui/material';
import {
  Edit,
  Delete,
  Add,
  Science,
  Storage,
} from '@mui/icons-material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { apiService } from '../../services/apiService';

interface ContainerDetailsProps {
  container: any;
  lookupData: {
    units: any[];
    samples: any[];
  };
  onEdit: () => void;
  onClose: () => void;
}

const ContainerDetails: React.FC<ContainerDetailsProps> = ({
  container,
  lookupData,
  onEdit,
  onClose,
}) => {
  const [showAddContent, setShowAddContent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleAddContent = async (contentData: any) => {
    setLoading(true);
    setError(null);
    
    try {
      await apiService.createContent({
        container_id: container.id,
        ...contentData,
      });
      
      // Refresh container data
      const updatedContainer = await apiService.getContainers();
      // Update the container in parent component
      setShowAddContent(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add sample to container');
    } finally {
      setLoading(false);
    }
  };

  const handleRemoveContent = async (contentId: string) => {
    try {
      await apiService.deleteContent(contentId);
      // Refresh container data
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to remove sample from container');
    }
  };

  const getLookupName = (id: string, list: any[]) => {
    const item = list.find(item => item.id === id);
    return item ? item.name : 'Unknown';
  };

  return (
    <Box>
      <Grid container spacing={3}>
        {/* Container Information */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">
                  <Storage sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Container Information
                </Typography>
                <Button
                  startIcon={<Edit />}
                  onClick={onEdit}
                  size="small"
                >
                  Edit
                </Button>
              </Box>
              
              <List dense>
                <ListItem>
                  <ListItemText
                    primary="Name"
                    secondary={container.name}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Type"
                    secondary={container.type?.name || 'Unknown'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Concentration"
                    secondary={`${container.concentration} ${getLookupName(container.concentration_units, lookupData.units)}`}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Amount"
                    secondary={`${container.amount} ${getLookupName(container.amount_units, lookupData.units)}`}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Created"
                    secondary={new Date(container.created_at).toLocaleString()}
                  />
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Contents */}
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                <Typography variant="h6">
                  <Science sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Contents ({container.contents?.length || 0})
                </Typography>
                <Button
                  startIcon={<Add />}
                  onClick={() => setShowAddContent(true)}
                  size="small"
                  variant="outlined"
                >
                  Add Sample
                </Button>
              </Box>
              
              {container.contents && container.contents.length > 0 ? (
                <List dense>
                  {container.contents.map((content: any) => (
                    <ListItem key={content.id}>
                      <ListItemText
                        primary={content.sample.name}
                        secondary={`${content.concentration} ${getLookupName(content.concentration_units, lookupData.units)} • ${content.amount} ${getLookupName(content.amount_units, lookupData.units)}`}
                      />
                      <ListItemSecondaryAction>
                        <IconButton
                          size="small"
                          onClick={() => handleRemoveContent(content.id)}
                        >
                          <Delete />
                        </IconButton>
                      </ListItemSecondaryAction>
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Typography color="text.secondary">
                  No samples in this container
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Add Content Dialog */}
      <Dialog
        open={showAddContent}
        onClose={() => setShowAddContent(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Add Sample to Container</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          
          <Formik
            initialValues={{
              sample_id: '',
              concentration: 0,
              concentration_units: '',
              amount: 0,
              amount_units: '',
            }}
            validationSchema={Yup.object({
              sample_id: Yup.string().required('Sample is required'),
              concentration: Yup.number().min(0, 'Concentration must be positive'),
              amount: Yup.number().min(0, 'Amount must be positive'),
              concentration_units: Yup.string().required('Concentration units are required'),
              amount_units: Yup.string().required('Amount units are required'),
            })}
            onSubmit={handleAddContent}
          >
            {({ values, errors, touched, setFieldValue, isValid }) => (
              <Form>
                <Grid container spacing={2} sx={{ mt: 1 }}>
                  <Grid size={12}>
                    <FormControl fullWidth required>
                      <InputLabel>Sample</InputLabel>
                      <Select
                        value={values.sample_id}
                        onChange={(e) => setFieldValue('sample_id', e.target.value)}
                        error={touched.sample_id && !!errors.sample_id}
                      >
                        {lookupData.samples.map((sample) => (
                          <MenuItem key={sample.id} value={sample.id}>
                            {sample.name} - {sample.description}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid size={6}>
                    <Field name="concentration">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Concentration"
                          type="number"
                          fullWidth
                          error={meta.touched && !!meta.error}
                          helperText={meta.touched && meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={6}>
                    <FormControl fullWidth required>
                      <InputLabel>Concentration Units</InputLabel>
                      <Select
                        value={values.concentration_units}
                        onChange={(e) => setFieldValue('concentration_units', e.target.value)}
                        error={touched.concentration_units && !!errors.concentration_units}
                      >
                        {lookupData.units
                          .filter((unit) => unit.type_name === 'concentration')
                          .map((unit) => (
                            <MenuItem key={unit.id} value={unit.id}>
                              {unit.name}
                            </MenuItem>
                          ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid size={6}>
                    <Field name="amount">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Amount"
                          type="number"
                          fullWidth
                          error={meta.touched && !!meta.error}
                          helperText={meta.touched && meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={6}>
                    <FormControl fullWidth required>
                      <InputLabel>Amount Units</InputLabel>
                      <Select
                        value={values.amount_units}
                        onChange={(e) => setFieldValue('amount_units', e.target.value)}
                        error={touched.amount_units && !!errors.amount_units}
                      >
                        {lookupData.units
                          .filter((unit) => unit.type_name === 'mass' || unit.type_name === 'volume')
                          .map((unit) => (
                            <MenuItem key={unit.id} value={unit.id}>
                              {unit.name}
                            </MenuItem>
                          ))}
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>

                <DialogActions>
                  <Button onClick={() => setShowAddContent(false)}>
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="contained"
                    disabled={!isValid || loading}
                  >
                    {loading ? 'Adding...' : 'Add Sample'}
                  </Button>
                </DialogActions>
              </Form>
            )}
          </Formik>
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default ContainerDetails;
