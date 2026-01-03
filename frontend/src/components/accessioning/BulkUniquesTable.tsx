import React from 'react';
import {
  Box,
  Button,
  IconButton,
  TextField,
  Typography,
  Paper,
} from '@mui/material';
import {
  Add,
  Delete,
} from '@mui/icons-material';
import { DataGrid, GridColDef, GridActionsCellItem, GridRowParams } from '@mui/x-data-grid';

interface CustomAttributeConfig {
  id: string;
  entity_type: string;
  attr_name: string;
  data_type: 'text' | 'number' | 'date' | 'boolean' | 'select';
  validation_rules: Record<string, any>;
  description?: string;
  active: boolean;
}

interface BulkUnique {
  id: string;
  name?: string;
  client_sample_id?: string;
  container_name: string;
  temperature?: number;
  anomalies?: string;
  description?: string;
  custom_attributes?: Record<string, any>;
}

interface BulkUniquesTableProps {
  uniques: BulkUnique[];
  onAdd: () => void;
  onRemove: (id: string) => void;
  onUpdate: (id: string, field: keyof BulkUnique | string, value: any) => void;
  autoNamePrefix?: string;
  autoNameStart?: number;
  onAutoNameChange: (prefix?: string, start?: number) => void;
  customAttributeConfigs?: CustomAttributeConfig[];
}

const BulkUniquesTable: React.FC<BulkUniquesTableProps> = ({
  uniques,
  onAdd,
  onRemove,
  onUpdate,
  autoNamePrefix,
  autoNameStart,
  onAutoNameChange,
  customAttributeConfigs = [],
}) => {
  // Build custom attribute columns
  const customColumns: GridColDef[] = customAttributeConfigs.map((config) => {
    const displayName = config.attr_name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
    
    return {
      field: `custom_attributes.${config.attr_name}`,
      headerName: displayName,
      width: 150,
      editable: true,
      type: config.data_type === 'number' ? 'number' : 'string',
      valueGetter: (value, row) => {
        return row.custom_attributes?.[config.attr_name] || '';
      },
      valueSetter: (value, row) => {
        const customAttrs = row.custom_attributes || {};
        return {
          ...row,
          custom_attributes: {
            ...customAttrs,
            [config.attr_name]: value,
          },
        };
      },
      renderCell: (params) => {
        const value = params.row.custom_attributes?.[config.attr_name];
        if (value === null || value === undefined || value === '') {
          return <Typography variant="body2" color="text.secondary">—</Typography>;
        }
        switch (config.data_type) {
          case 'boolean':
            return value === true || value === 'true' ? 'Yes' : 'No';
          case 'date':
            return typeof value === 'string' ? value : new Date(value).toLocaleDateString();
          default:
            return String(value);
        }
      },
    };
  });

  const columns: GridColDef[] = [
    {
      field: 'name',
      headerName: 'Sample Name',
      width: 200,
      editable: true,
    },
    {
      field: 'client_sample_id',
      headerName: 'Client Sample ID',
      width: 180,
      editable: true,
    },
    {
      field: 'container_name',
      headerName: 'Container Name',
      width: 200,
      editable: true,
    },
    {
      field: 'temperature',
      headerName: 'Temperature (°C)',
      width: 150,
      editable: true,
      type: 'number',
      valueFormatter: (value) => value || '',
    },
    {
      field: 'description',
      headerName: 'Description',
      width: 200,
      editable: true,
    },
    {
      field: 'anomalies',
      headerName: 'Anomalies',
      width: 200,
      editable: true,
    },
    ...customColumns,
    {
      field: 'actions',
      type: 'actions',
      headerName: 'Actions',
      width: 100,
      getActions: (params: GridRowParams) => [
        <GridActionsCellItem
          icon={<Delete />}
          label="Delete"
          onClick={() => onRemove(params.id as string)}
        />,
      ],
    },
  ];

  const handleProcessRowUpdate = (newRow: BulkUnique) => {
    // Update all fields that may have changed
    Object.keys(newRow).forEach((key) => {
      if (key !== 'id') {
        if (key === 'custom_attributes') {
          // Handle custom attributes separately
          const customAttrs = (newRow as any).custom_attributes || {};
          Object.keys(customAttrs).forEach((attrName) => {
            onUpdate(newRow.id, `custom_attributes.${attrName}`, customAttrs[attrName]);
          });
        } else {
          onUpdate(newRow.id, key as keyof BulkUnique, (newRow as any)[key]);
        }
      }
    });
    return newRow;
  };

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
        <Typography variant="h6">
          Unique Fields per Sample ({uniques.length} samples)
        </Typography>
        <Button
          variant="outlined"
          startIcon={<Add />}
          onClick={onAdd}
          size="small"
        >
          Add Row
        </Button>
      </Box>

      <Box mb={2}>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Auto-Naming (Optional)
          </Typography>
          <Box display="flex" gap={2} alignItems="center">
            <TextField
              label="Prefix"
              size="small"
              value={autoNamePrefix || ''}
              onChange={(e) => onAutoNameChange(e.target.value || undefined, autoNameStart)}
              placeholder="e.g., SAMPLE-"
              sx={{ width: 200 }}
            />
            <TextField
              label="Start Number"
              type="number"
              size="small"
              value={autoNameStart || ''}
              onChange={(e) => onAutoNameChange(autoNamePrefix, parseInt(e.target.value) || undefined)}
              inputProps={{ min: 1 }}
              sx={{ width: 150 }}
            />
            <Typography variant="body2" color="text.secondary">
              {autoNamePrefix && autoNameStart
                ? `Example: ${autoNamePrefix}${autoNameStart}, ${autoNamePrefix}${(autoNameStart || 1) + 1}...`
                : 'Leave sample names empty to use auto-naming'}
            </Typography>
          </Box>
        </Paper>
      </Box>

      <DataGrid
        rows={uniques}
        columns={columns}
        getRowId={(row) => row.id}
        processRowUpdate={handleProcessRowUpdate}
        onProcessRowUpdateError={(error) => {
          console.error('Row update error:', error);
        }}
        autoHeight
        disableRowSelectionOnClick
        sx={{
          '& .MuiDataGrid-cell': {
            display: 'flex',
            alignItems: 'center',
          },
        }}
      />
    </Box>
  );
};

export default BulkUniquesTable;

