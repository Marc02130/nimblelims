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
  FormControlLabel,
  InputLabel,
  Select,
  MenuItem,
  Switch,
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';

interface UserFormDialogProps {
  open: boolean;
  user?: {
    id: string;
    name?: string;
    description?: string;
    username: string;
    email: string;
    role_id: string;
    client_id?: string;
    active?: boolean;
    last_login?: string;
  } | null;
  existingUsernames: string[];
  existingEmails: string[];
  existingNames: string[];
  roles: Array<{ id: string; name: string }>;
  clients: Array<{ id: string; name: string }>;
  onClose: () => void;
  onSubmit: (data: {
    name?: string;
    description?: string;
    username: string;
    email: string;
    password?: string;
    role_id: string;
    client_id?: string;
    active?: boolean;
  }) => Promise<void>;
}

const createValidationSchema = (isEdit: boolean) => Yup.object({
  name: Yup.string()
    .required('Name is required')
    .max(255, 'Name must be less than 255 characters'),
  description: Yup.string()
    .max(1000, 'Description must be less than 1000 characters'),
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
  existingNames,
  roles,
  clients,
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const isEdit = !!user;

  const initialValues = {
    name: user?.name || '',
    description: user?.description || '',
    username: user?.username || '',
    email: user?.email || '',
    password: '',
    role_id: user?.role_id || '',
    client_id: user?.client_id || '',
    active: user?.active ?? true,
  };

  const handleSubmit = async (values: {
    name: string;
    description: string;
    username: string;
    email: string;
    password?: string;
    role_id: string;
    client_id?: string;
    active?: boolean;
  }) => {
    setLoading(true);
    setError(null);

    try {
      // Check for uniqueness (excluding current user if editing)
      if (existingUsernames.includes(values.username) && (!isEdit || values.username !== user?.username)) {
        setError('A user with this username already exists');
        setLoading(false);
        return;
      }

      if (existingEmails.includes(values.email) && (!isEdit || values.email !== user?.email)) {
        setError('A user with this email already exists');
        setLoading(false);
        return;
      }

      if (existingNames.includes(values.name) && (!isEdit || values.name !== user?.name)) {
        setError('A user with this name already exists');
        setLoading(false);
        return;
      }

      const submitData: any = {};

      if (isEdit) {
        // For updates, only include fields that have changed
        if (values.name !== user?.name) {
          submitData.name = values.name;
        }
        if (values.description !== (user?.description || '')) {
          submitData.description = values.description || null;
        }
        if (values.username !== user?.username) {
          submitData.username = values.username;
        }
        if (values.email !== user?.email) {
          submitData.email = values.email;
        }
        if (values.role_id !== user?.role_id) {
          submitData.role_id = values.role_id;
        }
        if (values.client_id !== (user?.client_id || '')) {
          submitData.client_id = values.client_id || null;
        }
        if (values.active !== user?.active) {
          submitData.active = values.active;
        }
      } else {
        // For creation, include all required fields
        submitData.name = values.name;
        submitData.description = values.description || null;
        submitData.username = values.username;
        submitData.email = values.email;
        submitData.role_id = values.role_id;
        if (values.password) {
          submitData.password = values.password;
        }
        if (values.client_id) {
          submitData.client_id = values.client_id;
        }
      }

      await onSubmit(submitData);
      onClose();
    } catch (err: any) {
      // Handle Pydantic validation errors (422) which return detail as array
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        // Extract error messages from Pydantic validation errors
        const messages = detail.map((e: any) => e.msg || e.message || JSON.stringify(e)).join(', ');
        setError(messages || 'Validation error');
      } else if (typeof detail === 'string') {
        setError(detail);
      } else if (typeof detail === 'object' && detail !== null) {
        setError(detail.msg || detail.message || JSON.stringify(detail));
      } else {
        setError('Failed to save user');
      }
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
                    <Field name="name">
                      {({ field, meta }: any) => (
                        <TextField
                          {...field}
                          label="Name"
                          fullWidth
                          required
                          margin="normal"
                          helperText={meta.touched && meta.error ? meta.error : 'Display name for the user'}
                          error={meta.touched && !!meta.error}
                        />
                      )}
                    </Field>
                  </Grid>

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
                          helperText={meta.touched && meta.error ? meta.error : 'Optional description for the user'}
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

                  {isEdit && (
                    <Grid size={{ xs: 12, sm: 6 }}>
                      <TextField
                        label="Last Login"
                        value={user?.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}
                        fullWidth
                        margin="normal"
                        disabled
                        helperText="Last login time (read-only)"
                      />
                    </Grid>
                  )}

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
                            autoComplete="new-password"
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

                  {isEdit && (
                    <Grid size={12}>
                      <FormControlLabel
                        control={
                          <Switch
                            checked={values.active}
                            onChange={(e) => setFieldValue('active', e.target.checked)}
                            color="primary"
                          />
                        }
                        label="Active"
                        sx={{ mt: 2 }}
                      />
                      <Box sx={{ ml: 2, color: 'text.secondary', fontSize: '0.875rem' }}>
                        {values.active 
                          ? 'User can log in and access the system' 
                          : 'User cannot log in (account disabled)'}
                      </Box>
                    </Grid>
                  )}
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

