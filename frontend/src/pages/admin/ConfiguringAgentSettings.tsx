import React, { useCallback, useEffect, useState } from 'react';
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
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Typography,
} from '@mui/material';
import { apiService } from '../../services/apiService';

const PROVIDERS = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'xai', label: 'xAI' },
  { value: 'anthropic', label: 'Anthropic' },
] as const;

interface SettingsRow {
  id: string;
  name: string;
  agent_provider: string | null;
  agent_model: string | null;
  key_set: boolean;
}

interface ModelOption {
  id: string;
  display_name?: string;
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

const ConfiguringAgentSettings: React.FC = () => {
  const [settings, setSettings] = useState<SettingsRow | null>(null);
  const [provider, setProvider] = useState('');
  const [model, setModel] = useState('');
  const [models, setModels] = useState<ModelOption[]>([]);
  const [modelsState, setModelsState] = useState<'idle' | 'loading' | 'error' | 'ready'>('idle');
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [keyInput, setKeyInput] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);

  const loadModels = useCallback(async (nextProvider: string) => {
    setModelsState('loading');
    setModelsError(null);
    setModels([]);
    try {
      const payload = await apiService.getConfiguringAgentModels(nextProvider);
      const rows = Array.isArray(payload?.models) ? payload.models : [];
      setModels(rows);
      setModelsState(rows.length ? 'ready' : 'error');
      if (!rows.length) setModelsError("Couldn't load models — check key or try again");
    } catch (err) {
      setModelsState('error');
      setModelsError(errorText(err));
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const row = await apiService.getConfiguringAgentSettings();
        if (cancelled) return;
        setSettings(row);
        setProvider(row.agent_provider || '');
        setModel(row.agent_model || '');
        if (row.agent_provider) {
          await loadModels(row.agent_provider);
        }
      } catch (err) {
        if (!cancelled) setError(errorText(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadModels]);

  const onProvider = async (next: string) => {
    setProvider(next);
    setModel('');
    setNotice(null);
    setBusy(true);
    try {
      const row = await apiService.saveConfiguringAgentSettings(next, null);
      setSettings(row);
      setModel('');
      await loadModels(next);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const saveModel = async () => {
    if (!provider || !model) return;
    setBusy(true);
    setError(null);
    try {
      const row = await apiService.saveConfiguringAgentSettings(provider, model);
      setSettings(row);
      setNotice('Provider and model saved.');
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const saveKey = async () => {
    const secret = keyInput.trim();
    if (!secret) return;
    setBusy(true);
    setError(null);
    try {
      const row = await apiService.setConfiguringAgentKey(secret);
      setSettings(row);
      setKeyInput('');
      setNotice('Key saved.');
      if (provider) await loadModels(provider);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  const clearStoredKey = async () => {
    setConfirmClear(false);
    setBusy(true);
    setError(null);
    try {
      const row = await apiService.clearConfiguringAgentKey();
      setSettings(row);
      setModel('');
      setNotice('Key cleared.');
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" minHeight={240}>
        <CircularProgress />
      </Box>
    );
  }

  const providerLabel = PROVIDERS.find((item) => item.value === provider)?.label || 'provider';

  return (
    <Box sx={{ maxWidth: 720 }}>
      <Typography variant="h4" gutterBottom>
        Configuring agent
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
        Pick one provider and a model from that provider’s live list. The key is stored encrypted and is not shown again.
        {settings ? ` Settings “${settings.name}” id ${settings.id}.` : ''}
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {notice && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setNotice(null)}>
          {notice}
        </Alert>
      )}
      <Box sx={{ mb: 2 }}>
        <Chip label={settings?.key_set ? 'Key set' : 'No key'} color={settings?.key_set ? 'success' : 'default'} />
      </Box>
      <FormControl fullWidth sx={{ mb: 2 }}>
        <InputLabel id="agent-provider-label">Provider</InputLabel>
        <Select
          labelId="agent-provider-label"
          label="Provider"
          value={provider}
          onChange={(event) => onProvider(String(event.target.value))}
          disabled={busy}
        >
          {PROVIDERS.map((item) => (
            <MenuItem key={item.value} value={item.value}>{item.label}</MenuItem>
          ))}
        </Select>
      </FormControl>
      <FormControl fullWidth sx={{ mb: 2 }} disabled={!provider || modelsState === 'loading'}>
        <InputLabel id="agent-model-label">Model</InputLabel>
        <Select
          labelId="agent-model-label"
          label="Model"
          value={model}
          onChange={(event) => setModel(String(event.target.value))}
        >
          <MenuItem value="" disabled>Select a model</MenuItem>
          {models.map((item) => (
            <MenuItem key={item.id} value={item.id}>
              {item.display_name && item.display_name !== item.id ? `${item.display_name} (${item.id})` : item.id}
            </MenuItem>
          ))}
          {model && !models.some((item) => item.id === model) && (
            <MenuItem value={model}>{model}</MenuItem>
          )}
        </Select>
      </FormControl>
      {modelsState === 'loading' && <Typography sx={{ mb: 2 }}>Loading models…</Typography>}
      {modelsError && <Alert severity="warning" sx={{ mb: 2 }}>{modelsError}</Alert>}
      <Button variant="contained" onClick={saveModel} disabled={busy || !provider || !model} sx={{ mb: 3 }}>
        Save model
      </Button>
      <Typography variant="h6" gutterBottom>API key</Typography>
      <TextField
        fullWidth
        type="password"
        label="API key"
        autoComplete="off"
        value={keyInput}
        onChange={(event) => setKeyInput(event.target.value)}
        disabled={!provider || busy}
        helperText="Not shown after save. Not written to the address bar."
        sx={{ mb: 2 }}
      />
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        <Button variant="contained" onClick={saveKey} disabled={busy || !provider || !keyInput.trim()}>
          Set key
        </Button>
        <Button variant="outlined" color="warning" onClick={() => setConfirmClear(true)} disabled={busy || !settings?.key_set}>
          Clear key
        </Button>
      </Box>
      <Dialog open={confirmClear} onClose={() => setConfirmClear(false)}>
        <DialogTitle>Clear key</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {`Clear the ${providerLabel} key? Configuring agent can't call that provider until a key is set again. The selected model is cleared too.`}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmClear(false)}>Cancel</Button>
          <Button color="warning" onClick={clearStoredKey}>Clear key</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ConfiguringAgentSettings;
