import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material';
import { apiService } from '../../services/apiService';

interface AdminStats {
  listsCount: number;
  containerTypesCount: number;
  usersCount: number;
  analysesCount: number;
  analytesCount: number;
  rolesCount: number;
  batteriesCount: number;
}

const AdminOverview: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<AdminStats>({
    listsCount: 0,
    containerTypesCount: 0,
    usersCount: 0,
    analysesCount: 0,
    analytesCount: 0,
    rolesCount: 0,
    batteriesCount: 0,
  });

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);

      const [lists, containerTypes, users, analyses, analytes, roles, batteries] =
        await Promise.all([
          apiService.getLists(),
          apiService.getContainerTypes(),
          apiService.getUsers().catch(() => []),
          apiService.getAnalyses().catch(() => []),
          apiService.getAnalytes().catch(() => []),
          apiService.getRoles().catch(() => []),
          apiService.getTestBatteries().catch(() => ({ batteries: [], total: 0 })),
        ]);

      setStats({
        listsCount: lists?.length || 0,
        containerTypesCount: containerTypes?.length || 0,
        usersCount: users?.length || 0,
        analysesCount: analyses?.length || 0,
        analytesCount: analytes?.length || 0,
        rolesCount: roles?.length || 0,
        batteriesCount: batteries?.total || batteries?.batteries?.length || 0,
      });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load admin statistics');
    } finally {
      setLoading(false);
    }
  };

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Admin Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Manage system configurations, lists, and container types.
      </Typography>

      {loading ? (
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight="400px"
        >
          <CircularProgress />
        </Box>
      ) : (
        <Grid container spacing={3}>
          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Total Lists
                </Typography>
                <Typography variant="h4">{stats.listsCount}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Container Types
                </Typography>
                <Typography variant="h4">{stats.containerTypesCount}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Total Users
                </Typography>
                <Typography variant="h4">{stats.usersCount}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Analyses
                </Typography>
                <Typography variant="h4">{stats.analysesCount}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Analytes
                </Typography>
                <Typography variant="h4">{stats.analytesCount}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Roles
                </Typography>
                <Typography variant="h4">{stats.rolesCount}</Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid size={{ xs: 12, sm: 6, md: 4 }}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Test Batteries
                </Typography>
                <Typography variant="h4">{stats.batteriesCount}</Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}
    </Box>
  );
};

export default AdminOverview;

