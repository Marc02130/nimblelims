import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  Chip,
} from '@mui/material';
import {
  Add,
  Edit,
  Delete,
  Visibility,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams, GridToolbar } from '@mui/x-data-grid';
import { useNavigate } from 'react-router-dom';
import { useUser } from '../contexts/UserContext';
import { apiService, addClientFilterIfNeeded } from '../services/apiService';
import ProjectForm from '../components/projects/ProjectForm';

interface Client {
  id: string;
  name: string;
}

interface ClientProject {
  id: string;
  name: string;
  client_id: string;
}

interface Project {
  id: string;
  name: string;
  description?: string;
  start_date: string;
  client_id: string;
  client_project_id?: string;
  status: string;
  active: boolean;
  created_at: string;
  modified_at: string;
  client?: Client;
  client_project?: ClientProject;
  status_name?: string;
  custom_attributes?: Record<string, any>;
}

const ProjectsManagement: React.FC = () => {
  const { hasPermission, user, isSystemClient, isAdmin } = useUser();
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [statuses, setStatuses] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null);
  const [paginationModel, setPaginationModel] = useState({ page: 0, pageSize: 10 });
  const [total, setTotal] = useState(0);

  const canManage = hasPermission('project:manage');

  useEffect(() => {
    loadLookupData();
  }, []);

  useEffect(() => {
    loadProjects();
  }, [paginationModel]);

  const loadLookupData = async () => {
    try {
      const [clientsData, statusesData] = await Promise.all([
        apiService.getClients(),
        apiService.getListEntries('project_status'),
      ]);
      setClients(clientsData || []);
      setStatuses(statusesData || []);
    } catch (err: any) {
      console.error('Failed to load lookup data:', err);
    }
  };

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Build filters - RLS will automatically filter, but we can add client_id for non-System clients
      const filters: Record<string, string | undefined> = {
        page: String(paginationModel.page + 1),
        size: String(paginationModel.pageSize),
      };
      
      // Add client_id filter for non-System clients (though RLS will also enforce this)
      const filteredFilters = addClientFilterIfNeeded(
        filters,
        user?.client_id,
        user?.role
      );
      
      const response = await apiService.getProjects(filteredFilters);

      // Handle paginated response
      if (response.projects) {
        // Enrich projects with status names
        const enrichedProjects = response.projects.map((project: any) => ({
          ...project,
          status_name: statuses.find((s: any) => s.id === project.status)?.name || 'Unknown',
        }));
        setProjects(enrichedProjects);
        setTotal(response.total || 0);
      } else {
        // Handle non-paginated response
        const enrichedProjects = (response || []).map((project: any) => ({
          ...project,
          status_name: statuses.find((s: any) => s.id === project.status)?.name || 'Unknown',
        }));
        setProjects(enrichedProjects);
        setTotal(enrichedProjects.length);
      }
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('Access denied: You do not have permission to view these projects. Client users can only view projects for their own client.');
      } else if (err.response?.status === 404) {
        setError('No projects found. This may be due to access restrictions.');
      } else {
        setError(err.response?.data?.detail || 'Failed to load projects');
      }
    } finally {
      setLoading(false);
    }
  };

  const getClientName = (clientId: string): string => {
    const client = clients.find((c) => c.id === clientId);
    return client?.name || 'Unknown';
  };

  const getClientProjectName = (clientProjectId?: string): string => {
    if (!clientProjectId) return '-';
    const project = projects.find((p) => p.client_project?.id === clientProjectId);
    return project?.client_project?.name || 'Unknown';
  };

  const handleCreate = async (data: {
    name: string;
    description?: string;
    start_date: string;
    client_id: string;
    client_project_id?: string;
    status: string;
    custom_attributes?: Record<string, any>;
  }) => {
    await apiService.createProject(data);
    await loadProjects();
  };

  const handleUpdate = async (data: {
    name: string;
    description?: string;
    start_date: string;
    client_id: string;
    client_project_id?: string;
    status: string;
    custom_attributes?: Record<string, any>;
  }) => {
    if (!selectedProject) return;
    await apiService.updateProject(selectedProject.id, data);
    await loadProjects();
    setSelectedProject(null);
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await apiService.deleteProject(deleteTarget.id);
      await loadProjects();
      setDeleteDialogOpen(false);
      setDeleteTarget(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete project');
    }
  };

  const handleEdit = (project: Project) => {
    setSelectedProject(project);
    setFormOpen(true);
  };

  const handleViewSamples = (projectId: string) => {
    navigate(`/samples?project_id=${projectId}`);
  };

  const columns: GridColDef[] = useMemo(() => [
    { 
      field: 'name', 
      headerName: 'Name', 
      width: 200, 
      flex: 1,
    },
    {
      field: 'status_name',
      headerName: 'Status',
      width: 150,
      renderCell: (params) => (
        <Chip
          label={params.value || 'Unknown'}
          size="small"
          color={params.row.active ? 'primary' : 'default'}
        />
      ),
    },
    {
      field: 'client',
      headerName: 'Client',
      width: 200,
      valueGetter: (value, row) => {
        if (row.client?.name) return row.client.name;
        return getClientName(row.client_id);
      },
    },
    {
      field: 'client_project',
      headerName: 'Client Project',
      width: 200,
      valueGetter: (value, row) => {
        if (row.client_project?.name) return row.client_project.name;
        return getClientProjectName(row.client_project_id);
      },
    },
    {
      field: 'start_date',
      headerName: 'Start Date',
      width: 120,
      valueGetter: (value) => value ? new Date(value).toLocaleDateString() : '',
    },
    {
      field: 'created_at',
      headerName: 'Created',
      width: 150,
      valueGetter: (value) => value ? new Date(value).toLocaleDateString() : '',
    },
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 150,
      getActions: (params: GridRowParams) => {
        const actions = [];
        
        // View samples button
        actions.push(
          <GridActionsCellItem
            icon={
              <Tooltip title="View related samples">
                <Visibility />
              </Tooltip>
            }
            label="View Samples"
            onClick={() => handleViewSamples(params.row.id)}
          />
        );

        // Edit button (requires permission)
        if (canManage) {
          actions.push(
            <GridActionsCellItem
              icon={
                <Tooltip title="Edit project">
                  <Edit />
                </Tooltip>
              }
              label="Edit"
              onClick={() => handleEdit(params.row)}
            />
          );

          // Delete button
          actions.push(
            <GridActionsCellItem
              icon={
                <Tooltip title="Delete project">
                  <Delete />
                </Tooltip>
              }
              label="Delete"
              onClick={() => {
                setDeleteTarget(params.row);
                setDeleteDialogOpen(true);
              }}
            />
          );
        }

        return actions;
      },
    },
  ], [canManage, clients, projects, statuses]);

  if (loading && projects.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom>
            Projects
          </Typography>
          <Tooltip title="Internal Projects: Core lab tracking units">
            <Typography variant="body2" color="text.secondary">
              Manage internal projects for sample tracking and workflow management
            </Typography>
          </Tooltip>
        </Box>
        {canManage && (
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => {
              setSelectedProject(null);
              setFormOpen(true);
            }}
          >
            Create Project
          </Button>
        )}
      </Box>

      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {!isSystemClient() && !isAdmin() && user?.client_id && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Showing projects for your client only. System users and administrators see all projects.
        </Alert>
      )}

      <Box sx={{ width: '100%', overflowX: 'auto' }}>
        <DataGrid
          rows={projects}
          columns={columns}
          loading={loading}
          paginationMode="server"
          paginationModel={paginationModel}
          onPaginationModelChange={setPaginationModel}
          pageSizeOptions={[10, 25, 50, 100]}
          rowCount={total}
          disableRowSelectionOnClick
          slots={{
            toolbar: GridToolbar,
          }}
          sx={{
            '& .MuiDataGrid-cell': {
              fontSize: '0.875rem',
            },
          }}
        />
      </Box>

      {/* Create/Edit Form Dialog */}
      <ProjectForm
        open={formOpen}
        project={selectedProject}
        onClose={() => {
          setFormOpen(false);
          setSelectedProject(null);
        }}
        onSubmit={selectedProject ? handleUpdate : handleCreate}
        existingNames={projects.map((p) => p.name).filter((name) => name !== selectedProject?.name)}
        clients={clients}
        statuses={statuses}
      />

      {/* Delete Confirmation Dialog */}
      {deleteTarget && (
        <Box
          component="div"
          sx={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: deleteDialogOpen ? 'flex' : 'none',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1300,
          }}
          onClick={() => setDeleteDialogOpen(false)}
        >
          <Box
            sx={{
              backgroundColor: 'white',
              padding: 3,
              borderRadius: 2,
              maxWidth: 400,
              width: '90%',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <Typography variant="h6" gutterBottom>
              Delete Project
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Are you sure you want to delete "{deleteTarget.name}"? This will soft-delete the project (set active=false).
            </Typography>
            <Box display="flex" justifyContent="flex-end" gap={1}>
              <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
              <Button variant="contained" color="error" onClick={handleDelete}>
                Delete
              </Button>
            </Box>
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default ProjectsManagement;
