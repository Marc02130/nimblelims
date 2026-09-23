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
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { apiService, ApiService } from '../../../services/apiService';
import { useUser } from '../../../contexts/UserContext';
import { FillHeightPage, FillHeightTable } from '../../../components/common/FillHeightPage';
import SchemaChrome from './SchemaChrome';

const SchemaPrivileges: React.FC = () => {
  const { hasPermission } = useUser();
  const canEdit = hasPermission('schema:edit');
  const [roles, setRoles] = useState<Array<{ id: string; name: string }>>([]);
  const [tables, setTables] = useState<any[]>([]);
  const [roleId, setRoleId] = useState('');
  const [rows, setRows] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([apiService.getRoles(), apiService.getSchemaTables()])
      .then(([r, t]) => {
        const rolesList = Array.isArray(r) ? r : [];
        setRoles(rolesList);
        setTables(Array.isArray(t) ? t : []);
        if (rolesList[0]) setRoleId(rolesList[0].id);
      })
      .catch((e) => setError(ApiService.formatError(e, 'Failed to load')));
  }, []);

  const load = async () => {
    if (!roleId) return;
    try {
      const privs = await apiService.getSchemaPrivileges({ role_id: roleId });
      const byTable: Record<string, string> = {};
      (Array.isArray(privs) ? privs : [])
        .filter((p: any) => !p.column_id)
        .forEach((p: any) => {
          byTable[p.table_id] = p.access;
        });
      setRows(
        tables.map((t) => ({
          id: t.id,
          display_name: t.display_name,
          access: byTable[t.id] || 'none',
        })),
      );
      setError(null);
    } catch (err) {
      setError(ApiService.formatError(err, 'Failed to load privileges'));
    }
  };

  useEffect(() => {
    void load();
  }, [roleId, tables]);

  const columns: GridColDef[] = [
    { field: 'display_name', headerName: 'Table', flex: 1, minWidth: 180 },
    {
      field: 'access',
      headerName: 'Access',
      width: 180,
      renderCell: (params) => (
        <Select
          size="small"
          value={params.row.access}
          disabled={!canEdit}
          onChange={(e) => {
            const access = e.target.value as string;
            setRows((prev) =>
              prev.map((r) => (r.id === params.row.id ? { ...r, access } : r)),
            );
          }}
        >
          <MenuItem value="none">None</MenuItem>
          <MenuItem value="read">Read</MenuItem>
          <MenuItem value="write">Write</MenuItem>
        </Select>
      ),
    },
  ];

  const save = async () => {
    try {
      await apiService.putSchemaPrivileges(
        rows.map((r) => ({
          role_id: roleId,
          table_id: r.id,
          access: r.access,
        })),
      );
      setInfo('Privileges saved. This is not schema:edit and does not CREATE tables.');
      await load();
    } catch (err) {
      setError(ApiService.formatError(err, 'Could not save privileges'));
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
          <Box display="flex" gap={2} mb={1} alignItems="center">
            <FormControl size="small" sx={{ minWidth: 220 }}>
              <InputLabel>Role</InputLabel>
              <Select label="Role" value={roleId} onChange={(e) => setRoleId(e.target.value)}>
                {roles.map((r) => (
                  <MenuItem key={r.id} value={r.id}>
                    {r.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            {canEdit && (
              <Button variant="contained" onClick={() => void save()}>
                Save privileges
              </Button>
            )}
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Default deny. Missing row = no access. schema:edit is a separate permission —
            Write on Samples does not grant it. Layout membership is not this screen.
          </Typography>
        </SchemaChrome>
      }
    >
      <FillHeightTable>
        <DataGrid
          rows={rows}
          columns={columns}
          pageSizeOptions={[10, 25]}
          disableRowSelectionOnClick
        />
      </FillHeightTable>
    </FillHeightPage>
  );
};

export default SchemaPrivileges;
