import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Typography,
} from '@mui/material';
import { apiService, ApiService } from '../../../services/apiService';
import { useUser } from '../../../contexts/UserContext';
import { FillHeightPage } from '../../../components/common/FillHeightPage';
import SchemaChrome from './SchemaChrome';

const SCREENS = [
  { key: 'receive', label: 'Receive' },
  { key: 'samples.list', label: 'Samples list' },
  { key: 'samples.detail', label: 'Samples detail' },
];

const SchemaLayouts: React.FC = () => {
  const { hasPermission } = useUser();
  const canEdit = hasPermission('layout:edit') || hasPermission('schema:edit');
  const [roles, setRoles] = useState<Array<{ id: string; name: string }>>([]);
  const [roleId, setRoleId] = useState('');
  const [screen, setScreen] = useState('samples.list');
  const [tables, setTables] = useState<Array<{ id: string }>>([]);
  const [available, setAvailable] = useState<any[]>([]);
  const [onLayout, setOnLayout] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    apiService
      .getRoles()
      .then((d) => {
        const list = Array.isArray(d) ? d : [];
        setRoles(list);
        if (list[0]) setRoleId(list[0].id);
      })
      .catch((e) => setError(ApiService.formatError(e, 'Failed to load roles')));
    apiService
      .getSchemaTables()
      .then((d) => setTables(Array.isArray(d) ? d : []))
      .catch(() => setTables([]));
  }, []);

  const load = async () => {
    if (!roleId || !tables.length) return;
    try {
      const samples = tables.find((t: any) => t.physical_name === 'samples') || tables[0];
      const [cols, layout] = await Promise.all([
        apiService.getSchemaColumns(samples.id),
        apiService.getSchemaLayout(roleId, screen),
      ]);
      const all = Array.isArray(cols) ? cols.filter((c: any) => c.status === 'active') : [];
      const fields = layout?.fields || [];
      const onIds = new Set(fields.map((f: any) => f.column_id));
      setOnLayout(fields);
      setAvailable(all.filter((c: any) => !onIds.has(c.id)));
      setError(null);
    } catch (err) {
      setError(ApiService.formatError(err, 'Failed to load layout'));
    }
  };

  useEffect(() => {
    void load();
  }, [roleId, screen, tables]);

  const add = (col: any) => {
    setOnLayout((prev) => [
      ...prev,
      { column_id: col.id, display_name: col.display_name, sort_order: prev.length },
    ]);
    setAvailable((prev) => prev.filter((c) => c.id !== col.id));
  };

  const remove = (field: any) => {
    setOnLayout((prev) => prev.filter((f) => f.column_id !== field.column_id));
    setAvailable((prev) => [
      ...prev,
      { id: field.column_id, display_name: field.display_name || field.column_id },
    ]);
  };

  const save = async () => {
    try {
      await apiService.putSchemaLayout({
        role_id: roleId,
        screen_key: screen,
        fields: onLayout.map((f, i) => ({
          column_id: f.column_id,
          sort_order: i,
          section: f.section,
        })),
      });
      setInfo('Layout saved. This does not change the database.');
      await load();
    } catch (err) {
      setError(ApiService.formatError(err, 'Could not save layout'));
    }
  };

  return (
    <FillHeightPage
      header={
        <SchemaChrome>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
          {info && (
            <Alert severity="info" sx={{ mb: 2 }} onClose={() => setInfo(null)}>
              {info}
            </Alert>
          )}
          <Box display="flex" gap={2} mb={2}>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>Role</InputLabel>
              <Select label="Role" value={roleId} onChange={(e) => setRoleId(e.target.value)}>
                {roles.map((r) => (
                  <MenuItem key={r.id} value={r.id}>
                    {r.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>Screen</InputLabel>
              <Select label="Screen" value={screen} onChange={(e) => setScreen(e.target.value)}>
                {SCREENS.map((s) => (
                  <MenuItem key={s.key} value={s.key}>
                    {s.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            {canEdit && (
              <Button variant="contained" onClick={() => void save()}>
                Save layout
              </Button>
            )}
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Membership only. Fields not added here are not shown. Read-only comes from
            privileges, not a hide toggle. Asked-for and routing are not layout screens.
          </Typography>
        </SchemaChrome>
      }
    >
      <Box display="flex" gap={3} px={1}>
        <Box flex={1}>
          <Typography variant="subtitle2">Available (this role can read)</Typography>
          {available.map((c) => (
            <Button key={c.id} fullWidth sx={{ justifyContent: 'flex-start' }} onClick={() => add(c)}>
              {c.display_name}
            </Button>
          ))}
        </Box>
        <Box flex={1}>
          <Typography variant="subtitle2">On this layout</Typography>
          {onLayout.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              No layout — default is all readable fields.
            </Typography>
          )}
          {onLayout.map((f) => (
            <Button
              key={f.column_id}
              fullWidth
              sx={{ justifyContent: 'flex-start' }}
              onClick={() => remove(f)}
            >
              {f.display_name || f.physical_name || f.column_id}
            </Button>
          ))}
        </Box>
      </Box>
    </FillHeightPage>
  );
};

export default SchemaLayouts;
