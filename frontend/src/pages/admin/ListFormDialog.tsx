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
import { normalizeListName } from '../../utils/listUtils';

interface ListFormDialogProps {
  open: boolean;
  list?: {
    id: string;
    name: string;
    description?: string;
  } | null;
  existingNames: string[];
  onClose: () => void;
  onSubmit: (data: { name: string; description?: string }) => Promise<void>;
}

const validationSchema = Yup.object({
  displayName: Yup.string()
    .required('List name is required')
    .min(2, 'List name must be at least 2 characters')
    .max(100, 'List name must be less than 100 characters'),
  description: Yup.string().max(500, 'Description must be less than 500 characters'),
});

const ListFormDialog: React.FC<ListFormDialogProps> = ({
  open,
  list,
  existingNames,
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const isEdit = !!list;
  const displayName = list ? list.name.split('_').map(
    (word) => word.charAt(0).toUpperCase() + word.slice(1)
  ).join(' ') : '';

  const initialValues = {
    displayName: displayName,
    description: list?.description || '',
  };

  const handleSubmit = async (values: { displayName: string; description?: string }) => {
    setLoading(true);
    setError(null);

    try {
      const normalizedName = normalizeListName(values.displayName);

      // Check for uniqueness (excluding current list if editing)
      if (existingNames.includes(normalizedName) && (!isEdit || normalizedName !== list.name)) {
        setError('A list with this name already exists');
        setLoading(false);
        return;
      }

      await onSubmit({
        name: normalizedName,
        description: values.description || undefined,
      });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save list');
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
            <DialogTitle>{isEdit ? 'Edit List' : 'Create New List'}</DialogTitle>
            <DialogContent>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              <Box sx={{ pt: 2 }}>
                <Field name="displayName">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="List Name"
                      fullWidth
                      required
                      margin="normal"
                      helperText={
                        meta.touched && meta.error
                          ? meta.error
                          : 'Enter a display name (e.g., "Sample Status"). It will be normalized to a slug format.'
                      }
                      error={meta.touched && !!meta.error}
                      disabled={isEdit} // Don't allow editing name after creation
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
                      helperText={meta.touched && meta.error ? meta.error : 'Optional description for this list'}
                      error={meta.touched && !!meta.error}
                    />
                  )}
                </Field>

                {!isEdit && (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    The list name will be normalized to: <strong>{normalizeListName(values.displayName || '')}</strong>
                  </Alert>
                )}
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

export default ListFormDialog;

