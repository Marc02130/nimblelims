import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
} from '@mui/material';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import EditIcon from '@mui/icons-material/Edit';
import { useNavigate, useSearchParams } from 'react-router-dom';
import SampleForm from '../components/samples/SampleForm';
import { apiService } from '../services/apiService';
import { useUser } from '../contexts/UserContext';

interface Sample {
  id: string;
  name: string;
  description?: string;
  status: string;
  sample_type: string;
  matrix: string;
  project_id: string;
  due_date?: string;
  received_date?: string;
  created_at: string;
  modified_at?: string;
  status_name?: string;
  sample_type_name?: string;
  matrix_name?: string;
  project_name?: string;
}

const SamplesManagement: React.FC = () => {
  const { hasPermission } = useUser();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [samples, setSamples] = useState<Sample[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSample, setSelectedSample] = useState<Sample | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [lookupData, setLookupData] = useState({
    sampleTypes: [],
    statuses: [],
    matrices: [],
    qcTypes: [],
    projects: [],
  });

  const canUpdate = hasPermission('sample:update');

  useEffect(() => {
    loadData();
  }, [searchParams]);

  const loadData = async () => {
    try {
      setLoading(true);
      // Get project_id from URL query parameters
      const projectId = searchParams.get('project_id') || undefined;
      
      // Build filters object
      const filters: { project_id?: string } = {};
      if (projectId) {
        filters.project_id = projectId;
      }

      const [samplesResponse, sampleTypes, statuses, matrices, qcTypes, projectsResponse] = await Promise.all([
        apiService.getSamples(filters),
        apiService.getListEntries('sample_types'),
        apiService.getListEntries('sample_status'),
        apiService.getListEntries('matrix_types'),
        apiService.getListEntries('qc_types'),
        apiService.getProjects(),
      ]);

      // Handle paginated response - extract samples array
      const samplesData = Array.isArray(samplesResponse) ? samplesResponse : (samplesResponse.samples || []);
      
      // Handle paginated projects response
      const projects = projectsResponse.projects || projectsResponse || [];

      // Enrich samples with names for display
      const enrichedSamples = samplesData.map((sample: any) => ({
        ...sample,
        status_name: statuses.find((s: any) => s.id === sample.status)?.name || 'Unknown',
        sample_type_name: sampleTypes.find((t: any) => t.id === sample.sample_type)?.name || 'Unknown',
        matrix_name: matrices.find((m: any) => m.id === sample.matrix)?.name || 'Unknown',
        project_name: projects.find((p: any) => p.id === sample.project_id)?.name || 'Unknown',
      }));

      setSamples(enrichedSamples);
      setLookupData({ sampleTypes, statuses, matrices, qcTypes, projects });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load samples');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = async (sampleId: string) => {
    try {
      const sample = await apiService.getSample(sampleId);
      setSelectedSample(sample);
      setShowForm(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load sample');
    }
  };

  const handleUpdateSample = async (sampleData: any) => {
    if (!selectedSample) return;
    try {
      await apiService.updateSample(selectedSample.id, sampleData);
      await loadData(); // Reload data
      setShowForm(false);
      setSelectedSample(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update sample');
      throw err;
    }
  };

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', width: 200, flex: 1 },
    { 
      field: 'status_name', 
      headerName: 'Status', 
      width: 150,
    },
    { 
      field: 'sample_type_name', 
      headerName: 'Sample Type', 
      width: 150,
    },
    { 
      field: 'matrix_name', 
      headerName: 'Matrix', 
      width: 150,
    },
    { 
      field: 'project_name', 
      headerName: 'Project', 
      width: 200,
    },
    { 
      field: 'due_date', 
      headerName: 'Due Date', 
      width: 120,
      valueGetter: (value) => value ? new Date(value).toLocaleDateString() : '',
    },
    { 
      field: 'modified_at', 
      headerName: 'Last Modified', 
      width: 150,
      valueGetter: (value) => value ? new Date(value).toLocaleDateString() : '',
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 100,
      getActions: (params) => [
        <GridActionsCellItem
          icon={
            <Tooltip title="Edit sample">
              <EditIcon />
            </Tooltip>
          }
          label="Edit"
          onClick={() => handleEdit(params.id as string)}
          disabled={!canUpdate}
          aria-label={`Edit sample ${params.row.name}`}
        />,
      ],
    },
  ];

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          Samples Management
        </Typography>
        <Button
          variant="contained"
          onClick={() => navigate('/accessioning')}
          aria-label="Navigate to accessioning form"
        >
          Create Sample
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {!canUpdate && (
        <Alert severity="info" sx={{ mb: 2 }}>
          You have read-only access. Contact your administrator for update permissions.
        </Alert>
      )}

      <Card>
        <CardContent>
          <DataGrid
            rows={samples}
            columns={columns}
            pageSizeOptions={[10, 25, 50, 100]}
            initialState={{
              pagination: {
                paginationModel: { page: 0, pageSize: 25 },
              },
            }}
            sx={{ height: 600 }}
            disableRowSelectionOnClick
          />
        </CardContent>
      </Card>

      {/* Sample Form Dialog */}
      <Dialog
        open={showForm}
        onClose={() => {
          setShowForm(false);
          setSelectedSample(null);
        }}
        maxWidth="md"
        fullWidth
        aria-labelledby="sample-form-dialog-title"
      >
        <DialogTitle id="sample-form-dialog-title">
          Edit Sample: {selectedSample?.name}
        </DialogTitle>
        <DialogContent>
          <SampleForm
            sample={selectedSample || undefined}
            lookupData={lookupData}
            onSubmit={handleUpdateSample}
            onCancel={() => {
              setShowForm(false);
              setSelectedSample(null);
            }}
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default SamplesManagement;

