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
} from '@mui/material';
import {
  PlayArrow as PlayArrowIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import ResultsEntryTable from './ResultsEntryTable';
import { apiService } from '../../services/apiService';

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
}

interface Sample {
  id: string;
  name: string;
  container_id: string;
  row: number;
  column: number;
}

interface BatchResultsViewProps {
  batchId: string;
  onBack?: () => void;
}

const BatchResultsView: React.FC<BatchResultsViewProps> = ({ batchId, onBack }) => {
  const [batch, setBatch] = useState<Batch | null>(null);
  const [tests, setTests] = useState<Test[]>([]);
  const [samples, setSamples] = useState<Sample[]>([]);
  const [selectedTest, setSelectedTest] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [resultsSaved, setResultsSaved] = useState(false);

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

  const handleResultsSaved = (results: any[]) => {
    setResultsSaved(true);
    // Optionally refresh the data or show success message
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
            <Typography variant="h5">{batch?.name}</Typography>
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
            {resultsSaved && (
              <Chip
                icon={<CheckCircleIcon />}
                label="Results Saved"
                color="success"
                variant="outlined"
              />
            )}
          </Box>

          <Divider sx={{ mb: 2 }} />

          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <FormControl fullWidth>
                <InputLabel>Select Test</InputLabel>
                <Select
                  value={selectedTest}
                  onChange={(e) => handleTestChange(e.target.value)}
                >
                  {tests.map((test) => (
                    <MenuItem key={test.id} value={test.id}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="body2">{test.name}</Typography>
                        <Chip
                          label={test.status}
                          size="small"
                          color={getTestStatusColor(test.status) as any}
                        />
                      </Box>
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 12, sm: 6 }}>
              <Button
                variant="contained"
                startIcon={<PlayArrowIcon />}
                disabled={!selectedTest}
                onClick={() => {
                  // This could trigger analysis or other batch operations
                  console.log('Starting analysis for test:', selectedTest);
                }}
              >
                Start Analysis
              </Button>
            </Grid>
          </Grid>

          {selectedTest && samples.length > 0 && (
            <ResultsEntryTable
              batchId={batchId}
              testId={selectedTest}
              samples={samples}
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
        </CardContent>
      </Card>
    </Box>
  );
};

export default BatchResultsView;
