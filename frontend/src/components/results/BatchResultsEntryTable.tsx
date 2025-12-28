import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  TextField,
  Tooltip,
  IconButton,
} from '@mui/material';
import {
  Save as SaveIcon,
  ContentCopy as ContentCopyIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridRowParams, GridCellParams, GridRenderCellParams } from '@mui/x-data-grid';
import { apiService } from '../../services/apiService';

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

interface Test {
  id: string;
  name: string;
  status: string;
  analysis_id: string;
  sample_id: string;
}

interface Sample {
  id: string;
  name: string;
  container_id: string;
  row: number;
  column: number;
  qc_type?: string;
}

interface TestWithSample extends Test {
  sample: Sample;
  analysis_name?: string;
}

interface ResultData {
  [testId: string]: {
    [analyteId: string]: {
      raw_result: string;
      reported_result: string;
      qualifiers?: string;
      notes?: string;
    };
  };
}

interface ValidationError {
  test_id: string;
  analyte_id?: string;
  error: string;
}

interface BatchResultsEntryTableProps {
  batchId: string;
  tests: Test[];
  samples: Sample[];
  onResultsSaved: () => void;
}

const BatchResultsEntryTable: React.FC<BatchResultsEntryTableProps> = ({
  batchId,
  tests,
  samples,
  onResultsSaved,
}) => {
  const [analytesMap, setAnalytesMap] = useState<Map<string, Analyte[]>>(new Map());
  const [resultsData, setResultsData] = useState<ResultData>({});
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>([]);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [qcFailures, setQcFailures] = useState<any[]>([]);
  const [autoFillValue, setAutoFillValue] = useState<{ analyteId: string; value: string } | null>(null);

  // Get QC blocking config from env
  const failQcBlocksBatch = process.env.REACT_APP_FAIL_QC_BLOCKS_BATCH === 'true';

  // Build test-sample mapping
  const testsWithSamples = useMemo(() => {
    const sampleMap = new Map(samples.map(s => [s.id, s]));
    return tests.map(test => ({
      ...test,
      sample: sampleMap.get(test.sample_id) || samples[0],
    })) as TestWithSample[];
  }, [tests, samples]);

  // Group tests by analysis to load analytes
  const analysisIds = useMemo(() => {
    return Array.from(new Set(tests.map(t => t.analysis_id)));
  }, [tests]);

  useEffect(() => {
    loadAnalytes();
  }, [analysisIds]);

  const loadAnalytes = async () => {
    try {
      setLoading(true);
      const analytesMap = new Map<string, Analyte[]>();
      
      for (const analysisId of analysisIds) {
        try {
          const analytes = await apiService.getAnalysisAnalytes(analysisId);
          analytesMap.set(analysisId, analytes.sort((a: Analyte, b: Analyte) => a.display_order - b.display_order));
        } catch (err) {
          console.error(`Failed to load analytes for analysis ${analysisId}:`, err);
        }
      }
      
      setAnalytesMap(analytesMap);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load analytes');
    } finally {
      setLoading(false);
    }
  };

  // Get all unique analytes across all analyses
  const allAnalytes = useMemo(() => {
    const analyteSet = new Map<string, Analyte>();
    analytesMap.forEach((analytes) => {
      analytes.forEach(analyte => {
        if (!analyteSet.has(analyte.id)) {
          analyteSet.set(analyte.id, analyte);
        }
      });
    });
    return Array.from(analyteSet.values()).sort((a, b) => a.display_order - b.display_order);
  }, [analytesMap]);

  // Get analytes for a specific test
  const getAnalytesForTest = (test: TestWithSample): Analyte[] => {
    return analytesMap.get(test.analysis_id) || [];
  };

  // Check if sample is QC
  const isQCSample = (sample: Sample): boolean => {
    return !!sample.qc_type;
  };

  // Validate a single result
  const validateResult = (value: string, analyte: Analyte): string | null => {
    if (analyte.is_required && !value.trim()) {
      return `${analyte.reported_name} is required`;
    }

    if (value && analyte.data_type === 'numeric') {
      const numValue = parseFloat(value);
      if (isNaN(numValue)) {
        return `${analyte.reported_name} must be a valid number`;
      }
      if (analyte.low_value !== undefined && numValue < analyte.low_value) {
        return `${analyte.reported_name} is below minimum value (${analyte.low_value})`;
      }
      if (analyte.high_value !== undefined && numValue > analyte.high_value) {
        return `${analyte.reported_name} is above maximum value (${analyte.high_value})`;
      }
    }

    return null;
  };

  // Handle cell value change
  const handleCellChange = (testId: string, analyteId: string, field: 'raw_result' | 'reported_result', value: string) => {
    setResultsData(prev => {
      const newData = { ...prev };
      if (!newData[testId]) {
        newData[testId] = {};
      }
      if (!newData[testId][analyteId]) {
        newData[testId][analyteId] = {
          raw_result: '',
          reported_result: '',
        };
      }
      newData[testId][analyteId][field] = value;
      return newData;
    });

    // Real-time validation
    const test = testsWithSamples.find(t => t.id === testId);
    if (test) {
      const analytes = getAnalytesForTest(test);
      const analyte = analytes.find(a => a.id === analyteId);
      if (analyte) {
        const error = validateResult(value, analyte);
        setValidationErrors(prev => {
          const filtered = prev.filter(e => !(e.test_id === testId && e.analyte_id === analyteId));
          if (error) {
            return [...filtered, { test_id: testId, analyte_id: analyteId, error }];
          }
          return filtered;
        });
      }
    }
  };

  // Auto-fill common values
  const handleAutoFill = (analyteId: string, value: string) => {
    setAutoFillValue({ analyteId, value });
    setResultsData(prev => {
      const newData = { ...prev };
      testsWithSamples.forEach(test => {
        const analytes = getAnalytesForTest(test);
        if (analytes.some(a => a.id === analyteId)) {
          if (!newData[test.id]) {
            newData[test.id] = {};
          }
          if (!newData[test.id][analyteId]) {
            newData[test.id][analyteId] = {
              raw_result: '',
              reported_result: '',
            };
          }
          newData[test.id][analyteId].raw_result = value;
          newData[test.id][analyteId].reported_result = value;
        }
      });
      return newData;
    });
    setAutoFillValue(null);
  };

  // Get validation error for a cell
  const getCellError = (testId: string, analyteId: string): string | null => {
    const error = validationErrors.find(e => e.test_id === testId && e.analyte_id === analyteId);
    return error?.error || null;
  };

  // Build DataGrid columns
  const columns: GridColDef[] = useMemo(() => {
    const baseColumns: GridColDef[] = [
      {
        field: 'sample_name',
        headerName: 'Sample',
        width: 150,
        renderCell: (params: GridRenderCellParams) => {
          const test = params.row as TestWithSample;
          const isQC = isQCSample(test.sample);
          return (
            <Box>
              <Typography variant="body2" fontWeight={isQC ? 'bold' : 'normal'} color={isQC ? 'warning.main' : 'inherit'}>
                {test.sample.name}
              </Typography>
              {isQC && (
                <Chip label="QC" size="small" color="warning" sx={{ mt: 0.5 }} />
              )}
            </Box>
          );
        },
      },
      {
        field: 'test_name',
        headerName: 'Test',
        width: 200,
      },
      {
        field: 'position',
        headerName: 'Position',
        width: 100,
        renderCell: (params: GridRenderCellParams) => {
          const test = params.row as TestWithSample;
          return (
            <Chip
              label={`${test.sample.row},${test.sample.column}`}
              size="small"
              variant="outlined"
            />
          );
        },
      },
    ];

    // Add analyte columns
    allAnalytes.forEach(analyte => {
      baseColumns.push({
        field: `analyte_${analyte.id}`,
        headerName: analyte.reported_name,
        width: 200,
        renderHeader: () => (
          <Box>
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
            <Tooltip title="Auto-fill all rows">
              <IconButton
                size="small"
                onClick={() => {
                  const value = prompt(`Enter value to auto-fill for ${analyte.reported_name}:`);
                  if (value) {
                    handleAutoFill(analyte.id, value);
                  }
                }}
              >
                <ContentCopyIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        ),
        renderCell: (params: GridRenderCellParams) => {
          const test = params.row as TestWithSample;
          const testAnalytes = getAnalytesForTest(test);
          const hasAnalyte = testAnalytes.some(a => a.id === analyte.id);
          
          if (!hasAnalyte) {
            return <Typography variant="body2" color="text.secondary">N/A</Typography>;
          }

          const result = resultsData[test.id]?.[analyte.id];
          const cellError = getCellError(test.id, analyte.id);
          const isQC = isQCSample(test.sample);

          return (
            <Box sx={{ width: '100%' }}>
              <TextField
                fullWidth
                size="small"
                label="Raw Result"
                value={result?.raw_result || ''}
                onChange={(e) => handleCellChange(test.id, analyte.id, 'raw_result', e.target.value)}
                error={!!cellError}
                helperText={cellError || ''}
                type={analyte.data_type === 'numeric' ? 'number' : 'text'}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    backgroundColor: isQC ? 'warning.light' : 'inherit',
                  },
                }}
              />
              <TextField
                fullWidth
                size="small"
                label="Reported"
                value={result?.reported_result || ''}
                onChange={(e) => handleCellChange(test.id, analyte.id, 'reported_result', e.target.value)}
                sx={{ mt: 0.5 }}
              />
            </Box>
          );
        },
        editable: true,
      });
    });

    return baseColumns;
  }, [allAnalytes, resultsData, validationErrors, testsWithSamples]);

  // Prepare rows for DataGrid
  const rows = useMemo(() => {
    return testsWithSamples.map((test, index) => ({
      ...test,
      sample_name: test.sample.name,
      test_name: test.name || `Test ${index + 1}`,
      position: `${test.sample.row},${test.sample.column}`,
    }));
  }, [testsWithSamples]);

  // Validate all results before submit
  const validateAllResults = (): ValidationError[] => {
    const errors: ValidationError[] = [];
    
    testsWithSamples.forEach(test => {
      const analytes = getAnalytesForTest(test);
      analytes.forEach(analyte => {
        const result = resultsData[test.id]?.[analyte.id];
        const value = result?.raw_result || '';
        const error = validateResult(value, analyte);
        if (error) {
          errors.push({ test_id: test.id, analyte_id: analyte.id, error });
        }
      });
    });

    return errors;
  };

  // Handle submit
  const handleSubmit = async () => {
    try {
      setSaving(true);
      setError(null);
      setQcFailures([]);

      // Validate all results
      const errors = validateAllResults();
      if (errors.length > 0) {
        setValidationErrors(errors);
        setError(`Validation errors found: ${errors.length} error(s). Please fix before submitting.`);
        setSaving(false);
        return;
      }

      // Prepare request data
      const requestData = {
        batch_id: batchId,
        results: testsWithSamples.map(test => {
          const analytes = getAnalytesForTest(test);
          const analyteResults = analytes
            .filter(analyte => {
              const result = resultsData[test.id]?.[analyte.id];
              return result && (result.raw_result || result.reported_result);
            })
            .map(analyte => {
              const result = resultsData[test.id]?.[analyte.id];
              return {
                analyte_id: analyte.id,
                raw_result: result?.raw_result || null,
                reported_result: result?.reported_result || null,
                qualifiers: result?.qualifiers || null,
                notes: result?.notes || null,
              };
            });

          return {
            test_id: test.id,
            analyte_results: analyteResults,
          };
        }).filter(tr => tr.analyte_results.length > 0),
      };

      // Submit to API
      const response = await apiService.enterBatchResults(batchId, requestData);
      
      // Check for QC failures in response
      if (response.qc_failures && response.qc_failures.length > 0) {
        setQcFailures(response.qc_failures);
        if (failQcBlocksBatch) {
          setError('QC failures detected and blocking is enabled. Batch submission blocked.');
          setSaving(false);
          return;
        } else {
          // Show warning but allow submission
          setError(`Warning: ${response.qc_failures.length} QC failure(s) detected.`);
        }
      }

      // Success
      onResultsSaved();
      setResultsData({});
      setValidationErrors([]);
    } catch (err: any) {
      const errorDetail = err.response?.data?.detail;
      if (errorDetail?.errors) {
        setValidationErrors(errorDetail.errors);
        setError(`Validation errors: ${errorDetail.errors.length} error(s)`);
      } else if (errorDetail?.qc_failures) {
        setQcFailures(errorDetail.qc_failures);
        if (failQcBlocksBatch) {
          setError('QC failures detected and blocking is enabled. Batch submission blocked.');
        } else {
          setError(`Warning: ${errorDetail.qc_failures.length} QC failure(s) detected.`);
        }
      } else {
        setError(errorDetail?.message || errorDetail || 'Failed to save results');
      }
    } finally {
      setSaving(false);
      setConfirmDialogOpen(false);
    }
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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Bulk Results Entry</Typography>
        <Button
          variant="contained"
          startIcon={saving ? <CircularProgress size={20} /> : <SaveIcon />}
          onClick={() => setConfirmDialogOpen(true)}
          disabled={saving}
        >
          Submit Results
        </Button>
      </Box>

      {error && (
        <Alert 
          severity={qcFailures.length > 0 && failQcBlocksBatch ? 'error' : 'warning'} 
          sx={{ mb: 2 }}
          icon={qcFailures.length > 0 ? <WarningIcon /> : undefined}
        >
          {error}
          {qcFailures.length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="body2" fontWeight="bold">QC Failures:</Typography>
              {qcFailures.map((failure, idx) => (
                <Typography key={idx} variant="body2">- {failure.reason || failure.error}</Typography>
              ))}
            </Box>
          )}
        </Alert>
      )}

      {validationErrors.length > 0 && (
        <Alert severity="error" sx={{ mb: 2 }}>
          <Typography variant="body2" fontWeight="bold">
            Validation Errors ({validationErrors.length}):
          </Typography>
          {validationErrors.slice(0, 5).map((err, idx) => (
            <Typography key={idx} variant="body2">- {err.error}</Typography>
          ))}
          {validationErrors.length > 5 && (
            <Typography variant="body2">... and {validationErrors.length - 5} more</Typography>
          )}
        </Alert>
      )}

      <Card>
        <CardContent>
          <Box sx={{ height: 600, width: '100%' }}>
            <DataGrid
              rows={rows}
              columns={columns}
              pageSizeOptions={[10, 25, 50, 100]}
              initialState={{
                pagination: {
                  paginationModel: { pageSize: 25 },
                },
              }}
              getRowClassName={(params: GridRowParams) => {
                const test = params.row as TestWithSample;
                return isQCSample(test.sample) ? 'qc-row' : '';
              }}
              sx={{
                '& .qc-row': {
                  backgroundColor: 'warning.light',
                  '&:hover': {
                    backgroundColor: 'warning.main',
                  },
                },
              }}
            />
          </Box>
        </CardContent>
      </Card>

      <Dialog open={confirmDialogOpen} onClose={() => setConfirmDialogOpen(false)}>
        <DialogTitle>Confirm Submission</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to submit results for {testsWithSamples.length} test(s)?
            {validationErrors.length > 0 && (
              <Typography color="error" sx={{ mt: 1 }}>
                Warning: {validationErrors.length} validation error(s) found. Please fix before submitting.
              </Typography>
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleSubmit} variant="contained" disabled={validationErrors.length > 0}>
            Submit
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default BatchResultsEntryTable;

