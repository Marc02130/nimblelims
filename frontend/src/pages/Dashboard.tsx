import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
  CircularProgress,
} from '@mui/material';
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { useUser } from '../contexts/UserContext';
import { apiService } from '../services/apiService';

interface Sample {
  id: string;
  name: string;
  description: string;
  status: string;
  sample_type: string;
  matrix: string;
  project_id: string;
  due_date: string;
  received_date: string;
  temperature: number;
  qc_type?: string;
  created_at: string;
  project?: {
    name: string;
  };
  status_info?: {
    name: string;
  };
  sample_type_info?: {
    name: string;
  };
  matrix_info?: {
    name: string;
  };
  qc_type_info?: {
    name: string;
  };
  tests?: Array<{
    id: string;
    status: string;
    analysis: {
      name: string;
    };
  }>;
}

const Dashboard: React.FC = () => {
  const { user } = useUser();
  const [samples, setSamples] = useState<Sample[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    status: '',
    project_id: '',
  });
  const [lookupData, setLookupData] = useState<{
    statuses: Array<{ id: string; name: string }>;
    projects: Array<{ id: string; name: string }>;
  }>({
    statuses: [],
    projects: [],
  });

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadSamples();
  }, [filters]);

  const loadData = async () => {
    try {
      const [statuses, projects] = await Promise.all([
        apiService.getListEntries('sample_status'),  // Use normalized slug format
        apiService.getProjects(),
      ]);

      setLookupData({ statuses, projects });
    } catch (err: any) {
      setError('Failed to load filter data');
    }
  };

  const loadSamples = async () => {
    try {
      setLoading(true);
      const samplesData = await apiService.getSamples(filters);
      setSamples(samplesData);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load samples');
    } finally {
      setLoading(false);
    }
  };

  const getLookupName = (id: string, list: any[]) => {
    const item = list.find(item => item.id === id);
    return item ? item.name : 'Unknown';
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'received':
        return 'default';
      case 'available for testing':
        return 'primary';
      case 'testing complete':
        return 'success';
      case 'reviewed':
        return 'info';
      case 'reported':
        return 'success';
      default:
        return 'default';
    }
  };

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Sample Name', width: 200 },
    { 
      field: 'status', 
      headerName: 'Status', 
      width: 150,
      renderCell: (params) => (
        <Chip
          label={getLookupName(params.row.status, lookupData.statuses)}
          color={getStatusColor(getLookupName(params.row.status, lookupData.statuses)) as any}
          size="small"
        />
      )
    },
    { 
      field: 'sample_type', 
      headerName: 'Type', 
      width: 150,
      valueGetter: (value, row) => getLookupName(row.sample_type, [])
    },
    { 
      field: 'matrix', 
      headerName: 'Matrix', 
      width: 120,
      valueGetter: (value, row) => getLookupName(row.matrix, [])
    },
    { 
      field: 'project', 
      headerName: 'Project', 
      width: 150,
      valueGetter: (value, row) => row.project?.name || 'Unknown'
    },
    { 
      field: 'due_date', 
      headerName: 'Due Date', 
      width: 120,
      valueGetter: (value, row) => new Date(row.due_date).toLocaleDateString()
    },
    { 
      field: 'temperature', 
      headerName: 'Temp (°C)', 
      width: 100,
      valueGetter: (value, row) => row.temperature
    },
    { 
      field: 'tests_count', 
      headerName: 'Tests', 
      width: 80,
      valueGetter: (value, row) => row.tests?.length || 0
    },
    { 
      field: 'qc_type', 
      headerName: 'QC', 
      width: 100,
      valueGetter: (value, row) => row.qc_type_info?.name || ''
    },
  ];

  if (loading && samples.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>
      
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Welcome, {user?.username}. Manage your samples and track their progress.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {/* Summary Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Samples
              </Typography>
              <Typography variant="h4">
                {samples.length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                In Progress
              </Typography>
              <Typography variant="h4">
                {samples.filter(s => 
                  getLookupName(s.status, lookupData.statuses) === 'Available for Testing' ||
                  getLookupName(s.status, lookupData.statuses) === 'Testing Complete'
                ).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Completed
              </Typography>
              <Typography variant="h4">
                {samples.filter(s => 
                  getLookupName(s.status, lookupData.statuses) === 'Reported'
                ).length}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Card>
            <CardContent>
              <Typography color="text.secondary" gutterBottom>
                Total Tests
              </Typography>
              <Typography variant="h4">
                {samples.reduce((total, sample) => total + (sample.tests?.length || 0), 0)}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Filters */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} alignItems="center">
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <FormControl fullWidth>
                <InputLabel>Status</InputLabel>
                <Select
                  value={filters.status}
                  onChange={(e) => setFilters({ ...filters, status: e.target.value })}
                >
                  <MenuItem value="">All Statuses</MenuItem>
                  {lookupData.statuses.map((status) => (
                    <MenuItem key={status.id} value={status.id}>
                      {status.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <FormControl fullWidth>
                <InputLabel>Project</InputLabel>
                <Select
                  value={filters.project_id}
                  onChange={(e) => setFilters({ ...filters, project_id: e.target.value })}
                >
                  <MenuItem value="">All Projects</MenuItem>
                  {lookupData.projects.map((project) => (
                    <MenuItem key={project.id} value={project.id}>
                      {project.name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Samples Table */}
      <Card>
        <CardContent>
          <DataGrid
            rows={samples}
            columns={columns}
            loading={loading}
            pageSizeOptions={[10, 25, 50]}
            initialState={{
              pagination: {
                paginationModel: { page: 0, pageSize: 10 },
              },
            }}
            sx={{ height: 600 }}
          />
        </CardContent>
      </Card>
    </Box>
  );
};

export default Dashboard;
