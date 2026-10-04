import React, { useMemo, useState } from 'react';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  Link,
  List,
  ListItem,
  ListItemText,
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { apiService } from '../services/apiService';

const validationSchema = Yup.object({
  new_password: Yup.string()
    .required('New password is required')
    .min(12, 'At least 12 characters'),
  confirm_password: Yup.string()
    .required('Confirm your new password')
    .oneOf([Yup.ref('new_password')], 'Passwords must match'),
});

export function tokenFromHash(hash: string): string {
  const raw = hash.startsWith('#') ? hash.slice(1) : hash;
  if (!raw) return '';
  return (new URLSearchParams(raw).get('token') || '').trim();
}

const ResetPassword: React.FC = () => {
  const location = useLocation();
  const token = useMemo(() => tokenFromHash(location.hash), [location.hash]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorsList, setErrorsList] = useState<string[]>([]);
  const [done, setDone] = useState(false);

  const handleSubmit = async (values: { new_password: string; confirm_password: string }) => {
    setLoading(true);
    setError(null);
    setErrorsList([]);
    try {
      await apiService.confirmPasswordReset(token, values.new_password);
      setDone(true);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (detail?.code === 'password_complexity' && Array.isArray(detail.errors)) {
        setErrorsList(detail.errors);
        setError('Password does not meet the rules');
      } else if (typeof detail === 'string') {
        setError(detail);
      } else {
        setError('Could not reset the password. Try the link again.');
      }
    } finally {
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
            Choose a new password
          </Typography>
          {!token && (
            <Alert severity="error" sx={{ mb: 2 }}>
              This reset link is invalid or has expired.
            </Alert>
          )}
          {token && !done && (
            <>
              <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 2 }}>
                At least 12 characters, with an uppercase letter, a lowercase letter, a digit, and a symbol.
                It cannot match your username or your current password.
              </Typography>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}
              {errorsList.length > 0 && (
                <List dense>
                  {errorsList.map((item) => (
                    <ListItem key={item} disablePadding>
                      <ListItemText primary={item} />
                    </ListItem>
                  ))}
                </List>
              )}
              <Formik
                initialValues={{ new_password: '', confirm_password: '' }}
                validationSchema={validationSchema}
                onSubmit={handleSubmit}
              >
                {({ isValid }) => (
                  <Form>
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
                  </Form>
                )}
              </Formik>
            </>
          )}
          {done && (
            <Alert severity="success" sx={{ mb: 2 }}>
              Password updated. Sign in with your new password.
            </Alert>
          )}
          <Typography variant="body2" align="center" sx={{ mt: 2 }}>
            <Link component={RouterLink} to="/">
              Back to sign in
            </Link>
          </Typography>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ResetPassword;
