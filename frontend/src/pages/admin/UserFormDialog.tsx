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
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';

interface UserFormDialogProps {
  open: boolean;
  user?: {
    id: string;
    username: string;
    email: string;
    role_id: string;
    client_id?: string;
  } | null;
  existingUsernames: string[];
  existingEmails: string[];
  roles: Array<{ id: string; name: string }>;
  clients: Array<{ id: string; name: string }>;
  onClose: () => void;
  onSubmit: (data: {
    username: string;
    email: string;
    password?: string;
    role_id: string;
    client_id?: string;
  }) => Promise<void>;
}

const createValidationSchema = (isEdit: boolean) => Yup.object({
  username: Yup.string()
    .required('Username is required')
    .min(3, 'Username must be at least 3 characters')
    .max(255, 'Username must be less than 255 characters'),
  email: Yup.string()
    .required('Email is required')
    .email('Invalid email address')
    .max(255, 'Email must be less than 255 characters'),
  password: isEdit
    ? Yup.string().notRequired()
    : Yup.string()
        .required('Password is required')
        .min(8, 'Password must be at least 8 characters'),
  role_id: Yup.string().required('Role is required'),
  client_id: Yup.string().nullable(),
});

const UserFormDialog: React.FC<UserFormDialogProps> = ({
  open,
  user,
  existingUsernames,
  existingEmails,
  roles,
  clients,
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const isEdit = !!user;

  const initialValues = {
    username: user?.username || '',
    email: user?.email || '',
    password: '',
    role_id: user?.role_id || '',
    client_id: user?.client_id || '',
  };

  const handleSubmit = async (values: {
    username: string;
    email: string;
    password?: string;
    role_id: string;
    client_id?: string;
  }) => {
    setLoading(true);
    setError(null);

    try {
      // Check for uniqueness (excluding current user if editing)
      if (existingUsernames.includes(values.username) && (!isEdit || values.username !== user.username)) {
        setError('A user with this username already exists');
        setLoading(false);
        return;
      }

      if (existingEmails.includes(values.email) && (!isEdit || values.email !== user.email)) {
        setError('A user with this email already exists');
        setLoading(false);
        return;
      }

      const submitData: any = {
        username: values.username,
        email: values.email,
        role_id: values.role_id,
      };

      // Only include password on create
      if (!isEdit && values.password) {
        submitData.password = values.password;
      }

      // Include client_id if provided
      if (values.client_id) {
        submitData.client_id = values.client_id;
      }

      await onSubmit(submitData);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save user');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <Formik
        initialValues={initialValues}
        validationSchema={createValidationSchema(isEdit)}
        onSubmit={handleSubmit}
        enableReinitialize
      >
        {({ values, errors, touched, setFieldValue, isValid }) => (
          <Form>
            <DialogTitle>{isEdit ? 'Edit User' : 'Create New User'}</DialogTitle>
            <DialogContent>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              <Box sx={{ pt: 2 }}>
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Field name="username">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Username"
                          fullWidth
                          required
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Unique username for login'}
                          error={meta.touched && !!meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Field name="email">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Email"
                          type="email"
                          fullWidth
                          required
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Unique email address'}
                          error={meta.touched && !!meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

                  {!isEdit && (
                    <Grid size={12}>
                      <Field name="password">
                        {({ field, meta }: any) => (
                          <TextField
                            {...field}
                            label="Password"
                            type="password"
                            fullWidth
                            required
                            margin="normal"
                            helperText={meta.touched && meta.error ? meta.error : 'Minimum 8 characters'}
                            error={meta.touched && !!meta.error}
                          />
                        )}
                      </Field>
                    </Grid>
                  )}

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <FormControl fullWidth required margin="normal">
                      <InputLabel>Role</InputLabel>
                      <Select
                        value={values.role_id}
                        onChange={(e) => setFieldValue('role_id', e.target.value)}
                        error={touched.role_id && !!errors.role_id}
                      >
                        {roles.map((role) => (
                          <MenuItem key={role.id} value={role.id}>
                            {role.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <FormControl fullWidth margin="normal">
                      <InputLabel>Client (Optional)</InputLabel>
                      <Select
                        value={values.client_id || ''}
                        onChange={(e) => setFieldValue('client_id', e.target.value || null)}
                      >
                        <MenuItem value="">None</MenuItem>
                        {clients.map((client) => (
                          <MenuItem key={client.id} value={client.id}>
                            {client.name}
                          </MenuItem>
                        ))}
                      </Select>
                    </FormControl>
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

export default UserFormDialog;

