import React, { useState, useEffect } from 'react';
import {
  Box,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
} from '@mui/material';
import { useFormik } from 'formik';
import * as yup from 'yup';
import { apiService } from '../../services/apiService';

interface Client {
  id: string;
  name: string;
  description?: string;
}

interface ClientProjectFormProps {
  open: boolean;
  clientProject?: {
    id: string;
    name: string;
    description?: string;
    client_id: string;
    active: boolean;
  } | null;
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
    client_id: string;
  }) => Promise<void>;
  existingNames?: string[];
}

const validationSchema = yup.object({
  name: yup
    .string()
    .required('Name is required')
    .min(1, 'Name must be at least 1 character')
    .max(255, 'Name must be at most 255 characters'),
  description: yup.string().max(1000, 'Description must be at most 1000 characters'),
  client_id: yup.string().required('Client is required'),
});

const ClientProjectForm: React.FC<ClientProjectFormProps> = ({
  open,
  clientProject,
  onClose,
  onSubmit,
  existingNames = [],
}) => {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingClients, setLoadingClients] = useState(true);

  useEffect(() => {
    if (open) {
      loadClients();
    }
  }, [open]);

  const loadClients = async () => {
    try {
      setLoadingClients(true);
      const clientsData = await apiService.getClients();
      setClients(clientsData || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load clients');
    } finally {
      setLoadingClients(false);
    }
  };

  const formik = useFormik({
    initialValues: {
      name: clientProject?.name || '',
      description: clientProject?.description || '',
      client_id: clientProject?.client_id || '',
    },
    validationSchema: yup.object({
      name: yup
        .string()
        .required('Name is required')
        .min(1, 'Name must be at least 1 character')
        .max(255, 'Name must be at most 255 characters')
        .test('unique', 'Name already exists', (value) => {
          if (!value) return true;
          if (clientProject && value === clientProject.name) return true;
          return !existingNames.includes(value);
        }),
      description: yup.string().max(1000, 'Description must be at most 1000 characters'),
      client_id: yup.string().required('Client is required'),
    }),
    enableReinitialize: true,
    onSubmit: async (values) => {
      setLoading(true);
      setError(null);
      try {
        await onSubmit({
          name: values.name,
          description: values.description || undefined,
          client_id: values.client_id,
        });
        formik.resetForm();
        onClose();
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to save client project');
      } finally {
        setLoading(false);
      }
    },
  });

  const handleClose = () => {
    if (!loading) {
      formik.resetForm();
      setError(null);
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <form onSubmit={formik.handleSubmit}>
        <DialogTitle>
          {clientProject ? 'Edit Client Project' : 'Create Client Project'}
        </DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              fullWidth
              label="Name"
              name="name"
              value={formik.values.name}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
              error={formik.touched.name && Boolean(formik.errors.name)}
              helperText={formik.touched.name && formik.errors.name}
              required
              disabled={loading}
            />

            <TextField
              fullWidth
              label="Description"
              name="description"
              value={formik.values.description}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
              error={formik.touched.description && Boolean(formik.errors.description)}
              helperText={formik.touched.description && formik.errors.description}
              multiline
              rows={3}
              disabled={loading}
            />

            <FormControl
              fullWidth
              required
              error={formik.touched.client_id && Boolean(formik.errors.client_id)}
              disabled={loading || loadingClients}
            >
              <InputLabel>Client</InputLabel>
              <Select
                name="client_id"
                value={formik.values.client_id}
                onChange={formik.handleChange}
                onBlur={formik.handleBlur}
                label="Client"
              >
                {loadingClients ? (
                  <MenuItem disabled>
                    <CircularProgress size={20} sx={{ mr: 1 }} />
                    Loading clients...
                  </MenuItem>
                ) : (
                  clients.map((client) => (
                    <MenuItem key={client.id} value={client.id}>
                      {client.name}
                    </MenuItem>
                  ))
                )}
              </Select>
              {formik.touched.client_id && formik.errors.client_id && (
                <Box sx={{ color: 'error.main', fontSize: '0.75rem', mt: 0.5, ml: 1.75 }}>
                  {formik.errors.client_id}
                </Box>
              )}
            </FormControl>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={loading || loadingClients}
            startIcon={loading && <CircularProgress size={20} />}
          >
            {clientProject ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default ClientProjectForm;

