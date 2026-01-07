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
  Tooltip,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Science as ScienceIcon,
  Inventory as InventoryIcon,
  ViewList as ViewListIcon,
  Assessment as AssessmentIcon,
  Settings as SettingsIcon,
  SettingsApplications as SettingsApplicationsIcon,
  ExpandMore,
  People,
  Security,
  Biotech,
  BatteryChargingFull,
  Business as BusinessIcon,
  Tune as TuneIcon,
  Help as HelpIcon,
  Straighten as StraightenIcon,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useUser } from '../contexts/UserContext';
import Logo from './Logo';

const DRAWER_WIDTH = 240;
const DRAWER_WIDTH_COLLAPSED = 56;

interface SidebarProps {
  mobileOpen: boolean;
  onMobileClose: () => void;
  collapsed?: boolean;
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

const Sidebar: React.FC<SidebarProps> = ({ mobileOpen, onMobileClose, collapsed = false }) => {
  const { user, hasPermission } = useUser();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();
  // Mobile breakpoint: <600px (sm breakpoint)
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const [adminExpanded, setAdminExpanded] = useState(
    location.pathname.startsWith('/admin')
  );
  const [clientExpanded, setClientExpanded] = useState(
    location.pathname.startsWith('/clients') || location.pathname.startsWith('/client-projects')
  );
  
  // Auto-expand accordions for /samples/ and /tests/ routes
  React.useEffect(() => {
    if (location.pathname.startsWith('/samples') || location.pathname.startsWith('/tests')) {
      // These are in core items, no accordion needed
    }
  }, [location.pathname]);

  // Collapse accordions when sidebar collapses
  React.useEffect(() => {
    if (collapsed) {
      setAdminExpanded(false);
      setClientExpanded(false);
    }
  }, [collapsed]);

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
      text: 'Samples',
      path: '/samples',
      icon: <ScienceIcon />,
      permission: 'sample:read',
    },
    {
      text: 'Tests',
      path: '/tests',
      icon: <Biotech />,
      permission: 'test:update',
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
      text: 'Help',
      path: '/help',
      icon: <HelpIcon />,
      // No permission required - visible to all users
    },
  ];

  // Client navigation items
  const clientItems: AdminNavItem[] = [
    {
      text: 'Clients',
      path: '/clients',
      icon: <People />,
    },
    {
      text: 'Client Projects',
      path: '/client-projects',
      icon: <ViewListIcon />,
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
      text: 'Units Management',
      path: '/admin/units',
      icon: <StraightenIcon />,
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
    {
      text: 'Help Management',
      path: '/admin/help',
      icon: <HelpIcon />,
    },
  ];

  const handleNavigation = (path: string) => {
    navigate(path);
    if (isMobile) {
      onMobileClose();
    }
    // Auto-expand accordions if collapsed sidebar and navigating to accordion item
    if (collapsed) {
      if (path.startsWith('/admin')) {
        setAdminExpanded(true);
      } else if (path.startsWith('/clients') || path.startsWith('/client-projects')) {
        setClientExpanded(true);
      }
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
  const hasClientAccess = hasPermission('project:manage');

  // Update accordion expanded states when route changes
  React.useEffect(() => {
    setAdminExpanded(location.pathname.startsWith('/admin'));
    setClientExpanded(
      location.pathname.startsWith('/clients') || location.pathname.startsWith('/client-projects')
    );
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
            justifyContent: collapsed ? 'center' : 'flex-start',
          }}
          aria-label="Navigate to dashboard"
        >
          <Logo sx={{ mr: collapsed ? 0 : 1, fontSize: 32 }} />
          {!collapsed && (
            <Typography variant="h6" noWrap component="div">
              NimbleLIMS
            </Typography>
          )}
        </Box>
      </Toolbar>
      <Divider />

      {/* Core Features Section */}
      <List
        component="nav"
        aria-label="core features navigation"
        sx={{ flexGrow: 1, overflow: 'auto' }}
      >
        {!collapsed && (
          <ListItem disablePadding>
            <Typography
              variant="overline"
              sx={{ px: 2, py: 1, fontWeight: 600, color: 'text.secondary' }}
            >
              Core Features
            </Typography>
          </ListItem>
        )}
        {coreItems
          .filter((item) => !item.permission || hasPermission(item.permission))
          .map((item) => {
            const active = isActive(item.path, item.exact);
            const listItemButton = (
              <ListItemButton
                selected={active}
                onClick={() => handleNavigation(item.path)}
                aria-label={`Navigate to ${item.text}`}
                aria-current={active ? 'page' : undefined}
                sx={{
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  minHeight: 48,
                }}
              >
                <ListItemIcon
                  sx={{
                    color: active ? 'primary.main' : 'inherit',
                    minWidth: collapsed ? 0 : 40,
                    justifyContent: 'center',
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                {!collapsed && <ListItemText primary={item.text} />}
              </ListItemButton>
            );
            
            return (
              <ListItem key={item.text} disablePadding>
                {collapsed ? (
                  <Tooltip title={item.text} placement="right" arrow>
                    {listItemButton}
                  </Tooltip>
                ) : (
                  listItemButton
                )}
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

        {/* Client Section */}
        {hasClientAccess && (
          <>
            <Divider sx={{ my: 1 }} />
            <Accordion
              expanded={clientExpanded}
              onChange={(_, expanded) => setClientExpanded(expanded)}
              sx={{
                boxShadow: 'none',
                '&:before': { display: 'none' },
                '&.Mui-expanded': { margin: 0 },
              }}
            >
              <AccordionSummary
                expandIcon={!collapsed ? <ExpandMore /> : null}
                aria-label="Client section"
                aria-controls="client-navigation-content"
                sx={{
                  px: 2,
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  '& .MuiAccordionSummary-content': {
                    my: 0,
                    justifyContent: collapsed ? 'center' : 'flex-start',
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: collapsed ? 0 : 40, justifyContent: 'center' }}>
                  <SettingsApplicationsIcon
                    color={
                      location.pathname.startsWith('/clients') || location.pathname.startsWith('/client-projects')
                        ? 'primary'
                        : 'inherit'
                    }
                  />
                </ListItemIcon>
                {!collapsed && (
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    Client
                  </Typography>
                )}
              </AccordionSummary>
              <AccordionDetails sx={{ p: 0 }}>
                <List component="nav" aria-label="client navigation">
                  {clientItems.map((item) => {
                    const active = isActive(item.path, item.exact);
                    const listItemButton = (
                      <ListItemButton
                        selected={active}
                        onClick={() => handleNavigation(item.path)}
                        sx={{ 
                          pl: collapsed ? 2 : 4,
                          justifyContent: collapsed ? 'center' : 'flex-start',
                          minHeight: 48,
                        }}
                        aria-label={`Navigate to ${item.text}`}
                        aria-current={active ? 'page' : undefined}
                      >
                        <ListItemIcon
                          sx={{
                            color: active ? 'primary.main' : 'inherit',
                            minWidth: collapsed ? 0 : 40,
                            justifyContent: 'center',
                          }}
                        >
                          {item.icon}
                        </ListItemIcon>
                        {!collapsed && <ListItemText primary={item.text} />}
                      </ListItemButton>
                    );
                    
                    return (
                      <ListItem key={item.text} disablePadding>
                        {collapsed ? (
                          <Tooltip title={item.text} placement="right" arrow>
                            {listItemButton}
                          </Tooltip>
                        ) : (
                          listItemButton
                        )}
                      </ListItem>
                    );
                  })}
                </List>
              </AccordionDetails>
            </Accordion>
          </>
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
                expandIcon={!collapsed ? <ExpandMore /> : null}
                aria-label="Admin section"
                aria-controls="admin-navigation-content"
                sx={{
                  px: 2,
                  justifyContent: collapsed ? 'center' : 'flex-start',
                  '& .MuiAccordionSummary-content': {
                    my: 0,
                    justifyContent: collapsed ? 'center' : 'flex-start',
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: collapsed ? 0 : 40, justifyContent: 'center' }}>
                  <SettingsIcon
                    color={location.pathname.startsWith('/admin') ? 'primary' : 'inherit'}
                  />
                </ListItemIcon>
                {!collapsed && (
                  <Typography variant="body1" sx={{ fontWeight: 600 }}>
                    Admin
                  </Typography>
                )}
              </AccordionSummary>
              <AccordionDetails sx={{ p: 0 }}>
                <List component="nav" aria-label="admin navigation">
                  {adminItems.map((item) => {
                    const active = isActive(item.path, item.exact);
                    const listItemButton = (
                      <ListItemButton
                        selected={active}
                        onClick={() => handleNavigation(item.path)}
                        sx={{ 
                          pl: collapsed ? 2 : 4,
                          justifyContent: collapsed ? 'center' : 'flex-start',
                          minHeight: 48,
                        }}
                        aria-label={`Navigate to ${item.text}`}
                        aria-current={active ? 'page' : undefined}
                      >
                        <ListItemIcon
                          sx={{
                            color: active ? 'primary.main' : 'inherit',
                            minWidth: collapsed ? 0 : 40,
                            justifyContent: 'center',
                          }}
                        >
                          {item.icon}
                        </ListItemIcon>
                        {!collapsed && <ListItemText primary={item.text} />}
                      </ListItemButton>
                    );
                    
                    return (
                      <ListItem key={item.text} disablePadding>
                        {collapsed ? (
                          <Tooltip title={item.text} placement="right" arrow>
                            {listItemButton}
                          </Tooltip>
                        ) : (
                          listItemButton
                        )}
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
      {!collapsed && (
        <Box sx={{ p: 2 }}>
          <Typography
            variant="body2"
            sx={{ color: 'text.secondary', fontWeight: 500 }}
          >
            {user?.username} ({user?.role})
          </Typography>
        </Box>
      )}
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
            width: collapsed ? DRAWER_WIDTH_COLLAPSED : DRAWER_WIDTH,
            overflowX: 'hidden',
            transition: theme.transitions.create('width', {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.enteringScreen,
            }),
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

