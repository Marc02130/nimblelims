import React from 'react';
import { Box, Container, Typography, Paper, Divider, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import EditIcon from '@mui/icons-material/Edit';
import { useUser } from '../contexts/UserContext';
import ClientHelpSection from '../components/help/ClientHelpSection';
import LabTechHelpSection from '../components/help/LabTechHelpSection';
import LabManagerHelpSection from '../components/help/LabManagerHelpSection';
import AdminHelpSection from '../components/help/AdminHelpSection';

const HelpPage: React.FC = () => {
  const { user, hasPermission } = useUser();
  const navigate = useNavigate();
  const isClient = user?.role === 'Client';
  const isLabTechnician = user?.role === 'Lab Technician';
  const isLabManager = user?.role === 'Lab Manager' || user?.role === 'lab-manager';
  const isAdministrator = user?.role === 'Administrator';
  const canEdit = hasPermission('config:edit');

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper elevation={2} sx={{ p: 4 }}>
        {canEdit && (
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 2 }}>
            <Button
              variant="outlined"
              startIcon={<EditIcon />}
              onClick={() => navigate('/admin/help')}
              aria-label="Manage help entries"
            >
              Manage Help
            </Button>
          </Box>
        )}
        {isClient ? (
          <ClientHelpSection />
        ) : isLabTechnician ? (
          <LabTechHelpSection />
        ) : isLabManager ? (
          <LabManagerHelpSection />
        ) : isAdministrator ? (
          <AdminHelpSection />
        ) : (
          <Box>
            <Typography variant="h4" component="h1" gutterBottom>
              Help & Documentation
            </Typography>
            <Divider sx={{ my: 3 }} />
            <Typography variant="body1" paragraph>
              Welcome to the NimbleLIMS help center. This section provides documentation
              and guidance for laboratory users.
            </Typography>
            <Typography variant="body1" paragraph>
              For detailed help content, please contact your system administrator or refer
              to the system documentation.
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 3 }}>
              Note: Role-specific help content is available for Client, Lab Technician, Lab Manager, and Administrator users. 
              If you need access to help content, please contact your administrator.
            </Typography>
          </Box>
        )}
      </Paper>
    </Container>
  );
};

export default HelpPage;

