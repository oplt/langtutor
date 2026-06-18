import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";

import { ApiError } from "../../../shared/api/httpClient";
import {
  createLlmProfile,
  fetchLlmModels,
  fetchLlmProfileModels,
  updateLlmProfile,
  type LlmProfile,
  type LlmProfileInput,
  type LlmProviderId,
} from "../api/settingsApi";
import { DEFAULT_AI_PROVIDERS, PROVIDER_IDS, PROVIDER_LABELS } from "../aiSettingsDefaults";

const emptyProfile = (): LlmProfileInput => ({
  name: "",
  provider: "ollama",
  api_base: "http://localhost:11434",
  model: "",
  enabled: true,
  api_key: "",
  timeout_seconds: 120,
  temperature: 0.2,
  max_tokens: 2048,
  context_window: 8192,
  streaming: true,
  vision_support: false,
  llama_connection_mode: "external_server",
  llama_command: "",
  llama_config: {
    binary_path: "",
    model_path: "",
    host: "127.0.0.1",
    port: 8080,
    api_base: "http://127.0.0.1:8080/v1",
    context_window: 8192,
    gpu_layers: 0,
    flash_attention: false,
    parallel_slots: 1,
    threads: 0,
    batch_size: 512,
    extra_allowed_args: [],
  },
});

function profileInput(profile: LlmProfile): LlmProfileInput {
  return {
    name: profile.name,
    provider: profile.provider,
    api_base: profile.api_base,
    model: profile.model,
    enabled: profile.enabled,
    api_key: "",
    has_api_key: profile.has_api_key,
    timeout_seconds: profile.timeout_seconds,
    temperature: profile.temperature,
    max_tokens: profile.max_tokens,
    context_window: profile.context_window,
    streaming: profile.streaming,
    vision_support: profile.vision_support,
    llama_connection_mode: profile.llama_connection_mode,
    llama_command: profile.llama_command,
    llama_config: profile.llama_config ?? emptyProfile().llama_config,
  };
}

type Props = {
  open: boolean;
  profile: LlmProfile | null;
  busy: boolean;
  onClose: () => void;
  onSaved: (profile: LlmProfile) => void;
  onBusyChange: (busy: boolean) => void;
};

export function LlmProfileDialog({
  open,
  profile,
  busy,
  onClose,
  onSaved,
  onBusyChange,
}: Props) {
  const [draft, setDraft] = useState<LlmProfileInput>(emptyProfile());
  const [models, setModels] = useState<{ id: string; name: string }[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setDraft(profile ? profileInput(profile) : emptyProfile());
    setModels([]);
    setError(null);
  }, [open, profile]);

  const fetchModels = async () => {
    onBusyChange(true);
    setError(null);
    try {
      const data = profile
        ? await fetchLlmProfileModels(profile.id)
        : await fetchLlmModels(draft.provider);
      setModels(data.models);
      if (!data.models.length) setError("No discovered models. Manual entry is available.");
    } catch (err) {
      setModels([]);
      setError(err instanceof ApiError ? err.message : "Model discovery failed.");
    } finally {
      onBusyChange(false);
    }
  };

  const saveProfile = async () => {
    if (!draft.name.trim()) {
      setError("Display name is required.");
      return;
    }
    onBusyChange(true);
    setError(null);
    try {
      const saved = profile
        ? await updateLlmProfile(profile.id, draft)
        : await createLlmProfile(draft);
      onSaved(saved);
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save profile.");
    } finally {
      onBusyChange(false);
    }
  };

  const onProviderChange = (provider: LlmProviderId) => {
    const defaults = DEFAULT_AI_PROVIDERS[provider];
    setDraft((prev) => ({
      ...prev,
      provider,
      api_base: defaults.api_base,
      timeout_seconds: defaults.timeout_seconds,
    }));
    setModels([]);
  };

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>{profile ? "Edit LLM profile" : "Add LLM profile"}</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ mt: 1 }}>
          {error && <Alert severity="warning">{error}</Alert>}
          <TextField
            label="Display name"
            value={draft.name}
            onChange={(e) => setDraft((prev) => ({ ...prev, name: e.target.value }))}
            fullWidth
          />
          <TextField
            select
            label="Provider"
            value={draft.provider}
            onChange={(e) => onProviderChange(e.target.value as LlmProviderId)}
            fullWidth
          >
            {PROVIDER_IDS.map((id) => (
              <MenuItem key={id} value={id}>
                {PROVIDER_LABELS[id]}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="API base"
            value={draft.api_base}
            onChange={(e) => setDraft((prev) => ({ ...prev, api_base: e.target.value }))}
            fullWidth
          />
          <Stack direction="row" spacing={1}>
            <TextField
              select
              label="Model"
              value={draft.model}
              onChange={(e) => setDraft((prev) => ({ ...prev, model: e.target.value }))}
              fullWidth
            >
              <MenuItem value="">Manual / none</MenuItem>
              {models.map((model) => (
                <MenuItem key={model.id} value={model.id}>
                  {model.name}
                </MenuItem>
              ))}
            </TextField>
            <Button variant="outlined" onClick={fetchModels} disabled={busy}>
              Discover
            </Button>
          </Stack>
          <TextField
            label="API key"
            type="password"
            value={draft.api_key ?? ""}
            onChange={(e) => setDraft((prev) => ({ ...prev, api_key: e.target.value }))}
            fullWidth
            helperText={draft.has_api_key ? "Leave blank to keep existing key." : undefined}
          />
          <TextField
            label="Temperature"
            type="number"
            inputProps={{ min: 0, max: 2, step: 0.1 }}
            value={draft.temperature}
            onChange={(e) =>
              setDraft((prev) => ({ ...prev, temperature: Number(e.target.value) }))
            }
            fullWidth
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" onClick={saveProfile} disabled={busy}>
          Save
        </Button>
      </DialogActions>
    </Dialog>
  );
}
