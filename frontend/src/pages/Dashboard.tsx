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
import { formatCalendarDay } from '../utils/localDate';
import { FillHeightPage, FillHeightTable } from '../components/common/FillHeightPage';

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
    sampleTypes: Array<{ id: string; name: string }>;
    matrices: Array<{ id: string; name: string }>;
    qcTypes: Array<{ id: string; name: string }>;
  }>({
    statuses: [],
    projects: [],
    sampleTypes: [],
    matrices: [],
    qcTypes: [],
  });

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    loadSamples();
  }, [filters]);

  const loadData = async () => {
    try {
      // Samples carry list-entry ids only (no *_info objects), so the grid
      // needs these lists to show names. Optional lists fall back to [].
      const optional = (p: Promise<any>) => Promise.resolve(p).catch(() => []);
      const [statusesRaw, projectsResponse, sampleTypesRaw, matricesRaw, qcTypesRaw] = await Promise.all([
        apiService.getListEntries('sample_status'),  // Use normalized slug format
        apiService.getProjects(),
        optional(apiService.getListEntries('sample_types')),
        optional(apiService.getListEntries('matrix_types')),
        optional(apiService.getListEntries('qc_types')),
      ]);

      // Ensure arrays for .map() – API may return objects or paginated shape
      const asArray = (raw: any) => (Array.isArray(raw) ? raw : []);
      const statuses = asArray(statusesRaw);
      const projects = Array.isArray(projectsResponse?.projects)
        ? projectsResponse.projects
        : Array.isArray(projectsResponse)
          ? projectsResponse
          : [];

      setLookupData({
        statuses,
        projects,
        sampleTypes: asArray(sampleTypesRaw),
        matrices: asArray(matricesRaw),
        qcTypes: asArray(qcTypesRaw),
      });
    } catch (err: any) {
      setError('Failed to load filter data');
    }
  };

  const loadSamples = async () => {
    try {
      setLoading(true);
      const raw = await apiService.getSamples(filters);
      const samplesData = Array.isArray(raw) ? raw : (raw?.samples ?? []);
      setSamples(Array.isArray(samplesData) ? samplesData : []);
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
      valueGetter: (value, row) => row.sample_type_info?.name || getLookupName(row.sample_type, lookupData.sampleTypes)
    },
    { 
      field: 'matrix', 
      headerName: 'Matrix', 
      width: 120,
      valueGetter: (value, row) =>
        row.matrix_info?.name || (row.matrix ? getLookupName(row.matrix, lookupData.matrices) : '')
    },
    { 
      field: 'project', 
      headerName: 'Project', 
      width: 150,
      valueGetter: (value, row) => row.project?.name || getLookupName(row.project_id, lookupData.projects)
    },
    { 
      field: 'due_date', 
      headerName: 'Due Date', 
      width: 120,
      valueGetter: (value, row) => formatCalendarDay(row.due_date)
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
      valueGetter: (value, row) =>
        row.qc_type_info?.name || (row.qc_type ? getLookupName(row.qc_type, lookupData.qcTypes) : '')
    },
  ];

  return (
    <FillHeightPage
      header={
        <>
          <Typography variant="h4" gutterBottom>
            Dashboard
          </Typography>

          <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
            Welcome, {user?.username}. Manage your samples and track their progress.
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {/* Summary Cards */}
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card>
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Total Samples
                  </Typography>
                  <Typography variant="h5">
                    {samples.length}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card>
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    In Progress
                  </Typography>
                  <Typography variant="h5">
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
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Completed
                  </Typography>
                  <Typography variant="h5">
                    {samples.filter(s =>
                      getLookupName(s.status, lookupData.statuses) === 'Reported'
                    ).length}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Card>
                <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                  <Typography color="text.secondary" gutterBottom variant="body2">
                    Total Tests
                  </Typography>
                  <Typography variant="h5">
                    {samples.reduce((total, sample) => total + (sample.tests?.length || 0), 0)}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* Filters */}
          <Grid container spacing={2} alignItems="center">
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <FormControl fullWidth size="small">
                <InputLabel id="dashboard-status-filter-label">Status</InputLabel>
                <Select
                  labelId="dashboard-status-filter-label"
                  value={filters.status}
                  label="Status"
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
              <FormControl fullWidth size="small">
                <InputLabel id="dashboard-project-filter-label">Project</InputLabel>
                <Select
                  labelId="dashboard-project-filter-label"
                  value={filters.project_id}
                  label="Project"
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
        </>
      }
    >
      {loading && samples.length === 0 ? (
        <Box display="flex" justifyContent="center" alignItems="center" flex={1}>
          <CircularProgress />
        </Box>
      ) : (
        <FillHeightTable>
          <DataGrid
            rows={samples}
            columns={columns}
            loading={loading}
            pageSizeOptions={[10, 25, 50, 100]}
            initialState={{
              pagination: {
                paginationModel: { page: 0, pageSize: 25 },
              },
            }}
            disableRowSelectionOnClick
          />
        </FillHeightTable>
      )}
    </FillHeightPage>
  );
};

export default Dashboard;
