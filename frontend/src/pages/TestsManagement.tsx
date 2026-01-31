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
  Alert,
  CircularProgress,
  Tooltip,
} from '@mui/material';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import EditIcon from '@mui/icons-material/Edit';
import { useNavigate } from 'react-router-dom';
import TestForm from '../components/tests/TestForm';
import { apiService, addClientFilterIfNeeded } from '../services/apiService';
import { useUser } from '../contexts/UserContext';

interface Test {
  id: string;
  name: string;
  description?: string;
  status: string;
  sample_id: string;
  analysis_id: string;
  technician_id?: string;
  test_date?: string;
  review_date?: string;
  created_at: string;
  modified_at?: string;
  status_name?: string;
  sample_name?: string;
  analysis_name?: string;
  technician_name?: string;
}

const TestsManagement: React.FC = () => {
  const { hasPermission, user, isSystemClient, isAdmin } = useUser();
  const navigate = useNavigate();
  const [tests, setTests] = useState<Test[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTest, setSelectedTest] = useState<Test | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [lookupData, setLookupData] = useState<{
    statuses: any[];
    users: any[];
  }>({
    statuses: [],
    users: [],
  });

  const canUpdate = hasPermission('test:update');
  const canManageUsers = hasPermission('user:manage');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // Build filters - RLS will automatically filter, but we can add client_id for non-System clients
      const filters: Record<string, string | undefined> = {};
      const filteredFilters = addClientFilterIfNeeded(
        filters,
        user?.client_id,
        user?.role
      );
      
      const [testsData, statuses] = await Promise.all([
        apiService.getTests(filteredFilters),
        apiService.getListEntries('test_status'),
      ]);
      
      // Only try to get users if user has permission
      let users: any[] = [];
      if (canManageUsers) {
        try {
          users = await apiService.getUsers();
        } catch (err) {
          // Silently fail if users endpoint is not available
          console.warn('Users endpoint not available or access denied');
        }
      }

      // Enrich tests with names for display
      const enrichedTests = testsData.tests?.map((test: any) => ({
        ...test,
        status_name: statuses.find((s: any) => s.id === test.status)?.name || 'Unknown',
        sample_name: test.sample?.name || 'Unknown',
        analysis_name: test.analysis?.name || 'Unknown',
        technician_name: test.technician ? (test.technician.name || test.technician.username) : 'Unassigned',
      })) || [];

      setTests(enrichedTests);
      setLookupData({ statuses, users });
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('Access denied: You do not have permission to view these tests. Client users can only view tests for samples from their own client\'s projects.');
      } else if (err.response?.status === 404) {
        setError('No tests found. This may be due to access restrictions.');
      } else {
        setError(err.response?.data?.detail || 'Failed to load tests');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = async (testId: string) => {
    try {
      const test = await apiService.getTest(testId);
      setSelectedTest(test);
      setShowForm(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load test');
    }
  };

  const handleUpdateTest = async (testData: any) => {
    if (!selectedTest) return;
    try {
      await apiService.updateTest(selectedTest.id, testData);
      await loadData(); // Reload data
      setShowForm(false);
      setSelectedTest(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update test');
      throw err;
    }
  };

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Test Name', width: 200, flex: 1 },
    { 
      field: 'status_name', 
      headerName: 'Status', 
      width: 150,
    },
    { 
      field: 'sample_name', 
      headerName: 'Sample', 
      width: 150,
    },
    { 
      field: 'analysis_name', 
      headerName: 'Analysis', 
      width: 200,
    },
    { 
      field: 'technician_name', 
      headerName: 'Technician', 
      width: 150,
    },
    { 
      field: 'test_date', 
      headerName: 'Test Date', 
      width: 120,
      valueGetter: (value) => value ? new Date(value).toLocaleDateString() : '',
    },
    { 
      field: 'review_date', 
      headerName: 'Review Date', 
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
            <Tooltip title="Edit test">
              <EditIcon />
            </Tooltip>
          }
          label="Edit"
          onClick={() => handleEdit(params.id as string)}
          disabled={!canUpdate}
          aria-label={`Edit test ${params.row.name}`}
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
          Tests Management
        </Typography>
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
            rows={tests}
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

      {/* Test Form Dialog */}
      <Dialog
        open={showForm}
        onClose={() => {
          setShowForm(false);
          setSelectedTest(null);
        }}
        maxWidth="md"
        fullWidth
        aria-labelledby="test-form-dialog-title"
      >
        <DialogTitle id="test-form-dialog-title">
          Edit Test: {selectedTest?.name}
        </DialogTitle>
        <DialogContent>
          <TestForm
            test={selectedTest || undefined}
            lookupData={lookupData}
            onSubmit={handleUpdateTest}
            onCancel={() => {
              setShowForm(false);
              setSelectedTest(null);
            }}
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default TestsManagement;

