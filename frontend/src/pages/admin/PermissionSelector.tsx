import React from 'react';
import {
  Box,
  FormControlLabel,
  Checkbox,
  Typography,
  Paper,
  TextField,
  InputAdornment,
} from '@mui/material';
import { Search } from '@mui/icons-material';

interface Permission {
  id: string;
  name: string;
  description?: string;
}

interface PermissionSelectorProps {
  permissions: Permission[];
  selectedPermissionIds: string[];
  onChange: (selectedIds: string[]) => void;
}

const PermissionSelector: React.FC<PermissionSelectorProps> = ({
  permissions,
  selectedPermissionIds,
  onChange,
}) => {
  const [searchTerm, setSearchTerm] = React.useState('');

  const filteredPermissions = permissions.filter((permission) =>
    permission.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    permission.description?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleToggle = (permissionId: string) => {
    if (selectedPermissionIds.includes(permissionId)) {
      onChange(selectedPermissionIds.filter((id) => id !== permissionId));
    } else {
      onChange([...selectedPermissionIds, permissionId]);
    }
  };

  const handleSelectAll = () => {
    if (selectedPermissionIds.length === filteredPermissions.length) {
      onChange([]);
    } else {
      onChange(filteredPermissions.map((p) => p.id));
    }
  };

  // Group permissions by resource (e.g., "sample:", "result:", etc.)
  const groupedPermissions = React.useMemo(() => {
    const groups: Record<string, Permission[]> = {};
    filteredPermissions.forEach((permission) => {
      const [resource] = permission.name.split(':');
      if (!groups[resource]) {
        groups[resource] = [];
      }
      groups[resource].push(permission);
    });
    return groups;
  }, [filteredPermissions]);

  return (
    <Box>
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="subtitle2" color="text.secondary">
          {selectedPermissionIds.length} of {permissions.length} permissions selected
        </Typography>
        <FormControlLabel
          control={
            <Checkbox
              checked={selectedPermissionIds.length === filteredPermissions.length && filteredPermissions.length > 0}
              indeterminate={selectedPermissionIds.length > 0 && selectedPermissionIds.length < filteredPermissions.length}
              onChange={handleSelectAll}
            />
          }
          label="Select All"
        />
      </Box>

      <TextField
        fullWidth
        size="small"
        placeholder="Search permissions..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <Search />
            </InputAdornment>
          ),
        }}
        sx={{ mb: 2 }}
      />

      <Paper
        variant="outlined"
        sx={{
          maxHeight: 400,
          overflow: 'auto',
          p: 2,
        }}
      >
        {filteredPermissions.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
            No permissions found
          </Typography>
        ) : (
          Object.entries(groupedPermissions).map(([resource, perms]) => (
            <Box key={resource} sx={{ mb: 2 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1, textTransform: 'capitalize' }}>
                {resource}
              </Typography>
              <Box sx={{ pl: 2 }}>
                {perms.map((permission) => (
                  <FormControlLabel
                    key={permission.id}
                    control={
                      <Checkbox
                        checked={selectedPermissionIds.includes(permission.id)}
                        onChange={() => handleToggle(permission.id)}
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body2">{permission.name}</Typography>
                        {permission.description && (
                          <Typography variant="caption" color="text.secondary">
                            {permission.description}
                          </Typography>
                        )}
                      </Box>
                    }
                  />
                ))}
              </Box>
            </Box>
          ))
        )}
      </Paper>
    </Box>
  );
};

export default PermissionSelector;

