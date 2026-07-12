import React from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Paper,
} from '@mui/material';
import type { PromotionPreview, PromotionPreviewItem } from '../../services/apiService';

const MAX_DETAIL_ROWS = 40;

interface PublishPromotionDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  hasAnalysis: boolean;
  analysisName?: string | null;
  preview: PromotionPreview | null;
  loading: boolean;
  loadError: string | null;
  publishing: boolean;
}

const shortId = (id?: string | null) =>
  id ? `${id.slice(0, 8)}…` : '—';

const ItemsTable: React.FC<{
  title: string;
  items: PromotionPreviewItem[];
  emptyLabel: string;
  tone?: 'default' | 'error';
}> = ({ title, items, emptyLabel, tone = 'default' }) => {
  if (items.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        {emptyLabel}
      </Typography>
    );
  }
  const shown = items.slice(0, MAX_DETAIL_ROWS);
  return (
    <Box sx={{ mb: 2 }}>
      <Typography
        variant="subtitle2"
        color={tone === 'error' ? 'error' : 'text.primary'}
        sx={{ mb: 0.5 }}
      >
        {title} ({items.length}
        {items.length > MAX_DETAIL_ROWS ? `, showing ${MAX_DETAIL_ROWS}` : ''})
      </Typography>
      <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 220 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Analyte</TableCell>
              <TableCell>Value</TableCell>
              <TableCell>Rep</TableCell>
              <TableCell>Sample</TableCell>
              <TableCell>Match</TableCell>
              {tone === 'error' && <TableCell>Message</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {shown.map((item, idx) => (
              <TableRow key={`${item.analyte_id}-${item.replicate}-${item.sample_id}-${idx}`}>
                <TableCell>{item.analyte_name || item.column_key || '—'}</TableCell>
                <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                  {item.raw_result ?? '—'}
                </TableCell>
                <TableCell>{item.replicate ?? 1}</TableCell>
                <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                  {shortId(item.sample_id)}
                </TableCell>
                <TableCell>{item.match_via || '—'}</TableCell>
                {tone === 'error' && (
                  <TableCell sx={{ fontSize: '0.75rem' }}>{item.message || '—'}</TableCell>
                )}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

const PublishPromotionDialog: React.FC<PublishPromotionDialogProps> = ({
  open,
  onClose,
  onConfirm,
  hasAnalysis,
  analysisName,
  preview,
  loading,
  loadError,
  publishing,
}) => {
  const hasConflicts = (preview?.conflict_count ?? 0) > 0;
  const canPublish =
    !loading &&
    !loadError &&
    !publishing &&
    (!hasAnalysis || (preview != null && !hasConflicts));

  const creates = (preview?.items || []).filter((i) => i.action === 'create');
  const updates = (preview?.items || []).filter((i) => i.action === 'update');
  const conflicts = (preview?.items || []).filter((i) => i.action === 'conflict');

  return (
    <Dialog open={open} onClose={publishing ? undefined : onClose} maxWidth="md" fullWidth>
      <DialogTitle>Publish run</DialogTitle>
      <DialogContent dividers>
        {!hasAnalysis && (
          <>
            <Alert severity="warning" sx={{ mb: 2 }}>
              No analysis is associated with this run. Publishing will <strong>not</strong> write
              Tests or Results from imported instrument data.
            </Alert>
            <DialogContentText>
              Continue only if this is intentional (e.g. non-reportable plate QC). You can cancel
              and leave the run in complete status.
            </DialogContentText>
          </>
        )}

        {hasAnalysis && (
          <>
            <DialogContentText sx={{ mb: 2 }}>
              Publishing will write structured Tests and Results for analysis
              {analysisName ? (
                <>
                  {' '}
                  <strong>{analysisName}</strong>
                </>
              ) : null}
              . Review the dry-run plan below before confirming.
            </DialogContentText>

            {loading && (
              <Box display="flex" alignItems="center" gap={1.5} py={3}>
                <CircularProgress size={24} />
                <Typography color="text.secondary">Building promotion preview…</Typography>
              </Box>
            )}

            {loadError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {loadError}
              </Alert>
            )}

            {!loading && !loadError && preview && (
              <>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
                  <Chip
                    size="small"
                    color="success"
                    label={`Create ${preview.create_count}`}
                  />
                  <Chip
                    size="small"
                    color="info"
                    label={`Update ${preview.update_count}`}
                  />
                  <Chip
                    size="small"
                    color={preview.conflict_count > 0 ? 'error' : 'default'}
                    label={`Conflict ${preview.conflict_count}`}
                  />
                  <Chip
                    size="small"
                    color={preview.unresolved_columns?.length ? 'warning' : 'default'}
                    label={`Unresolved cols ${preview.unresolved_columns?.length ?? 0}`}
                  />
                  {preview.missing_sample_rows > 0 && (
                    <Chip
                      size="small"
                      color="warning"
                      label={`Missing sample ${preview.missing_sample_rows}`}
                    />
                  )}
                  {preview.skip_count > 0 && (
                    <Chip size="small" variant="outlined" label={`Skipped ${preview.skip_count}`} />
                  )}
                </Stack>

                {hasConflicts && (
                  <Alert severity="error" sx={{ mb: 2 }}>
                    Publish is blocked: some results already exist from another run or manual entry.
                    Resolve conflicts (or clear the conflicting results) before publishing.
                  </Alert>
                )}

                {preview.errors?.length > 0 && (
                  <Alert severity={hasConflicts ? 'error' : 'warning'} sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Messages
                    </Typography>
                    <Box component="ul" sx={{ m: 0, pl: 2 }}>
                      {preview.errors.slice(0, 12).map((e, i) => (
                        <li key={i}>
                          <Typography variant="body2">{e}</Typography>
                        </li>
                      ))}
                    </Box>
                  </Alert>
                )}

                {preview.unresolved_columns?.length > 0 && (
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Unresolved columns (no analyte name/alias match)
                    </Typography>
                    <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                      {preview.unresolved_columns.map((col) => (
                        <Chip key={col} size="small" label={col} variant="outlined" color="warning" />
                      ))}
                    </Stack>
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                      Add analyte aliases or rename columns; unresolved values are not written.
                    </Typography>
                  </Box>
                )}

                {!hasConflicts &&
                  preview.create_count === 0 &&
                  preview.update_count === 0 && (
                    <Alert severity="warning" sx={{ mb: 2 }}>
                      No results will be created or updated. Check that imported rows have sample IDs
                      and column headers match analyte names or aliases.
                    </Alert>
                  )}

                <ItemsTable
                  title="Conflicts"
                  items={conflicts}
                  emptyLabel="No conflicts."
                  tone="error"
                />
                <ItemsTable
                  title="Will create"
                  items={creates}
                  emptyLabel="No new results will be created."
                />
                <ItemsTable
                  title="Will update (this run)"
                  items={updates}
                  emptyLabel="No existing results from this run will be updated."
                />

                {preview.items_truncated && (
                  <Typography variant="caption" color="text.secondary">
                    Item list truncated in API response; counts above are complete.
                  </Typography>
                )}
              </>
            )}
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={publishing}>
          Cancel
        </Button>
        <Button
          variant="contained"
          color={hasConflicts ? 'error' : 'success'}
          disabled={!canPublish}
          onClick={onConfirm}
        >
          {publishing ? 'Publishing…' : hasConflicts ? 'Cannot publish' : 'Confirm publish'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PublishPromotionDialog;
