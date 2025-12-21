import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Tabs,
  Tab,
  Box,
  Alert,
} from '@mui/material';
import AliquotForm from './AliquotForm';
import DerivativeForm from './DerivativeForm';

interface AliquotDerivativeDialogProps {
  open: boolean;
  onClose: () => void;
  parentSampleId: string;
  parentSampleName: string;
  onSuccess: (result: any) => void;
}

const AliquotDerivativeDialog: React.FC<AliquotDerivativeDialogProps> = ({
  open,
  onClose,
  parentSampleId,
  parentSampleName,
  onSuccess,
}) => {
  const [activeTab, setActiveTab] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
    setError(null);
  };

  const handleSuccess = (result: any) => {
    onSuccess(result);
    onClose();
    setActiveTab(0);
    setError(null);
  };

  const handleCancel = () => {
    onClose();
    setActiveTab(0);
    setError(null);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        Create Aliquot or Derivative from {parentSampleName}
      </DialogTitle>
      
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
          <Tabs value={activeTab} onChange={handleTabChange}>
            <Tab label="Create Aliquot" />
            <Tab label="Create Derivative" />
          </Tabs>
        </Box>

        {activeTab === 0 && (
          <AliquotForm
            parentSampleId={parentSampleId}
            onSuccess={handleSuccess}
            onCancel={handleCancel}
          />
        )}

        {activeTab === 1 && (
          <DerivativeForm
            parentSampleId={parentSampleId}
            onSuccess={handleSuccess}
            onCancel={handleCancel}
          />
        )}
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export default AliquotDerivativeDialog;
