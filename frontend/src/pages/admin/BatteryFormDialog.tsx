import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/apiService';
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
import { Formik, Form, Field, FieldProps } from 'formik';
import * as Yup from 'yup';
import AnalysisSelector from './AnalysisSelector';

interface BatteryAnalysis {
  analysis_id: string;
  analysis_name: string;
  analysis_method?: string;
  sequence: number;
  optional: boolean;
}

interface TestBattery {
  id: string;
  name: string;
  description?: string;
  analyses?: BatteryAnalysis[];
}

interface BatteryFormDialogProps {
  open: boolean;
  battery?: TestBattery | null;
  existingNames: string[];
  onClose: () => void;
  onSubmit: (data: {
    name: string;
    description?: string;
    analyses: BatteryAnalysis[];
  }) => Promise<void>;
}

const validationSchema = Yup.object({
  name: Yup.string()
    .required('Battery name is required')
    .min(2, 'Battery name must be at least 2 characters')
    .max(255, 'Battery name must be less than 255 characters')
    .test('unique', 'Battery name already exists', function (value) {
      if (!value) return true;
      const context = this.options.context as { existingNames: string[]; battery?: TestBattery | null } | undefined;
      if (!context || !context.existingNames) return true;
      const { existingNames, battery } = context;
      if (battery && battery.name === value) return true;
      return !existingNames.includes(value);
    }),
  description: Yup.string().max(500, 'Description must be less than 500 characters'),
  analyses: Yup.array()
    .of(
      Yup.object({
        analysis_id: Yup.string().required(),
        sequence: Yup.number().min(1).required(),
        optional: Yup.boolean().required(),
      })
    )
    .min(1, 'At least one analysis is required')
    .test('unique-analyses', 'Each analysis can only be added once', function (analyses) {
      if (!analyses) return true;
      const ids = analyses.map((a: any) => a.analysis_id);
      return new Set(ids).size === ids.length;
    })
    .test('sequential', 'Sequences must be sequential starting from 1', function (analyses) {
      if (!analyses || analyses.length === 0) return true;
      const sequences = analyses
        .map((a: any) => a.sequence)
        .sort((a: number, b: number) => a - b);
      for (let i = 0; i < sequences.length; i++) {
        if (sequences[i] !== i + 1) return false;
      }
      return true;
    }),
});

const BatteryFormDialog: React.FC<BatteryFormDialogProps> = ({
  open,
  battery,
  existingNames,
  onClose,
  onSubmit,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isEdit = !!battery;

  const [initialAnalyses, setInitialAnalyses] = useState<BatteryAnalysis[]>([]);
  const [loadingAnalyses, setLoadingAnalyses] = useState(false);

  useEffect(() => {
    if (open && battery) {
      // Load full battery data with analyses
      setLoadingAnalyses(true);
      apiService.getTestBattery(battery.id)
        .then((fullBattery) => {
          setInitialAnalyses(fullBattery.analyses || []);
        })
        .catch(() => {
          setInitialAnalyses(battery.analyses || []);
        })
        .finally(() => {
          setLoadingAnalyses(false);
        });
    } else if (open && !battery) {
      setInitialAnalyses([]);
    }
  }, [open, battery]);

  const handleSubmit = async (values: {
    name: string;
    description?: string;
    analyses: BatteryAnalysis[];
  }) => {
    try {
      setLoading(true);
      setError(null);
      
      // Ensure sequences are sequential
      const sortedAnalyses = [...values.analyses].sort((a, b) => a.sequence - b.sequence);
      const normalizedAnalyses = sortedAnalyses.map((a, index) => ({
        ...a,
        sequence: index + 1,
      }));
      
      await onSubmit({
        name: values.name,
        description: values.description || undefined,
        analyses: normalizedAnalyses,
      });
      
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save battery');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <Formik
        initialValues={{
          name: battery?.name || '',
          description: battery?.description || '',
          analyses: initialAnalyses,
        }}
        validationSchema={validationSchema}
        enableReinitialize
        onSubmit={handleSubmit}
        context={{ existingNames, battery }}
      >
        {({ values, errors, touched, handleChange, setFieldValue, isValid, dirty }) => (
          <Form>
            <DialogTitle>
              {isEdit ? 'Edit Test Battery' : 'Create Test Battery'}
            </DialogTitle>
            <DialogContent>
              {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {error}
                </Alert>
              )}

              {loadingAnalyses && isEdit && (
                <Alert severity="info" sx={{ mb: 2 }}>
                  Loading analyses...
                </Alert>
              )}

              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
                <Field name="name">
                  {({ field, meta }: FieldProps) => (
                    <TextField
                      {...field}
                      label="Battery Name"
                      fullWidth
                      required
                      error={meta.touched && !!meta.error}
                      helperText={meta.touched && meta.error}
                    />
                  )}
                </Field>

                <Field name="description">
                  {({ field, meta }: FieldProps) => (
                    <TextField
                      {...field}
                      label="Description"
                      fullWidth
                      multiline
                      rows={3}
                      error={meta.touched && !!meta.error}
                      helperText={meta.touched && meta.error}
                    />
                  )}
                </Field>

                <Divider />

                <Typography variant="h6" gutterBottom>
                  Analyses
                </Typography>

                <AnalysisSelector
                  selectedAnalyses={values.analyses}
                  onChange={(analyses) => setFieldValue('analyses', analyses)}
                  error={
                    touched.analyses && errors.analyses
                      ? typeof errors.analyses === 'string'
                        ? errors.analyses
                        : 'Invalid analyses configuration'
                      : undefined
                  }
                />
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={onClose} disabled={loading}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="contained"
                disabled={loading || !isValid || (!dirty && isEdit)}
              >
                {loading ? 'Saving...' : isEdit ? 'Update' : 'Create'}
              </Button>
            </DialogActions>
          </Form>
        )}
      </Formik>
    </Dialog>
  );
};

export default BatteryFormDialog;

