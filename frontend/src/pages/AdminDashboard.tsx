import React, { useState, useEffect } from 'react';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  Typography,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Card,
  CardContent,
  Grid,
  Alert,
  CircularProgress,
  IconButton,
  Divider,
  Button,
} from '@mui/material';
import {
  Settings,
  ViewList,
  Inventory,
  Menu as MenuIcon,
  Logout,
  Dashboard as DashboardIcon,
  ArrowBack,
  People,
  Security,
} from '@mui/icons-material';
import Logo from '../components/Logo';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useUser } from '../contexts/UserContext';
import { apiService } from '../services/apiService';

const DRAWER_WIDTH = 240;

interface ListSummary {
  id: string;
  name: string;
  entries_count: number;
}

interface ContainerTypeSummary {
  id: string;
  name: string;
}

const AdminDashboard: React.FC = () => {
  const { user, logout, hasPermission } = useUser();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    listsCount: 0,
    containerTypesCount: 0,
    usersCount: 0,
  });

  // Check permission on mount
  useEffect(() => {
    if (!hasPermission('config:edit')) {
      navigate('/dashboard', { replace: true });
    }
  }, [hasPermission, navigate]);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const [lists, containerTypes, users] = await Promise.all([
        apiService.getLists(),
        apiService.getContainerTypes(),
        apiService.getUsers().catch(() => []), // Users endpoint may not exist yet
      ]);

      setStats({
        listsCount: lists?.length || 0,
        containerTypesCount: containerTypes?.length || 0,
        usersCount: users?.length || 0,
      });
    } catch (err: any) {
      if (err.response?.status === 403) {
        setError('You do not have permission to access the admin section.');
        navigate('/dashboard', { replace: true });
      } else {
        setError(err.response?.data?.detail || 'Failed to load admin statistics');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleBackToDashboard = () => {
    navigate('/dashboard');
  };

  const menuItems = [
    {
      text: 'Overview',
      icon: <DashboardIcon />,
      path: '/admin',
      exact: true,
    },
    {
      text: 'Lists Management',
      icon: <ViewList />,
      path: '/admin/lists',
    },
    {
      text: 'Container Types',
      icon: <Inventory />,
      path: '/admin/container-types',
    },
    {
      text: 'Users Management',
      icon: <People />,
      path: '/admin/users',
    },
    {
      text: 'Roles & Permissions',
      icon: <Security />,
      path: '/admin/roles',
    },
  ];

  const drawer = (
    <Box>
      <Toolbar
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-start',
          px: [1],
        }}
      >
        <Settings sx={{ mr: 2 }} />
        <Typography 
          variant="h6" 
          noWrap 
          component="div"
          sx={{ 
            cursor: 'pointer',
            '&:hover': { opacity: 0.8 }
          }}
          onClick={handleBackToDashboard}
        >
          Admin
        </Typography>
      </Toolbar>
      <Divider />
      <List>
        {menuItems.map((item) => {
          const isActive = item.exact
            ? location.pathname === item.path
            : location.pathname.startsWith(item.path);
          
          return (
            <ListItem key={item.text} disablePadding>
              <ListItemButton
                selected={isActive}
                onClick={() => navigate(item.path)}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
    </Box>
  );

  if (!hasPermission('config:edit')) {
    return null; // Will redirect via useEffect
  }

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${DRAWER_WIDTH}px)` },
          ml: { sm: `${DRAWER_WIDTH}px` },
        }}
      >
        <Toolbar>
          <IconButton
            color="inherit"
            aria-label="open drawer"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
            <Logo sx={{ mr: 1, fontSize: 24 }} />
            <Typography variant="h6" noWrap component="div">
              Administration
            </Typography>
          </Box>
          <Button
            color="inherit"
            startIcon={<ArrowBack />}
            onClick={handleBackToDashboard}
            sx={{ mr: 2 }}
          >
            Back to Dashboard
          </Button>
          <Typography variant="body2" sx={{ mr: 2 }}>
            {user?.username} ({user?.role})
          </Typography>
          <IconButton color="inherit" onClick={handleLogout}>
            <Logout />
          </IconButton>
        </Toolbar>
      </AppBar>
      
      <Box
        component="nav"
        sx={{ width: { sm: DRAWER_WIDTH }, flexShrink: { sm: 0 } }}
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // Better open performance on mobile.
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
            },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: DRAWER_WIDTH,
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: `calc(100% - ${DRAWER_WIDTH}px)` },
          mt: '64px',
        }}
      >
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {location.pathname === '/admin' ? (
          <>
            <Typography variant="h4" gutterBottom>
              Admin Dashboard
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              Manage system configurations, lists, and container types.
            </Typography>

            {loading ? (
              <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
                <CircularProgress />
              </Box>
            ) : (
              <Grid container spacing={3}>
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Total Lists
                      </Typography>
                      <Typography variant="h4">
                        {stats.listsCount}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                
                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Container Types
                      </Typography>
                      <Typography variant="h4">
                        {stats.containerTypesCount}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>

                <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                  <Card>
                    <CardContent>
                      <Typography color="text.secondary" gutterBottom>
                        Total Users
                      </Typography>
                      <Typography variant="h4">
                        {stats.usersCount}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </Grid>
            )}
          </>
        ) : (
          <Outlet />
        )}
      </Box>
    </Box>
  );
};

export default AdminDashboard;

