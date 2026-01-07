import React, { useState } from 'react';
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
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';

interface ContainerFormProps {
  container?: any;
  lookupData: {
    containerTypes: any[];
    units: any[];
  };
  onSubmit: (data: any) => void;
  onCancel: () => void;
}

const getValidationSchema = (isEditMode: boolean) => {
  const baseSchema: any = {
    name: Yup.string().min(1, 'Container name is required').max(255, 'Name must be less than 255 characters'),
    type_id: isEditMode ? Yup.string().nullable() : Yup.string().required('Container type is required'),
    concentration: Yup.number().nullable().min(0, 'Concentration must be positive or zero'),
    amount: Yup.number().nullable().min(0, 'Amount must be positive or zero'),
    concentration_units: Yup.string().nullable(),
    amount_units: Yup.string().nullable(),
  };
  return Yup.object(baseSchema);
};

const ContainerForm: React.FC<ContainerFormProps> = ({
  container,
  lookupData,
  onSubmit,
  onCancel,
}) => {
  const [loading, setLoading] = useState(false);
  const isEditMode = !!container;

  const initialValues = {
    name: container?.name || '',
    type_id: container?.type_id || '',
    concentration: container?.concentration || null,
    amount: container?.amount || null,
    concentration_units: container?.concentration_units || '',
    amount_units: container?.amount_units || '',
    parent_container_id: container?.parent_container_id || '',
  };

  const handleSubmit = async (values: any) => {
    setLoading(true);
    try {
      // Prepare update data (only include fields that are set)
      const updateData: any = {};
      if (values.name !== undefined) updateData.name = values.name;
      if (values.type_id) updateData.type_id = values.type_id;
      if (values.concentration !== null && values.concentration !== undefined) {
        updateData.concentration = values.concentration;
        if (values.concentration_units) updateData.concentration_units = values.concentration_units;
      }
      if (values.amount !== null && values.amount !== undefined) {
        updateData.amount = values.amount;
        if (values.amount_units) updateData.amount_units = values.amount_units;
      }
      if (values.parent_container_id) updateData.parent_container_id = values.parent_container_id;

      await onSubmit(isEditMode ? updateData : values);
    } catch (error) {
      // Error handling is done in parent component
      throw error;
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 2 }}>
      <Formik
        initialValues={initialValues}
        validationSchema={getValidationSchema(isEditMode)}
        onSubmit={handleSubmit}
        enableReinitialize
      >
        {({ values, errors, touched, setFieldValue, isValid }) => (
          <Form>
            <Grid container spacing={3}>
              <Grid size={{ xs: 12, sm: 6 }}>
                <Field name="name">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Container Name"
                      fullWidth
                      required
                      error={meta.touched && !!meta.error}
                      helperText={meta.touched && meta.error}
                    />
                  )}
                </Field>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth required={!isEditMode}>
                  <InputLabel>Container Type</InputLabel>
                  <Select
                    value={values.type_id || ''}
                    onChange={(e) => setFieldValue('type_id', e.target.value)}
                    error={touched.type_id && !!errors.type_id}
                  >
                    <MenuItem value="">None</MenuItem>
                    {lookupData.containerTypes.map((type) => (
                      <MenuItem key={type.id} value={type.id}>
                        {type.name} ({type.material}, {type.dimensions})
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>

              <Grid size={12}>
                <Divider sx={{ my: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Contents Information
                </Typography>
              </Grid>

              <Grid size={{ xs: 12, sm: 6 }}>
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

              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth>
                  <InputLabel>Concentration Units</InputLabel>
                  <Select
                    value={values.concentration_units || ''}
                    onChange={(e) => setFieldValue('concentration_units', e.target.value || null)}
                    error={touched.concentration_units && !!errors.concentration_units}
                  >
                    <MenuItem value="">None</MenuItem>
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

              <Grid size={{ xs: 12, sm: 6 }}>
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

              <Grid size={{ xs: 12, sm: 6 }}>
                <FormControl fullWidth>
                  <InputLabel>Amount Units</InputLabel>
                  <Select
                    value={values.amount_units || ''}
                    onChange={(e) => setFieldValue('amount_units', e.target.value || null)}
                    error={touched.amount_units && !!errors.amount_units}
                  >
                    <MenuItem value="">None</MenuItem>
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

              <Grid size={12}>
                <Divider sx={{ my: 2 }} />
                <Typography variant="body2" color="text.secondary">
                  Container will be created with the specified concentration and amount.
                  Samples can be added to this container later through the contents management.
                </Typography>
              </Grid>
            </Grid>

            <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 2, mt: 3 }}>
              <Button onClick={onCancel} disabled={loading}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="contained"
                disabled={!isValid || loading}
              >
                {loading ? 'Saving...' : container ? 'Update' : 'Create'}
              </Button>
            </Box>
          </Form>
        )}
      </Formik>
    </Box>
  );
};

export default ContainerForm;
