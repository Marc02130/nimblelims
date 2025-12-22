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
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';

interface AnalyteFormDialogProps {
  open: boolean;
  analyte?: {
    id: string;
    name: string;
    description?: string;
  } | null;
  existingNames: string[];
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
  }) => Promise<void>;
}

const validationSchema = Yup.object({
  name: Yup.string()
    .required('Analyte name is required')
    .min(2, 'Analyte name must be at least 2 characters')
    .max(255, 'Analyte name must be less than 255 characters'),
  description: Yup.string().max(500, 'Description must be less than 500 characters'),
});

const AnalyteFormDialog: React.FC<AnalyteFormDialogProps> = ({
  open,
  analyte,
  existingNames,
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const isEdit = !!analyte;

  const initialValues = {
    name: analyte?.name || '',
    description: analyte?.description || '',
  };

  const handleSubmit = async (values: { name: string; description?: string }) => {
    setLoading(true);
    setError(null);

    try {
      // Check for uniqueness (excluding current analyte if editing)
      if (existingNames.includes(values.name) && (!isEdit || values.name !== analyte.name)) {
        setError('An analyte with this name already exists');
        setLoading(false);
        return;
      }

      await onSubmit({
        name: values.name,
        description: values.description || undefined,
      });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save analyte');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <Formik
        initialValues={initialValues}
        validationSchema={validationSchema}
        onSubmit={handleSubmit}
        enableReinitialize
      >
        {({ values, errors, touched, isValid }) => (
          <Form>
            <DialogTitle>{isEdit ? 'Edit Analyte' : 'Create New Analyte'}</DialogTitle>
            <DialogContent>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              <Box sx={{ pt: 2 }}>
                <Field name="name">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Analyte Name"
                      fullWidth
                      required
                      margin="normal"
                      helperText={meta.touched && meta.error ? meta.error : 'Unique identifier for this analyte'}
                      error={meta.touched && !!meta.error}
                    />
                  )}
                </Field>

                <Field name="description">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Description"
                      fullWidth
                      multiline
                      rows={3}
                      margin="normal"
                      helperText={meta.touched && meta.error ? meta.error : 'Optional description for this analyte'}
                      error={meta.touched && !!meta.error}
                    />
                  )}
                </Field>
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

export default AnalyteFormDialog;

