import React, { useEffect, useState, useCallback, useRef } from 'react';
import { Box, Typography, Alert, CircularProgress } from '@mui/material';
import { FixedSizeGrid } from 'react-window';
import { apiService } from '../../services/apiService';
import CurveThumbnail from './CurveThumbnail';
import { Category } from './CategorySidebar';

interface CurveResult {
  id: string;
  sample_id: string;
  compound_id?: string;
  curve_category: string;
  review_status: string;
  potency?: number;
  hill_slope?: number;
  r_squared?: number;
  thumbnail_svg?: string;
  quality_flag?: string;
}

interface Props {
  runId: string;
  category: Category;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onReviewDone: () => void;
  containerWidth: number;
  containerHeight: number;
  refreshKey: number;
}

const CELL_WIDTH = 216; // 200px card + padding
const CELL_HEIGHT = 196; // 180px card + padding
const PAGE_SIZE = 100;

const CurveGrid: React.FC<Props> = ({
  runId,
  category,
  selectedId,
  onSelect,
  onReviewDone,
  containerWidth,
  containerHeight,
  refreshKey,
}) => {
  const [results, setResults] = useState<CurveResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const colCount = Math.max(1, Math.floor(containerWidth / CELL_WIDTH));

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiService.getDoseResponseResults(runId, {
        category,
        page: 1,
        size: PAGE_SIZE,
      });
      setResults(res?.results ?? []);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load curves');
    } finally {
      setLoading(false);
    }
  }, [runId, category]);

  useEffect(() => {
    load();
  }, [load, refreshKey]);

  const handleReview = async (result: CurveResult, status: 'approved' | 'rejected' | 'flagged') => {
    try {
      await apiService.reviewDoseResponseResult(runId, result.id, status);
      // Optimistic update
      setResults((prev) =>
        prev.map((r) => (r.id === result.id ? { ...r, review_status: status } : r))
      );
      onReviewDone();
    } catch {
      // let grid reload on next refresh
    }
  };

  const rowCount = Math.ceil(results.length / colCount);

  const Cell = useCallback(
    ({ columnIndex, rowIndex, style }: { columnIndex: number; rowIndex: number; style: React.CSSProperties }) => {
      const idx = rowIndex * colCount + columnIndex;
      if (idx >= results.length) return <div style={style} />;
      const result = results[idx];
      return (
        <Box style={style} sx={{ p: 0.5 }}>
          <CurveThumbnail
            result={result}
            selected={result.id === selectedId}
            onSelect={() => onSelect(result.id)}
            onReview={(status) => handleReview(result, status)}
          />
        </Box>
      );
    },
    [results, selectedId, colCount, onSelect]
  );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error" sx={{ m: 2 }}>{error}</Alert>;
  }

  if (results.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
        <Typography color="text.secondary">No curves in this category.</Typography>
      </Box>
    );
  }

  return (
    <FixedSizeGrid
      columnCount={colCount}
      columnWidth={CELL_WIDTH}
      rowCount={rowCount}
      rowHeight={CELL_HEIGHT}
      width={containerWidth}
      height={containerHeight}
      itemData={results}
    >
      {Cell}
    </FixedSizeGrid>
  );
};

export default CurveGrid;
