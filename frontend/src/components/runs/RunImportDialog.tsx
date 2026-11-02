import React, { useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Typography,
} from '@mui/material';

export interface ParserOption {
  id: string;
  name: string;
  version?: number;
  instrument_id?: string | null;
  cro_source_id?: string | null;
  instrument_type_id?: string | null;
}

export interface UnmatchedImportRow {
  row_index: number;
  well_position?: string | null;
  sample_key?: string | null;
  reason: string;
}

export interface ImportFileResult {
  imported: number;
  skipped: number;
  linked?: number;
  unmatched_count?: number;
  unmatched?: UnmatchedImportRow[];
  warnings?: string[];
}

interface RunImportDialogProps {
  open: boolean;
  parsers: ParserOption[];
  submitting: boolean;
  error: string | null;
  result: ImportFileResult | null;
  onClose: () => void;
  onSubmit: (parser: ParserOption, file: File) => void;
}

const RunImportDialog: React.FC<RunImportDialogProps> = ({
  open,
  parsers,
  submitting,
  error,
  result,
  onClose,
  onSubmit,
}) => {
  const [parserId, setParserId] = useState('');
  const [file, setFile] = useState<File | null>(null);

  const selected = parsers.find((p) => p.id === parserId) || null;

  const handleClose = () => {
    if (submitting) return;
    setFile(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Import instrument file</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Pick the parser for this analysis and upload the reader export. Rows that do not
          match a sample are kept and listed here.
        </Typography>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        {result && (
          <Alert severity={result.unmatched_count ? 'warning' : 'success'} sx={{ mb: 2 }}>
            Imported {result.imported} row{result.imported === 1 ? '' : 's'}. Linked{' '}
            {result.linked ?? 0}. Unmatched {result.unmatched_count ?? 0}.
            {(result.warnings || []).length > 0 && (
              <Box component="ul" sx={{ m: 0, pl: 2, mt: 1 }}>
                {result.warnings!.slice(0, 5).map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </Box>
            )}
          </Alert>
        )}
        {result?.unmatched && result.unmatched.length > 0 && (
          <Box sx={{ mb: 2, maxHeight: 200, overflow: 'auto' }}>
            <Typography variant="subtitle2">Unmatched rows (kept)</Typography>
            <Box component="ul" sx={{ m: 0, pl: 2 }}>
              {result.unmatched.slice(0, 20).map((row) => (
                <li key={`${row.row_index}-${row.sample_key || ''}`}>
                  {row.well_position ? `${row.well_position}: ` : ''}
                  {row.sample_key || '(blank)'} — {row.reason}
                </li>
              ))}
            </Box>
            {result.unmatched.length > 20 && (
              <Typography variant="caption">
                And {result.unmatched.length - 20} more.
              </Typography>
            )}
          </Box>
        )}
        <FormControl fullWidth size="small" sx={{ mb: 2 }} required>
          <InputLabel id="import-parser-label">Parser</InputLabel>
          <Select
            labelId="import-parser-label"
            label="Parser"
            value={parserId}
            onChange={(e) => setParserId(String(e.target.value))}
            inputProps={{ 'data-testid': 'import-parser' }}
          >
            {parsers.length === 0 && (
              <MenuItem value="" disabled>
                No active parser for this analysis
              </MenuItem>
            )}
            {parsers.map((p) => (
              <MenuItem key={p.id} value={p.id}>
                {p.name}
                {p.version ? ` (v${p.version})` : ''}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button variant="outlined" component="label" data-testid="import-file-button">
          {file ? file.name : 'Choose file'}
          <input
            type="file"
            hidden
            data-testid="import-file-input"
            accept=".csv,text/csv,text/plain"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </Button>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={submitting}>
          Close
        </Button>
        <Button
          variant="contained"
          data-testid="import-submit"
          disabled={submitting || !selected || !file}
          onClick={() => {
            if (selected && file) onSubmit(selected, file);
          }}
        >
          {submitting ? 'Importing…' : 'Import'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default RunImportDialog;
