import React, { useState } from 'react';
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  TextField,
} from '@mui/material';

interface RejectPlateDialogProps {
  open: boolean;
  submitting: boolean;
  error: string | null;
  sampleCount: number;
  onClose: () => void;
  onConfirm: (reason: string) => void;
}

const RejectPlateDialog: React.FC<RejectPlateDialogProps> = ({
  open,
  submitting,
  error,
  sampleCount,
  onClose,
  onConfirm,
}) => {
  const [reason, setReason] = useState('');

  return (
    <Dialog open={open} onClose={() => !submitting && onClose()} maxWidth="sm" fullWidth>
      <DialogTitle>Reject plate</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>
          The run is marked failed and the reason is kept. Imported rows stay. Nothing is
          deleted. When a plate fails, every sample on it is rerun
          {sampleCount > 0 ? ` (${sampleCount} sample${sampleCount === 1 ? '' : 's'})` : ''}.
        </DialogContentText>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        <TextField
          label="Reason"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          required
          fullWidth
          multiline
          minRows={2}
          inputProps={{ 'data-testid': 'reject-reason' }}
          helperText="Required. For example: QC-H out of range."
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={submitting}>
          Cancel
        </Button>
        <Button
          color="error"
          variant="contained"
          data-testid="reject-confirm"
          disabled={submitting || !reason.trim()}
          onClick={() => onConfirm(reason.trim())}
        >
          Reject plate
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default RejectPlateDialog;
