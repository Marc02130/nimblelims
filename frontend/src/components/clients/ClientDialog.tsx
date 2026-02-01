import React, { useState } from 'react';
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
  FormControlLabel,
  Switch,
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';

interface ClientDialogProps {
  open: boolean;
  client?: {
    id: string;
    name: string;
    description?: string;
    abbreviation?: string;
    active: boolean;
  } | null;
  existingNames: string[];
  existingAbbreviations: string[];
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
    abbreviation?: string;
    active: boolean;
  }) => Promise<void>;
  readOnly?: boolean;
}

const createValidationSchema = (
  isEdit: boolean,
  existingNames: string[],
  existingAbbreviations: string[],
  currentName?: string,
  currentAbbreviation?: string
) => Yup.object({
  name: Yup.string()
    .required('Name is required')
    .min(1, 'Name must be at least 1 character')
    .max(255, 'Name must be less than 255 characters')
    .test('unique', 'A client with this name already exists', (value) => {
      if (!value) return true;
      if (isEdit && value === currentName) return true;
      return !existingNames.includes(value);
    }),
  description: Yup.string()
    .max(1000, 'Description must be less than 1000 characters'),
  abbreviation: Yup.string()
    .max(50, 'Abbreviation must be 50 characters or less')
    .nullable()
    .transform((v) => (v === '' ? undefined : v))
    .test('unique', 'This abbreviation is already used', (value) => {
      if (!value || !value.trim()) return true;
      const abbr = value.trim();
      if (isEdit && abbr === currentAbbreviation) return true;
      return !existingAbbreviations.includes(abbr);
    }),
  active: Yup.boolean(),
});

const ClientDialog: React.FC<ClientDialogProps> = ({
  open,
  client,
  existingNames,
  existingAbbreviations,
  onClose,
  onSubmit,
  readOnly = false,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEdit = !!client;

  const initialValues = {
    name: client?.name || '',
    description: client?.description || '',
    abbreviation: client?.abbreviation || '',
    active: client?.active ?? true,
  };

  const handleSubmit = async (values: {
    name: string;
    description?: string;
    abbreviation?: string;
    active: boolean;
  }) => {
    setLoading(true);
    setError(null);

    try {
      if (existingNames.includes(values.name) && (!isEdit || values.name !== client!.name)) {
        setError('A client with this name already exists');
        setLoading(false);
        return;
      }
      const abbr = values.abbreviation?.trim();
      if (abbr && existingAbbreviations.includes(abbr) && (!isEdit || abbr !== client!.abbreviation)) {
        setError('This abbreviation is already used');
        setLoading(false);
        return;
      }

      const submitData: {
        name: string;
        description?: string;
        abbreviation?: string;
        active: boolean;
      } = {
        name: values.name,
        active: values.active,
      };
      if (values.description) submitData.description = values.description;
      if (abbr) submitData.abbreviation = abbr;

      await onSubmit(submitData);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save client');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <Formik
        initialValues={initialValues}
        validationSchema={createValidationSchema(isEdit, existingNames, existingAbbreviations, client?.name, client?.abbreviation)}
        onSubmit={handleSubmit}
        enableReinitialize
      >
        {({ values, errors, touched, setFieldValue, isValid }) => (
          <Form>
            <DialogTitle>{readOnly ? 'View Client' : (isEdit ? 'Edit Client' : 'Create New Client')}</DialogTitle>
            <DialogContent>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              <Box sx={{ pt: 2 }}>
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12 }}>
                    <Field name="name">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Name"
                          fullWidth
                          required
                          margin="normal"
                          disabled={readOnly}
                          helperText={meta.touched && meta.error ? meta.error : 'Unique name for the client organization'}
                          error={meta.touched && !!meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={{ xs: 12 }}>
                    <Field name="abbreviation">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Client abbreviation (CLIABV)"
                          fullWidth
                          margin="normal"
                          disabled={readOnly}
                          helperText={meta.touched && meta.error ? meta.error : 'Optional, unique. Used for {CLIENT} in name templates.'}
                          error={meta.touched && !!meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={{ xs: 12 }}>
                    <Field name="description">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Description"
                          fullWidth
                          multiline
                          rows={3}
                          margin="normal"
                          disabled={readOnly}
                          helperText={meta.touched && meta.error ? meta.error : 'Optional description for this client'}
                          error={meta.touched && !!meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={{ xs: 12 }}>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={values.active}
                          onChange={(e) => setFieldValue('active', e.target.checked)}
                          color="primary"
                          disabled={readOnly}
                        />
                      }
                      label="Active"
                    />
                  </Grid>
                </Grid>
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={onClose} disabled={loading}>
                {readOnly ? 'Close' : 'Cancel'}
              </Button>
              {!readOnly && (
                <Button type="submit" variant="contained" disabled={loading || !isValid}>
                  {loading ? 'Saving...' : isEdit ? 'Update' : 'Create'}
                </Button>
              )}
            </DialogActions>
          </Form>
        )}
      </Formik>
    </Dialog>
  );
};

export default ClientDialog;

