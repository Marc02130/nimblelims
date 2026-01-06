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
  FormControlLabel,
  Checkbox,
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';

interface EntryFormDialogProps {
  open: boolean;
  listName: string;
  entry?: {
    id: string;
    name: string;
    description?: string;
    active?: boolean;
  } | null;
  existingNames: string[];
  onClose: () => void;
  onSubmit: (data: { name: string; description?: string; active: boolean }) => Promise<void>;
}

const validationSchema = Yup.object({
  name: Yup.string()
    .required('Entry name is required')
    .min(1, 'Entry name must be at least 1 character')
    .max(100, 'Entry name must be less than 100 characters'),
  description: Yup.string().max(500, 'Description must be less than 500 characters'),
});

const EntryFormDialog: React.FC<EntryFormDialogProps> = ({
  open,
  listName,
  entry,
  existingNames,
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const isEdit = !!entry;

  const initialValues = {
    name: entry?.name || '',
    description: entry?.description || '',
    active: entry?.active !== undefined ? entry.active : true,
  };

  const handleSubmit = async (values: { name: string; description?: string; active: boolean }) => {
    setLoading(true);
    setError(null);

    try {
      // Check for uniqueness within the list (excluding current entry if editing)
      if (existingNames.includes(values.name) && (!isEdit || values.name !== entry.name)) {
        setError('An entry with this name already exists in this list');
        setLoading(false);
        return;
      }

      await onSubmit({
        name: values.name,
        description: values.description || undefined,
        active: values.active,
      });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save entry');
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
        {({ errors, touched, isValid }) => (
          <Form>
            <DialogTitle>
              {isEdit ? 'Edit Entry' : 'Create New Entry'}
              <Box component="span" sx={{ ml: 1, fontSize: '0.875rem', color: 'text.secondary' }}>
                ({listName})
              </Box>
            </DialogTitle>
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
                      label="Entry Name"
                      fullWidth
                      required
                      margin="normal"
                      helperText={meta.touched && meta.error ? meta.error : 'Name must be unique within this list'}
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
                      helperText={meta.touched && meta.error ? meta.error : 'Optional description for this entry'}
                      error={meta.touched && !!meta.error}
                    />
                  )}
                </Field>

                <Field name="active">
                  {({ field }: any) => (
                    <FormControlLabel
                      control={
                        <Checkbox
                          {...field}
                          checked={field.value}
                          color="primary"
                        />
                      }
                      label="Active"
                      sx={{ mt: 2 }}
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

export default EntryFormDialog;

