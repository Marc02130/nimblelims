import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { useUser } from '../contexts/UserContext';

const validationSchema = Yup.object({
  current_password: Yup.string().required('Current password is required'),
  new_password: Yup.string()
    .required('New password is required')
    .min(12, 'At least 12 characters'),
  confirm_password: Yup.string()
    .required('Confirm your new password')
    .oneOf([Yup.ref('new_password')], 'Passwords must match'),
});

const ChangePassword: React.FC = () => {
  const { changePassword, user, logout } = useUser();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorsList, setErrorsList] = useState<string[]>([]);

  const handleSubmit = async (values: {
    current_password: string;
    new_password: string;
    confirm_password: string;
  }) => {
    setLoading(true);
    setError(null);
    setErrorsList([]);
    try {
      await changePassword(values.current_password, values.new_password);
      setLoading(false);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (detail?.code === 'password_complexity' && Array.isArray(detail.errors)) {
        setErrorsList(detail.errors);
        setError('Password does not meet complexity requirements');
      } else if (typeof detail === 'string') {
        setError(detail);
      } else if (detail?.message) {
        setError(detail.message);
      } else {
        setError(err?.message || 'Failed to change password');
      }
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        bgcolor: 'background.default',
      }}
    >
      <Card sx={{ maxWidth: 440, width: '100%', mx: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" align="center" gutterBottom>
            Change password
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 2 }}>
            {user?.username
              ? `Signed in as ${user.username}. You must set a new password before continuing.`
              : 'You must set a new password before continuing.'}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 2 }}>
            Requirements: 12+ characters, upper, lower, digit, and symbol; must not match
            username or current password.
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
              {errorsList.length > 0 && (
                <List dense disablePadding>
                  {errorsList.map((e) => (
                    <ListItem key={e} disableGutters>
                      <ListItemText primary={e} />
                    </ListItem>
                  ))}
                </List>
              )}
            </Alert>
          )}

          <Formik
            initialValues={{
              current_password: '',
              new_password: '',
              confirm_password: '',
            }}
            validationSchema={validationSchema}
            onSubmit={handleSubmit}
          >
            {({ isValid }) => (
              <Form>
                <Field name="current_password">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Current password"
                      type="password"
                      fullWidth
                      margin="normal"
                      required
                      autoComplete="current-password"
                      error={meta.touched && !!meta.error}
                      helperText={meta.touched && meta.error}
                    />
                  )}
                </Field>
                <Field name="new_password">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="New password"
                      type="password"
                      fullWidth
                      margin="normal"
                      required
                      autoComplete="new-password"
                      error={meta.touched && !!meta.error}
                      helperText={meta.touched && meta.error}
                    />
                  )}
                </Field>
                <Field name="confirm_password">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Confirm new password"
                      type="password"
                      fullWidth
                      margin="normal"
                      required
                      autoComplete="new-password"
                      error={meta.touched && !!meta.error}
                      helperText={meta.touched && meta.error}
                    />
                  )}
                </Field>
                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  size="large"
                  disabled={!isValid || loading}
                  sx={{ mt: 3 }}
                >
                  {loading ? <CircularProgress size={24} /> : 'Update password'}
                </Button>
                <Button fullWidth sx={{ mt: 1 }} onClick={() => logout()}>
                  Sign out
                </Button>
              </Form>
            )}
          </Formik>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ChangePassword;
