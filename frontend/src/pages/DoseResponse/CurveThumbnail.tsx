import React from 'react';
import { Box, Typography, Chip, IconButton, Tooltip } from '@mui/material';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import CancelOutlinedIcon from '@mui/icons-material/CancelOutlined';
import FlagOutlinedIcon from '@mui/icons-material/FlagOutlined';

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
  result: CurveResult;
  selected: boolean;
  onSelect: () => void;
  onReview: (status: 'approved' | 'rejected' | 'flagged') => void;
}

const REVIEW_COLORS: Record<string, 'success' | 'error' | 'warning' | 'default'> = {
  approved: 'success',
  rejected: 'error',
  flagged: 'warning',
  pending: 'default',
};

const CurveThumbnail: React.FC<Props> = ({ result, selected, onSelect, onReview }) => {
  const ic50Display = result.potency != null
    ? result.potency < 0.001
      ? `${(result.potency * 1e9).toFixed(1)} nM`
      : result.potency < 1
      ? `${(result.potency * 1000).toFixed(1)} nM`
      : `${result.potency.toFixed(3)} µM`
    : null;

  return (
    <Box
      onClick={onSelect}
      sx={{
        width: 200,
        height: 180,
        border: selected ? '2px solid' : '1px solid',
        borderColor: selected ? 'primary.main' : 'divider',
        borderRadius: 1,
        overflow: 'hidden',
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: 'background.paper',
        '&:hover': { boxShadow: 2 },
        transition: 'box-shadow 0.15s',
      }}
    >
      {/* SVG thumbnail area */}
      <Box
        sx={{
          width: 200,
          height: 120,
          bgcolor: '#fafafa',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        {result.thumbnail_svg ? (
          <Box
            component="div"
            dangerouslySetInnerHTML={{ __html: result.thumbnail_svg }}
            sx={{ width: 200, height: 120, '& svg': { width: '100%', height: '100%' } }}
          />
        ) : (
          <Typography variant="caption" color="text.secondary">
            No preview
          </Typography>
        )}
      </Box>

      {/* Info row */}
      <Box sx={{ px: 1, pt: 0.5, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" noWrap sx={{ maxWidth: 100, fontWeight: 600 }}>
          {result.compound_id ?? result.sample_id.slice(0, 8)}
        </Typography>
        <Chip
          size="small"
          label={result.review_status}
          color={REVIEW_COLORS[result.review_status] ?? 'default'}
          sx={{ height: 16, '& .MuiChip-label': { px: 0.75, fontSize: '0.6rem' } }}
        />
      </Box>

      {/* IC50 + R² */}
      <Box sx={{ px: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="caption" color="text.secondary" noWrap>
          {ic50Display ? `IC₅₀ ${ic50Display}` : '—'}
        </Typography>
        {result.r_squared != null && (
          <Typography variant="caption" color="text.secondary">
            R²{result.r_squared.toFixed(2)}
          </Typography>
        )}
      </Box>

      {/* Review buttons */}
      <Box
        sx={{ px: 0.5, display: 'flex', justifyContent: 'flex-end', gap: 0.25 }}
        onClick={(e) => e.stopPropagation()}
      >
        <Tooltip title="Approve">
          <IconButton
            size="small"
            color={result.review_status === 'approved' ? 'success' : 'default'}
            onClick={() => onReview('approved')}
            sx={{ p: 0.25 }}
          >
            <CheckCircleOutlineIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Reject">
          <IconButton
            size="small"
            color={result.review_status === 'rejected' ? 'error' : 'default'}
            onClick={() => onReview('rejected')}
            sx={{ p: 0.25 }}
          >
            <CancelOutlinedIcon fontSize="small" />
          </IconButton>
        </Tooltip>
        <Tooltip title="Flag">
          <IconButton
            size="small"
            color={result.review_status === 'flagged' ? 'warning' : 'default'}
            onClick={() => onReview('flagged')}
            sx={{ p: 0.25 }}
          >
            <FlagOutlinedIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>
    </Box>
  );
};

export default CurveThumbnail;
