/**
 * MainNav – central navigation structure for the app.
 * Used by the sidebar/navigation bar. Admin section includes sub-links
 * to Name Templates, Custom Attributes, and Lists (and other admin routes).
 * Admin routes are protected by config:edit (or other) permission in App routes.
 */

import React from 'react';
import {
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Box,
  Tooltip,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  Science as ScienceIcon,
  Inventory as InventoryIcon,
  ViewList as ViewListIcon,
  Assessment as AssessmentIcon,
  ExpandMore,
  People,
  Security,
  Biotech,
  BatteryChargingFull,
  Tune as TuneIcon,
  Help as HelpIcon,
  Straighten as StraightenIcon,
  Folder as FolderIcon,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useUser } from '../contexts/UserContext';

export interface NavItem {
  text: string;
  path: string;
  icon: React.ReactNode;
  permission?: string;
  exact?: boolean;
}

export interface AdminNavItem {
  text: string;
  path: string;
  icon: React.ReactNode;
  exact?: boolean;
}

/** Core nav items (Dashboard, Help) */
export const coreNavItems: NavItem[] = [
  { text: 'Dashboard', path: '/dashboard', icon: <DashboardIcon />, exact: true },
  { text: 'Help', path: '/help', icon: <HelpIcon /> },
];

/**
 * Admin section nav items. First three are the primary admin sub-links:
 * Name Templates, Custom Attributes, Lists. Then remaining admin routes.
 */
export const adminNavItems: AdminNavItem[] = [
  { text: 'Overview', path: '/admin', icon: <DashboardIcon />, exact: true },
  { text: 'Name Templates', path: '/admin/name-templates', icon: <TuneIcon /> },
  { text: 'Custom Attributes', path: '/admin/custom-attributes', icon: <TuneIcon /> },
  { text: 'Lists', path: '/admin/lists', icon: <ViewListIcon /> },
  { text: 'Container Types', path: '/admin/container-types', icon: <InventoryIcon /> },
  { text: 'Units Management', path: '/admin/units', icon: <StraightenIcon /> },
  { text: 'Users Management', path: '/admin/users', icon: <People /> },
  { text: 'Roles & Permissions', path: '/admin/roles', icon: <Security /> },
  { text: 'Analyses Management', path: '/admin/analyses', icon: <ScienceIcon /> },
  { text: 'Analytes Management', path: '/admin/analytes', icon: <Biotech /> },
  { text: 'Test Batteries', path: '/admin/test-batteries', icon: <BatteryChargingFull /> },
  { text: 'Custom Fields', path: '/admin/custom-fields', icon: <TuneIcon /> },
  { text: 'Custom Names', path: '/admin/custom-names', icon: <TuneIcon /> },
  { text: 'Help Management', path: '/admin/help', icon: <HelpIcon /> },
];

interface MainNavProps {
  /** Whether the sidebar is collapsed (icon-only) */
  collapsed?: boolean;
  /** Whether we're on mobile (affects tooltips / expand) */
  isMobile?: boolean;
  /** Callback when a link is chosen (e.g. close mobile drawer) */
  onNavigate?: () => void;
}

/**
 * Renders the Admin section of the main navigation (accordion with sub-links).
 * Use inside Sidebar/layout. Visibility is gated by config:edit.
 */
export const MainNavAdminSection: React.FC<MainNavProps> = ({
  collapsed = false,
  isMobile = false,
  onNavigate,
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { hasPermission } = useUser();
  const [adminExpanded, setAdminExpanded] = React.useState(location.pathname.startsWith('/admin'));

  React.useEffect(() => {
    setAdminExpanded(location.pathname.startsWith('/admin'));
  }, [location.pathname]);

  const hasAdminAccess = hasPermission('config:edit');
  if (!hasAdminAccess) return null;

  const isActive = (path: string, exact?: boolean) => {
    if (exact) return location.pathname === path;
    return location.pathname.startsWith(path);
  };

  const handleNav = (path: string) => {
    navigate(path);
    onNavigate?.();
  };

  return (
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
            '& .MuiAccordionSummary-content': { my: 0, justifyContent: collapsed ? 'center' : 'flex-start' },
          }}
        >
          <ListItemIcon sx={{ minWidth: collapsed ? 0 : 40, justifyContent: 'center' }}>
            {collapsed ? (
              <Tooltip title="Admin" placement="right" arrow>
                <Box sx={{ display: 'flex', color: location.pathname.startsWith('/admin') ? 'primary.main' : 'inherit' }}>
                  <TuneIcon />
                </Box>
              </Tooltip>
            ) : (
              <TuneIcon color={location.pathname.startsWith('/admin') ? 'primary' : 'inherit'} />
            )}
          </ListItemIcon>
          {!collapsed && (
            <Tooltip title="Admin" placement="right" arrow>
              <Typography variant="body1" sx={{ fontWeight: 600 }}>
                Admin
              </Typography>
            </Tooltip>
          )}
        </AccordionSummary>
        <AccordionDetails sx={{ p: 0 }}>
          <List component="nav" aria-label="admin navigation">
            {adminNavItems.map((item) => {
              const active = isActive(item.path, item.exact);
              const btn = (
                <ListItemButton
                  selected={active}
                  onClick={() => handleNav(item.path)}
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
                <ListItem key={item.path} disablePadding>
                  {collapsed ? (
                    <Tooltip title={item.text} placement="right" arrow>
                      {btn}
                    </Tooltip>
                  ) : (
                    btn
                  )}
                </ListItem>
              );
            })}
          </List>
        </AccordionDetails>
      </Accordion>
    </>
  );
};

/**
 * MainNav – provides the navigation structure and Admin section component.
 * Sidebar (or other layout) can use coreNavItems, adminNavItems, and MainNavAdminSection.
 */
const MainNav: React.FC = () => null;

export default MainNav;
