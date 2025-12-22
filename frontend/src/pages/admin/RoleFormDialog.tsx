import React, { useState, useEffect } from 'react';
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
  Divider,
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { apiService } from '../../services/apiService';
import PermissionSelector from './PermissionSelector';

interface Permission {
  id: string;
  name: string;
  description?: string;
}

interface RoleFormDialogProps {
  open: boolean;
  role?: {
    id: string;
    name: string;
    description?: string;
    permissions?: Permission[];
  } | null;
  existingNames: string[];
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
    permission_ids: string[];
  }) => Promise<void>;
}

const validationSchema = Yup.object({
  name: Yup.string()
    .required('Role name is required')
    .min(2, 'Role name must be at least 2 characters')
    .max(255, 'Role name must be less than 255 characters'),
  description: Yup.string().max(500, 'Description must be less than 500 characters'),
});

const RoleFormDialog: React.FC<RoleFormDialogProps> = ({
  open,
  role,
  existingNames,
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = useState(false);
  const [loadingPermissions, setLoadingPermissions] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [allPermissions, setAllPermissions] = useState<Permission[]>([]);
  const [selectedPermissionIds, setSelectedPermissionIds] = useState<string[]>([]);

  const isEdit = !!role;

  useEffect(() => {
    if (open) {
      loadPermissions();
      if (isEdit && role) {
        loadRolePermissions();
      } else {
        setSelectedPermissionIds([]);
      }
    }
  }, [open, isEdit, role]);

  const loadPermissions = async () => {
    try {
      setLoadingPermissions(true);
      const permissions = await apiService.getPermissions();
      setAllPermissions(permissions || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load permissions');
    } finally {
      setLoadingPermissions(false);
    }
  };

  const loadRolePermissions = async () => {
    if (!role) return;
    try {
      const rolePermissions = await apiService.getRolePermissions(role.id);
      setSelectedPermissionIds(rolePermissions.map((p: Permission) => p.id));
    } catch (err: any) {
      // If endpoint doesn't exist yet, use permissions from role object if available
      if (role.permissions) {
        setSelectedPermissionIds(role.permissions.map((p) => p.id));
      }
    }
  };

  const initialValues = {
    name: role?.name || '',
    description: role?.description || '',
  };

  const handleSubmit = async (values: { name: string; description?: string }) => {
    setLoading(true);
    setError(null);

    try {
      // Check for uniqueness (excluding current role if editing)
      if (existingNames.includes(values.name) && (!isEdit || values.name !== role.name)) {
        setError('A role with this name already exists');
        setLoading(false);
        return;
      }

      await onSubmit({
        name: values.name,
        description: values.description || undefined,
        permission_ids: selectedPermissionIds,
      });
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save role');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <Formik
        initialValues={initialValues}
        validationSchema={validationSchema}
        onSubmit={handleSubmit}
        enableReinitialize
      >
        {({ values, errors, touched, isValid }) => (
          <Form>
            <DialogTitle>{isEdit ? 'Edit Role' : 'Create New Role'}</DialogTitle>
            <DialogContent>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              <Box sx={{ pt: 2 }}>
                <Field name="name">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Role Name"
                      fullWidth
                      required
                      margin="normal"
                      helperText={meta.touched && meta.error ? meta.error : 'Unique identifier for this role'}
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
                      helperText={meta.touched && meta.error ? meta.error : 'Optional description for this role'}
                      error={meta.touched && !!meta.error}
                    />
                  )}
                </Field>

                <Divider sx={{ my: 3 }} />

                <Typography variant="h6" gutterBottom>
                  Permissions
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Select the permissions to assign to this role. Changes will be saved when you submit the form.
                </Typography>

                {loadingPermissions ? (
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <Typography>Loading permissions...</Typography>
                  </Box>
                ) : (
                  <PermissionSelector
                    permissions={allPermissions}
                    selectedPermissionIds={selectedPermissionIds}
                    onChange={setSelectedPermissionIds}
                  />
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

export default RoleFormDialog;

