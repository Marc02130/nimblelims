import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  AccountCircle,
  Dashboard,
  Science,
  Inventory,
  Logout,
  ViewList,
  Assessment,
  Settings,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { useUser } from '../contexts/UserContext';

const Navbar: React.FC = () => {
  const { user, logout, hasPermission } = useUser();
  const navigate = useNavigate();
  const location = useLocation();
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);

  const handleMenu = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleLogout = () => {
    logout();
    handleClose();
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <AppBar position="static">
      <Toolbar>
        <Science sx={{ mr: 2 }} />
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          LIMS
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            color="inherit"
            startIcon={<Dashboard />}
            onClick={() => navigate('/dashboard')}
            sx={{ 
              bgcolor: isActive('/dashboard') ? 'rgba(255,255,255,0.1)' : 'transparent'
            }}
          >
            Dashboard
          </Button>
          
          {hasPermission('sample:create') && (
            <Button
              color="inherit"
              startIcon={<Science />}
              onClick={() => navigate('/accessioning')}
              sx={{ 
                bgcolor: isActive('/accessioning') ? 'rgba(255,255,255,0.1)' : 'transparent'
              }}
            >
              Accessioning
            </Button>
          )}
          
          {hasPermission('sample:update') && (
            <Button
              color="inherit"
              startIcon={<Inventory />}
              onClick={() => navigate('/containers')}
              sx={{ 
                bgcolor: isActive('/containers') ? 'rgba(255,255,255,0.1)' : 'transparent'
              }}
            >
              Containers
            </Button>
          )}

          {hasPermission('batch:manage') && (
            <Button
              color="inherit"
              startIcon={<ViewList />}
              onClick={() => navigate('/batches')}
              sx={{ 
                bgcolor: isActive('/batches') ? 'rgba(255,255,255,0.1)' : 'transparent'
              }}
            >
              Batches
            </Button>
          )}

          {hasPermission('result:enter') && (
            <Button
              color="inherit"
              startIcon={<Assessment />}
              onClick={() => navigate('/results')}
              sx={{ 
                bgcolor: isActive('/results') ? 'rgba(255,255,255,0.1)' : 'transparent'
              }}
            >
              Results
            </Button>
          )}

          {hasPermission('config:edit') && (
            <Button
              color="inherit"
              startIcon={<Settings />}
              onClick={() => navigate('/admin')}
              sx={{ 
                bgcolor: isActive('/admin') ? 'rgba(255,255,255,0.1)' : 'transparent'
              }}
            >
              Admin
            </Button>
          )}
        </Box>

        <Box sx={{ ml: 2 }}>
          <IconButton
            size="large"
            aria-label="account of current user"
            aria-controls="menu-appbar"
            aria-haspopup="true"
            onClick={handleMenu}
            color="inherit"
          >
            <AccountCircle />
          </IconButton>
          <Menu
            id="menu-appbar"
            anchorEl={anchorEl}
            anchorOrigin={{
              vertical: 'top',
              horizontal: 'right',
            }}
            keepMounted
            transformOrigin={{
              vertical: 'top',
              horizontal: 'right',
            }}
            open={Boolean(anchorEl)}
            onClose={handleClose}
          >
            <MenuItem disabled>
              <Typography variant="body2">
                {user?.username} ({user?.role})
              </Typography>
            </MenuItem>
            <MenuItem onClick={handleLogout}>
              <Logout sx={{ mr: 1 }} />
              Logout
            </MenuItem>
          </Menu>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

export default Navbar;
