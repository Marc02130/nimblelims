import React, { useState } from 'react';
import {
  Drawer,
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  useTheme,
  useMediaQuery,
  Toolbar,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Science as ScienceIcon,
  Inventory as InventoryIcon,
  ViewList as ViewListIcon,
  Assessment as AssessmentIcon,
  Settings as SettingsIcon,
  ExpandMore,
  People,
  Security,
  Biotech,
  BatteryChargingFull,
  Tune as TuneIcon,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useUser } from '../contexts/UserContext';
import Logo from './Logo';

const DRAWER_WIDTH = 240;

interface SidebarProps {
  mobileOpen: boolean;
  onMobileClose: () => void;
}

interface NavItem {
  text: string;
  path: string;
  icon: React.ReactNode;
  permission?: string;
  exact?: boolean;
}

interface AdminNavItem {
  text: string;
  path: string;
  icon: React.ReactNode;
  exact?: boolean;
}

const Sidebar: React.FC<SidebarProps> = ({ mobileOpen, onMobileClose }) => {
  const { user, hasPermission } = useUser();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  // Mobile breakpoint: <600px (sm breakpoint)
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [adminExpanded, setAdminExpanded] = useState(
    location.pathname.startsWith('/admin')
  );

  // Core Features navigation items
  const coreItems: NavItem[] = [
    {
      text: 'Dashboard',
      path: '/dashboard',
      icon: <DashboardIcon />,
      exact: true,
    },
    {
      text: 'Accessioning',
      path: '/accessioning',
      icon: <ScienceIcon />,
      permission: 'sample:create',
    },
    {
      text: 'Containers',
      path: '/containers',
      icon: <InventoryIcon />,
      permission: 'sample:update',
    },
    {
      text: 'Batches',
      path: '/batches',
      icon: <ViewListIcon />,
      permission: 'batch:manage',
    },
    {
      text: 'Results',
      path: '/results',
      icon: <AssessmentIcon />,
      permission: 'result:enter',
    },
    {
      text: 'Client Projects',
      path: '/client-projects',
      icon: <ViewListIcon />,
      permission: 'project:manage',
    },
  ];

  // Admin navigation items
  const adminItems: AdminNavItem[] = [
    {
      text: 'Overview',
      path: '/admin',
      icon: <DashboardIcon />,
      exact: true,
    },
    {
      text: 'Lists Management',
      path: '/admin/lists',
      icon: <ViewListIcon />,
    },
    {
      text: 'Container Types',
      path: '/admin/container-types',
      icon: <InventoryIcon />,
    },
    {
      text: 'Users Management',
      path: '/admin/users',
      icon: <People />,
    },
    {
      text: 'Roles & Permissions',
      path: '/admin/roles',
      icon: <Security />,
    },
    {
      text: 'Analyses Management',
      path: '/admin/analyses',
      icon: <ScienceIcon />,
    },
    {
      text: 'Analytes Management',
      path: '/admin/analytes',
      icon: <Biotech />,
    },
    {
      text: 'Test Batteries',
      path: '/admin/test-batteries',
      icon: <BatteryChargingFull />,
    },
    {
      text: 'Custom Fields',
      path: '/admin/custom-fields',
      icon: <TuneIcon />,
    },
  ];

  const handleNavigation = (path: string) => {
    navigate(path);
    if (isMobile) {
      onMobileClose();
    }
  };

  // Logout is handled in MainLayout AppBar

  const isActive = (path: string, exact?: boolean): boolean => {
    if (exact) {
      return location.pathname === path;
    }
    return location.pathname.startsWith(path);
  };

  const hasAdminAccess = hasPermission('config:edit');

  // Update admin accordion expanded state when route changes
  React.useEffect(() => {
    setAdminExpanded(location.pathname.startsWith('/admin'));
  }, [location.pathname]);

  const drawerContent = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Logo Section */}
      <Toolbar
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-start',
          px: 2,
          minHeight: '64px !important',
        }}
      >
        <Box
          onClick={() => handleNavigation('/dashboard')}
          sx={{
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
            '&:hover': { opacity: 0.8 },
          }}
          aria-label="Navigate to dashboard"
        >
          <Logo sx={{ mr: 1, fontSize: 32 }} />
          <Typography variant="h6" noWrap component="div">
            NimbleLIMS
          </Typography>
        </Box>
      </Toolbar>
      <Divider />

      {/* Core Features Section */}
      <List
        component="nav"
        aria-label="core features navigation"
        sx={{ flexGrow: 1, overflow: 'auto' }}
      >
        <ListItem disablePadding>
          <Typography
            variant="overline"
            sx={{ px: 2, py: 1, fontWeight: 600, color: 'text.secondary' }}
          >
            Core Features
          </Typography>
        </ListItem>
        {coreItems
          .filter((item) => !item.permission || hasPermission(item.permission))
          .map((item) => {
            const active = isActive(item.path, item.exact);
            return (
              <ListItem key={item.text} disablePadding>
                <ListItemButton
                  selected={active}
                  onClick={() => handleNavigation(item.path)}
                  aria-label={`Navigate to ${item.text}`}
                  aria-current={active ? 'page' : undefined}
                >
                  <ListItemIcon
                    sx={{
                      color: active ? 'primary.main' : 'inherit',
                      minWidth: 40,
                    }}
                  >
                    {item.icon}
                  </ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            );
          })}
        {/* Show message if no core items are visible */}
        {coreItems.filter((item) => !item.permission || hasPermission(item.permission)).length === 0 && (
          <ListItem disablePadding>
            <Typography variant="body2" sx={{ px: 2, py: 1, color: 'text.secondary', fontStyle: 'italic' }}>
              No items available
            </Typography>
          </ListItem>
        )}

        {/* Admin Section */}
        {hasAdminAccess && (
          <>
            <Divider sx={{ my: 1 }} />
            <Accordion
              expanded={adminExpanded}
              onChange={(_, expanded) => setAdminExpanded(expanded)}
              sx={{
                boxShadow: 'none',
                '&:before': { display: 'none' },
                '&.Mui-expanded': { margin: 0 },
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMore />}
                aria-label="Admin section"
                aria-controls="admin-navigation-content"
                sx={{
                  px: 2,
                  '& .MuiAccordionSummary-content': {
                    my: 0,
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 40 }}>
                  <SettingsIcon
                    color={location.pathname.startsWith('/admin') ? 'primary' : 'inherit'}
                  />
                </ListItemIcon>
                <Typography variant="body1" sx={{ fontWeight: 600 }}>
                  Admin
                </Typography>
              </AccordionSummary>
              <AccordionDetails sx={{ p: 0 }}>
                <List component="nav" aria-label="admin navigation">
                  {adminItems.map((item) => {
                    const active = isActive(item.path, item.exact);
                    return (
                      <ListItem key={item.text} disablePadding>
                        <ListItemButton
                          selected={active}
                          onClick={() => handleNavigation(item.path)}
                          sx={{ pl: 4 }}
                          aria-label={`Navigate to ${item.text}`}
                          aria-current={active ? 'page' : undefined}
                        >
                          <ListItemIcon
                            sx={{
                              color: active ? 'primary.main' : 'inherit',
                              minWidth: 40,
                            }}
                          >
                            {item.icon}
                          </ListItemIcon>
                          <ListItemText primary={item.text} />
                        </ListItemButton>
                      </ListItem>
                    );
                  })}
                </List>
              </AccordionDetails>
            </Accordion>
          </>
        )}
      </List>

      <Divider />

      {/* User Info Section */}
      <Box sx={{ p: 2 }}>
        <Typography
          variant="body2"
          sx={{ color: 'text.secondary', fontWeight: 500 }}
        >
          {user?.username} ({user?.role})
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Box
      component="nav"
      sx={{ width: { sm: DRAWER_WIDTH }, flexShrink: { sm: 0 } }}
      aria-label="main navigation"
    >
      {/* Mobile drawer */}
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={onMobileClose}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile
        }}
        sx={{
          display: { xs: 'block', sm: 'none' },
          '& .MuiDrawer-paper': {
            boxSizing: 'border-box',
            width: DRAWER_WIDTH,
          },
        }}
      >
        {drawerContent}
      </Drawer>

      {/* Desktop drawer */}
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
        {drawerContent}
      </Drawer>
    </Box>
  );
};

export default Sidebar;

