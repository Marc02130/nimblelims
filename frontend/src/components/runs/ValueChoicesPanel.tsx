import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Checkbox,
  FormControlLabel,
  Radio,
  RadioGroup,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { apiService } from '../../services/apiService';

interface ChoiceOption {
  lims_run_id: string;
  run_name: string;
  run_status: string;
  status_reason?: string | null;
  raw_result: string;
  source: string;
  counts_as_failed?: boolean;
}

interface ValueChoice {
  sample_id: string;
  sample_name?: string | null;
  client_sample_id?: string | null;
  analyte_id: string;
  analyte_name: string;
  replicate: number;
  options: ChoiceOption[];
  accepted_lims_run_id?: string | null;
  accepted_value?: string | null;
  acceptance_reason?: string | null;
}

interface ValueChoicesPanelProps {
  runId: string;
}

const rowKey = (row: ValueChoice) => `${row.sample_id}:${row.analyte_id}:${row.replicate}`;

const isFailedOption = (opt?: ChoiceOption) =>
  Boolean(opt && (opt.counts_as_failed || opt.run_status === 'failed'));

const optionStatus = (opt: ChoiceOption) =>
  opt.run_status !== 'failed' && opt.counts_as_failed
    ? `${opt.run_status}, counts as failed`
    : opt.run_status;

const ValueChoicesPanel: React.FC<ValueChoicesPanelProps> = ({ runId }) => {
  const [rows, setRows] = useState<ValueChoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [picks, setPicks] = useState<Record<string, string>>({});
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [overrides, setOverrides] = useState<Record<string, boolean>>({});
  const [savingKey, setSavingKey] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiService.getLimsRunValueChoices(runId);
      const list: ValueChoice[] = Array.isArray(data) ? data : [];
      setRows(list);
      const next: Record<string, string> = {};
      list.forEach((row) => {
        if (row.accepted_lims_run_id) next[rowKey(row)] = row.accepted_lims_run_id;
      });
      setPicks(next);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Could not load value choices');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [runId]);

  const accept = async (row: ValueChoice) => {
    const key = rowKey(row);
    const accepted = picks[key];
    const reason = (reasons[key] || '').trim();
    const selected = row.options.find((opt) => opt.lims_run_id === accepted);
    const fromFailed = isFailedOption(selected);
    if (!accepted || !reason || (fromFailed && !overrides[key])) {
      setError(
        fromFailed
          ? 'Pick a value, confirm the failed run, and enter a reason'
          : 'Pick a value and enter a reason'
      );
      return;
    }
    setSavingKey(key);
    setError(null);
    try {
      await apiService.acceptLimsRunValue(runId, {
        sample_id: row.sample_id,
        analyte_id: row.analyte_id,
        replicate: row.replicate,
        accepted_lims_run_id: accepted,
        reason,
        override_failed: fromFailed,
      });
      await load();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Could not save the accepted value');
    } finally {
      setSavingKey(null);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" py={2}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (rows.length === 0) {
    return null;
  }

  return (
    <Card variant="outlined" sx={{ mt: 2 }} data-testid="value-choices">
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Accepted value
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          This run replaces another run. Pick which value is accepted. Both values stay.
          Nothing is deleted.
        </Typography>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Sample</TableCell>
              <TableCell>Analyte</TableCell>
              <TableCell>Rep</TableCell>
              <TableCell>Values</TableCell>
              <TableCell>Reason</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row) => {
              const key = rowKey(row);
              const selected = row.options.find((opt) => opt.lims_run_id === picks[key]);
              const fromFailed = isFailedOption(selected);
              return (
                <TableRow key={key}>
                  <TableCell>
                    {row.client_sample_id || row.sample_name || row.sample_id}
                  </TableCell>
                  <TableCell>{row.analyte_name}</TableCell>
                  <TableCell>{row.replicate}</TableCell>
                  <TableCell>
                    <RadioGroup
                      value={picks[key] || ''}
                      onChange={(e) => setPicks((prev) => ({ ...prev, [key]: e.target.value }))}
                    >
                      {row.options.map((opt) => (
                        <FormControlLabel
                          key={opt.lims_run_id}
                          value={opt.lims_run_id}
                          control={<Radio size="small" />}
                          label={`${opt.run_name} (${optionStatus(opt)}): ${opt.raw_result}`}
                        />
                      ))}
                    </RadioGroup>
                    {fromFailed && (
                      <FormControlLabel
                        control={
                          <Checkbox
                            size="small"
                            checked={Boolean(overrides[key])}
                            onChange={(e) =>
                              setOverrides((prev) => ({ ...prev, [key]: e.target.checked }))
                            }
                            inputProps={{ 'aria-label': `Override failed run for ${row.client_sample_id || row.sample_name}` }}
                          />
                        }
                        label="Accept this value from a failed run"
                      />
                    )}
                    {row.accepted_value && (
                      <Typography variant="caption" color="text.secondary">
                        Accepted: {row.accepted_value}
                        {row.acceptance_reason ? ` — ${row.acceptance_reason}` : ''}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <TextField
                      size="small"
                      value={reasons[key] || ''}
                      onChange={(e) =>
                        setReasons((prev) => ({ ...prev, [key]: e.target.value }))
                      }
                      placeholder="Why this value"
                      inputProps={{ 'aria-label': `Reason for ${row.client_sample_id || row.sample_name}` }}
                    />
                  </TableCell>
                  <TableCell>
                    <Button
                      size="small"
                      variant="contained"
                      disabled={
                        savingKey === key ||
                        !picks[key] ||
                        !(reasons[key] || '').trim() ||
                        (fromFailed && !overrides[key])
                      }
                      onClick={() => void accept(row)}
                    >
                      Accept
                    </Button>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
};

export default ValueChoicesPanel;
