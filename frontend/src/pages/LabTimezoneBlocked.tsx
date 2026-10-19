import React from 'react';
import { Alert, Box, Button, Card, CardContent, Typography } from '@mui/material';
import { useUser } from '../contexts/UserContext';

const LabTimezoneBlocked: React.FC = () => {
  const { logout, user } = useUser();

  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        bgcolor: 'background.default',
      }}
    >
      <Card sx={{ maxWidth: 480, width: '100%', mx: 2 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" align="center" gutterBottom>
            Lab timezone required
          </Typography>
          <Alert severity="warning" sx={{ mb: 2 }}>
            The lab timezone hasn&apos;t been set. An administrator must set it
            before you can use the rest of the app.
          </Alert>
          <Typography variant="body2" color="text.secondary" align="center" sx={{ mb: 2 }}>
            {user?.username ? `Signed in as ${user.username}.` : null}
          </Typography>
          <Button fullWidth variant="outlined" onClick={logout}>
            Sign out
          </Button>
        </CardContent>
      </Card>
    </Box>
  );
};

export default LabTimezoneBlocked;
