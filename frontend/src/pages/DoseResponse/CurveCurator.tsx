import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Divider,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useNavigate, useParams } from 'react-router-dom';
import { apiService } from '../../services/apiService';
import CategorySidebar, { CATEGORIES, Category } from './CategorySidebar';
import CurveGrid from './CurveGrid';
import CurveDetail from './CurveDetail';
import BatchApproveBar from './BatchApproveBar';

interface DoseResponseSummary {
  run_id: string;
  fit_in_progress: boolean;
  total: number;
  by_category: Record<string, number>;
  by_review_status: Record<string, number>;
  last_fit_at?: string;
}

const CurveCurator: React.FC = () => {
  const navigate = useNavigate();
  const { runId } = useParams<{ runId: string }>();
  const [summary, setSummary] = useState<DoseResponseSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<Category>('SIGMOID');
  const [selectedResultId, setSelectedResultId] = useState<string | null>(null);
  const [gridRefreshKey, setGridRefreshKey] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const [gridDims, setGridDims] = useState({ width: 800, height: 600 });

  const loadSummary = useCallback(async () => {
    if (!runId) return;
    try {
      const data = await apiService.getDoseResponseSummary(runId);
      setSummary(data);
      // Auto-select first non-empty category
      if (!data.by_category[selectedCategory] || data.by_category[selectedCategory] === 0) {
        const firstNonEmpty = CATEGORIES.find((c) => (data.by_category[c] ?? 0) > 0);
        if (firstNonEmpty) setSelectedCategory(firstNonEmpty);
      }
    } catch (err: any) {
      setSummaryError(err.response?.data?.detail || 'Failed to load summary');
    }
  }, [runId]);

  useEffect(() => {
    setSummaryLoading(true);
    loadSummary().finally(() => setSummaryLoading(false));
  }, [loadSummary]);

  // Track grid container size
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setGridDims({ width: Math.max(200, width), height: Math.max(200, height) });
      }
    });
    observer.observe(el);
    setGridDims({ width: el.clientWidth, height: el.clientHeight });
    return () => observer.disconnect();
  }, []);

  const handleReviewDone = () => {
    setGridRefreshKey((k) => k + 1);
    loadSummary();
  };

  const handleRefitDone = () => {
    setGridRefreshKey((k) => k + 1);
    loadSummary();
    setSelectedResultId(null);
  };

  const pendingInCategory = summary
    ? (summary.by_category[selectedCategory] ?? 0) -
      // approximate pending as total minus reviewed (rough; BatchApproveBar handles real count server-side)
      0
    : 0;

  if (summaryLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Top bar */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 2,
          px: 2,
          py: 1,
          borderBottom: 1,
          borderColor: 'divider',
          flexShrink: 0,
        }}
      >
        <Button
          startIcon={<ArrowBackIcon />}
          size="small"
          onClick={() => navigate(`/runs/${runId}`)}
        >
          Back to Run
        </Button>
        <Typography variant="h6">
          Curve Curator
          {summary && (
            <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
              — {summary.total} curves
            </Typography>
          )}
        </Typography>
        {summaryError && (
          <Alert severity="error" sx={{ py: 0 }} onClose={() => setSummaryError(null)}>
            {summaryError}
          </Alert>
        )}
      </Box>

      {/* Main area: sidebar + grid */}
      <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Category sidebar */}
        <CategorySidebar
          byCategoryCount={summary?.by_category ?? {}}
          selected={selectedCategory}
          onSelect={(cat) => {
            setSelectedCategory(cat);
            setSelectedResultId(null);
          }}
        />

        {/* Grid + batch bar */}
        <Box sx={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
          {/* Batch approve bar */}
          {runId && (
            <Box sx={{ px: 2, pt: 1, flexShrink: 0 }}>
              <BatchApproveBar
                runId={runId}
                category={selectedCategory}
                pendingCount={summary?.by_category[selectedCategory] ?? 0}
                onDone={handleReviewDone}
              />
            </Box>
          )}
          <Divider />

          {/* Grid */}
          <Box ref={containerRef} sx={{ flex: 1, overflow: 'hidden' }}>
            {runId && (
              <CurveGrid
                runId={runId}
                category={selectedCategory}
                selectedId={selectedResultId}
                onSelect={setSelectedResultId}
                onReviewDone={handleReviewDone}
                containerWidth={gridDims.width}
                containerHeight={gridDims.height}
                refreshKey={gridRefreshKey}
              />
            )}
          </Box>
        </Box>
      </Box>

      {/* Right-side detail drawer */}
      {runId && (
        <CurveDetail
          runId={runId}
          resultId={selectedResultId}
          onClose={() => setSelectedResultId(null)}
          onRefitDone={handleRefitDone}
          onReviewDone={handleReviewDone}
        />
      )}
    </Box>
  );
};

export default CurveCurator;
