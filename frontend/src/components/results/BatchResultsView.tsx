import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  CircularProgress,
  Grid,
  Chip,
  Divider,
  FormControlLabel,
  Switch,
  Tooltip,
} from '@mui/material';
import {
  PlayArrow as PlayArrowIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import ResultsEntryTable from './ResultsEntryTable';
import BatchResultsEntryTable from './BatchResultsEntryTable';
import { apiService } from '../../services/apiService';
import { useUser } from '../../contexts/UserContext';

interface Batch {
  id: string;
  name: string;
  description?: string;
  status: string;
}

interface Test {
  id: string;
  name: string;
  status: string;
  analysis_id: string;
  sample_id: string;
  custom_attributes?: Record<string, any>;
}

interface Sample {
  id: string;
  name: string;
  container_id: string;
  row: number;
  column: number;
  qc_type?: string;
}

interface BatchResultsViewProps {
  batchId: string;
  onBack?: () => void;
}

const BatchResultsView: React.FC<BatchResultsViewProps> = ({ batchId, onBack }) => {
  const { user } = useUser();
  const isLabManager = user?.role === 'Lab Manager' || user?.role === 'lab-manager';
  const [batch, setBatch] = useState<Batch | null>(null);
  const [tests, setTests] = useState<Test[]>([]);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [selectedTest, setSelectedTest] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resultsSaved, setResultsSaved] = useState(false);
  const [bulkMode, setBulkMode] = useState(false);

  useEffect(() => {
    loadBatchData();
  }, [batchId]);

  const loadBatchData = async () => {
    try {
      setLoading(true);
      const [batchData, containersData] = await Promise.all([
        apiService.getBatch(batchId),
        apiService.getBatchContainers(batchId),
      ]);

      if (batchData) {
        setBatch(batchData);
      }

      // Extract samples from containers
      const allSamples: Sample[] = [];
      containersData.forEach((container: any) => {
        if (container.contents) {
          container.contents.forEach((content: any) => {
            allSamples.push({
              id: content.sample_id,
              name: content.sample_name,
              container_id: container.id,
              row: container.row,
              column: container.column,
              qc_type: content.sample?.qc_type || content.qc_type,
            });
          });
        }
      });
      setSamples(allSamples);

      // Load tests for the batch
      const testsData = await apiService.getTestsByBatch(batchId);
      setTests(testsData);

      if (testsData.length > 0) {
        setSelectedTest(testsData[0].id);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load batch data');
    } finally {
      setLoading(false);
    }
  };

  const handleTestChange = (testId: string) => {
    setSelectedTest(testId);
    setResultsSaved(false);
  };

  const handleResultsSaved = (results?: any[]) => {
    setResultsSaved(true);
    // Refresh batch data to get updated statuses
    loadBatchData();
  };

  const getTestStatusColor = (status: string) => {
    switch (status) {
      case 'In Process':
        return 'primary';
      case 'In Analysis':
        return 'warning';
      case 'Complete':
        return 'success';
      default:
        return 'default';
    }
  };

  const getBatchStatusColor = (status: string) => {
    switch (status) {
      case 'Created':
        return 'default';
      case 'In Process':
        return 'primary';
      case 'Completed':
        return 'success';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={3}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
        {onBack && (
          <Button onClick={onBack}>
            Back
          </Button>
        )}
      </Box>
    );
  }

  return (
    <Box>
      {onBack && (
        <Button onClick={onBack} sx={{ mb: 2 }}>
          Back
        </Button>
      )}

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Tooltip
              title={isLabManager ? 'QC at batch: US-27. Review QC samples and validate results meet acceptance criteria.' : ''}
              arrow
            >
              <Typography variant="h5">{batch?.name}</Typography>
            </Tooltip>
            <Chip
              label={batch?.status}
              color={getBatchStatusColor(batch?.status || '') as any}
            />
          </Box>

          <Typography variant="body1" sx={{ mb: 2 }}>
            {batch?.description}
          </Typography>

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Typography variant="body2" color="text.secondary">
                <strong>Samples:</strong> {samples.length}
              </Typography>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Typography variant="body2" color="text.secondary">
                <strong>Tests:</strong> {tests.length}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6">Results Entry</Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <FormControlLabel
                control={
                  <Switch
                    checked={bulkMode}
                    onChange={(e) => {
                      setBulkMode(e.target.checked);
                      setResultsSaved(false);
                    }}
                  />
                }
                label="Bulk Entry Mode"
              />
            {resultsSaved && (
              <Chip
                icon={<CheckCircleIcon />}
                label="Results Saved"
                color="success"
                variant="outlined"
              />
            )}
            </Box>
          </Box>

          <Divider sx={{ mb: 2 }} />

          {bulkMode ? (
            tests.length > 0 && samples.length > 0 ? (
              <BatchResultsEntryTable
                batchId={batchId}
                tests={tests}
                samples={samples}
                onResultsSaved={handleResultsSaved}
              />
            ) : (
              <Box textAlign="center" py={4}>
                <Typography variant="body1" color="text.secondary">
                  No tests or samples found in this batch
                </Typography>
                      </Box>
            )
          ) : (
            <>
          {selectedTest && samples.length > 0 && (
            <ResultsEntryTable
              batchId={batchId}
              testId={selectedTest}
              samples={samples}
              test={tests.find((t) => t.id === selectedTest)}
              onResultsSaved={handleResultsSaved}
            />
          )}

          {samples.length === 0 && (
            <Box textAlign="center" py={4}>
              <Typography variant="body1" color="text.secondary">
                No samples found in this batch
              </Typography>
            </Box>
          )}

          {!selectedTest && (
            <Box textAlign="center" py={4}>
              <Typography variant="body1" color="text.secondary">
                Select a test to enter results
              </Typography>
            </Box>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </Box>
  );
};

export default BatchResultsView;
