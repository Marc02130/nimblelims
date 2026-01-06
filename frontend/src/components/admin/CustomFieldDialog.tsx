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
  FormControlLabel,
  Checkbox,
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
  validation_rules: Yup.string()
    .test(
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
    )
    .test(
      'validate-number-rules',
      function (value) {
        const { data_type } = this.parent;
        if (!value || value.trim() === '' || data_type !== 'number') return true;
        try {
          const parsed = JSON.parse(value);
          if (parsed.min !== undefined && parsed.max !== undefined) {
            if (parsed.min > parsed.max) {
              return this.createError({
                message: 'Minimum value must be less than or equal to maximum value',
              });
            }
          }
          if (parsed.min !== undefined && typeof parsed.min !== 'number') {
            return this.createError({
              message: 'Minimum value must be a number',
            });
          }
          if (parsed.max !== undefined && typeof parsed.max !== 'number') {
            return this.createError({
              message: 'Maximum value must be a number',
            });
          }
          return true;
        } catch {
          return true; // JSON parsing error is handled by is-valid-json test
        }
      }
    )
    .test(
      'validate-date-rules',
      function (value) {
        const { data_type } = this.parent;
        if (!value || value.trim() === '' || data_type !== 'date') return true;
        try {
          const parsed = JSON.parse(value);
          if (parsed.min_date !== undefined && parsed.max_date !== undefined) {
            const minDate = new Date(parsed.min_date);
            const maxDate = new Date(parsed.max_date);
            if (isNaN(minDate.getTime()) || isNaN(maxDate.getTime())) {
              return this.createError({
                message: 'min_date and max_date must be valid ISO date strings (YYYY-MM-DD)',
              });
            }
            if (minDate > maxDate) {
              return this.createError({
                message: 'Minimum date must be less than or equal to maximum date',
              });
            }
          }
          if (parsed.min_date !== undefined) {
            const minDate = new Date(parsed.min_date);
            if (isNaN(minDate.getTime())) {
              return this.createError({
                message: 'min_date must be a valid ISO date string (YYYY-MM-DD)',
              });
            }
          }
          if (parsed.max_date !== undefined) {
            const maxDate = new Date(parsed.max_date);
            if (isNaN(maxDate.getTime())) {
              return this.createError({
                message: 'max_date must be a valid ISO date string (YYYY-MM-DD)',
              });
            }
          }
          return true;
        } catch {
          return true; // JSON parsing error is handled by is-valid-json test
        }
      }
    )
    .test(
      'validate-select-rules',
      function (value) {
        const { data_type } = this.parent;
        if (!value || value.trim() === '' || data_type !== 'select') return true;
        try {
          const parsed = JSON.parse(value);
          if (!parsed.options || !Array.isArray(parsed.options)) {
            return this.createError({
              message: 'Select data type requires an "options" array in validation rules',
            });
          }
          if (parsed.options.length === 0) {
            return this.createError({
              message: 'Options array cannot be empty',
            });
          }
          return true;
        } catch {
          return true; // JSON parsing error is handled by is-valid-json test
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
    active: config?.active !== undefined ? config.active : true,
    validation_rules: config?.validation_rules
      ? JSON.stringify(config.validation_rules, null, 2)
      : '',
    description: config?.description || '',
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

      if (values.data_type === 'date') {
        if (parsedRules.min_date !== undefined && parsedRules.max_date !== undefined) {
          try {
            const minDate = new Date(parsedRules.min_date);
            const maxDate = new Date(parsedRules.max_date);
            if (isNaN(minDate.getTime()) || isNaN(maxDate.getTime())) {
              setError('min_date and max_date must be valid ISO date strings (YYYY-MM-DD)');
              setLoading(false);
              return;
            }
            if (minDate > maxDate) {
              setError('Minimum date must be less than or equal to maximum date');
              setLoading(false);
              return;
            }
          } catch (err) {
            setError('Invalid date format. Use ISO date strings (YYYY-MM-DD)');
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
        return 'JSON object with optional rules: max_length (number), min_length (number). Example: {"max_length": 100, "min_length": 1}';
      case 'number':
        return 'JSON object with optional rules: min (number), max (number). Example: {"min": 0, "max": 100}';
      case 'date':
        return 'JSON object with optional: min_date (ISO date string), max_date (ISO date string). Example: {"min_date": "2024-01-01", "max_date": "2024-12-31"}';
      case 'boolean':
        return 'JSON object (no validation rules currently supported for booleans). Example: {}';
      case 'select':
        return 'JSON object with required: options (array of strings). Example: {"options": ["option1", "option2"]}';
      default:
        return 'Enter validation rules as JSON object';
    }
  };

  const getValidationRulesHelpNote = (dataType: string): string => {
    switch (dataType) {
      case 'text':
        return 'Available validation rules:\n• min_length (number): Minimum character length\n• max_length (number): Maximum character length\n\nExample: {"min_length": 1, "max_length": 255}';
      case 'number':
        return 'Available validation rules:\n• min (number): Minimum allowed value\n• max (number): Maximum allowed value\n\nNote: min must be ≤ max\nExample: {"min": 0, "max": 14}';
      case 'date':
        return 'Available validation rules:\n• min_date (ISO date string): Minimum allowed date (YYYY-MM-DD)\n• max_date (ISO date string): Maximum allowed date (YYYY-MM-DD)\n\nNote: min_date must be ≤ max_date\nExample: {"min_date": "2024-01-01", "max_date": "2024-12-31"}';
      case 'boolean':
        return 'No validation rules are currently supported for boolean fields.\nLeave empty or use: {}';
      case 'select':
        return 'Required validation rule:\n• options (array of strings): List of selectable options\n\nExample: {"options": ["Option 1", "Option 2", "Option 3"]}';
      default:
        return 'Enter validation rules as a JSON object based on the selected data type.';
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
        {({ values, errors, touched, isValid, setFieldValue, setFieldTouched }) => (
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
                  {({ field, meta }: any) => {
                    // Parse and validate on change for real-time feedback
                    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
                      field.onChange(e);
                      // Trigger validation after a short delay
                      setTimeout(() => {
                        setFieldTouched('validation_rules', true);
                      }, 300);
                    };

                    return (
                      <Box>
                    <TextField
                      {...field}
                          onChange={handleChange}
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
                        <Box
                          sx={{
                            mt: 1,
                            p: 1.5,
                            bgcolor: 'info.light',
                            borderRadius: 1,
                            border: '1px solid',
                            borderColor: 'info.main',
                          }}
                        >
                          <Typography variant="caption" component="div" sx={{ whiteSpace: 'pre-line', color: 'text.primary' }}>
                            <strong>Validation Rules Help:</strong>
                            <br />
                            {getValidationRulesHelpNote(values.data_type)}
                          </Typography>
                        </Box>
                      </Box>
                    );
                  }}
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

                  <Field name="active">
                  {({ field }: any) => (
                    <FormControlLabel
                      control={
                        <Checkbox
                        {...field}
                          checked={field.value !== undefined ? field.value : true}
                          color="primary"
                        />
                      }
                      label="Active"
                      sx={{ mt: 2 }}
                    />
                    )}
                  </Field>
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

