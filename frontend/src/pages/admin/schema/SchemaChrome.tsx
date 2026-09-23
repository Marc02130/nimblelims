import React from 'react';
import { Box, Tab, Tabs, Typography } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';

const TABS = [
  { label: 'Tables', path: '/admin/schema/tables' },
  { label: 'Columns', path: '/admin/schema/columns' },
  { label: 'Layouts', path: '/admin/schema/layouts' },
  { label: 'Privileges', path: '/admin/schema/privileges' },
];

const SchemaChrome: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const current = TABS.findIndex((t) => location.pathname.startsWith(t.path));

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Schema
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Real database tables and fields. Layout is what a role sees. Privileges are
        what the API allows. Not on a layout is not shown — there is no hide toggle.
      </Typography>
      <Tabs
        value={current < 0 ? 0 : current}
        onChange={(_, i) => navigate(TABS[i].path)}
        sx={{ mb: 2 }}
      >
        {TABS.map((t) => (
          <Tab key={t.path} label={t.label} />
        ))}
      </Tabs>
      {children}
    </Box>
  );
};

export default SchemaChrome;
