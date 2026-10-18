import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Chip,
  Grid,
  FormControlLabel,
  Checkbox,
  Tooltip,
  IconButton,
} from '@mui/material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import {
  Save as SaveIcon,
  Check as CheckIcon,
} from '@mui/icons-material';
import { apiService } from '../../services/apiService';
import { useUser } from '../../contexts/UserContext';
import { apiErrorText } from '../../utils/apiErrorText';
import { localDateString } from '../../utils/localDate';

interface CustomAttributeConfig {
  id: string;
  entity_type: string;
  attr_name: string;
  data_type: 'text' | 'number' | 'date' | 'boolean' | 'select';
  validation_rules: Record<string, any>;
  description?: string;
  active: boolean;
}

interface Analyte {
  id: string;
  name: string;
  data_type: string;
  high_value?: number;
  low_value?: number;
  significant_figures?: number;
  is_required: boolean;
  default_value?: string;
  reported_name: string;
  display_order: number;
}

interface Result {
  id?: string;
  test_id: string;
  analyte_id: string;
  raw_result: string;
  reported_result: string;
  qualifiers?: string;
  calculated_result?: string;
  entry_date?: string;
  entered_by?: string;
}

interface Sample {
  id: string;
  name: string;
  container_id: string;
  row: number;
  column: number;
}

interface Test {
  id: string;
  sample_id: string;
  analysis_id?: string;
  custom_attributes?: Record<string, any>;
}

interface ResultsEntryTableProps {
  batchId: string;
  testId: string;
  samples: Sample[];
  test?: Test;
  onResultsSaved: (results: Result[]) => void;
  onTemplateApplied?: () => void;
}

const ResultsEntryTable: React.FC<ResultsEntryTableProps> = ({
  batchId,
  testId,
  samples,
  test,
  onResultsSaved,
  onTemplateApplied,
}) => {
  const { hasPermission } = useUser();
  const [analytes, setAnalytes] = useState<Analyte[]>([]);
  const [results, setResults] = useState<Result[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entryDate, setEntryDate] = useState(() => localDateString());
  const [success, setSuccess] = useState<string | null>(null);
  const [qualifiers, setQualifiers] = useState<any[]>([]);
  const [customAttributeConfigs, setCustomAttributeConfigs] = useState<CustomAttributeConfig[]>([]);
  const [loadingConfigs, setLoadingConfigs] = useState(false);
  const [workflowTemplates, setWorkflowTemplates] = useState<{ id: string; name: string }[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>('');
  const [applyTemplateLoading, setApplyTemplateLoading] = useState(false);
  const [applyTemplateError, setApplyTemplateError] = useState<string | null>(null);
  const [applyTemplateSuccess, setApplyTemplateSuccess] = useState<string | null>(null);

  const canExecuteWorkflow = hasPermission('workflow:execute');

  useEffect(() => {
    loadAnalytes();
    loadQualifiers();
    loadCustomAttributeConfigs();
  }, [testId, samples]);

  // Build the result rows once analytes have loaded. This used to run in the effect above,
  // before loadAnalytes resolved, so results stayed empty and typed values were dropped.
  useEffect(() => {
    initializeResults();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analytes, samples, testId]);

  useEffect(() => {
    if (!canExecuteWorkflow) return;
    apiService.getWorkflowTemplates({ active: true })
      .then((list) => setWorkflowTemplates(Array.isArray(list) ? list : []))
      .catch((err) => console.error('Failed to load workflow templates:', err));
  }, [canExecuteWorkflow]);

  const loadCustomAttributeConfigs = async () => {
    try {
      setLoadingConfigs(true);
      const response = await apiService.getCustomAttributeConfigs({
        entity_type: 'tests',
        active: true,
      });
      setCustomAttributeConfigs(response.configs || []);
    } catch (err: any) {
      console.error('Error loading custom attribute configs:', err);
    } finally {
      setLoadingConfigs(false);
    }
  };

  const loadAnalytes = async () => {
    try {
      setLoading(true);
      // Analytes belong to the test's analysis; the endpoint takes an analysis id, not a test id.
      const data = await apiService.getAnalysisAnalytes(test?.analysis_id ?? testId);
      setAnalytes(data.sort((a: Analyte, b: Analyte) => a.display_order - b.display_order));
    } catch (err: any) {
      setError(apiErrorText(err, 'Failed to load analytes'));
    } finally {
      setLoading(false);
    }
  };

  const loadQualifiers = async () => {
    try {
      const data = await apiService.getListEntries('qualifiers');
      setQualifiers(data);
    } catch (err) {
      console.error('Failed to load qualifiers:', err);
    }
  };

  const initializeResults = () => {
    // One test has one result per analyte. (Looping over samples too created duplicate
    // rows per analyte, and every duplicate was submitted.)
    const initialResults: Result[] = analytes.map(analyte => ({
      test_id: testId,
      analyte_id: analyte.id,
      raw_result: analyte.default_value || '',
      reported_result: '',
      qualifiers: '',
      calculated_result: '',
    }));
    setResults(initialResults);
  };

  const handleResultChange = (
    sampleId: string,
    analyteId: string,
    field: keyof Result,
    value: string
  ) => {
    setResults(prev => prev.map(result => {
      if (result.analyte_id === analyteId) {
        return { ...result, [field]: value };
      }
      return result;
    }));
  };

  const validateResult = (result: Result, analyte: Analyte): string[] => {
    const errors: string[] = [];

    if (analyte.is_required && !result.raw_result.trim()) {
      errors.push(`${analyte.reported_name} is required`);
    }

    if (result.raw_result && analyte.data_type === 'numeric') {
      const numValue = parseFloat(result.raw_result);
      if (isNaN(numValue)) {
        errors.push(`${analyte.reported_name} must be a valid number`);
      } else {
        if (analyte.low_value !== undefined && numValue < analyte.low_value) {
          errors.push(`${analyte.reported_name} is below minimum value (${analyte.low_value})`);
        }
        if (analyte.high_value !== undefined && numValue > analyte.high_value) {
          errors.push(`${analyte.reported_name} is above maximum value (${analyte.high_value})`);
        }
      }
    }

    return errors;
  };

  const handleSaveResults = async () => {
    try {
      setSaving(true);
      setError(null);
      setSuccess(null);

      // Validate all results
      const validationErrors: string[] = [];
      results.forEach(result => {
        const analyte = analytes.find(a => a.id === result.analyte_id);
        if (analyte) {
          const errors = validateResult(result, analyte);
          validationErrors.push(...errors);
        }
      });

      if (validationErrors.length > 0) {
        setError(`Validation errors: ${validationErrors.join(', ')}`);
        return;
      }

      // POST /results/batch expects {batch_id, results: [{test_id, analyte_results}]} (US-28).
      // The old flat {batch_id, test_id, results} body did not match and was rejected (422).
      const resultsData = {
        batch_id: batchId,
        results: [
          {
            test_id: testId,
            entry_date: entryDate !== '' ? entryDate : null,
            analyte_results: results
              .filter(result => result.raw_result || result.reported_result)
              .map(result => ({
                analyte_id: result.analyte_id,
                raw_result: result.raw_result || null,
                reported_result: result.reported_result || null,
                qualifiers: result.qualifiers || null,
              })),
          },
        ],
      };

      const savedResults = await apiService.enterBatchResults(batchId, resultsData);
      // Keep the entered rows: the response is not a Result[] (it can be an object or empty),
      // and replacing state with it broke the table (results.find on a non-array).
      onResultsSaved(savedResults);
      setSuccess('Results saved successfully');
    } catch (err: any) {
      setError(apiErrorText(err, 'Failed to save results'));
    } finally {
      setSaving(false);
    }
  };

  const handleApplyTemplate = async () => {
    if (!selectedTemplateId || !canExecuteWorkflow) return;
    setApplyTemplateLoading(true);
    setApplyTemplateError(null);
    setApplyTemplateSuccess(null);
    try {
      await apiService.executeWorkflow(selectedTemplateId, {
        context: { batch_id: batchId, test_id: testId },
      });
      setApplyTemplateSuccess('Workflow executed successfully.');
      setSelectedTemplateId('');
      onTemplateApplied?.();
    } catch (err: any) {
      setApplyTemplateError(err.response?.data?.detail || err.message || 'Failed to execute workflow');
    } finally {
      setApplyTemplateLoading(false);
    }
  };

  const getResultForSample = (sampleId: string, analyteId: string): Result | undefined => {
    return results.find(r => r.analyte_id === analyteId);
  };

  const getValidationErrors = (sampleId: string, analyteId: string): string[] => {
    const result = getResultForSample(sampleId, analyteId);
    const analyte = analytes.find(a => a.id === analyteId);
    if (result && analyte) {
      return validateResult(result, analyte);
    }
    return [];
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={3}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2, mb: 2 }}>
        <Typography variant="h6">Results Entry</Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <TextField
            label="Entry date"
            type="date"
            size="small"
            value={entryDate}
            onChange={(event) => setEntryDate(event.target.value)}
            InputLabelProps={{ shrink: true }}
            inputProps={{ max: localDateString() }}
            sx={{ width: 160 }}
          />
          {canExecuteWorkflow && workflowTemplates.length > 0 && (
            <>
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <InputLabel id="results-apply-template-label">Apply Template</InputLabel>
                <Select
                  labelId="results-apply-template-label"
                  value={selectedTemplateId}
                  label="Apply Template"
                  onChange={(e) => setSelectedTemplateId(e.target.value)}
                  disabled={applyTemplateLoading}
                >
                  <MenuItem value="">
                    <em>Select workflow...</em>
                  </MenuItem>
                  {workflowTemplates.map((t) => (
                    <MenuItem key={t.id} value={t.id}>
                      {t.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Button
                variant="outlined"
                onClick={handleApplyTemplate}
                disabled={!selectedTemplateId || applyTemplateLoading}
                startIcon={applyTemplateLoading ? <CircularProgress size={18} /> : null}
              >
                {applyTemplateLoading ? 'Running...' : 'Apply'}
              </Button>
            </>
          )}
          <Button
            variant="contained"
            startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
            onClick={handleSaveResults}
            disabled={saving}
          >
            Save Results
          </Button>
        </Box>
      </Box>

      {applyTemplateError && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setApplyTemplateError(null)}>
          {applyTemplateError}
        </Alert>
      )}
      {applyTemplateSuccess && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setApplyTemplateSuccess(null)}>
          {applyTemplateSuccess}
        </Alert>
      )}
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

      <Card>
        <CardContent>
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Sample</TableCell>
                  <TableCell>Position</TableCell>
                  {customAttributeConfigs.map((config) => (
                    <TableCell key={config.id}>
                      <Typography variant="body2" fontWeight="bold">
                        {config.attr_name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                      </Typography>
                      {config.description && (
                        <Typography variant="caption" color="text.secondary">
                          {config.description}
                        </Typography>
                      )}
                    </TableCell>
                  ))}
                  {analytes.map((analyte) => (
                    <TableCell key={analyte.id}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        <Box sx={{ flex: 1 }}>
                        <Typography variant="body2" fontWeight="bold">
                          {analyte.reported_name}
                        </Typography>
                        {analyte.is_required && (
                            <Chip label="Required" size="small" color="error" sx={{ mt: 0.5 }} />
                        )}
                        {analyte.data_type === 'numeric' && (
                            <Typography variant="caption" color="text.secondary" display="block">
                            {analyte.low_value !== undefined && `Min: ${analyte.low_value}`}
                            {analyte.high_value !== undefined && ` Max: ${analyte.high_value}`}
                          </Typography>
                        )}
                        </Box>
                        <Tooltip
                          title={`Analytes: Rules. ${analyte.is_required ? 'Required field. ' : ''}${analyte.data_type === 'numeric' ? `Numeric type with ${analyte.low_value !== undefined ? `minimum ${analyte.low_value}` : ''}${analyte.high_value !== undefined ? ` maximum ${analyte.high_value}` : ''}. ` : ''}${analyte.significant_figures != null ? `Significant figures: ${analyte.significant_figures}. ` : ''}Follow validation rules when entering results.`}
                          arrow
                          placement="top"
                        >
                          <IconButton
                            size="small"
                            aria-label={`${analyte.reported_name} analyte rules help`}
                            sx={{ p: 0.5 }}
                          >
                            <HelpOutlineIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {samples.map((sample) => {
                  const testForSample = test || ({} as Test);
                  const customAttrs = testForSample.custom_attributes || {};

                  return (
                    <TableRow key={sample.id}>
                      <TableCell>
                        <Typography variant="body2" fontWeight="bold">
                          {sample.name}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={`${sample.row},${sample.column}`}
                          size="small"
                          variant="outlined"
                        />
                      </TableCell>
                      {customAttributeConfigs.map((config) => {
                        const value = customAttrs[config.attr_name];
                        let displayValue: string = '';

                        if (value !== null && value !== undefined) {
                          switch (config.data_type) {
                            case 'boolean':
                              displayValue = value === true || value === 'true' ? 'Yes' : 'No';
                              break;
                            case 'date':
                              displayValue = typeof value === 'string' ? value : new Date(value).toLocaleDateString();
                              break;
                            case 'number':
                              displayValue = String(value);
                              break;
                            case 'select':
                              displayValue = String(value);
                              break;
                            default:
                              displayValue = String(value);
                          }
                        }

                        return (
                          <TableCell key={config.id}>
                            <Typography variant="body2" color={value ? 'text.primary' : 'text.secondary'}>
                              {displayValue || 'N/A'}
                            </Typography>
                          </TableCell>
                        );
                      })}
                      {analytes.map((analyte) => {
                        const result = getResultForSample(sample.id, analyte.id);
                        const validationErrors = getValidationErrors(sample.id, analyte.id);
                        const hasErrors = validationErrors.length > 0;

                        return (
                          <TableCell key={`${sample.id}-${analyte.id}`}>
                            <Box>
                              <TextField
                                fullWidth
                                size="small"
                                label="Raw Result"
                                value={result?.raw_result || ''}
                                onChange={(e) => handleResultChange(sample.id, analyte.id, 'raw_result', e.target.value)}
                                error={hasErrors}
                                helperText={hasErrors ? validationErrors[0] : ''}
                                type={analyte.data_type === 'numeric' ? 'number' : 'text'}
                              />
                              <TextField
                                fullWidth
                                size="small"
                                label="Reported Result"
                                value={result?.reported_result || ''}
                                onChange={(e) => handleResultChange(sample.id, analyte.id, 'reported_result', e.target.value)}
                                sx={{ mt: 1 }}
                              />
                              <FormControl fullWidth size="small" sx={{ mt: 1 }}>
                                <InputLabel id={`qualifiers-label-${sample.id}-${analyte.id}`}>Qualifiers</InputLabel>
                                <Select
                                  labelId={`qualifiers-label-${sample.id}-${analyte.id}`}
                                  label="Qualifiers"
                                  value={result?.qualifiers || ''}
                                  onChange={(e) => handleResultChange(sample.id, analyte.id, 'qualifiers', e.target.value)}
                                >
                                  <MenuItem value="">None</MenuItem>
                                  {qualifiers.map((qualifier) => (
                                    <MenuItem key={qualifier.id} value={qualifier.id}>
                                      {qualifier.name}
                                    </MenuItem>
                                  ))}
                                </Select>
                              </FormControl>
                            </Box>
                          </TableCell>
                        );
                      })}
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ResultsEntryTable;
