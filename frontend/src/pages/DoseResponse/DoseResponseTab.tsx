import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  LinearProgress,
  Card,
  CardContent,
  Chip,
} from '@mui/material';
import ScienceIcon from '@mui/icons-material/Science';
import AssessmentIcon from '@mui/icons-material/Assessment';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../../services/apiService';

/** Safely convert a FastAPI/Pydantic error to a display string. */
const apiErrorMsg = (err: any, fallback: string): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length > 0) return detail[0]?.msg || fallback;
  return fallback;
};

interface DoseResponseSummary {
  run_id: string;
  fit_in_progress: boolean;
  total: number;
  by_category: Record<string, number>;
  by_review_status: Record<string, number>;
  last_fit_at?: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  SIGMOID: 'Sigmoid',
  INACTIVE: 'Inactive',
  INVERSE: 'Inverse Agonist',
  PARTIAL_HIGH: 'Partial High',
  PARTIAL_LOW: 'Partial Low',
  HOOK_EFFECT: 'Hook Effect',
  NOISY: 'Noisy',
  CANNOT_FIT: 'Cannot Fit',
};

const CATEGORY_COLORS: Record<string, 'success' | 'default' | 'warning' | 'error' | 'info' | 'primary' | 'secondary'> = {
  SIGMOID: 'success',
  INACTIVE: 'default',
  INVERSE: 'warning',
  PARTIAL_HIGH: 'info',
  PARTIAL_LOW: 'info',
  HOOK_EFFECT: 'warning',
  NOISY: 'secondary',
  CANNOT_FIT: 'error',
};

interface Props {
  runId: string;
  runStatus: string;
}

const DoseResponseTab: React.FC<Props> = ({ runId, runStatus }) => {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DoseResponseSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fitting, setFitting] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const loadSummary = async () => {
    try {
      const data = await apiService.getDoseResponseSummary(runId);
      setSummary(data);
      return data;
    } catch (err: any) {
      if (err.response?.status !== 404) {
        setError(apiErrorMsg(err, 'Failed to load summary'));
      }
      return null;
    }
  };

  useEffect(() => {
    setLoading(true);
    loadSummary().finally(() => setLoading(false));
  }, [runId]);

  // Poll while fit_in_progress
  useEffect(() => {
    if (summary?.fit_in_progress) {
      pollRef.current = setInterval(async () => {
        const s = await loadSummary();
        if (s && !s.fit_in_progress) {
          if (pollRef.current) clearInterval(pollRef.current);
          // Auto-navigate to curator when done
          navigate(`/runs/${runId}/dose-response`);
        }
      }, 3000);
    } else {
      if (pollRef.current) clearInterval(pollRef.current);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [summary?.fit_in_progress]);

  const handleFit = async () => {
    setFitting(true);
    setError(null);
    try {
      await apiService.triggerDoseResponseFit(runId);
      await loadSummary();
    } catch (err: any) {
      setError(apiErrorMsg(err, 'Failed to trigger fit'));
    } finally {
      setFitting(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ py: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Box>
    );
  }

  const canFit = runStatus === 'running' || runStatus === 'results_received' || runStatus === 'complete';

  return (
    <Box sx={{ mt: 2 }}>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {summary?.fit_in_progress && (
        <Card variant="outlined" sx={{ mb: 2 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
              <CircularProgress size={20} />
              <Typography variant="body1">Fitting curves… this may take a minute.</Typography>
            </Box>
            <LinearProgress />
          </CardContent>
        </Card>
      )}

      <Box sx={{ display: 'flex', gap: 2, mb: 3, alignItems: 'center' }}>
        {canFit && (
          <Button
            variant="contained"
            startIcon={fitting ? <CircularProgress size={16} color="inherit" /> : <ScienceIcon />}
            onClick={handleFit}
            disabled={fitting || summary?.fit_in_progress}
          >
            {summary?.total ? 'Re-fit Curves' : 'Fit Curves'}
          </Button>
        )}
        {summary && summary.total > 0 && (
          <Button
            variant="outlined"
            startIcon={<AssessmentIcon />}
            onClick={() => navigate(`/runs/${runId}/dose-response`)}
          >
            Review Curves ({summary.total})
          </Button>
        )}
      </Box>

      {summary && summary.total > 0 ? (
        <>
          <Typography variant="subtitle2" sx={{ mb: 1 }} color="text.secondary">
            Last fit: {summary.last_fit_at ? new Date(summary.last_fit_at).toLocaleString() : '—'}
          </Typography>

          {(summary.by_category['CANNOT_FIT'] ?? 0) > 0 && (
            <Alert
              severity="error"
              sx={{ mb: 2 }}
              action={
                <Button color="inherit" size="small" onClick={() => navigate(`/runs/${runId}/dose-response`)}>
                  Review
                </Button>
              }
            >
              {summary.by_category['CANNOT_FIT']} compound{summary.by_category['CANNOT_FIT'] === 1 ? '' : 's'} could not be fitted. Open Curve Curator to investigate.
            </Alert>
          )}

          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 3 }}>
            {Object.entries(summary.by_category).map(([cat, count]) => (
              <Chip
                key={cat}
                label={`${CATEGORY_LABELS[cat] ?? cat}: ${count}`}
                color={CATEGORY_COLORS[cat] ?? 'default'}
                variant="outlined"
              />
            ))}
          </Box>

          <Typography variant="subtitle2" sx={{ mb: 1 }} color="text.secondary">
            Review status
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {Object.entries(summary.by_review_status).map(([status, count]) => (
              <Chip
                key={status}
                label={`${status}: ${count}`}
                color={status === 'approved' ? 'success' : status === 'rejected' ? 'error' : 'default'}
                variant="outlined"
              />
            ))}
          </Box>
        </>
      ) : !summary?.fit_in_progress ? (
        <Typography color="text.secondary">
          {canFit
            ? 'No dose-response curves yet. Click "Fit Curves" to run curve fitting.'
            : 'Run must be in "running" or "complete" state to fit curves.'}
        </Typography>
      ) : null}
    </Box>
  );
};

export default DoseResponseTab;
