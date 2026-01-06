import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Paper,
  Stepper,
  Step,
  StepLabel,
  Button,
  Typography,
  Alert,
  CircularProgress,
  FormControlLabel,
  Switch,
  Divider,
} from '@mui/material';
import { Formik, Form } from 'formik';
import * as Yup from 'yup';
import SampleDetailsStep from '../components/accessioning/SampleDetailsStep';
import TestAssignmentStep from '../components/accessioning/TestAssignmentStep';
import ReviewStep from '../components/accessioning/ReviewStep';
import BulkUniquesTable from '../components/accessioning/BulkUniquesTable';
import AliquotDerivativeDialog from '../components/aliquots/AliquotDerivativeDialog';
import { apiService } from '../services/apiService';
import { useUser } from '../contexts/UserContext';

const steps = ['Sample Details', 'Test Assignment', 'Review & Submit'];

interface BulkUnique {
  id: string;
  name?: string;
  client_sample_id?: string;
  container_name: string;
  temperature?: number;
  anomalies?: string;
  description?: string;
  custom_attributes?: Record<string, any>;
}

interface SampleFormData {
  // Bulk mode toggle
  bulk_mode: boolean;
  
  // Sample details (common in bulk mode)
  name: string;
  description: string;
  due_date: string;
  received_date: string;
  sample_type: string;
  status: string;
  matrix: string;
  temperature: number;
  anomalies: string;
  project_id: string;
  client_project_id: string;
  qc_type: string;
  
  // Custom attributes
  custom_attributes: Record<string, any>;
  
  // Test assignment
  selected_analyses: string[];
  battery_id: string;
  
  // Container assignment
  container_type_id: string;
  container_name: string;
  container_row: number;
  container_column: number;
  container_concentration: number | null;
  container_concentration_units: string;
  container_amount: number | null;
  container_amount_units: string;
  
  // Bulk mode specific
  bulk_uniques: BulkUnique[];
  auto_name_prefix: string;
  auto_name_start: number;
  
  // Double entry validation
  double_entry_enabled: boolean;
  name_verification: string;
  sample_type_verification: string;
}

const initialValues: SampleFormData = {
  bulk_mode: false,
  name: '',
  description: '',
  due_date: '',
  received_date: new Date().toISOString().split('T')[0],
  sample_type: '',
  status: '',
  matrix: '',
  temperature: 0,
  anomalies: '',
  project_id: '',
  client_project_id: '',
  qc_type: '',
  custom_attributes: {},
  selected_analyses: [],
  battery_id: '',
  container_type_id: '',
  container_name: '',
  container_row: 1,
  container_column: 1,
  container_concentration: null,
  container_concentration_units: '',
  container_amount: null,
  container_amount_units: '',
  bulk_uniques: [{ id: '1', container_name: '', custom_attributes: {} }],
  auto_name_prefix: '',
  auto_name_start: 1,
  double_entry_enabled: false,
  name_verification: '',
  sample_type_verification: '',
};

const buildCustomAttributesValidation = (configs: any[]): Record<string, any> => {
  const customAttrsSchema: Record<string, any> = {};
  
  configs.forEach((config) => {
    if (!config.active) return;
    
    // Use the attribute name directly (not the full path)
    const fieldName = config.attr_name;
    let fieldSchema: any = null;
    
    switch (config.data_type) {
      case 'text':
        fieldSchema = Yup.string().nullable();
        if (config.validation_rules?.max_length) {
          fieldSchema = fieldSchema.max(config.validation_rules.max_length, `Maximum length is ${config.validation_rules.max_length}`);
        }
        if (config.validation_rules?.min_length) {
          fieldSchema = fieldSchema.min(config.validation_rules.min_length, `Minimum length is ${config.validation_rules.min_length}`);
        }
        break;
      
      case 'number':
        fieldSchema = Yup.number()
          .nullable()
          .transform((value, originalValue) => {
            // Handle empty strings
            if (originalValue === '' || originalValue === null || originalValue === undefined) {
              return null;
            }
            // Parse number
            const parsed = typeof originalValue === 'string' ? parseFloat(originalValue) : originalValue;
            // Return null for NaN instead of NaN
            return isNaN(parsed) ? null : parsed;
          })
          .test('is-number', 'Must be a valid number', (value) => {
            if (value === null || value === undefined) return true; // Allow null/undefined
            return typeof value === 'number' && !isNaN(value);
          });
        if (config.validation_rules?.min !== undefined) {
          fieldSchema = fieldSchema.min(config.validation_rules.min, `Value must be at least ${config.validation_rules.min}`);
        }
        if (config.validation_rules?.max !== undefined) {
          fieldSchema = fieldSchema.max(config.validation_rules.max, `Value must be at most ${config.validation_rules.max}`);
        }
        break;
      
      case 'date':
        // Date values come as ISO strings, so we need to transform them
        fieldSchema = Yup.mixed()
          .nullable()
          .transform((value, originalValue) => {
            // If it's already a Date, return it
            if (value instanceof Date) return value;
            // If it's a string (ISO format), convert to Date
            if (typeof value === 'string' && value) {
              const date = new Date(value);
              return isNaN(date.getTime()) ? null : date;
            }
            return null;
          })
          .test('is-date', 'Must be a valid date', (value) => {
            if (value === null || value === undefined) return true; // Allow null/undefined
            return value instanceof Date && !isNaN(value.getTime());
          });
        if (config.validation_rules?.min_date) {
          fieldSchema = fieldSchema.test(
            'min-date',
            `Date must be on or after ${config.validation_rules.min_date}`,
            function(value: any) {
              if (!value) return true; // Allow null/undefined
              const minDate = new Date(config.validation_rules.min_date);
              return value >= minDate;
            }
          );
        }
        if (config.validation_rules?.max_date) {
          fieldSchema = fieldSchema.test(
            'max-date',
            `Date must be on or before ${config.validation_rules.max_date}`,
            function(value: any) {
              if (!value) return true; // Allow null/undefined
              const maxDate = new Date(config.validation_rules.max_date);
              return value <= maxDate;
            }
          );
        }
        break;
      
      case 'boolean':
        fieldSchema = Yup.boolean().nullable();
        break;
      
      case 'select':
        const options = config.validation_rules?.options || [];
        fieldSchema = Yup.string().oneOf([...options, ''], `Must be one of: ${options.join(', ')}`).nullable();
        break;
      
      default:
        fieldSchema = Yup.mixed().nullable();
    }
    
      if (fieldSchema) {
        customAttrsSchema[fieldName] = fieldSchema;
      }
    });
  
  // Return as a nested object structure for custom_attributes
  // Use noUnknown(true) to allow fields not in the schema (e.g., inactive fields)
  return {
    custom_attributes: Yup.object().shape(customAttrsSchema).noUnknown(true).nullable()
  };
};

const getValidationSchema = (bulkMode: boolean, customAttributeConfigs: any[] = []) => {
  const baseSchema: any = {
    due_date: Yup.date().required('Due date is required'),
    received_date: Yup.date().required('Received date is required'),
    sample_type: Yup.string().required('Sample type is required'),
    status: Yup.string().required('Status is required'),
    matrix: Yup.string().required('Matrix is required'),
    project_id: Yup.string().required('Project is required'),
    container_type_id: Yup.string().required('Container type is required'),
    container_concentration: Yup.number().nullable().min(0, 'Concentration must be positive or zero'),
    container_amount: Yup.number().nullable().min(0, 'Amount must be positive or zero'),
    container_concentration_units: Yup.string().when('container_concentration', {
      is: (val: number | null) => val !== null && val !== undefined && val > 0,
      then: (schema: any) => schema.required('Concentration units are required when concentration is specified'),
      otherwise: (schema: any) => schema.notRequired(),
    }),
    container_amount_units: Yup.string().when('container_amount', {
      is: (val: number | null) => val !== null && val !== undefined && val > 0,
      then: (schema: any) => schema.required('Amount units are required when amount is specified'),
      otherwise: (schema: any) => schema.notRequired(),
    }),
  };

  if (!bulkMode) {
    baseSchema.name = Yup.string().required('Sample name is required');
    baseSchema.temperature = Yup.number().required('Temperature is required');
    baseSchema.container_name = Yup.string().required('Container name/barcode is required');
    baseSchema.container_row = Yup.number().min(1, 'Row must be at least 1').required();
    baseSchema.container_column = Yup.number().min(1, 'Column must be at least 1').required();
    baseSchema.name_verification = Yup.string().when('double_entry_enabled', {
      is: true,
      then: (schema: any) => schema.required('Name verification is required for double entry'),
      otherwise: (schema: any) => schema.notRequired(),
    });
    baseSchema.sample_type_verification = Yup.string().when('double_entry_enabled', {
      is: true,
      then: (schema: any) => schema.required('Sample type verification is required for double entry'),
      otherwise: (schema: any) => schema.notRequired(),
    });
  } else {
    // Build custom attributes validation for bulk uniques
    const bulkUniqueCustomAttrsValidation: Record<string, any> = {};
    customAttributeConfigs.forEach((config) => {
      if (!config.active) return;
      
      // Use the attribute name directly (not the full path) since we're already inside custom_attributes
      const fieldName = config.attr_name;
      let fieldSchema: any = null;
      
      switch (config.data_type) {
        case 'text':
          fieldSchema = Yup.string().nullable();
          if (config.validation_rules?.max_length) {
            fieldSchema = fieldSchema.max(config.validation_rules.max_length);
          }
          if (config.validation_rules?.min_length) {
            fieldSchema = fieldSchema.min(config.validation_rules.min_length);
          }
          break;
        case 'number':
          fieldSchema = Yup.number().nullable();
          if (config.validation_rules?.min !== undefined) {
            fieldSchema = fieldSchema.min(
              config.validation_rules.min,
              `Value must be at least ${config.validation_rules.min}`
            );
          }
          if (config.validation_rules?.max !== undefined) {
            fieldSchema = fieldSchema.max(
              config.validation_rules.max,
              `Value must be at most ${config.validation_rules.max}`
            );
          }
          break;
        case 'date':
          fieldSchema = Yup.date().nullable();
          if (config.validation_rules?.min_date) {
            fieldSchema = fieldSchema.min(
              new Date(config.validation_rules.min_date),
              `Date must be on or after ${config.validation_rules.min_date}`
            );
          }
          if (config.validation_rules?.max_date) {
            fieldSchema = fieldSchema.max(
              new Date(config.validation_rules.max_date),
              `Date must be on or before ${config.validation_rules.max_date}`
            );
          }
          break;
        case 'boolean':
          fieldSchema = Yup.boolean().nullable();
          break;
        case 'select':
          const options = config.validation_rules?.options || [];
          fieldSchema = Yup.string().oneOf([...options, ''], `Must be one of: ${options.join(', ')}`).nullable();
          break;
        default:
          fieldSchema = Yup.mixed().nullable();
      }
      
      if (fieldSchema) {
        bulkUniqueCustomAttrsValidation[fieldName] = fieldSchema;
      }
    });

    baseSchema.bulk_uniques = Yup.array()
      .of(
        Yup.object().shape({
          id: Yup.string(),
          name: Yup.string(),
          client_sample_id: Yup.string(),
          container_name: Yup.string().required('Container name is required'),
          temperature: Yup.number(),
          anomalies: Yup.string(),
          description: Yup.string(),
          custom_attributes: Yup.object().shape(bulkUniqueCustomAttrsValidation).noUnknown(true).nullable(),
        })
      )
      .min(1, 'At least one sample is required')
      .test('names-or-auto', 'Either provide names or configure auto-naming', function (uniques) {
        const { auto_name_prefix } = this.parent;
        const hasNames = uniques?.some((u: any) => u.name);
        const hasAutoNaming = !!auto_name_prefix;
        return hasNames || hasAutoNaming;
      });
  }

  // Add custom attributes validation
  const customAttrsValidation = buildCustomAttributesValidation(customAttributeConfigs);
  Object.assign(baseSchema, customAttrsValidation);

  return Yup.object(baseSchema);
};

const AccessioningForm: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [aliquotDialogOpen, setAliquotDialogOpen] = useState(false);
  const [createdSample, setCreatedSample] = useState<any>(null);
  const [lookupData, setLookupData] = useState({
    sampleTypes: [],
    statuses: [],
    matrices: [],
    qcTypes: [],
    projects: [],
    clientProjects: [],
    analyses: [],
    batteries: [],
    containerTypes: [],
    units: [],
  });
  const [customAttributeConfigs, setCustomAttributeConfigs] = useState<any[]>([]);

  const { user } = useUser();

  useEffect(() => {
    loadLookupData();
    loadCustomAttributeConfigs();
  }, []);

  const loadLookupData = async () => {
    try {
      const [
        sampleTypes,
        statuses,
        matrices,
        qcTypes,
        projects,
        clientProjects,
        analyses,
        batteries,
        containerTypes,
        units,
      ] = await Promise.all([
        apiService.getListEntries('sample_types'),
        apiService.getListEntries('sample_status'),
        apiService.getListEntries('matrix_types'),
        apiService.getListEntries('qc_types'),
        apiService.getProjects(),
        apiService.getClientProjects().catch(() => ({ client_projects: [] })),
        apiService.getAnalyses(),
        apiService.getTestBatteries().catch(() => ({ batteries: [] })),
        apiService.getContainerTypes(),
        apiService.getUnits(),
      ]);

      setLookupData({
        sampleTypes,
        statuses,
        matrices,
        qcTypes,
        projects,
        clientProjects: clientProjects.client_projects || clientProjects || [],
        analyses,
        batteries: batteries.batteries || batteries || [],
        containerTypes,
        units,
      });
    } catch (err) {
      setError('Failed to load form data');
    }
  };

  const loadCustomAttributeConfigs = async () => {
    try {
      const response = await apiService.getCustomAttributeConfigs({
        entity_type: 'samples',
        active: true,
      });
      setCustomAttributeConfigs(response.configs || []);
    } catch (err: any) {
      console.error('Error loading custom attribute configs:', err);
    }
  };

  const handleNext = () => {
    setActiveStep((prevActiveStep) => prevActiveStep + 1);
  };

  const handleBack = () => {
    setActiveStep((prevActiveStep) => prevActiveStep - 1);
  };

  const handleSubmit = async (values: SampleFormData) => {
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      if (values.bulk_mode) {
        // Bulk accessioning
        const bulkData = {
          due_date: values.due_date,
          received_date: values.received_date,
          sample_type: values.sample_type,
          matrix: values.matrix,
          project_id: values.project_id,
          client_project_id: values.client_project_id || undefined,
          qc_type: values.qc_type || undefined,
          assigned_tests: values.selected_analyses,
          battery_id: values.battery_id || undefined,
          container_type_id: values.container_type_id,
          uniques: values.bulk_uniques.map((u) => {
            const uniqueData: any = {
              name: u.name || undefined,
              client_sample_id: u.client_sample_id || undefined,
              container_name: u.container_name,
              temperature: u.temperature || undefined,
              anomalies: u.anomalies || undefined,
              description: u.description || undefined,
            };
            // Include custom_attributes if present
            if (u.custom_attributes && Object.keys(u.custom_attributes).length > 0) {
              uniqueData.custom_attributes = u.custom_attributes;
            }
            return uniqueData;
          }),
          auto_name_prefix: values.auto_name_prefix || undefined,
          auto_name_start: values.auto_name_start || undefined,
        };

        const results = await apiService.bulkAccessionSamples(bulkData);
        setSuccess(`Successfully accessioned ${results.length} sample(s)!`);
        setCreatedSample(results[0]); // Use first sample for aliquot dialog
        setAliquotDialogOpen(true);
        setActiveStep(0);
      } else {
        // Single sample accessioning (existing flow)
        // Step 1: Create container instance
        const containerData: any = {
          name: values.container_name,
          type_id: values.container_type_id,
          row: values.container_row || 1,
          column: values.container_column || 1,
        };

        if (values.container_concentration !== null && values.container_concentration !== undefined) {
          containerData.concentration = values.container_concentration;
          if (values.container_concentration_units) {
            containerData.concentration_units = values.container_concentration_units;
          }
        }

        if (values.container_amount !== null && values.container_amount !== undefined) {
          containerData.amount = values.container_amount;
          if (values.container_amount_units) {
            containerData.amount_units = values.container_amount_units;
          }
        }

        const container = await apiService.createContainer(containerData);

        // Step 2: Create sample
        const sampleData: any = {
          name: values.name,
          description: values.description,
          due_date: values.due_date,
          received_date: values.received_date,
          sample_type: values.sample_type,
          status: values.status,
          matrix: values.matrix,
          temperature: values.temperature,
          anomalies: values.anomalies,
          project_id: values.project_id,
          client_project_id: values.client_project_id || undefined,
          qc_type: values.qc_type || undefined,
        };

        // Include custom_attributes if present
        if (values.custom_attributes && Object.keys(values.custom_attributes).length > 0) {
          sampleData.custom_attributes = values.custom_attributes;
        }

        const sample = await apiService.createSample(sampleData);

        // Step 3: Link sample to container via contents
        const contentData: any = {
          container_id: container.id,
          sample_id: sample.id,
        };

        if (values.container_concentration !== null && values.container_concentration !== undefined) {
          contentData.concentration = values.container_concentration;
          if (values.container_concentration_units) {
            contentData.concentration_units = values.container_concentration_units;
          }
        }

        if (values.container_amount !== null && values.container_amount !== undefined) {
          contentData.amount = values.container_amount;
          if (values.container_amount_units) {
            contentData.amount_units = values.container_amount_units;
          }
        }

        await apiService.createContent(contentData);

        // Step 4: Create tests for selected analyses
        for (const analysisId of values.selected_analyses) {
          await apiService.createTest({
            sample_id: sample.id,
            analysis_id: analysisId,
          });
        }

        setSuccess('Sample accessioned successfully!');
        setCreatedSample(sample);
        setAliquotDialogOpen(true);
        setActiveStep(0);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to accession sample(s)');
    } finally {
      setLoading(false);
    }
  };

  const renderStepContent = (step: number, values: SampleFormData, setFieldValue: any, setFieldTouched?: any, validateField?: any, errors?: any, touched?: any) => {
    switch (step) {
      case 0:
        return (
          <SampleDetailsStep
            values={values}
            setFieldValue={setFieldValue}
            setFieldTouched={setFieldTouched}
            validateField={validateField}
            lookupData={lookupData}
            bulkMode={values.bulk_mode}
            errors={errors}
            touched={touched}
            customAttributeConfigs={customAttributeConfigs}
          />
        );
      case 1:
        return (
          <TestAssignmentStep
            values={values}
            setFieldValue={setFieldValue}
            lookupData={lookupData}
            bulkMode={values.bulk_mode}
          />
        );
      case 2:
        return (
          <ReviewStep
            values={values}
            lookupData={lookupData}
            bulkMode={values.bulk_mode}
          />
        );
      default:
        return null;
    }
  };

  return (
    <Box sx={{ maxWidth: 1200, margin: '0 auto', p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h4">
          Sample Accessioning
        </Typography>
      </Box>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        <Stepper activeStep={activeStep} sx={{ mb: 3 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        <Formik
          initialValues={initialValues}
          validationSchema={useMemo(() => getValidationSchema(initialValues.bulk_mode, customAttributeConfigs), [initialValues.bulk_mode, customAttributeConfigs])}
          onSubmit={handleSubmit}
          enableReinitialize
          validateOnChange={true}
          validateOnBlur={true}
        >
          {({ values, setFieldValue, setFieldTouched, validateField, isValid, errors, touched, setValues }) => {
            const bulkMode = values.bulk_mode;

            return (
              <Form>
                {/* Bulk Mode Toggle */}
                <Box mb={3}>
                  <FormControlLabel
                    control={
                      <Switch
                        checked={bulkMode}
                        onChange={(e) => {
                          const newBulkMode = e.target.checked;
                          setFieldValue('bulk_mode', newBulkMode);
                          if (newBulkMode) {
                            // Initialize with one empty unique row
                            if (values.bulk_uniques.length === 0) {
                              setFieldValue('bulk_uniques', [{ id: '1', container_name: '', custom_attributes: {} }]);
                            }
                          }
                          // Re-validate with new schema
                          setTimeout(() => {
                            // Force re-validation by touching a field
                            setFieldValue('bulk_mode', newBulkMode);
                          }, 0);
                        }}
                      />
                    }
                    label="Bulk Accessioning Mode"
                  />
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {bulkMode
                      ? 'Create multiple samples with common fields and unique per-sample data'
                      : 'Create a single sample'}
                  </Typography>
                </Box>

                <Divider sx={{ mb: 3 }} />

                {renderStepContent(activeStep, values, setFieldValue, setFieldTouched, validateField, errors, touched)}

                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 3 }}>
                  <Button
                    disabled={activeStep === 0}
                    onClick={handleBack}
                  >
                    Back
                  </Button>
                  
                  {activeStep === steps.length - 1 ? (
                    <Button
                      type="submit"
                      variant="contained"
                      disabled={!isValid || loading}
                      startIcon={loading && <CircularProgress size={20} />}
                    >
                      {loading ? 'Submitting...' : bulkMode ? `Submit ${values.bulk_uniques.length} Sample(s)` : 'Submit'}
                    </Button>
                  ) : (
                    <Button
                      variant="contained"
                      onClick={handleNext}
                      disabled={!isValid}
                    >
                      Next
                    </Button>
                  )}
                </Box>
              </Form>
            );
          }}
        </Formik>
      </Paper>

      {createdSample && (
        <AliquotDerivativeDialog
          open={aliquotDialogOpen}
          onClose={() => {
            setAliquotDialogOpen(false);
            setCreatedSample(null);
          }}
          parentSampleId={createdSample.id}
          parentSampleName={createdSample.name}
          onSuccess={(result) => {
            setSuccess(`Aliquot/Derivative created successfully: ${result.name}`);
            setAliquotDialogOpen(false);
            setCreatedSample(null);
          }}
        />
      )}
    </Box>
  );
};

export default AccessioningForm;
