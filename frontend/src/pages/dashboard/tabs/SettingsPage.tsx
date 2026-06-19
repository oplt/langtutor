import { useEffect, useMemo, useState } from "react";
import Header from "../components/Header";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Alert from "@mui/material/Alert";
import CircularProgress from "@mui/material/CircularProgress";
import {
  type LlmProviderId,
} from "../../../modules/settings/api/settingsApi";
import { useAppSettingsQuery, useSaveAiSettingsMutation } from "../../../modules/settings/hooks/useSettingsQueries";
import type { PrivacyPrefs } from "../../../modules/settings/api/privacyApi";
import {
  usePrivacyActionMutations,
  usePrivacyAuditLogQuery,
  usePrivacyPreferencesQuery,
  useUpdatePrivacyPreferencesMutation,
} from "../../../modules/settings/hooks/usePrivacyQueries";
import { SettingsMemorySection } from "../../../modules/settings/components/SettingsMemorySection";
import { SettingsPrivacyAuditCard } from "../../../modules/settings/components/SettingsPrivacyAuditCard";
import { SettingsPrivacyCard } from "../../../modules/settings/components/SettingsPrivacyCard";
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
  const settingsQuery = useAppSettingsQuery();
  const saveAiSettingsMutation = useSaveAiSettingsMutation();
  const [aiSettings, setAiSettings] = useState<AISettingsForm>(defaultAiSettings);
  const aiLoading = settingsQuery.isLoading;
  const aiSaving = saveAiSettingsMutation.isPending;
  const [prefs, setPrefs] = useState<PrivacyPrefs>(defaultPrefs);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);
  const [serverNotice, setServerNotice] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);
  const [busyAction, setBusyAction] = useState<"export" | "deleteHistory" | "deleteAccount" | "retentionCleanup" | null>(null);

  const prefsLoading = prefsQuery.isLoading;
  const auditItems = auditQuery.data ?? [];
  const auditLoading = auditQuery.isLoading;

  useEffect(() => {
    if (!settingsQuery.data) return;
    const doc = settingsQuery.data;
    setAiSettings({
      active_provider: (doc.ai.active_provider as LlmProviderId) || "ollama",
      system_prompt: doc.ai.system_prompt,
      profiles: doc.ai.profiles?.length ? doc.ai.profiles : DEFAULT_LLM_PROFILES,
      default_profile_id: doc.ai.default_profile_id || "ollama",
      task_overrides: doc.ai.task_overrides ?? {},
    });
  }, [settingsQuery.data]);

  useEffect(() => {
    if (!settingsQuery.error) return;
    setAiSettings(defaultAiSettings);
    setServerError("Could not load AI settings. Showing defaults.");
  }, [settingsQuery.error]);

  const saveAiSettings = async () => {
    setServerError(null);
    setServerNotice(null);
    try {
      const providers = { ...DEFAULT_AI_PROVIDERS };
      await saveAiSettingsMutation.mutateAsync({
        doc: {
          ai: {
            active_provider: aiSettings.active_provider,
            system_prompt: aiSettings.system_prompt,
            providers,
            task_defaults: DEFAULT_TASK_DEFAULTS,
            profiles: aiSettings.profiles,
            default_profile_id: aiSettings.default_profile_id,
            task_overrides: aiSettings.task_overrides,
          },
        },
        routing: {
          default_profile_id: aiSettings.default_profile_id,
          task_overrides: aiSettings.task_overrides,
        },
      });
      setServerNotice("AI agent settings saved.");
    } catch (err: unknown) {
      setServerError(err instanceof Error ? err.message : "Failed to save AI settings.");
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
    const previous = prefsQuery.data ?? prefs;
    const saved = await runServerAction(
      () => updatePrefsMutation.mutateAsync(nextPrefs),
      "Privacy preferences saved.",
    );
    if (saved) {
      setPrefs(saved);
      setSaveNotice("Preferences synced to your account.");
      window.setTimeout(() => setSaveNotice(null), 2500);
    } else {
      setPrefs({
        ...previous,
        goalPreset: normalizeGoalPreset(previous.goalPreset),
      });
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
              <SettingsMemorySection />
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <SettingsPrivacyCard
                prefs={prefs}
                prefsLoading={prefsLoading}
                busyAction={busyAction}
                onPrefsChange={setPrefs}
                onSavePrefs={saveServerPrefs}
                onRetentionCleanup={async () => {
                  if (!window.confirm(`Run retention cleanup now for data older than ${prefs.retentionDays} days?`)) return;
                  setBusyAction("retentionCleanup");
                  await runServerAction(
                    () => privacyActions.retentionCleanup.mutateAsync(),
                    "Retention cleanup completed.",
                  );
                  setBusyAction(null);
                }}
                onExport={async () => {
                  setBusyAction("export");
                  const payload = await runServerAction(
                    () => privacyActions.exportAccount.mutateAsync(),
                    "Export generated. Download should start automatically.",
                  );
                  if (payload) downloadExport(payload);
                  setBusyAction(null);
                }}
                onDeleteHistory={async () => {
                  if (!window.confirm("Delete your server-side learning history now? This cannot be undone.")) return;
                  setBusyAction("deleteHistory");
                  await runServerAction(
                    () => privacyActions.deleteHistory.mutateAsync(),
                    "Server-side learning history deleted.",
                  );
                  setBusyAction(null);
                }}
                onDeleteAccount={async () => {
                  if (!window.confirm("Delete your account and associated data? This action is permanent.")) return;
                  setBusyAction("deleteAccount");
                  const ok = await runServerAction(
                    () => privacyActions.deleteAccount.mutateAsync(),
                    "Account deleted. Signing out...",
                  );
                  setBusyAction(null);
                  if (ok) logout();
                }}
              />
            </CardContent>
          </Card>
          <Card variant="outlined">
            <CardContent>
              <SettingsPrivacyAuditCard
                items={auditItems}
                loading={auditLoading}
                error={auditQuery.error instanceof Error ? auditQuery.error : null}
                onRefresh={() => {
                  void auditQuery.refetch();
                }}
              />
            </CardContent>
          </Card>
        </Stack>
      </Box>
    </>
  );
}
