import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  TextField,
  Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import { apiService } from '../../services/apiService';

const GROUP_LABEL: Record<string, string> = {
  schema_tables: 'Schema tables',
  schema_columns: 'Schema columns',
  layouts: 'Layouts',
  privileges: 'Privileges',
  relations: 'Relations',
  other: 'Other configuration',
};

const GROUP_ORDER = ['schema_tables', 'schema_columns', 'layouts', 'privileges', 'relations', 'other'];

interface LedgerItem {
  id: string;
  name: string;
  kind: string;
  target_id: string | null;
  detail: string | null;
}

interface ConfigDocument {
  id: string;
  name: string;
  status: string;
  chunk_count: number;
  error_message: string | null;
}

interface RunSummary {
  id: string;
  name: string;
  status: string;
  banner: string | null;
}

interface ConfigurationRow {
  id: string;
  name: string;
  description: string | null;
  documents: ConfigDocument[];
  items: LedgerItem[];
  runs: RunSummary[];
}

interface StepRow {
  id: string;
  position: number;
  group: string;
  target: string;
  action: string;
  why: string;
  decision: string;
  status: string;
  gap: string | null;
  error_message: string | null;
}

interface RunRow {
  id: string;
  name: string;
  configuration_id: string;
  status: string;
  goal_note: string | null;
  banner: string | null;
  error_message: string | null;
  applied_count: number;
  skipped_count: number;
  stopped_count: number;
  steps: StepRow[];
}

function errorText(err: unknown): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => (item && typeof item === 'object' && 'msg' in item ? String(item.msg) : '')).filter(Boolean).join(' ')
      || 'Request failed';
  }
  return 'Request failed';
}

const ConfiguringAgentRun: React.FC = () => {
  const [configurations, setConfigurations] = useState<ConfigurationRow[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [goal, setGoal] = useState('');
  const [run, setRun] = useState<RunRow | null>(null);
  const [feedback, setFeedback] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const selected = configurations.find((row) => row.id === selectedId) || null;

  const refreshList = async (keepId?: string) => {
    const rows = await apiService.getConfigurations();
    setConfigurations(rows);
    const next = keepId || selectedId;
    if (next && rows.some((row: ConfigurationRow) => row.id === next)) {
      setSelectedId(next);
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const rows = await apiService.getConfigurations();
        setConfigurations(rows);
      } catch (err) {
        setError(errorText(err));
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const createNamed = async () => {
    setBusy(true);
    setError(null);
    try {
      const row = await apiService.createConfiguration(name.trim(), description.trim());
      setName('');
      setDescription('');
      await refreshList(row.id);
      setRun(null);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const upload = async (file: File | null) => {
    if (!file || !selectedId) return;
    setBusy(true);
    setError(null);
    try {
      await apiService.uploadConfigurationDocument(selectedId, file);
      await refreshList(selectedId);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const start = async () => {
    if (!selectedId) return;
    setBusy(true);
    setError(null);
    try {
      const created = await apiService.startConfigurationRun(selectedId, goal.trim());
      setRun(created);
      await refreshList(selectedId);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const mutate = async (action: () => Promise<RunRow>) => {
    setBusy(true);
    setError(null);
    try {
      const next = await action();
      setRun(next);
      if (selectedId) await refreshList(selectedId);
    } catch (err) {
      setError(errorText(err));
      if (run) {
        try {
          setRun(await apiService.getConfigurationRun(run.id));
        } catch {
          /* keep the run already on screen */
        }
      }
    } finally {
      setBusy(false);
    }
  };

  const grouped = useMemo(() => {
    const steps = run?.steps || [];
    return GROUP_ORDER.map((group) => ({
      group,
      label: GROUP_LABEL[group],
      steps: steps.filter((step) => step.group === group),
    })).filter((group) => group.steps.length > 0);
  }, [run]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" minHeight={240}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Configuring agent</Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
        A configuration has a name and an id. Lab files and the list of what was configured stay on that configuration.
        Apply writes accepted steps together. If one step cannot be done, every change from that apply is undone.
      </Typography>
      <Button component={RouterLink} to="/admin/settings/configuring-agent" sx={{ mb: 2 }}>
        Provider settings
      </Button>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>
      )}

      <Typography variant="h6">New configuration</Typography>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, maxWidth: 640, mb: 3 }}>
        <TextField label="Name" value={name} onChange={(event) => setName(event.target.value)} fullWidth />
        <TextField label="Description" value={description} onChange={(event) => setDescription(event.target.value)} fullWidth />
        <Button variant="contained" onClick={createNamed} disabled={busy || !name.trim()} sx={{ alignSelf: 'flex-start' }}>
          Create
        </Button>
      </Box>

      <Typography variant="h6">Configurations</Typography>
      {configurations.length === 0 && <Typography sx={{ mb: 2 }}>No configurations yet.</Typography>}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
        {configurations.map((row) => (
          <Chip
            key={row.id}
            label={row.name}
            color={row.id === selectedId ? 'primary' : 'default'}
            onClick={() => {
              setSelectedId(row.id);
              setRun(null);
            }}
          />
        ))}
      </Box>

      {selected && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1">{selected.name}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>Id {selected.id}</Typography>
          {selected.description && <Typography sx={{ mb: 1 }}>{selected.description}</Typography>}
          <Button variant="outlined" component="label" disabled={busy} sx={{ mb: 1 }}>
            Add lab file
            <input
              hidden
              type="file"
              accept=".pdf,.docx,.txt,.csv,.md,.json,application/pdf,text/plain"
              onChange={(event) => {
                const file = event.target.files?.[0] || null;
                event.target.value = '';
                upload(file);
              }}
            />
          </Button>
          <List dense>
            {selected.documents.map((doc) => (
              <ListItem key={doc.id} disablePadding>
                <ListItemText
                  primary={`${doc.name} · ${doc.status} · ${doc.chunk_count} chunks`}
                  secondary={doc.error_message || `Document id ${doc.id}`}
                />
              </ListItem>
            ))}
          </List>
          <Typography variant="subtitle2" sx={{ mt: 1 }}>Configuration done</Typography>
          {selected.items.length === 0 && <Typography variant="body2">Nothing stored yet.</Typography>}
          <List dense>
            {selected.items.map((item) => (
              <ListItem key={item.id} disablePadding>
                <ListItemText
                  primary={`${item.name} · ${item.kind}`}
                  secondary={`Id ${item.id}${item.target_id ? ` · target ${item.target_id}` : ''}`}
                />
              </ListItem>
            ))}
          </List>
          <TextField
            label="Goal note (optional)"
            value={goal}
            onChange={(event) => setGoal(event.target.value)}
            fullWidth
            sx={{ mt: 1, mb: 1 }}
            helperText="A note is not lab input. Add a file before starting."
          />
          <Button variant="contained" onClick={start} disabled={busy || selected.documents.every((doc) => doc.status !== 'ready')}>
            Start run
          </Button>
          {selected.runs.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2">Earlier runs</Typography>
              {selected.runs.map((item) => (
                <Button
                  key={item.id}
                  size="small"
                  onClick={() => mutate(() => apiService.getConfigurationRun(item.id))}
                  disabled={busy}
                >
                  {item.name} · {item.status}
                </Button>
              ))}
            </Box>
          )}
        </Box>
      )}

      {run && (
        <Box>
          <Divider sx={{ mb: 2 }} />
          <Typography variant="h6">{run.name}</Typography>
          <Typography variant="body2" sx={{ mb: 1 }}>
            Run id {run.id} · {run.status} · applied {run.applied_count} · skipped {run.skipped_count} · stopped {run.stopped_count}
          </Typography>
          {run.banner && <Alert severity="warning" sx={{ mb: 2 }}>{run.banner}</Alert>}
          {run.error_message && <Alert severity="error" sx={{ mb: 2 }}>{run.error_message}</Alert>}
          {grouped.map((group) => (
            <Box key={group.group} sx={{ mb: 2 }}>
              <Typography variant="subtitle1">{group.label}</Typography>
              {group.steps.map((step) => (
                <Box key={step.id} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1.5, mb: 1 }}>
                  <Typography variant="subtitle2">{step.target}</Typography>
                  <Typography>{step.action}</Typography>
                  <Typography variant="body2" color="text.secondary">{step.why}</Typography>
                  <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                    {step.decision} · {step.status}
                  </Typography>
                  {step.gap && <Alert severity="warning" sx={{ mt: 1 }}>{step.gap}</Alert>}
                  {step.error_message && <Alert severity="error" sx={{ mt: 1 }}>{step.error_message}</Alert>}
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 1 }}>
                    <Button
                      size="small"
                      variant="contained"
                      disabled={busy || Boolean(step.gap) || step.status === 'stopped' || step.status === 'applied'}
                      onClick={() => mutate(() => apiService.acceptConfigurationStep(run.id, step.id))}
                    >
                      Accept
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      disabled={busy || step.status === 'applied'}
                      onClick={() => mutate(() => apiService.skipConfigurationStep(run.id, step.id))}
                    >
                      Skip
                    </Button>
                  </Box>
                  <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, gap: 1, mt: 1 }}>
                    <TextField
                      size="small"
                      fullWidth
                      label="Feedback"
                      value={feedback[step.id] || ''}
                      onChange={(event) => setFeedback((prev) => ({ ...prev, [step.id]: event.target.value }))}
                    />
                    <Button
                      size="small"
                      disabled={busy || !(feedback[step.id] || '').trim()}
                      onClick={() => mutate(() => apiService.redoConfigurationStep(run.id, step.id, feedback[step.id]))}
                    >
                      Redo
                    </Button>
                  </Box>
                </Box>
              ))}
            </Box>
          ))}
          <Button
            variant="contained"
            disabled={busy || !run.steps.some((step) => step.decision === 'accepted') || run.status === 'done'}
            onClick={() => mutate(() => apiService.applyConfigurationRun(run.id))}
          >
            Apply accepted steps
          </Button>
          {run.status === 'done' && (
            <Typography sx={{ mt: 2 }}>
              Applied changes are on the configuration ledger. Open Schema, Lists, or Roles to review them. This screen does not edit those records.
            </Typography>
          )}
        </Box>
      )}
    </Box>
  );
};

export default ConfiguringAgentRun;
