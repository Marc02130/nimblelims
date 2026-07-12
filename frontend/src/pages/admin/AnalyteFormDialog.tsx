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
  Typography,
  Chip,
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { apiService } from '../../services/apiService';

interface AnalyteFormDialogProps {
  open: boolean;
  analyte?: {
    id: string;
    name: string;
    description?: string;
    aliases?: string[];
  } | null;
  existingNames: string[];
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
    aliases?: string[];
  }) => Promise<void>;
}

const validationSchema = Yup.object({
  name: Yup.string()
    .required('Analyte name is required')
    .min(2, 'Analyte name must be at least 2 characters')
    .max(255, 'Analyte name must be less than 255 characters'),
  description: Yup.string().max(500, 'Description must be less than 500 characters'),
  aliasesText: Yup.string(),
});

const AnalyteFormDialog: React.FC<AnalyteFormDialogProps> = ({
  open,
  analyte,
  existingNames,
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [loadedAliases, setLoadedAliases] = React.useState<string[]>([]);

  const isEdit = !!analyte;

  React.useEffect(() => {
    if (!open) return;
    setError(null);
    if (analyte?.id) {
      apiService
        .getAnalyteAliases(analyte.id)
        .then((rows: any) => {
          const list = Array.isArray(rows) ? rows.map((r: any) => r.alias) : [];
          setLoadedAliases(list);
        })
        .catch(() => setLoadedAliases(analyte.aliases || []));
    } else {
      setLoadedAliases([]);
    }
  }, [open, analyte?.id]);

  const initialValues = {
    name: analyte?.name || '',
    description: analyte?.description || '',
    aliasesText: loadedAliases.join('\n'),
  };

  const handleSubmit = async (values: {
    name: string;
    description?: string;
    aliasesText?: string;
  }) => {
    setLoading(true);
    setError(null);

    try {
      if (existingNames.includes(values.name) && (!isEdit || values.name !== analyte!.name)) {
        setError('An analyte with this name already exists');
        setLoading(false);
        return;
      }

      const aliases = (values.aliasesText || '')
        .split(/[\n,]+/)
        .map((s) => s.trim())
        .filter(Boolean);

      await onSubmit({
        name: values.name,
        description: values.description || undefined,
        aliases,
      });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save analyte');
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
        {({ values, isValid }) => (
          <Form>
            <DialogTitle>{isEdit ? 'Edit Analyte' : 'Create New Analyte'}</DialogTitle>
            <DialogContent>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {typeof error === 'string' ? error : JSON.stringify(error)}
                </Alert>
              )}

              <Box sx={{ pt: 2 }}>
                <Field name="name">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Analyte Name"
                      fullWidth
                      required
                      margin="normal"
                      helperText={
                        meta.touched && meta.error
                          ? meta.error
                          : 'Canonical name in the catalog (e.g. Ethanol)'
                      }
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
                      rows={2}
                      margin="normal"
                      helperText={meta.touched && meta.error ? meta.error : 'Optional'}
                      error={meta.touched && !!meta.error}
                    />
                  )}
                </Field>

                <Field name="aliasesText">
                  {({ field }: any) => (
                    <TextField
                      {...field}
                      label="Aliases (CRO / instrument names)"
                      fullWidth
                      multiline
                      minRows={3}
                      margin="normal"
                      placeholder={'EtOH\nC2H5OH\nEthyl alcohol'}
                      helperText="One per line or comma-separated. Used to match import column headers (exact match, case-insensitive)."
                    />
                  )}
                </Field>
                {loadedAliases.length > 0 && (
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1 }}>
                    <Typography variant="caption" color="text.secondary" sx={{ width: '100%' }}>
                      Current aliases:
                    </Typography>
                    {loadedAliases.map((a) => (
                      <Chip key={a} size="small" label={a} />
                    ))}
                  </Box>
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

export default AnalyteFormDialog;
