import React, { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  TextField,
  Typography,
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { useUser } from '../contexts/UserContext';

const validationSchema = Yup.object({
  timezone: Yup.string().required('Timezone is required'),
});

const LabTimezoneSetup: React.FC = () => {
  const { saveLabTimezone, user, logout } = useUser();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (values: { timezone: string }) => {
    setLoading(true);
    setError(null);
    try {
      await saveLabTimezone(values.timezone.trim());
      setLoading(false);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (detail?.message) {
        setError(detail.message);
      } else {
        setError(err?.message || 'Failed to save the lab timezone');
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
      <Card sx={{ maxWidth: 480, width: '100%', mx: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" align="center" gutterBottom>
            Set the lab timezone
          </Typography>
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 2 }}>
            {user?.username
              ? `Signed in as ${user.username}. The lab timezone is required before anyone can use the rest of the app.`
              : 'The lab timezone is required before anyone can use the rest of the app.'}
          </Typography>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          <Formik
            initialValues={{ timezone: '' }}
            validationSchema={validationSchema}
            onSubmit={handleSubmit}
          >
            {({ isValid, dirty }) => (
              <Form>
                <Field name="timezone">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="IANA timezone"
                      placeholder="America/New_York"
                      fullWidth
                      margin="normal"
                      required
                      error={meta.touched && !!meta.error}
                      helperText={
                        meta.touched && meta.error
                          ? meta.error
                          : 'Use a real IANA name such as America/New_York.'
                      }
                    />
                  )}
                </Field>
                <Button
                  type="submit"
                  fullWidth
                  variant="contained"
                  sx={{ mt: 2 }}
                  disabled={loading || !isValid || !dirty}
                >
                  {loading ? <CircularProgress size={24} /> : 'Save timezone'}
                </Button>
              </Form>
            )}
          </Formik>
          <Button fullWidth variant="text" sx={{ mt: 1 }} onClick={logout}>
            Sign out
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
};

export default LabTimezoneSetup;
