import React, { useState, useEffect, lazy, Suspense } from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  CircularProgress,
  Alert,
  Divider,
  Button,
  Chip,
  List,
  ListItem,
  ListItemText,
  TextField,
  Tooltip,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import RefreshIcon from '@mui/icons-material/Refresh';
import BlockIcon from '@mui/icons-material/Block';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import { apiService } from '../../services/apiService';

// Lazy load Plotly — only needed in this drawer
const Plot = lazy(() => import('react-plotly.js'));

interface DataPoint {
  id: string;
  well_position?: string;
  concentration: number;
  response: number;
  excluded?: boolean;
}

interface CurveResultDetail {
  id: string;
  sample_id: string;
  compound_id?: string;
  curve_category: string;
  review_status: string;
  potency?: number;
  hill_slope?: number;
  top?: number;
  bottom?: number;
  r_squared?: number;
  ci_low_95?: number;
  ci_high_95?: number;
  ci_method?: string;
  quality_flag?: string;
  review_notes?: string;
  fit_version: number;
  data_points?: DataPoint[];
}

interface Props {
  runId: string;
  resultId: string | null;
  onClose: () => void;
  onRefitDone: () => void;
  onReviewDone: () => void;
}

const REVIEW_COLORS: Record<string, 'success' | 'error' | 'warning' | 'default'> = {
  approved: 'success',
  rejected: 'error',
  flagged: 'warning',
  pending: 'default',
};

const CurveDetail: React.FC<Props> = ({ runId, resultId, onClose, onRefitDone, onReviewDone }) => {
  const [detail, setDetail] = useState<CurveResultDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refitting, setRefitting] = useState(false);
  const [reviewNotes, setReviewNotes] = useState('');
  const [reviewing, setReviewing] = useState(false);
  const [excludingId, setExcludingId] = useState<string | null>(null);

  useEffect(() => {
    if (!resultId) {
      setDetail(null);
      return;
    }
    setLoading(true);
    setError(null);
    apiService
      .getDoseResponseResult(runId, resultId)
      .then((d: CurveResultDetail) => {
        setDetail(d);
        setReviewNotes(d.review_notes ?? '');
      })
      .catch((e: any) => setError(e.response?.data?.detail || 'Failed to load curve detail'))
      .finally(() => setLoading(false));
  }, [runId, resultId]);

  const handleRefit = async () => {
    if (!detail) return;
    setRefitting(true);
    setError(null);
    try {
      await apiService.triggerDoseResponseRefit(runId, detail.sample_id);
      onRefitDone();
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Refit failed');
    } finally {
      setRefitting(false);
    }
  };

  const handleReview = async (status: 'approved' | 'rejected' | 'flagged') => {
    if (!detail) return;
    setReviewing(true);
    try {
      await apiService.reviewDoseResponseResult(runId, detail.id, status, reviewNotes || undefined);
      onReviewDone();
      // Reload detail to show updated status
      const updated = await apiService.getDoseResponseResult(runId, detail.id);
      setDetail(updated);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Review failed');
    } finally {
      setReviewing(false);
    }
  };

  const handleToggleExclusion = async (point: DataPoint) => {
    setExcludingId(point.id);
    try {
      if (point.excluded) {
        await apiService.unexcludeDataPoint(point.id);
      } else {
        await apiService.excludeDataPoint(point.id, 'Manual exclusion');
      }
      // Reload detail
      if (resultId) {
        const updated = await apiService.getDoseResponseResult(runId, resultId);
        setDetail(updated);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Toggle exclusion failed');
    } finally {
      setExcludingId(null);
    }
  };

  const buildPlotData = () => {
    if (!detail?.data_points || !detail.potency) return null;

    const active = detail.data_points.filter((p) => !p.excluded);
    const excluded = detail.data_points.filter((p) => p.excluded);

    // Fit curve — logistic 4PL: bottom + (top - bottom) / (1 + (x/ec50)^hill)
    const { potency, hill_slope, top = 100, bottom = 0 } = detail;
    const xMin = Math.min(...active.map((p) => p.concentration)) * 0.5;
    const xMax = Math.max(...active.map((p) => p.concentration)) * 2;
    const curveX: number[] = [];
    const curveY: number[] = [];
    const steps = 100;
    for (let i = 0; i <= steps; i++) {
      const logX = Math.log10(xMin) + (i / steps) * (Math.log10(xMax) - Math.log10(xMin));
      const x = Math.pow(10, logX);
      const y = bottom + (top - bottom) / (1 + Math.pow(x / potency, -(hill_slope ?? 1)));
      curveX.push(x);
      curveY.push(y);
    }

    return {
      active,
      excluded,
      curveX,
      curveY,
      xMin,
      xMax,
    };
  };

  const plotData = detail ? buildPlotData() : null;

  return (
    <Drawer
      anchor="right"
      open={!!resultId}
      onClose={onClose}
      sx={{ '& .MuiDrawer-paper': { width: '40%', minWidth: 400 } }}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Header */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: 2,
            py: 1.5,
            borderBottom: 1,
            borderColor: 'divider',
          }}
        >
          <Typography variant="h6" noWrap>
            {detail?.compound_id ?? detail?.sample_id?.slice(0, 8) ?? 'Loading…'}
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Content */}
        <Box sx={{ flex: 1, overflowY: 'auto', p: 2 }}>
          {loading && (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress />
            </Box>
          )}

          {error && (
            <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {detail && (
            <>
              {/* Status chips */}
              <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                <Chip label={detail.curve_category} size="small" />
                <Chip
                  label={detail.review_status}
                  size="small"
                  color={REVIEW_COLORS[detail.review_status] ?? 'default'}
                />
                {detail.quality_flag && (
                  <Chip label={detail.quality_flag} size="small" variant="outlined" color="warning" />
                )}
                <Chip label={`v${detail.fit_version}`} size="small" variant="outlined" />
              </Box>

              {/* Plotly chart */}
              {plotData ? (
                <Suspense fallback={<Box sx={{ height: 300, display: 'flex', alignItems: 'center', justifyContent: 'center' }}><CircularProgress /></Box>}>
                  <Plot
                    data={[
                      // Fit curve
                      {
                        x: plotData.curveX,
                        y: plotData.curveY,
                        type: 'scatter',
                        mode: 'lines',
                        line: { color: '#1976d2', width: 2 },
                        name: 'Fit',
                      },
                      // Active data points
                      {
                        x: plotData.active.map((p) => p.concentration),
                        y: plotData.active.map((p) => p.response),
                        type: 'scatter',
                        mode: 'markers',
                        marker: { color: '#1976d2', size: 7 },
                        name: 'Data',
                        customdata: plotData.active.map((p) => p.id),
                      },
                      // Excluded points in grey
                      ...(plotData.excluded.length > 0
                        ? [{
                            x: plotData.excluded.map((p) => p.concentration),
                            y: plotData.excluded.map((p) => p.response),
                            type: 'scatter' as const,
                            mode: 'markers' as const,
                            marker: { color: '#ccc', size: 7, symbol: 'x' as const },
                            name: 'Excluded',
                          }]
                        : []),
                      // IC50 dashed line
                      ...(detail.potency
                        ? [{
                            x: [detail.potency, detail.potency],
                            y: [detail.bottom ?? 0, detail.top ?? 100],
                            type: 'scatter' as const,
                            mode: 'lines' as const,
                            line: { color: '#e91e63', width: 1, dash: 'dash' as const },
                            name: 'IC₅₀',
                          }]
                        : []),
                    ]}
                    layout={{
                      width: undefined,
                      height: 300,
                      margin: { l: 50, r: 20, t: 20, b: 50 },
                      xaxis: { type: 'log', title: { text: 'Concentration (µM)' } },
                      yaxis: { title: { text: '% Inhibition' } },
                      legend: { orientation: 'h', y: -0.2 },
                      autosize: true,
                    }}
                    config={{ displayModeBar: false, responsive: true }}
                    style={{ width: '100%' }}
                  />
                </Suspense>
              ) : (
                <Box
                  sx={{
                    height: 300,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    bgcolor: '#f5f5f5',
                    borderRadius: 1,
                    mb: 2,
                  }}
                >
                  <Typography color="text.secondary" variant="body2">
                    No curve data to display
                  </Typography>
                </Box>
              )}

              {/* Fit parameters */}
              <List dense sx={{ mb: 2 }}>
                {detail.potency != null && (
                  <ListItem disableGutters>
                    <ListItemText
                      primary="IC₅₀"
                      secondary={`${detail.potency.toExponential(3)} µM${
                        detail.ci_low_95 != null && detail.ci_high_95 != null
                          ? ` (95% CI: ${detail.ci_low_95.toExponential(2)} – ${detail.ci_high_95.toExponential(2)}, ${detail.ci_method ?? ''})`
                          : ''
                      }`}
                    />
                  </ListItem>
                )}
                {detail.hill_slope != null && (
                  <ListItem disableGutters>
                    <ListItemText primary="Hill slope" secondary={detail.hill_slope.toFixed(3)} />
                  </ListItem>
                )}
                {detail.top != null && (
                  <ListItem disableGutters>
                    <ListItemText primary="Top" secondary={`${detail.top.toFixed(1)}%`} />
                  </ListItem>
                )}
                {detail.bottom != null && (
                  <ListItem disableGutters>
                    <ListItemText primary="Bottom" secondary={`${detail.bottom.toFixed(1)}%`} />
                  </ListItem>
                )}
                {detail.r_squared != null && (
                  <ListItem disableGutters>
                    <ListItemText primary="R²" secondary={detail.r_squared.toFixed(4)} />
                  </ListItem>
                )}
              </List>

              <Divider sx={{ mb: 2 }} />

              {/* Knockout controls */}
              {detail.data_points && detail.data_points.length > 0 && (
                <>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    Data Points ({detail.data_points.length})
                  </Typography>
                  <List dense sx={{ mb: 2 }}>
                    {detail.data_points.map((p) => (
                      <ListItem
                        key={p.id}
                        disableGutters
                        secondaryAction={
                          <Tooltip title={p.excluded ? 'Re-include' : 'Exclude'}>
                            <span>
                              <IconButton
                                size="small"
                                onClick={() => handleToggleExclusion(p)}
                                disabled={excludingId === p.id}
                                color={p.excluded ? 'default' : 'error'}
                              >
                                {excludingId === p.id ? (
                                  <CircularProgress size={14} />
                                ) : p.excluded ? (
                                  <CheckCircleOutlineIcon fontSize="small" />
                                ) : (
                                  <BlockIcon fontSize="small" />
                                )}
                              </IconButton>
                            </span>
                          </Tooltip>
                        }
                      >
                        <ListItemText
                          primary={
                            <Typography
                              variant="caption"
                              sx={{ textDecoration: p.excluded ? 'line-through' : 'none', color: p.excluded ? 'text.disabled' : 'text.primary' }}
                            >
                              {p.well_position ?? '—'} | {p.concentration.toExponential(2)} µM → {p.response.toFixed(1)}%
                            </Typography>
                          }
                        />
                      </ListItem>
                    ))}
                  </List>
                  <Divider sx={{ mb: 2 }} />
                </>
              )}

              {/* Review section */}
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                Review
              </Typography>
              <TextField
                fullWidth
                size="small"
                multiline
                rows={2}
                label="Notes (optional)"
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                sx={{ mb: 1.5 }}
              />
              <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <Button
                  variant="contained"
                  color="success"
                  size="small"
                  disabled={reviewing}
                  onClick={() => handleReview('approved')}
                >
                  Approve
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  size="small"
                  disabled={reviewing}
                  onClick={() => handleReview('rejected')}
                >
                  Reject
                </Button>
                <Button
                  variant="outlined"
                  color="warning"
                  size="small"
                  disabled={reviewing}
                  onClick={() => handleReview('flagged')}
                >
                  Flag
                </Button>
              </Box>

              {/* Re-fit */}
              <Button
                variant="outlined"
                size="small"
                startIcon={refitting ? <CircularProgress size={14} /> : <RefreshIcon />}
                onClick={handleRefit}
                disabled={refitting}
              >
                Re-fit this compound
              </Button>
            </>
          )}
        </Box>
      </Box>
    </Drawer>
  );
};

export default CurveDetail;
