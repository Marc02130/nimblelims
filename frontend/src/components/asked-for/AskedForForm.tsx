import React, { useEffect, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Checkbox,
  FormControlLabel,
  TextField,
  Typography,
} from '@mui/material';
import { apiService, ApiService } from '../../services/apiService';

export interface AskedForFormValues {
  sample_ids: string[];
  analysis_id: string;
  tat_days: number;
  params: Record<string, unknown>;
}

interface SampleOption {
  id: string;
  name: string;
}

interface AnalysisOption {
  id: string;
  name: string;
  turnaround_time?: number | null;
}

interface ParamDef {
  id: string;
  key: string;
  data_type: string;
  unit?: string | null;
  required: boolean;
  allowed_values?: unknown[] | null;
  sort_order: number;
}

interface AskedForFormProps {
  sampleIds?: string[];
  sampleOptions?: SampleOption[];
  lockSamples?: boolean;
  onSubmit: (values: AskedForFormValues) => Promise<void> | void;
  onCancel: () => void;
}

const AskedForForm: React.FC<AskedForFormProps> = ({
  sampleIds,
  sampleOptions = [],
  lockSamples = false,
  onSubmit,
  onCancel,
}) => {
  const [analyses, setAnalyses] = useState<AnalysisOption[]>([]);
  const [analysis, setAnalysis] = useState<AnalysisOption | null>(null);
  const [selectedSamples, setSelectedSamples] = useState<SampleOption[]>(
    sampleOptions.filter((s) => (sampleIds || []).includes(s.id))
  );
  const [tatDays, setTatDays] = useState<number>(1);
  const [paramDefs, setParamDefs] = useState<ParamDef[]>([]);
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    apiService
      .getAnalyses({ active: true, size: 500 })
      .then((res) => {
        if (!cancelled) setAnalyses(ApiService.unwrapAnalysesList(res));
      })
      .catch(() => {
        if (!cancelled) setAnalyses([]);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (lockSamples && sampleIds && sampleOptions.length) {
      setSelectedSamples(sampleOptions.filter((s) => sampleIds.includes(s.id)));
    }
  }, [lockSamples, sampleIds, sampleOptions]);

  useEffect(() => {
    if (!analysis?.id) {
      setParamDefs([]);
      setParams({});
      return;
    }
    if (analysis.turnaround_time && analysis.turnaround_time >= 1) {
      setTatDays(analysis.turnaround_time);
    }
    let cancelled = false;
    apiService
      .getAnalysisParamDefs(analysis.id)
      .then((res: { items?: ParamDef[] }) => {
        if (cancelled) return;
        setParamDefs(Array.isArray(res?.items) ? res.items : []);
        setParams({});
      })
      .catch(() => {
        if (!cancelled) {
          setParamDefs([]);
          setParams({});
        }
      });
    return () => {
      cancelled = true;
    };
  }, [analysis]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const ids =
      lockSamples && sampleIds?.length ? sampleIds : selectedSamples.map((s) => s.id);
    if (!ids.length) {
      setError('Select at least one sample.');
      return;
    }
    if (!analysis) {
      setError('Select a requested analysis.');
      return;
    }
    if (!Number.isInteger(tatDays) || tatDays < 1) {
      setError('TAT must be an integer of at least 1 day.');
      return;
    }
    for (const def of paramDefs) {
      if (def.required && (params[def.key] === undefined || params[def.key] === '')) {
        setError(`Param '${def.key}' is required.`);
        return;
      }
    }
    setSaving(true);
    try {
      await onSubmit({
        sample_ids: ids,
        analysis_id: analysis.id,
        tat_days: tatDays,
        params,
      });
    } catch (err: unknown) {
      setError(ApiService.formatError(err, 'Could not record asked-for'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ pt: 1 }}>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Record a requested analysis. This does not assign a test or start work.
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {!lockSamples && (
        <Autocomplete
          multiple
          options={sampleOptions}
          getOptionLabel={(o) => o.name || o.id}
          value={selectedSamples}
          onChange={(_e, value) => setSelectedSamples(value)}
          isOptionEqualToValue={(a, b) => a.id === b.id}
          renderInput={(params) => (
            <TextField {...params} label="Samples" margin="normal" />
          )}
        />
      )}
      <Autocomplete
        options={analyses}
        getOptionLabel={(o) => o.name || o.id}
        value={analysis}
        onChange={(_e, value) => setAnalysis(value)}
        isOptionEqualToValue={(a, b) => a.id === b.id}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Requested analysis"
            margin="normal"
            required
          />
        )}
      />
      <TextField
        label="TAT (days)"
        type="number"
        margin="normal"
        fullWidth
        value={tatDays}
        onChange={(e) => setTatDays(Number(e.target.value))}
        inputProps={{ min: 1, step: 1 }}
        required
      />
      {paramDefs.length > 0 && (
        <Box sx={{ mt: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            Method params
          </Typography>
          {paramDefs.map((def) => (
            <ParamField
              key={def.key}
              def={def}
              value={params[def.key]}
              onChange={(v) => setParams((prev) => ({ ...prev, [def.key]: v }))}
            />
          ))}
        </Box>
      )}
      <Box display="flex" justifyContent="flex-end" gap={1} mt={2}>
        <Button onClick={onCancel} disabled={saving}>
          Cancel
        </Button>
        <Button type="submit" variant="contained" disabled={saving}>
          {saving ? 'Saving…' : 'Record asked-for'}
        </Button>
      </Box>
    </Box>
  );
};

const ParamField: React.FC<{
  def: ParamDef;
  value: unknown;
  onChange: (v: unknown) => void;
}> = ({ def, value, onChange }) => {
  const label = def.unit ? `${def.key} (${def.unit})` : def.key;
  if (def.data_type === 'bool') {
    return (
      <FormControlLabel
        control={
          <Checkbox
            checked={Boolean(value)}
            onChange={(e) => onChange(e.target.checked)}
          />
        }
        label={label + (def.required ? ' *' : '')}
      />
    );
  }
  const allowed = Array.isArray(def.allowed_values) ? def.allowed_values : null;
  if (allowed && allowed.length) {
    return (
      <Autocomplete
        options={allowed.map(String)}
        value={value == null ? null : String(value)}
        onChange={(_e, v) => onChange(v)}
        renderInput={(params) => (
          <TextField
            {...params}
            label={label}
            margin="normal"
            required={def.required}
          />
        )}
      />
    );
  }
  return (
    <TextField
      label={label}
      margin="normal"
      fullWidth
      required={def.required}
      type={def.data_type === 'text' ? 'text' : 'number'}
      value={value == null ? '' : String(value)}
      onChange={(e) => {
        const raw = e.target.value;
        if (raw === '') {
          onChange('');
          return;
        }
        if (def.data_type === 'int') onChange(parseInt(raw, 10));
        else if (def.data_type === 'number') onChange(Number(raw));
        else onChange(raw);
      }}
    />
  );
};

export default AskedForForm;
