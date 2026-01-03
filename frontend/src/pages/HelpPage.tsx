import React from 'react';
import { Box, Container, Typography, Paper, Divider } from '@mui/material';
import { useUser } from '../contexts/UserContext';
import ClientHelpSection from '../components/help/ClientHelpSection';

const HelpPage: React.FC = () => {
  const { user } = useUser();
  const isClient = user?.role === 'Client';

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Paper elevation={2} sx={{ p: 4 }}>
        {isClient ? (
          <ClientHelpSection />
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
              Note: Role-specific help content is available for Client users. If you need
              access to help content, please contact your administrator.
            </Typography>
          </Box>
        )}
      </Paper>
    </Container>
  );
};

export default HelpPage;

