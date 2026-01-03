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
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Typography,
  FormControlLabel,
  Switch,
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';

interface HelpEntry {
  id: string;
  section: string;
  content: string;
  role_filter: string | null;
  active: boolean;
}

interface Role {
  id: string;
  name: string;
}

interface HelpEntryDialogProps {
  open: boolean;
  entry?: HelpEntry | null;
  roles: Role[];
  onClose: () => void;
  onSubmit: (data: {
    section?: string;
    content?: string;
    role_filter?: string | null;
    active?: boolean;
  }) => Promise<void>;
}

const validationSchema = Yup.object({
  section: Yup.string()
    .required('Section is required')
    .min(1, 'Section must be at least 1 character')
    .max(255, 'Section must be less than 255 characters'),
  content: Yup.string()
    .required('Content is required')
    .min(1, 'Content must be at least 1 character'),
  role_filter: Yup.string().nullable(),
  active: Yup.boolean(),
});

const HelpEntryDialog: React.FC<HelpEntryDialogProps> = ({
  open,
  entry,
  roles,
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEdit = !!entry;

  const initialValues = {
    section: entry?.section || '',
    content: entry?.content || '',
    role_filter: entry?.role_filter || '',
    active: entry?.active !== undefined ? entry.active : true,
  };

  const handleSubmit = async (values: {
    section: string;
    content: string;
    role_filter: string;
    active: boolean;
  }) => {
    try {
      setLoading(true);
      setError(null);
      
      const submitData: {
        section?: string;
        content?: string;
        role_filter?: string | null;
        active?: boolean;
      } = {};

      if (!isEdit || values.section !== entry.section) {
        submitData.section = values.section;
      }
      if (!isEdit || values.content !== entry.content) {
        submitData.content = values.content;
      }
      if (!isEdit || values.role_filter !== (entry?.role_filter || '')) {
        submitData.role_filter = values.role_filter || null;
      }
      if (!isEdit || values.active !== entry.active) {
        submitData.active = values.active;
      }

      await onSubmit(submitData);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save help entry');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      aria-labelledby="help-entry-dialog-title"
      aria-describedby="help-entry-dialog-description"
    >
      <Formik
        initialValues={initialValues}
        validationSchema={validationSchema}
        onSubmit={handleSubmit}
        enableReinitialize
      >
        {({ values, errors, touched, handleChange, handleBlur, setFieldValue }) => (
          <Form>
            <DialogTitle id="help-entry-dialog-title">
              {isEdit ? 'Edit Help Entry' : 'Create Help Entry'}
            </DialogTitle>
            <DialogContent>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
                <Field
                  as={TextField}
                  name="section"
                  label="Section"
                  fullWidth
                  required
                  error={touched.section && !!errors.section}
                  helperText={touched.section && errors.section}
                  value={values.section}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  aria-describedby="section-help-text"
                />
                <Typography
                  id="section-help-text"
                  variant="caption"
                  color="text.secondary"
                  sx={{ mt: -1.5 }}
                >
                  Section name (e.g., &quot;User Management&quot;, &quot;EAV Configuration&quot;)
                </Typography>

                <Field
                  as={TextField}
                  name="content"
                  label="Content"
                  fullWidth
                  required
                  multiline
                  rows={8}
                  error={touched.content && !!errors.content}
                  helperText={touched.content && errors.content}
                  value={values.content}
                  onChange={handleChange}
                  onBlur={handleBlur}
                  aria-describedby="content-help-text"
                />
                <Typography
                  id="content-help-text"
                  variant="caption"
                  color="text.secondary"
                  sx={{ mt: -1.5 }}
                >
                  Help content text. Use line breaks for formatting.
                </Typography>

                <FormControl fullWidth>
                  <InputLabel>Role Filter</InputLabel>
                  <Field
                    as={Select}
                    name="role_filter"
                    label="Role Filter"
                    value={values.role_filter}
                    onChange={(e: any) => {
                      setFieldValue('role_filter', e.target.value);
                    }}
                    onBlur={handleBlur}
                    aria-describedby="role-filter-help-text"
                  >
                    <MenuItem value="">Public (No Role)</MenuItem>
                    {roles.map((role) => {
                      const roleSlug = role.name.toLowerCase().replace(' ', '-');
                      return (
                        <MenuItem key={role.id} value={roleSlug}>
                          {role.name}
                        </MenuItem>
                      );
                    })}
                  </Field>
                  <Typography
                    id="role-filter-help-text"
                    variant="caption"
                    color="text.secondary"
                    sx={{ mt: 1 }}
                  >
                    Select a role to filter this help entry, or leave empty for public access.
                    Role filter will be validated against existing roles.
                  </Typography>
                </FormControl>

                {isEdit && (
                  <FormControlLabel
                    control={
                      <Switch
                        checked={values.active}
                        onChange={(e) => setFieldValue('active', e.target.checked)}
                        name="active"
                      />
                    }
                    label="Active"
                  />
                )}
              </Box>
            </DialogContent>
            <DialogActions sx={{ px: 3, pb: 2 }}>
              <Button onClick={onClose} disabled={loading}>
                Cancel
              </Button>
              <Button type="submit" variant="contained" disabled={loading}>
                {loading ? 'Saving...' : isEdit ? 'Update' : 'Create'}
              </Button>
            </DialogActions>
          </Form>
        )}
      </Formik>
    </Dialog>
  );
};

export default HelpEntryDialog;

