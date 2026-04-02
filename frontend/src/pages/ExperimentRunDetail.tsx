import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Chip,
  List,
  ListItem,
  ListItemText,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useNavigate, useParams } from 'react-router-dom';
import { apiService } from '../services/apiService';
import DoseResponseTab from './DoseResponse/DoseResponseTab';

interface RunDetail {
  id: string;
  name: string;
  description?: string;
  experiment_template_id: string;
  status: string;
  started_at?: string;
  completed_at?: string;
  published_at?: string;
  created_at: string;
  modified_at?: string;
}

const statusColor = (s: string) => {
  if (s === 'published') return 'success';
  if (s === 'running') return 'warning';
  if (s === 'complete') return 'info';
  if (s === 'failed') return 'error';
  return 'default';
};

const ExperimentRunDetail: React.FC = () => {
  const navigate = useNavigate();
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);
  const [dataRows, setDataRows] = useState<any[]>([]);
  const [dataLoading, setDataLoading] = useState(false);
  const [transitioning, setTransitioning] = useState(false);

  useEffect(() => {
    if (!runId) return;
    loadRun();
  }, [runId]);

  const loadRun = async () => {
    if (!runId) return;
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getExperimentRun(runId);
      setRun(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load run');
    } finally {
      setLoading(false);
    }
  };

  const loadData = async () => {
    if (!runId) return;
    setDataLoading(true);
    try {
      const res = await apiService.getExperimentRunData(runId, { page: 1, size: 200 });
      setDataRows(res?.data ?? []);
    } catch {
      // non-fatal
    } finally {
      setDataLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 1) loadData();
  }, [activeTab, runId]);

  const handleTransition = async (action: 'start' | 'review' | 'publish') => {
    if (!runId) return;
    setTransitioning(true);
    try {
      if (action === 'start') await apiService.startExperimentRun(runId);
      else if (action === 'review') await apiService.reviewExperimentRun(runId);
      else await apiService.publishExperimentRun(runId);
      await loadRun();
    } catch (err: any) {
      setError(err.response?.data?.detail || `Failed to ${action} run`);
    } finally {
      setTransitioning(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!run) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error || 'Run not found'}</Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/runs')} sx={{ mt: 2 }}>
          Back to Runs
        </Button>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/runs')} sx={{ mb: 2 }}>
        Back to Runs
      </Button>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
        <Typography variant="h4">{run.name}</Typography>
        <Chip label={run.status} color={statusColor(run.status) as any} />
      </Box>
      {run.description && (
        <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
          {run.description}
        </Typography>
      )}

      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        {run.status === 'draft' && (
          <Button
            variant="contained"
            color="primary"
            size="small"
            disabled={transitioning}
            onClick={() => handleTransition('start')}
          >
            Start Run
          </Button>
        )}
        {run.status === 'running' && (
          <Button
            variant="contained"
            color="warning"
            size="small"
            disabled={transitioning}
            onClick={() => handleTransition('review')}
          >
            Mark Ready for Review
          </Button>
        )}
        {run.status === 'complete' && (
          <Button
            variant="contained"
            color="success"
            size="small"
            disabled={transitioning}
            onClick={() => handleTransition('publish')}
          >
            Publish
          </Button>
        )}
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} variant="scrollable" scrollButtons="auto">
          <Tab label="Overview" />
          <Tab label="Data" />
          <Tab label="Dose Response" />
        </Tabs>
      </Box>

      {activeTab === 0 && (
        <Card variant="outlined" sx={{ mt: 2 }}>
          <CardContent>
            <List dense>
              <ListItem>
                <ListItemText primary="Status" secondary={run.status} />
              </ListItem>
              <ListItem>
                <ListItemText primary="Template ID" secondary={run.experiment_template_id} />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Started"
                  secondary={run.started_at ? new Date(run.started_at).toLocaleString() : '—'}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Completed"
                  secondary={run.completed_at ? new Date(run.completed_at).toLocaleString() : '—'}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Published"
                  secondary={run.published_at ? new Date(run.published_at).toLocaleString() : '—'}
                />
              </ListItem>
              <ListItem>
                <ListItemText
                  primary="Created"
                  secondary={new Date(run.created_at).toLocaleString()}
                />
              </ListItem>
            </List>
          </CardContent>
        </Card>
      )}

      {activeTab === 1 && (
        <Card variant="outlined" sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Imported Data ({dataRows.length} rows)
            </Typography>
            {dataLoading ? (
              <Box display="flex" justifyContent="center" py={3}>
                <CircularProgress />
              </Box>
            ) : dataRows.length === 0 ? (
              <Typography color="text.secondary">No data imported yet.</Typography>
            ) : (
              <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 400 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell>Well</TableCell>
                      <TableCell>Sample ID</TableCell>
                      <TableCell>Row Data</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {dataRows.map((row: any) => (
                      <TableRow key={row.id}>
                        <TableCell>{row.well_position ?? '—'}</TableCell>
                        <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                          {row.sample_id ?? '—'}
                        </TableCell>
                        <TableCell>
                          <Box component="pre" sx={{ m: 0, fontSize: '0.7rem', maxWidth: 400, overflow: 'auto' }}>
                            {JSON.stringify(row.row_data, null, 2)}
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>
      )}

      {activeTab === 2 && runId && (
        <DoseResponseTab runId={runId} runStatus={run.status} />
      )}
    </Box>
  );
};

export default ExperimentRunDetail;
