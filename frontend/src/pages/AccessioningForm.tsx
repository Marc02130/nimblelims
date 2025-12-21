import React, { useState, useEffect } from 'react';
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
} from '@mui/material';
import { Formik, Form } from 'formik';
import * as Yup from 'yup';
import SampleDetailsStep from '../components/accessioning/SampleDetailsStep';
import TestAssignmentStep from '../components/accessioning/TestAssignmentStep';
import ReviewStep from '../components/accessioning/ReviewStep';
import AliquotDerivativeDialog from '../components/aliquots/AliquotDerivativeDialog';
import { apiService } from '../services/apiService';
import { useUser } from '../contexts/UserContext';

const steps = ['Sample Details', 'Test Assignment', 'Review & Submit'];

interface SampleFormData {
  // Sample details
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
  qc_type: string;
  
  // Test assignment
  selected_analyses: string[];
  
  // Container assignment
  container_type: string;
  container_name: string;
  concentration: number;
  concentration_units: string;
  amount: number;
  amount_units: string;
  
  // Double entry validation
  double_entry_enabled: boolean;
  name_verification: string;
  sample_type_verification: string;
}

const initialValues: SampleFormData = {
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
  qc_type: '',
  selected_analyses: [],
  container_type: '',
  container_name: '',
  concentration: 0,
  concentration_units: '',
  amount: 0,
  amount_units: '',
  double_entry_enabled: false,
  name_verification: '',
  sample_type_verification: '',
};

const validationSchema = Yup.object({
  name: Yup.string().required('Sample name is required'),
  due_date: Yup.date().required('Due date is required'),
  received_date: Yup.date().required('Received date is required'),
  sample_type: Yup.string().required('Sample type is required'),
  status: Yup.string().required('Status is required'),
  matrix: Yup.string().required('Matrix is required'),
  temperature: Yup.number().required('Temperature is required'),
  project_id: Yup.string().required('Project is required'),
  container_type: Yup.string().required('Container type is required'),
  container_name: Yup.string().required('Container name is required'),
  concentration: Yup.number().min(0, 'Concentration must be positive'),
  amount: Yup.number().min(0, 'Amount must be positive'),
  concentration_units: Yup.string().required('Concentration units are required'),
  amount_units: Yup.string().required('Amount units are required'),
  name_verification: Yup.string().when('double_entry_enabled', {
    is: true,
    then: (schema) => schema.required('Name verification is required for double entry'),
    otherwise: (schema) => schema.notRequired(),
  }),
  sample_type_verification: Yup.string().when('double_entry_enabled', {
    is: true,
    then: (schema) => schema.required('Sample type verification is required for double entry'),
    otherwise: (schema) => schema.notRequired(),
  }),
});

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
    analyses: [],
    containerTypes: [],
    units: [],
  });

  const { user } = useUser();

  useEffect(() => {
    loadLookupData();
  }, []);

  const loadLookupData = async () => {
    try {
      const [
        sampleTypes,
        statuses,
        matrices,
        qcTypes,
        projects,
        analyses,
        containerTypes,
        units,
      ] = await Promise.all([
        apiService.getListEntries('sample_types'),
        apiService.getListEntries('statuses'),
        apiService.getListEntries('matrices'),
        apiService.getListEntries('qc_types'),
        apiService.getProjects(),
        apiService.getAnalyses(),
        apiService.getContainerTypes(),
        apiService.getUnits(),
      ]);

      setLookupData({
        sampleTypes,
        statuses,
        matrices,
        qcTypes,
        projects,
        analyses,
        containerTypes,
        units,
      });
    } catch (err) {
      setError('Failed to load form data');
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
      // Create sample
      const sampleData = {
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
        qc_type: values.qc_type,
      };

      const sample = await apiService.createSample(sampleData);

      // Create container
      const containerData = {
        name: values.container_name,
        type_id: values.container_type,
        concentration: values.concentration,
        concentration_units: values.concentration_units,
        amount: values.amount,
        amount_units: values.amount_units,
      };

      const container = await apiService.createContainer(containerData);

      // Link sample to container
      await apiService.createContent({
        container_id: container.id,
        sample_id: sample.id,
        concentration: values.concentration,
        concentration_units: values.concentration_units,
        amount: values.amount,
        amount_units: values.amount_units,
      });

      // Create tests for selected analyses
      for (const analysisId of values.selected_analyses) {
        await apiService.createTest({
          sample_id: sample.id,
          analysis_id: analysisId,
          status: 'In Process',
        });
      }

      setSuccess('Sample accessioned successfully!');
      setCreatedSample(sample);
      setAliquotDialogOpen(true);
      setActiveStep(0);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to accession sample');
    } finally {
      setLoading(false);
    }
  };

  const renderStepContent = (step: number, values: SampleFormData, setFieldValue: any) => {
    switch (step) {
      case 0:
        return (
          <SampleDetailsStep
            values={values}
            setFieldValue={setFieldValue}
            lookupData={lookupData}
          />
        );
      case 1:
        return (
          <TestAssignmentStep
            values={values}
            setFieldValue={setFieldValue}
            lookupData={lookupData}
          />
        );
      case 2:
        return (
          <ReviewStep
            values={values}
            lookupData={lookupData}
          />
        );
      default:
        return null;
    }
  };

  return (
    <Box sx={{ maxWidth: 800, margin: '0 auto', p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Sample Accessioning
      </Typography>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
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
          validationSchema={validationSchema}
          onSubmit={handleSubmit}
        >
          {({ values, setFieldValue, isValid }) => (
            <Form>
              {renderStepContent(activeStep, values, setFieldValue)}

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
                    {loading ? 'Submitting...' : 'Submit'}
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
          )}
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
