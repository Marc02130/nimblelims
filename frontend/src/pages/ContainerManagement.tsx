import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
} from '@mui/material';
import { DataGrid, GridColDef, GridActionsCellItem } from '@mui/x-data-grid';
import EditIcon from '@mui/icons-material/Edit';
import { Tooltip } from '@mui/material';
import ContainerForm from '../components/containers/ContainerForm';
import ContainerDetails from '../components/containers/ContainerDetails';
import { apiService } from '../services/apiService';

interface Container {
  id: string;
  name: string;
  type_id: string;
  concentration: number;
  concentration_units: string;
  amount: number;
  amount_units: string;
  parent_container_id?: string;
  created_at: string;
  type?: {
    name: string;
    capacity: number;
    material: string;
  };
  contents?: Array<{
    id: string;
    sample_id: string;
    sample: {
      name: string;
      description: string;
    };
    concentration: number;
    concentration_units: string;
    amount: number;
    amount_units: string;
  }>;
}

const ContainerManagement: React.FC = () => {
  const [containers, setContainers] = useState<Container[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedContainer, setSelectedContainer] = useState<Container | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const [lookupData, setLookupData] = useState({
    containerTypes: [],
    units: [],
    samples: [],
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [containersData, containerTypes, units, samples] = await Promise.all([
        apiService.getContainers(),
        apiService.getContainerTypes(),
        apiService.getUnits(),
        apiService.getSamples(),
      ]);

      setContainers(containersData);
      setLookupData({ containerTypes, units, samples });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load containers');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateContainer = async (containerData: any) => {
    try {
      const newContainer = await apiService.createContainer(containerData);
      setContainers([...containers, newContainer]);
      setShowForm(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create container');
    }
  };

  const handleUpdateContainer = async (id: string, containerData: any) => {
    try {
      const updatedContainer = await apiService.updateContainer(id, containerData);
      setContainers(containers.map(c => c.id === id ? updatedContainer : c));
      setShowForm(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update container');
    }
  };

  const handleRowClick = (params: any) => {
    setSelectedContainer(params.row);
    setShowDetails(true);
  };

  const handleEdit = async (containerId: string) => {
    try {
      const container = await apiService.getContainer(containerId);
      setSelectedContainer(container);
      setShowForm(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load container');
    }
  };

  const columns: GridColDef[] = [
    { field: 'name', headerName: 'Name', width: 200, flex: 1 },
    { 
      field: 'type', 
      headerName: 'Type', 
      width: 150,
      valueGetter: (value, row) => row.type?.name || 'Unknown'
    },
    { 
      field: 'concentration', 
      headerName: 'Concentration', 
      width: 150,
      valueGetter: (value, row) => row.concentration ? `${row.concentration} ${row.concentration_units || ''}` : 'N/A'
    },
    { 
      field: 'amount', 
      headerName: 'Amount', 
      width: 150,
      valueGetter: (value, row) => row.amount ? `${row.amount} ${row.amount_units || ''}` : 'N/A'
    },
    { 
      field: 'contents_count', 
      headerName: 'Samples', 
      width: 100,
      valueGetter: (value, row) => row.contents?.length || 0
    },
    { 
      field: 'modified_at', 
      headerName: 'Last Modified', 
      width: 150,
      valueGetter: (value, row) => row.modified_at ? new Date(row.modified_at).toLocaleDateString() : new Date(row.created_at).toLocaleDateString()
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 100,
      getActions: (params) => [
        <GridActionsCellItem
          icon={
            <Tooltip title="Edit container">
              <EditIcon />
            </Tooltip>
          }
          label="Edit"
          onClick={() => handleEdit(params.id as string)}
          aria-label={`Edit container ${params.row.name}`}
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
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">
          Container Management
        </Typography>
        <Button
          variant="contained"
          onClick={() => setShowForm(true)}
        >
          Create Container
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Card>
        <CardContent>
          <DataGrid
            rows={containers}
            columns={columns}
            onRowClick={handleRowClick}
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

      {/* Container Form Dialog */}
      <Dialog
        open={showForm}
        onClose={() => setShowForm(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {selectedContainer ? `Edit Container: ${selectedContainer.name}` : 'Create Container'}
        </DialogTitle>
        <DialogContent>
          <ContainerForm
            container={selectedContainer}
            lookupData={lookupData}
            onSubmit={selectedContainer ? 
              (data) => handleUpdateContainer(selectedContainer.id, data) :
              handleCreateContainer
            }
            onCancel={() => {
              setShowForm(false);
              setSelectedContainer(null);
            }}
          />
        </DialogContent>
      </Dialog>

      {/* Container Details Dialog */}
      <Dialog
        open={showDetails}
        onClose={() => setShowDetails(false)}
        maxWidth="lg"
        fullWidth
      >
        <DialogTitle>Container Details</DialogTitle>
        <DialogContent>
          {selectedContainer && (
            <ContainerDetails
              container={selectedContainer}
              lookupData={lookupData}
              onEdit={() => {
                setShowDetails(false);
                setShowForm(true);
              }}
              onClose={() => setShowDetails(false)}
            />
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default ContainerManagement;
