import { useEffect, useMemo, useState } from "react";
import Header from "../components/Header";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import Divider from "@mui/material/Divider";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import TextField from "@mui/material/TextField";
import MenuItem from "@mui/material/MenuItem";
import {
  fetchAppSettings,
  updateAppSettings,
  updateLlmRouting,
  type LlmProviderId,
} from "../../../modules/settings/api/settingsApi";
import type { PrivacyPrefs } from "../../../modules/settings/api/privacyApi";
import {
  usePrivacyActionMutations,
  usePrivacyAuditLogQuery,
  usePrivacyPreferencesQuery,
  useUpdatePrivacyPreferencesMutation,
} from "../../../modules/settings/hooks/usePrivacyQueries";
import { MemoryWorkbenchPanel } from "../../../modules/memory/components/MemoryWorkbenchPanel";
import { AiSettingsPanel, type AISettingsForm } from "../../../modules/settings/components/AiSettingsPanel";
import { useAuth } from "../../../context/AuthContext";
import {
  DEFAULT_AI_PROVIDERS,
  DEFAULT_LLM_PROFILES,
  DEFAULT_TASK_DEFAULTS,
} from "../../../modules/settings/aiSettingsDefaults";


const defaultPrefs: PrivacyPrefs = {
  allowAnalytics: true,
  retainHistory: true,
  coachPersonalization: true,
  retentionDays: 180,
  goalPreset: "balanced",
};

function normalizeGoalPreset(value: string | undefined): PrivacyPrefs["goalPreset"] {
  if (value === "balanced" || value === "vocabulary" || value === "grammar" || value === "conversation") {
    return value;
  }
  return "balanced";
}

const defaultAiSettings: AISettingsForm = {
  active_provider: "ollama",
  system_prompt:
    "You are a supportive Dutch language tutor. Explain clearly, correct gently, and adapt to the learner's CEFR level.",
  profiles: DEFAULT_LLM_PROFILES,
  default_profile_id: "ollama",
  task_overrides: {},
};

export default function SettingsPage() {
  const { logout } = useAuth();
  const prefsQuery = usePrivacyPreferencesQuery();
  const auditQuery = usePrivacyAuditLogQuery();
  const updatePrefsMutation = useUpdatePrivacyPreferencesMutation();
  const privacyActions = usePrivacyActionMutations();
  const [aiSettings, setAiSettings] = useState<AISettingsForm>(defaultAiSettings);
  const [aiLoading, setAiLoading] = useState(true);
  const [aiSaving, setAiSaving] = useState(false);
  const [prefs, setPrefs] = useState<PrivacyPrefs>(defaultPrefs);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);
  const [serverNotice, setServerNotice] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<"export" | "deleteHistory" | "deleteAccount" | "retentionCleanup" | null>(null);

  const prefsLoading = prefsQuery.isLoading;
  const auditItems = auditQuery.data ?? [];
  const auditLoading = auditQuery.isLoading;

  useEffect(() => {
    let mounted = true;
    const loadAiSettings = async () => {
      setAiLoading(true);
      try {
        const doc = await fetchAppSettings();
        if (!mounted) return;
        setAiSettings({
          active_provider: (doc.ai.active_provider as LlmProviderId) || "ollama",
          system_prompt: doc.ai.system_prompt,
          profiles: doc.ai.profiles?.length ? doc.ai.profiles : DEFAULT_LLM_PROFILES,
          default_profile_id: doc.ai.default_profile_id || "ollama",
          task_overrides: doc.ai.task_overrides ?? {},
        });
      } catch {
        if (mounted) {
          setAiSettings(defaultAiSettings);
          setServerError("Could not load AI settings. Showing defaults.");
        }
      } finally {
        if (mounted) setAiLoading(false);
      }
    };
    void loadAiSettings();
    return () => {
      mounted = false;
    };
  }, []);

  const saveAiSettings = async () => {
    setAiSaving(true);
    setServerError(null);
    setServerNotice(null);
    try {
      const providers = { ...DEFAULT_AI_PROVIDERS };
      await updateAppSettings({
        ai: {
          active_provider: aiSettings.active_provider,
          system_prompt: aiSettings.system_prompt,
          providers,
          task_defaults: DEFAULT_TASK_DEFAULTS,
          profiles: aiSettings.profiles,
          default_profile_id: aiSettings.default_profile_id,
          task_overrides: aiSettings.task_overrides,
        },
      });
      await updateLlmRouting({
        default_profile_id: aiSettings.default_profile_id,
        task_overrides: aiSettings.task_overrides,
      });
      setServerNotice("AI agent settings saved.");
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : "Failed to save AI settings.");
    } finally {
      setAiSaving(false);
    }
  };

  useEffect(() => {
    if (prefsQuery.data) {
      setPrefs({
        ...prefsQuery.data,
        goalPreset: normalizeGoalPreset(prefsQuery.data.goalPreset),
      });
    }
  }, [prefsQuery.data]);

  useEffect(() => {
    if (prefsQuery.error) {
      setServerError(
        prefsQuery.error instanceof Error
          ? prefsQuery.error.message
          : "Failed to load privacy preferences.",
      );
    }
  }, [prefsQuery.error]);

  const privacyStatus = useMemo(() => {
    const enabled = [prefs.allowAnalytics, prefs.retainHistory, prefs.coachPersonalization].filter(Boolean).length;
    if (enabled === 3) return { label: "High personalization", color: "success" as const };
    if (enabled === 0) return { label: "Strict privacy mode", color: "warning" as const };
    return { label: "Balanced privacy", color: "default" as const };
  }, [prefs]);

  const downloadExport = (payload: unknown) => {
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    const date = new Date().toISOString().slice(0, 10);
    link.download = `language-app-export-${date}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const runServerAction = async <T,>(action: () => Promise<T>, successMessage: string): Promise<T | null> => {
    setServerError(null);
    setServerNotice(null);
    try {
      const result = await action();
      setServerNotice(successMessage);
      return result;
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : "Request failed.");
      return null;
    }
  };

  const saveServerPrefs = async (nextPrefs: PrivacyPrefs) => {
    const saved = await runServerAction(
      () => updatePrefsMutation.mutateAsync(nextPrefs),
      "Privacy preferences saved.",
    );
    if (saved) {
      setPrefs(saved);
      setSaveNotice("Preferences synced to your account.");
      window.setTimeout(() => setSaveNotice(null), 2500);
    }
  };

  return (
    <>
      <Header />
      <Box sx={{ width: "100%", maxWidth: { sm: "100%", md: "1700px" } }}>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2, flexWrap: "wrap" }}>
          <Typography component="h2" variant="h6">
            User Settings
          </Typography>
          <Chip size="small" color={privacyStatus.color} label={privacyStatus.label} />
        </Stack>
        {saveNotice && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {saveNotice}
          </Alert>
        )}
        {serverNotice && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {serverNotice}
          </Alert>
        )}
        {serverError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {serverError}
          </Alert>
        )}
        <Stack gap={2}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2 }}>
                <Typography variant="subtitle2">AI Agent Settings</Typography>
                <Button variant="contained" disabled={aiLoading || aiSaving} onClick={() => void saveAiSettings()}>
                  {aiSaving ? <CircularProgress size={16} /> : "Save AI settings"}
                </Button>
              </Stack>
              {aiLoading ? (
                <Stack direction="row" alignItems="center" spacing={1}>
                  <CircularProgress size={16} />
                  <Typography variant="caption" color="text.secondary">
                    Loading AI settings...
                  </Typography>
                </Stack>
              ) : (
                <AiSettingsPanel
                  ai={aiSettings}
                  onAiFieldChange={(field, value) =>
                    setAiSettings((prev) => ({ ...prev, [field]: value }))
                  }
                  onProfilesPersisted={(profiles) =>
                    setAiSettings((prev) => ({ ...prev, profiles }))
                  }
                />
              )}
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <MemoryWorkbenchPanel />
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="subtitle2" gutterBottom>
                Privacy
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure how your account uses learning data. Preferences are saved server-side.
              </Typography>
              {prefsLoading && (
                <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                  <CircularProgress size={16} />
                  <Typography variant="caption" color="text.secondary">
                    Loading preferences...
                  </Typography>
                </Stack>
              )}
              <Stack spacing={1}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={prefs.allowAnalytics}
                      disabled={prefsLoading || busyAction !== null}
                      onChange={(e) => {
                        const nextPrefs = { ...prefs, allowAnalytics: e.target.checked };
                        setPrefs(nextPrefs);
                        void saveServerPrefs(nextPrefs);
                      }}
                    />
                  }
                  label="Allow analytics insights and trends in dashboard cards"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={prefs.retainHistory}
                      disabled={prefsLoading || busyAction !== null}
                      onChange={(e) => {
                        const nextPrefs = { ...prefs, retainHistory: e.target.checked };
                        setPrefs(nextPrefs);
                        void saveServerPrefs(nextPrefs);
                      }}
                    />
                  }
                  label="Retain learning history for longitudinal comparisons"
                />
                <FormControlLabel
                  control={
                    <Switch
                      checked={prefs.coachPersonalization}
                      disabled={prefsLoading || busyAction !== null}
                      onChange={(e) => {
                        const nextPrefs = { ...prefs, coachPersonalization: e.target.checked };
                        setPrefs(nextPrefs);
                        void saveServerPrefs(nextPrefs);
                      }}
                    />
                  }
                  label="Allow AI Tutor to personalize guidance from recent study patterns"
                />
                <TextField
                  select
                  size="small"
                  label="Learning goal preset"
                  value={prefs.goalPreset}
                  disabled={prefsLoading || busyAction !== null}
                  onChange={(e) => {
                    const nextPrefs = { ...prefs, goalPreset: e.target.value as PrivacyPrefs["goalPreset"] };
                    setPrefs(nextPrefs);
                    void saveServerPrefs(nextPrefs);
                  }}
                >
                  <MenuItem value="balanced">Balanced</MenuItem>
                  <MenuItem value="vocabulary">Vocabulary focus</MenuItem>
                  <MenuItem value="grammar">Grammar focus</MenuItem>
                  <MenuItem value="conversation">Conversation focus</MenuItem>
                </TextField>
                <TextField
                  size="small"
                  type="number"
                  label="Retention window (days)"
                  value={prefs.retentionDays}
                  disabled={prefsLoading || busyAction !== null}
                  inputProps={{ min: 7, max: 730 }}
                  onBlur={() => {
                    const normalized = Math.max(7, Math.min(730, Number(prefs.retentionDays || 180)));
                    const nextPrefs = { ...prefs, retentionDays: normalized };
                    setPrefs(nextPrefs);
                    void saveServerPrefs(nextPrefs);
                  }}
                  onChange={(e) => setPrefs((prev) => ({ ...prev, retentionDays: Number(e.target.value || 180) }))}
                />
              </Stack>
              <Divider sx={{ my: 2 }} />
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                <Button
                  variant="outlined"
                  disabled={prefsLoading || busyAction !== null}
                  onClick={() => {
                    setPrefs(defaultPrefs);
                    void saveServerPrefs(defaultPrefs);
                  }}
                >
                  Reset preferences
                </Button>
                <Button
                  variant="text"
                  disabled={busyAction !== null}
                  onClick={() => {
                    setSaveNotice("Local export options reset.");
                    window.setTimeout(() => setSaveNotice(null), 2500);
                  }}
                >
                  Reset local options
                </Button>
                <Button
                  color="info"
                  variant="outlined"
                  disabled={busyAction !== null}
                  onClick={async () => {
                    if (!window.confirm(`Run retention cleanup now for data older than ${prefs.retentionDays} days?`)) return;
                    setBusyAction("retentionCleanup");
                    await runServerAction(
                      () => privacyActions.retentionCleanup.mutateAsync(),
                      "Retention cleanup completed.",
                    );
                    setBusyAction(null);
                  }}
                >
                  {busyAction === "retentionCleanup" ? <CircularProgress size={16} /> : "Run retention cleanup"}
                </Button>
                <Button
                  variant="outlined"
                  disabled={busyAction !== null}
                  onClick={async () => {
                    setBusyAction("export");
                    const payload = await runServerAction(
                      () => privacyActions.exportAccount.mutateAsync(),
                      "Export generated. Download should start automatically.",
                    );
                    if (payload) downloadExport(payload);
                    setBusyAction(null);
                  }}
                >
                  {busyAction === "export" ? <CircularProgress size={16} /> : "Export account data"}
                </Button>
                <Button
                  color="warning"
                  variant="outlined"
                  disabled={busyAction !== null}
                  onClick={async () => {
                    if (!window.confirm("Delete your server-side learning history now? This cannot be undone.")) return;
                    setBusyAction("deleteHistory");
                    await runServerAction(
                      () => privacyActions.deleteHistory.mutateAsync(),
                      "Server-side learning history deleted.",
                    );
                    setBusyAction(null);
                  }}
                >
                  {busyAction === "deleteHistory" ? <CircularProgress size={16} /> : "Delete learning history"}
                </Button>
                <Button
                  color="error"
                  variant="contained"
                  disabled={busyAction !== null}
                  onClick={async () => {
                    if (!window.confirm("Delete your account and associated data? This action is permanent.")) return;
                    setBusyAction("deleteAccount");
                    const ok = await runServerAction(
                      () => privacyActions.deleteAccount.mutateAsync(),
                      "Account deleted. Signing out...",
                    );
                    setBusyAction(null);
                    if (ok) logout();
                  }}
                >
                  {busyAction === "deleteAccount" ? <CircularProgress size={16} /> : "Delete account"}
                </Button>
              </Stack>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
                Export and deletion actions now apply to your authenticated server-side data.
              </Typography>
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
                <Typography variant="subtitle2">Privacy Activity</Typography>
                <Button
                  size="small"
                  variant="text"
                  onClick={() => {
                    void auditQuery.refetch();
                  }}
                >
                  Refresh
                </Button>
              </Stack>
              {auditQuery.error && (
                <Alert severity="error" sx={{ mb: 1 }}>
                  Could not load privacy activity. Try Refresh.
                </Alert>
              )}
              {auditLoading ? (
                <Stack direction="row" alignItems="center" spacing={1}>
                  <CircularProgress size={14} />
                  <Typography variant="caption" color="text.secondary">
                    Loading privacy activity...
                  </Typography>
                </Stack>
              ) : auditItems.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No privacy activity recorded yet.
                </Typography>
              ) : (
                <List dense sx={{ p: 0 }}>
                  {auditItems.map((item) => (
                    <ListItem key={item.id} disableGutters sx={{ py: 0.5 }}>
                      <ListItemText
                        primary={item.action.replaceAll("_", " ")}
                        secondary={item.createdAt ? new Date(item.createdAt).toLocaleString() : "Unknown time"}
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Stack>
      </Box>
    </>
  );
}
