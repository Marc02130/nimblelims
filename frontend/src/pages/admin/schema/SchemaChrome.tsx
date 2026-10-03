import React from 'react';
import { Box, Tab, Tabs, Typography } from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import { useUser } from '../../../contexts/UserContext';

interface SchemaTab {
  label: string;
  path: string;
  /** When set, the tab is only offered to users holding this permission. */
  permission?: string;
}

const TABS: SchemaTab[] = [
  { label: 'Tables', path: '/admin/schema/tables' },
  { label: 'Columns', path: '/admin/schema/columns' },
  { label: 'Relations', path: '/admin/schema/relations', permission: 'schema:edit' },
  { label: 'Layouts', path: '/admin/schema/layouts' },
  { label: 'Privileges', path: '/admin/schema/privileges', permission: 'schema:edit' },
];

const SchemaChrome: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const { hasPermission } = useUser();
  const tabs = TABS.filter((t) => !t.permission || hasPermission(t.permission));
  const current = tabs.findIndex((t) => location.pathname.startsWith(t.path));

  return (
    <Box>
      <Typography variant="h4" sx={{ mb: 1 }}>
        Schema
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        A browser over the real database tables. A field is a column on a table; a link is a
        real foreign key. Layout is what a role sees. Privileges are what the API allows. Not on
        a layout is not shown — there is no hide toggle.
      </Typography>
      <Tabs
        value={current < 0 ? 0 : current}
        onChange={(_, i) => navigate(tabs[i].path)}
        sx={{ mb: 2 }}
      >
        {tabs.map((t) => (
          <Tab key={t.path} label={t.label} />
        ))}
      </Tabs>
      {children}
    </Box>
  );
};

export default SchemaChrome;
