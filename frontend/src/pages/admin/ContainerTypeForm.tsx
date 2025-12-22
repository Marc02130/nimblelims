import React from 'react';
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
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';

interface ContainerTypeFormProps {
  open: boolean;
  containerType?: {
    id: string;
    name: string;
    description?: string;
    capacity?: number;
    material?: string;
    dimensions?: string;
    preservative?: string;
  } | null;
  existingNames: string[];
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
    capacity?: number;
    material?: string;
    dimensions?: string;
    preservative?: string;
  }) => Promise<void>;
}

const validationSchema = Yup.object({
  name: Yup.string()
    .required('Container type name is required')
    .min(1, 'Name must be at least 1 character')
    .max(255, 'Name must be less than 255 characters'),
  description: Yup.string().max(500, 'Description must be less than 500 characters'),
  capacity: Yup.number()
    .nullable()
    .transform((value, originalValue) => (originalValue === '' ? null : value))
    .min(0, 'Capacity must be positive or zero'),
  material: Yup.string()
    .required('Material is required')
    .max(255, 'Material must be less than 255 characters'),
  dimensions: Yup.string()
    .required('Dimensions are required')
    .max(50, 'Dimensions must be less than 50 characters'),
  preservative: Yup.string().max(255, 'Preservative must be less than 255 characters'),
});

const ContainerTypeForm: React.FC<ContainerTypeFormProps> = ({
  open,
  containerType,
  existingNames,
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const isEdit = !!containerType;

  const initialValues = {
    name: containerType?.name || '',
    description: containerType?.description || '',
    capacity: containerType?.capacity ?? null,
    material: containerType?.material || '',
    dimensions: containerType?.dimensions || '',
    preservative: containerType?.preservative || '',
  };

  const handleSubmit = async (values: {
    name: string;
    description?: string;
    capacity?: number | null;
    material?: string;
    dimensions?: string;
    preservative?: string;
  }) => {
    setLoading(true);
    setError(null);

    try {
      // Check for uniqueness (excluding current container type if editing)
      if (existingNames.includes(values.name) && (!isEdit || values.name !== containerType.name)) {
        setError('A container type with this name already exists');
        setLoading(false);
        return;
      }

      await onSubmit({
        name: values.name,
        description: values.description || undefined,
        capacity: values.capacity !== null && values.capacity !== undefined ? values.capacity : undefined,
        material: values.material || undefined,
        dimensions: values.dimensions || undefined,
        preservative: values.preservative || undefined,
      });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save container type');
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
        {({ errors, touched, isValid }) => (
          <Form>
            <DialogTitle>{isEdit ? 'Edit Container Type' : 'Create New Container Type'}</DialogTitle>
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
                          label="Container Type Name"
                          fullWidth
                          required
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Unique identifier for this container type'}
                          error={meta.touched && !!meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Field name="capacity">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Capacity"
                          type="number"
                          fullWidth
                          margin="normal"
                          inputProps={{ min: 0, step: 0.01 }}
                          helperText={meta.touched && meta.error ? meta.error : 'Capacity in base units (optional)'}
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

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Field name="material">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Material"
                          fullWidth
                          required
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Material composition (e.g., polypropylene, glass)'}
                          error={meta.touched && !!meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Field name="dimensions">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Dimensions"
                          fullWidth
                          required
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Dimensions (e.g., 8x12, 15x100mm)'}
                          error={meta.touched && !!meta.error}
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
                          helperText={meta.touched && meta.error ? meta.error : 'Optional description for this container type'}
                          error={meta.touched && !!meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={12}>
                    <Field name="preservative">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Preservative"
                          fullWidth
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Optional preservative information'}
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

export default ContainerTypeForm;

