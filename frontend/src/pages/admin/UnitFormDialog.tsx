import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Alert,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { apiService } from '../../services/apiService';

interface UnitFormDialogProps {
  open: boolean;
  unit?: {
    id: string;
    name: string;
    description?: string;
    multiplier?: number;
    type: string;
    type_name?: string;
    active: boolean;
  } | null;
  existingNames: string[];
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
    multiplier?: number;
    type: string;
    active?: boolean;
  }) => Promise<void>;
}

const validationSchema = Yup.object({
  name: Yup.string()
    .required('Unit name is required')
    .min(1, 'Name must be at least 1 character')
    .max(255, 'Name must be less than 255 characters'),
  description: Yup.string().max(500, 'Description must be less than 500 characters'),
  multiplier: Yup.number()
    .nullable()
    .transform((value, originalValue) => (originalValue === '' ? null : value))
    .min(0, 'Multiplier must be positive or zero'),
  type: Yup.string().required('Unit type is required'),
});

const UnitFormDialog: React.FC<UnitFormDialogProps> = ({
  open,
  unit,
  existingNames,
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unitTypes, setUnitTypes] = useState<Array<{ id: string; name: string }>>([]);

  const isEdit = !!unit;

  useEffect(() => {
    if (open) {
      loadUnitTypes();
    }
  }, [open]);

  const loadUnitTypes = async () => {
    try {
      const types = await apiService.getListEntries('unit_types');
      setUnitTypes(types || []);
    } catch (err: any) {
      console.error('Failed to load unit types:', err);
    }
  };

  const initialValues = {
    name: unit?.name || '',
    description: unit?.description || '',
    multiplier: unit?.multiplier ?? null,
    type: unit?.type || '',
    active: unit?.active ?? true,
  };

  const handleSubmit = async (values: {
    name: string;
    description?: string;
    multiplier?: number | null;
    type: string;
    active?: boolean;
  }) => {
    setLoading(true);
    setError(null);

    try {
      // Check for uniqueness (excluding current unit if editing)
      if (existingNames.includes(values.name) && (!isEdit || values.name !== unit.name)) {
        setError('A unit with this name already exists');
        setLoading(false);
        return;
      }

      await onSubmit({
        name: values.name,
        description: values.description || undefined,
        multiplier: values.multiplier !== null && values.multiplier !== undefined ? values.multiplier : undefined,
        type: values.type,
        active: values.active,
      });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save unit');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <Formik
        initialValues={initialValues}
        validationSchema={validationSchema}
        onSubmit={handleSubmit}
        enableReinitialize
      >
        {({ errors, touched, isValid, values, setFieldValue }) => (
          <Form>
            <DialogTitle>{isEdit ? 'Edit Unit' : 'Create New Unit'}</DialogTitle>
            <DialogContent>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              <Box sx={{ pt: 2 }}>
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Field name="name">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Unit Name"
                          fullWidth
                          required
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Unique identifier for this unit (e.g., g/L, mg, mL)'}
                          error={meta.touched && !!meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <FormControl fullWidth required margin="normal">
                      <InputLabel>Unit Type</InputLabel>
                      <Select
                        value={values.type}
                        onChange={(e) => setFieldValue('type', e.target.value)}
                        error={touched.type && !!errors.type}
                        label="Unit Type"
                      >
                        {unitTypes.map((type) => (
                          <MenuItem key={type.id} value={type.id}>
                            {type.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Field name="multiplier">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Multiplier"
                          type="number"
                          fullWidth
                          margin="normal"
                          inputProps={{ min: 0, step: 0.000000001 }}
                          helperText={meta.touched && meta.error ? meta.error : 'Multiplier relative to base unit (e.g., 0.001 for mg relative to g)'}
                          error={meta.touched && !!meta.error}
                          value={field.value ?? ''}
                          onChange={(e) => {
                            const value = e.target.value === '' ? null : parseFloat(e.target.value);
                            field.onChange({ target: { value } });
                          }}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={12}>
                    <Field name="description">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Description"
                          fullWidth
                          multiline
                          rows={3}
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Optional description for this unit'}
                          error={meta.touched && !!meta.error}
                        />
                      )}
                    </Field>
                  </Grid>
                </Grid>
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={onClose} disabled={loading}>
                Cancel
              </Button>
              <Button type="submit" variant="contained" disabled={loading || !isValid}>
                {loading ? 'Saving...' : isEdit ? 'Update' : 'Create'}
              </Button>
            </DialogActions>
          </Form>
        )}
      </Formik>
    </Dialog>
  );
};

export default UnitFormDialog;

