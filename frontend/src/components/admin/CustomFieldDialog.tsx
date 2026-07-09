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
  IconButton,
} from '@mui/material';
import { Add as AddIcon } from '@mui/icons-material';
import { Formik, Form, Field } from 'formik';
import * as Yup from 'yup';
import { apiService } from '../../services/apiService';
import ListFormDialog from '../../pages/admin/ListFormDialog';
import { slugToDisplayName } from '../../utils/listUtils';

interface CustomAttributeConfig {
  id: string;
  entity_type: string;
  attr_name: string;
  data_type: 'text' | 'number' | 'date' | 'boolean' | 'list';
  validation_rules: Record<string, any>;
  source_list_id?: string;
  description?: string;
  active: boolean;
}

interface FieldLike {
  id: string;
  entity_type?: string;
  attr_name?: string;
  data_type?: string;
  validation_rules?: Record<string, any>;
  description?: string;
  source?: 'oob' | 'custom';
}

interface CustomFieldDialogProps {
  open: boolean;
  config?: CustomAttributeConfig | null;
  entityTypes: string[];
  dataTypes: string[];
  // Now receives unified OOB + custom so we can show context
  existingFields?: FieldLike[];
  onClose: () => void;
  onSubmit: (data: {
    entity_type?: string;
    attr_name?: string;
    data_type?: 'text' | 'number' | 'date' | 'boolean' | 'list';
    validation_rules?: Record<string, any>;
    description?: string;
    active?: boolean;
    source_list_id?: string;
  }) => Promise<void>;
}

// Keep in sync with management page
const ALL_ENTITY_TYPES = [
  'samples',
  'tests',
  'results',
  'projects',
  'client_projects',
  'batches',
  'units',
  'clients',
  'experiments',
  'analyses',
  'containers',
];

const validationSchema = Yup.object({
  entity_type: Yup.string()
    .required('Entity type is required')
    .oneOf(ALL_ENTITY_TYPES as any, 'Invalid entity type'),
  attr_name: Yup.string()
    .required('Attribute name is required')
    .min(1, 'Attribute name must be at least 1 character')
    .max(255, 'Attribute name must be less than 255 characters')
    .matches(/^[a-zA-Z0-9_-]+$/, 'Attribute name can only contain letters, numbers, underscores, and hyphens'),
  data_type: Yup.string()
    .required('Data type is required')
    .oneOf(['text', 'number', 'date', 'boolean', 'list'], 'Invalid data type'),
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
      'validate-list-rules',
      function (value) {
        const { data_type } = this.parent;
        if (!value || value.trim() === '' || data_type !== 'list') return true;
        try {
          const parsed = JSON.parse(value);
          if (!parsed.source_list) {
            return this.createError({
              message: 'List data type requires a "source_list" in validation rules (or select a list below)',
            });
          }
          return true;
        } catch {
          return true; // JSON parsing error is handled by is-valid-json test
        }
      }
    )
    .test(
      'validate-text-rules',
      function (value) {
        const { data_type } = this.parent;
        if (!value || value.trim() === '' || data_type !== 'text') return true;
        try {
          const parsed = JSON.parse(value);
          if (parsed.min_length !== undefined && typeof parsed.min_length !== 'number') {
            return this.createError({ message: 'min_length must be a number' });
          }
          if (parsed.max_length !== undefined && typeof parsed.max_length !== 'number') {
            return this.createError({ message: 'max_length must be a number' });
          }
          if (
            parsed.min_length !== undefined &&
            parsed.max_length !== undefined &&
            parsed.min_length > parsed.max_length
          ) {
            return this.createError({
              message: 'min_length must be less than or equal to max_length',
            });
          }
          return true;
        } catch {
          return true;
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
  existingFields = [],
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [checkingUniqueness, setCheckingUniqueness] = useState(false);
  const [isUnique, setIsUnique] = useState<boolean | null>(null);

  const [availableLists, setAvailableLists] = useState<any[]>([]);
  const [listDialogOpen, setListDialogOpen] = useState(false);
  const [listsLoading, setListsLoading] = useState(false);

  const isEdit = !!config;
  const isOob = isEdit && (config as any)?.source === 'oob';

  const loadAvailableLists = async () => {
    setListsLoading(true);
    try {
      const data = await apiService.getLists();
      setAvailableLists(data || []);
    } catch (e) {
      // non-fatal for dialog
      setAvailableLists([]);
    } finally {
      setListsLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      loadAvailableLists();
    }
  }, [open]);

  const initialValues = {
    entity_type: config?.entity_type || '',
    attr_name: config?.attr_name || '',
    data_type: config?.data_type || 'text',
    active: config?.active !== undefined ? config.active : true,
    validation_rules: config?.validation_rules
      ? JSON.stringify(config.validation_rules, null, 2)
      : '',
    description: config?.description || '',
    source_list: config?.source_list_id || (config?.validation_rules as any)?.source_list_id || (config?.validation_rules as any)?.source_list || '',
  };

  const handleSubmit = async (values: {
    entity_type: string;
    attr_name: string;
    data_type: 'text' | 'number' | 'date' | 'boolean' | 'list';
    validation_rules: string;
    description?: string;
    active: boolean;
    source_list?: string;
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
      const isDuplicate = (existingFields || []).some(
        (f: any) =>
          f.entity_type === values.entity_type &&
          f.attr_name === values.attr_name &&
          (!isEdit || f.id !== config?.id)
      );

      if (isDuplicate) {
        setError(
          `A custom field with attribute name "${values.attr_name}" already exists for entity type "${values.entity_type}"`
        );
        setLoading(false);
        return;
      }

      // Validate data type specific rules
      if (values.data_type === 'list') {
        const listName = values.source_list || parsedRules.source_list;
        if (!listName) {
          setError('List data type requires selecting a source list (or create new with +)');
          setLoading(false);
          return;
        }
        parsedRules.source_list = listName;
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

      if (values.data_type === 'text') {
        if (parsedRules.min_length !== undefined && typeof parsedRules.min_length !== 'number') {
          setError('min_length must be a number');
          setLoading(false);
          return;
        }
        if (parsedRules.max_length !== undefined && typeof parsedRules.max_length !== 'number') {
          setError('max_length must be a number');
          setLoading(false);
          return;
        }
        if (
          parsedRules.min_length !== undefined &&
          parsedRules.max_length !== undefined &&
          parsedRules.min_length > parsedRules.max_length
        ) {
          setError('min_length must be less than or equal to max_length');
          setLoading(false);
          return;
        }
      }

      const submitData: any = {
        entity_type: values.entity_type,
        attr_name: values.attr_name,
        data_type: values.data_type,
        validation_rules: parsedRules,
        description: values.description || undefined,
        active: values.active,
        source_list_id: values.source_list || undefined,  // for list type, passed to new endpoint
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
      // Check against unified fields (OOB + custom)
      const isDuplicate = (existingFields || []).some(
        (f: any) => f.entity_type === entityType && f.attr_name === attrName && (!currentId || f.id !== currentId)
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
      case 'list':
        return 'Select source list (values come from the list, not here). Additional validation rules optional.';
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
      case 'list':
        return 'List-backed field (USE LISTS):\n• Choose an existing list (reusable across top-level fields and inside Entries)\n• Or click + to create a new list on the fly\n• List values are NOT stored in validation_rules.\n• Use validation_rules JSON for additional constraints if needed (e.g. required).';
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
          <>
          <Form>
            <DialogTitle>
              {isEdit 
                ? (isOob ? 'Edit Built-in (OOB) Field' : 'Edit Custom Field') 
                : 'Create New Custom Field'}
            </DialogTitle>
            <DialogContent>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
                  {error}
                </Alert>
              )}

              <Box sx={{ pt: 2 }}>
                {/* Entity Type is required FIRST. Other fields are disabled until chosen (for create). */}
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
                          onChange={(e: any) => {
                            field.onChange(e);
                            // Clear dependent uniqueness when entity changes
                            setIsUnique(null);
                          }}
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
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5 }}>
                    You must select an entity type before defining a new custom field.
                  </Typography>
                </FormControl>

                {/* Context: existing fields on the selected entity (OOB + Custom). This helps the user. */}
                {values.entity_type && (
                  <Box
                    sx={{
                      mt: 1,
                      mb: 2,
                      p: 1.5,
                      bgcolor: 'grey.50',
                      border: '1px solid',
                      borderColor: 'divider',
                      borderRadius: 1,
                    }}
                  >
                    <Typography variant="subtitle2" gutterBottom>
                      Fields already defined for <strong>{values.entity_type}</strong>
                    </Typography>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                      {(() => {
                        const fieldsForEntity = (existingFields || []).filter(
                          (f: any) => f.entity_type === values.entity_type
                        );
                        if (fieldsForEntity.length === 0) {
                          return <Typography variant="body2" color="text.secondary">No fields defined yet.</Typography>;
                        }
                        return fieldsForEntity.slice(0, 12).map((f: any, idx: number) => (
                          <Chip
                            key={idx}
                            size="small"
                            label={`${f.attr_name} (${f.data_type || 'list'})`}
                            color={f.source === 'oob' ? 'default' : 'success'}
                            variant={f.source === 'oob' ? 'outlined' : 'filled'}
                          />
                        ));
                      })()}
                    </Box>
                    <Typography variant="caption" color="text.secondary">
                      OOB = Built-in / Out-of-the-Box. Custom = user-added. This context helps you avoid duplicates and choose good names.
                    </Typography>
                  </Box>
                )}

                <Field name="attr_name">
                  {({ field, meta }: any) => (
                    <Box>
                      <TextField
                        {...field}
                        label="Attribute Name"
                        fullWidth
                        required
                        margin="normal"
                        disabled={!values.entity_type && !isEdit || isOob}
                        helperText={
                          meta.touched && meta.error
                            ? meta.error
                            : isUnique === false
                            ? 'This attribute name already exists for this entity type'
                            : isUnique === true
                            ? 'Attribute name is available'
                            : 'Unique identifier for this field (alphanumeric, underscores, hyphens only)'
                        }
                        error={meta.touched && !!meta.error}
                        onChange={(e) => {
                          field.onChange(e);
                          if (values.entity_type) {
                            checkAttributeNameUniqueness(values.entity_type, e.target.value, config?.id);
                          }
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
                        <Select
                          {...field}
                          label="Data Type"
                          error={meta.touched && !!meta.error}
                          disabled={!values.entity_type && !isEdit || isOob}
                          onChange={(e) => {
                            field.onChange(e);
                            if (e.target.value !== 'list') {
                              setFieldValue('source_list', '');
                            }
                          }}
                        >
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

                  {/* List selector with inline create button - preferred for list-backed fields */}
                  {values.data_type === 'list' && (
                    <FormControl fullWidth margin="normal" required>
                      <InputLabel>Source List</InputLabel>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Select
                          value={values.source_list || ''}
                          onChange={(e) => {
                            const newListId = e.target.value as string;
                            setFieldValue('source_list', newListId);
                          }}
                          label="Source List"
                          fullWidth
                          disabled={!values.entity_type && !isEdit || isOob}
                        >
                          {availableLists.map((l: any) => (
                            <MenuItem key={l.id} value={l.id}>
                              {slugToDisplayName(l.name)}
                            </MenuItem>
                          ))}
                          {availableLists.length === 0 && !listsLoading && (
                            <MenuItem disabled value="">No lists yet - use + to create</MenuItem>
                          )}
                          {listsLoading && (
                            <MenuItem disabled value="">Loading lists...</MenuItem>
                          )}
                        </Select>
                        <IconButton
                          aria-label="Create new list"
                          onClick={() => setListDialogOpen(true)}
                          disabled={!values.entity_type && !isEdit || isOob}
                          color="primary"
                          size="small"
                        >
                          <AddIcon />
                        </IconButton>
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        A single list can back fields on Samples and inside Sample data Entries. Choose existing or create new.
                      </Typography>
                    </FormControl>
                  )}

                  {/* Note about list preference */}
                  {values.data_type === 'list' && (
                    <Typography variant="caption" color="info.main" sx={{ mt: 0.5, display: 'block' }}>
                      Using lists: one list maintained in one place, reusable for top-level fields and Entry fields.
                    </Typography>
                  )}

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
                      disabled={!values.entity_type && !isEdit}
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
                      disabled={isOob ? false : (!values.entity_type && !isEdit)}
                      helperText={meta.touched && meta.error ? meta.error : 'Optional description for this field'}
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
                          disabled={isOob}
                        />
                      }
                      label="Active"
                      sx={{ mt: 2 }}
                    />
                    )}
                  </Field>

                  {isOob && (
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      This is a built-in (OOB) field. You can edit its validation rules and description. For list OOB, the list (values) is managed via Lists; core list choice locked here. Use JSON editor for additional rules on scalars/lists.
                    </Typography>
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

          {/* Popup for creating new list inline when selecting source list.
               Rendered as sibling to <Form> inside a fragment because the Formik
               render prop must return a single root element. */}
          <ListFormDialog
            open={listDialogOpen}
            list={null}
            existingNames={availableLists.map((l: any) => l.name)}
            onClose={() => setListDialogOpen(false)}
            onSubmit={async (data: { name: string; description?: string }) => {
              try {
                const newList = await apiService.createList(data);
                await loadAvailableLists();
                // Auto select the newly created list by id
                setFieldValue('source_list', newList.id);
              } catch (e: any) {
                // ListFormDialog will show its own error; rethrow if needed
                throw e;
              }
            }}
          />
        </>
      )}
      </Formik>
    </Dialog>
  );
};

export default CustomFieldDialog;

