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

interface BulkUnique {
  id: string;
  name?: string;
  client_sample_id?: string;
  container_name: string;
  temperature?: number;
  anomalies?: string;
  description?: string;
}

interface BulkUniquesTableProps {
  uniques: BulkUnique[];
  onAdd: () => void;
  onRemove: (id: string) => void;
  onUpdate: (id: string, field: keyof BulkUnique, value: any) => void;
  autoNamePrefix?: string;
  autoNameStart?: number;
  onAutoNameChange: (prefix?: string, start?: number) => void;
}

const BulkUniquesTable: React.FC<BulkUniquesTableProps> = ({
  uniques,
  onAdd,
  onRemove,
  onUpdate,
  autoNamePrefix,
  autoNameStart,
  onAutoNameChange,
}) => {
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
        onUpdate(newRow.id, key as keyof BulkUnique, (newRow as any)[key]);
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

