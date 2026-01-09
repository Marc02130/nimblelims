import React, { useState } from 'react';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Button,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import {
  Menu as MenuIcon,
  ArrowBack,
  Logout,
  ChevronLeft,
  ChevronRight,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useUser } from '../contexts/UserContext';
import Sidebar from '../components/Sidebar';

const DRAWER_WIDTH = 240;
const DRAWER_WIDTH_COLLAPSED = 56;

interface MainLayoutProps {
  children: React.ReactNode;
}

// Route title mapping
const getRouteTitle = (pathname: string): string => {
  const routeMap: Record<string, string> = {
    '/dashboard': 'Dashboard',
    '/accessioning': 'Accessioning',
    '/containers': 'Containers',
    '/batches': 'Batches',
    '/results': 'Results',
    '/clients': 'Clients',
    '/client-projects': 'Client Projects',
    '/admin': 'Admin Dashboard',
    '/admin/lists': 'Lists Management',
    '/admin/container-types': 'Container Types',
    '/admin/users': 'Users Management',
    '/admin/roles': 'Roles & Permissions',
    '/admin/analyses': 'Analyses Management',
    '/admin/analytes': 'Analytes Management',
    '/admin/test-batteries': 'Test Batteries',
    '/admin/custom-names': 'Custom Names Management',
  };

  // Check for nested routes (e.g., /admin/analyses/:id/analytes)
  if (pathname.startsWith('/admin/analyses/') && pathname.includes('/analytes')) {
    return 'Analysis Analytes Configuration';
  }

  // Check exact match first
  if (routeMap[pathname]) {
    return routeMap[pathname];
  }

  // Check prefix match for admin routes
  for (const [route, title] of Object.entries(routeMap)) {
    if (route !== '/admin' && pathname.startsWith(route)) {
      return title;
    }
  }

  return 'NimbleLIMS';
};

// Check if route should show back button
const shouldShowBackButton = (pathname: string): boolean => {
  // Show back button for nested routes (e.g., /admin/analyses/:id/analytes)
  if (pathname.match(/\/admin\/analyses\/[^/]+\/analytes/)) {
    return true;
  }
  return false;
};

// Get back button target
const getBackButtonTarget = (pathname: string): string => {
  if (pathname.match(/\/admin\/analyses\/[^/]+\/analytes/)) {
    return '/admin/analyses';
  }
  return '/dashboard';
};

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const { user, logout } = useUser();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  // Mobile breakpoint: <600px (sm breakpoint)
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [mobileOpen, setMobileOpen] = useState(false);
  
  // Sidebar collapsed state with localStorage persistence
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    const saved = localStorage.getItem('sidebarCollapsed');
    return saved ? JSON.parse(saved) : false;
  });

  const handleDrawerToggle = () => {
    if (isMobile) {
      setMobileOpen(!mobileOpen);
    } else {
      // Desktop: toggle collapsed state
      const newCollapsed = !sidebarCollapsed;
      setSidebarCollapsed(newCollapsed);
      localStorage.setItem('sidebarCollapsed', JSON.stringify(newCollapsed));
    }
  };

  const handleSidebarToggle = () => {
    const newCollapsed = !sidebarCollapsed;
    setSidebarCollapsed(newCollapsed);
    localStorage.setItem('sidebarCollapsed', JSON.stringify(newCollapsed));
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleBack = () => {
    const target = getBackButtonTarget(location.pathname);
    navigate(target);
  };

  const pageTitle = getRouteTitle(location.pathname);
  const showBackButton = shouldShowBackButton(location.pathname);
  
  // Calculate drawer width based on collapsed state (desktop only)
  const drawerWidth = isMobile ? DRAWER_WIDTH : (sidebarCollapsed ? DRAWER_WIDTH_COLLAPSED : DRAWER_WIDTH);

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <Sidebar 
        mobileOpen={mobileOpen} 
        onMobileClose={() => setMobileOpen(false)}
        collapsed={!isMobile && sidebarCollapsed}
      />

      {/* Main content area */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          display: 'flex',
          flexDirection: 'column',
          transition: theme.transitions.create(['width', 'margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
        }}
      >
        {/* Top AppBar */}
        <AppBar
          position="fixed"
          sx={{
            width: { sm: `calc(100% - ${drawerWidth}px)` },
            ml: { sm: `${drawerWidth}px` },
            zIndex: (theme) => theme.zIndex.drawer + 1,
            transition: theme.transitions.create(['width', 'margin'], {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
          }}
        >
          <Toolbar>
            {/* Mobile menu toggle */}
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2, display: { sm: 'none' } }}
            >
              <MenuIcon />
            </IconButton>

            {/* Desktop sidebar toggle */}
            {!isMobile && (
              <IconButton
                color="inherit"
                aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
                edge="start"
                onClick={handleSidebarToggle}
                sx={{ mr: 2, display: { xs: 'none', sm: 'flex' } }}
              >
                {sidebarCollapsed ? <ChevronRight /> : <ChevronLeft />}
              </IconButton>
            )}

            {/* Back button (for nested routes) */}
            {showBackButton && (
              <IconButton
                color="inherit"
                aria-label="go back"
                onClick={handleBack}
                sx={{ mr: 2 }}
              >
                <ArrowBack />
              </IconButton>
            )}

            {/* Page title */}
            <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
              {pageTitle}
            </Typography>

            {/* User info and logout */}
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="body2" sx={{ display: { xs: 'none', sm: 'block' } }}>
                {user?.username} ({user?.role})
              </Typography>
              <IconButton
                color="inherit"
                onClick={handleLogout}
                aria-label="logout"
              >
                <Logout />
              </IconButton>
            </Box>
          </Toolbar>
        </AppBar>

        {/* Main content */}
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 3,
            mt: '64px',
            width: '100%',
            overflow: 'auto',
          }}
        >
          {children}
        </Box>
      </Box>
    </Box>
  );
};

export default MainLayout;

