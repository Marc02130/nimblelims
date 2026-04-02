import React, { useState } from 'react';
import { Box, Button, CircularProgress, Alert } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { apiService } from '../../services/apiService';
import { CATEGORY_LABELS, Category } from './CategorySidebar';

interface Props {
  runId: string;
  category: Category;
  pendingCount: number;
  onDone: () => void;
}

const BatchApproveBar: React.FC<Props> = ({ runId, category, pendingCount, onDone }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleBatchApprove = async () => {
    setLoading(true);
    setError(null);
    try {
      await apiService.batchReviewDoseResponse(runId, category, 'approved');
      onDone();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Batch approve failed');
    } finally {
      setLoading(false);
    }
  };

  if (pendingCount === 0) return null;

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 1 }}>
      {error && (
        <Alert severity="error" onClose={() => setError(null)} sx={{ py: 0 }}>
          {error}
        </Alert>
      )}
      <Button
        variant="outlined"
        color="success"
        size="small"
        startIcon={loading ? <CircularProgress size={14} color="inherit" /> : <CheckCircleIcon />}
        onClick={handleBatchApprove}
        disabled={loading}
      >
        Approve all pending {CATEGORY_LABELS[category]} ({pendingCount})
      </Button>
    </Box>
  );
};

export default BatchApproveBar;
