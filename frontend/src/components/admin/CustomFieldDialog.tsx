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
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Typography,
  Chip,
} from '@mui/material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { apiService } from '../../services/apiService';

interface CustomAttributeConfig {
  id: string;
  entity_type: string;
  attr_name: string;
  data_type: 'text' | 'number' | 'date' | 'boolean' | 'select';
  validation_rules: Record<string, any>;
  description?: string;
  active: boolean;
}

interface CustomFieldDialogProps {
  open: boolean;
  config?: CustomAttributeConfig | null;
  entityTypes: string[];
  dataTypes: string[];
  existingConfigs: CustomAttributeConfig[];
  onClose: () => void;
  onSubmit: (data: {
    entity_type?: string;
    attr_name?: string;
    data_type?: 'text' | 'number' | 'date' | 'boolean' | 'select';
    validation_rules?: Record<string, any>;
    description?: string;
    active?: boolean;
  }) => Promise<void>;
}

const validationSchema = Yup.object({
  entity_type: Yup.string()
    .required('Entity type is required')
    .oneOf(['samples', 'tests', 'results', 'projects', 'client_projects', 'batches'], 'Invalid entity type'),
  attr_name: Yup.string()
    .required('Attribute name is required')
    .min(1, 'Attribute name must be at least 1 character')
    .max(255, 'Attribute name must be less than 255 characters')
    .matches(/^[a-zA-Z0-9_-]+$/, 'Attribute name can only contain letters, numbers, underscores, and hyphens'),
  data_type: Yup.string()
    .required('Data type is required')
    .oneOf(['text', 'number', 'date', 'boolean', 'select'], 'Invalid data type'),
  validation_rules: Yup.string().test(
    'is-valid-json',
    'Validation rules must be valid JSON',
    (value) => {
      if (!value || value.trim() === '') return true;
      try {
        const parsed = JSON.parse(value);
        return typeof parsed === 'object' && parsed !== null;
      } catch {
        return false;
      }
    }
  ),
  description: Yup.string().max(500, 'Description must be less than 500 characters'),
  active: Yup.boolean(),
});

const CustomFieldDialog: React.FC<CustomFieldDialogProps> = ({
  open,
  config,
  entityTypes,
  dataTypes,
  existingConfigs,
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [checkingUniqueness, setCheckingUniqueness] = useState(false);
  const [isUnique, setIsUnique] = useState<boolean | null>(null);

  const isEdit = !!config;

  const initialValues = {
    entity_type: config?.entity_type || '',
    attr_name: config?.attr_name || '',
    data_type: config?.data_type || 'text',
    validation_rules: config?.validation_rules
      ? JSON.stringify(config.validation_rules, null, 2)
      : '',
    description: config?.description || '',
    active: config?.active ?? true,
  };

  const handleSubmit = async (values: {
    entity_type: string;
    attr_name: string;
    data_type: 'text' | 'number' | 'date' | 'boolean' | 'select';
    validation_rules: string;
    description?: string;
    active: boolean;
  }) => {
    setLoading(true);
    setError(null);

    try {
      // Parse validation_rules JSON
      let parsedRules: Record<string, any> = {};
      if (values.validation_rules && values.validation_rules.trim() !== '') {
        try {
          parsedRules = JSON.parse(values.validation_rules);
        } catch (err) {
          setError('Invalid JSON in validation rules');
          setLoading(false);
          return;
        }
      }

      // Check for uniqueness (entity_type + attr_name combination)
      const isDuplicate = existingConfigs.some(
        (c) =>
          c.entity_type === values.entity_type &&
          c.attr_name === values.attr_name &&
          (!isEdit || c.id !== config.id)
      );

      if (isDuplicate) {
        setError(
          `A custom field with attribute name "${values.attr_name}" already exists for entity type "${values.entity_type}"`
        );
        setLoading(false);
        return;
      }

      // Validate data type specific rules
      if (values.data_type === 'select' && (!parsedRules.options || !Array.isArray(parsedRules.options))) {
        setError('Select data type requires an "options" array in validation rules');
        setLoading(false);
        return;
      }

      if (values.data_type === 'number') {
        if (parsedRules.min !== undefined && parsedRules.max !== undefined) {
          if (parsedRules.min > parsedRules.max) {
            setError('Minimum value must be less than or equal to maximum value');
            setLoading(false);
            return;
          }
        }
      }

      const submitData: any = {
        entity_type: values.entity_type,
        attr_name: values.attr_name,
        data_type: values.data_type,
        validation_rules: parsedRules,
        description: values.description || undefined,
        active: values.active,
      };

      if (isEdit) {
        await onSubmit(submitData);
      } else {
        await onSubmit(submitData);
      }
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to save custom field');
    } finally {
      setLoading(false);
    }
  };

  const checkAttributeNameUniqueness = async (
    entityType: string,
    attrName: string,
    currentId?: string
  ) => {
    if (!attrName || !entityType) {
      setIsUnique(null);
      return;
    }

    setCheckingUniqueness(true);
    try {
      // Check against existing configs
      const isDuplicate = existingConfigs.some(
        (c) => c.entity_type === entityType && c.attr_name === attrName && (!currentId || c.id !== currentId)
      );
      setIsUnique(!isDuplicate);
    } catch (err) {
      setIsUnique(null);
    } finally {
      setCheckingUniqueness(false);
    }
  };

  const getValidationRulesHelperText = (dataType: string): string => {
    switch (dataType) {
      case 'text':
        return 'JSON object with optional: max_length (number), min_length (number). Example: {"max_length": 100, "min_length": 1}';
      case 'number':
        return 'JSON object with optional: min (number), max (number). Example: {"min": 0, "max": 100}';
      case 'date':
        return 'JSON object (currently no validation rules for dates). Example: {}';
      case 'boolean':
        return 'JSON object (currently no validation rules for booleans). Example: {}';
      case 'select':
        return 'JSON object with required: options (array of strings). Example: {"options": ["option1", "option2"]}';
      default:
        return 'Enter validation rules as JSON object';
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
        {({ values, errors, touched, isValid, setFieldValue }) => (
          <Form>
            <DialogTitle>{isEdit ? 'Edit Custom Field' : 'Create New Custom Field'}</DialogTitle>
            <DialogContent>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              <Box sx={{ pt: 2 }}>
                <FormControl fullWidth margin="normal" required>
                  <InputLabel>Entity Type</InputLabel>
                  <Field name="entity_type">
                    {({ field, meta }: any) => (
                      <>
                        <Select
                          {...field}
                          label="Entity Type"
                          error={meta.touched && !!meta.error}
                          disabled={isEdit}
                        >
                          {entityTypes.map((type) => (
                            <MenuItem key={type} value={type}>
                              {type}
                            </MenuItem>
                          ))}
                        </Select>
                        {meta.touched && meta.error && (
                          <Typography variant="caption" color="error" sx={{ mt: 0.5 }}>
                            {meta.error}
                          </Typography>
                        )}
                      </>
                    )}
                  </Field>
                </FormControl>

                <Field name="attr_name">
                  {({ field, meta }: any) => (
                    <Box>
                      <TextField
                        {...field}
                        label="Attribute Name"
                        fullWidth
                        required
                        margin="normal"
                        helperText={
                          meta.touched && meta.error
                            ? meta.error
                            : isUnique === false
                            ? 'This attribute name already exists for this entity type'
                            : isUnique === true
                            ? 'Attribute name is available'
                            : 'Unique identifier for this custom attribute (alphanumeric, underscores, hyphens only)'
                        }
                        error={meta.touched && !!meta.error}
                        onChange={(e) => {
                          field.onChange(e);
                          checkAttributeNameUniqueness(values.entity_type, e.target.value, config?.id);
                        }}
                        InputProps={{
                          endAdornment:
                            checkingUniqueness && values.attr_name ? (
                              <Chip label="Checking..." size="small" />
                            ) : isUnique === true ? (
                              <Chip label="Available" size="small" color="success" />
                            ) : isUnique === false ? (
                              <Chip label="Taken" size="small" color="error" />
                            ) : null,
                        }}
                      />
                    </Box>
                  )}
                </Field>

                <FormControl fullWidth margin="normal" required>
                  <InputLabel>Data Type</InputLabel>
                  <Field name="data_type">
                    {({ field, meta }: any) => (
                      <>
                        <Select {...field} label="Data Type" error={meta.touched && !!meta.error}>
                          {dataTypes.map((type) => (
                            <MenuItem key={type} value={type}>
                              {type}
                            </MenuItem>
                          ))}
                        </Select>
                        {meta.touched && meta.error && (
                          <Typography variant="caption" color="error" sx={{ mt: 0.5 }}>
                            {meta.error}
                          </Typography>
                        )}
                      </>
                    )}
                  </Field>
                </FormControl>

                <Field name="validation_rules">
                  {({ field, meta }: any) => (
                    <TextField
                      {...field}
                      label="Validation Rules"
                      fullWidth
                      multiline
                      rows={6}
                      margin="normal"
                      helperText={
                        meta.touched && meta.error
                          ? meta.error
                          : getValidationRulesHelperText(values.data_type)
                      }
                      error={meta.touched && !!meta.error}
                      placeholder='{"min": 0, "max": 100}'
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
                      rows={3}
                      margin="normal"
                      helperText={meta.touched && meta.error ? meta.error : 'Optional description for this custom field'}
                      error={meta.touched && !!meta.error}
                    />
                  )}
                </Field>

                <FormControl fullWidth margin="normal">
                  <InputLabel>Status</InputLabel>
                  <Field name="active">
                    {({ field, meta }: any) => (
                      <Select
                        {...field}
                        label="Status"
                        value={field.value ? 'true' : 'false'}
                        onChange={(e) => field.onChange(e.target.value === 'true')}
                      >
                        <MenuItem value="true">Active</MenuItem>
                        <MenuItem value="false">Inactive</MenuItem>
                      </Select>
                    )}
                  </Field>
                </FormControl>
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

export default CustomFieldDialog;

