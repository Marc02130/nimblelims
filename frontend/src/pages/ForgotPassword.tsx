import React, { useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
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
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { apiService } from '../services/apiService';

const validationSchema = Yup.object({
  email: Yup.string().email('Enter a valid email').required('Email is required'),
});

const ForgotPassword: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const handleSubmit = async (values: { email: string }) => {
    setLoading(true);
    setError(null);
    setNotice(null);
    try {
      const payload = await apiService.requestPasswordReset(values.email);
      setNotice(payload?.message || 'If an account exists for that email, we sent a reset link.');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Could not send a reset email. Try again.');
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
            Forgot password
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 2 }}>
            Enter the email on your account. If it matches, we send a link to choose a new password.
          </Typography>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          {notice && (
            <Alert severity="success" sx={{ mb: 2 }}>
              {notice}
            </Alert>
          )}
          <Formik
            initialValues={{ email: '' }}
            validationSchema={validationSchema}
            onSubmit={handleSubmit}
          >
            {({ isValid }) => (
              <Form>
                <Field name="email">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Email"
                      type="email"
                      fullWidth
                      margin="normal"
                      required
                      autoComplete="email"
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
                  {loading ? <CircularProgress size={24} /> : 'Send reset link'}
                </Button>
              </Form>
            )}
          </Formik>
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

export default ForgotPassword;
