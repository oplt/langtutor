import { useMemo, useState } from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  IconButton,
  MenuItem,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import Grid from "@mui/material/Grid2";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import NetworkCheckIcon from "@mui/icons-material/NetworkCheck";
import AddIcon from "@mui/icons-material/Add";

import {
  deleteLlmProfile,
  fetchLlmProfiles,
  testLlmProfile,
  type LlmProfile,
  type LlmProviderId,
  type LlmTaskName,
} from "../api/settingsApi";
import { AdvancedTaskRouting } from "./AdvancedTaskRouting";
import { LlmProfileDialog } from "./LlmProfileDialog";

export type AISettingsForm = {
  active_provider: LlmProviderId;
  system_prompt: string;
  profiles: LlmProfile[];
  default_profile_id: string;
  task_overrides: Partial<Record<LlmTaskName, string>>;
};

type Props = {
  ai: AISettingsForm;
  onAiFieldChange: (field: keyof AISettingsForm, value: unknown) => void;
  onProfilesPersisted?: (profiles: LlmProfile[]) => void;
};

export function AiSettingsPanel({ ai, onAiFieldChange, onProfilesPersisted }: Props) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingProfile, setEditingProfile] = useState<LlmProfile | null>(null);
  const [statusById, setStatusById] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const defaultProfile = useMemo(
    () => ai.profiles.find((profile) => profile.id === ai.default_profile_id),
    [ai.default_profile_id, ai.profiles],
  );

  const setProfiles = (profiles: LlmProfile[]) => onAiFieldChange("profiles", profiles);

  const setDefaultProfile = (profileId: string) => {
    onAiFieldChange("default_profile_id", profileId);
    const profile = ai.profiles.find((item) => item.id === profileId);
    if (profile) onAiFieldChange("active_provider", profile.provider);
  };

  const openAdd = () => {
    setEditingProfile(null);
    setError(null);
    setDialogOpen(true);
  };

  const openEdit = (profile: LlmProfile) => {
    setEditingProfile(profile);
    setError(null);
    setDialogOpen(true);
  };

  const handleSavedProfile = async (saved: LlmProfile) => {
    setError(null);
    try {
      const { profiles } = await fetchLlmProfiles();
      if (onProfilesPersisted) onProfilesPersisted(profiles);
      else setProfiles(profiles);
      setSuccess(`Saved LLM profile "${saved.name}".`);
      if (!ai.default_profile_id) setDefaultProfile(saved.id);
    } catch (err) {
      const fallback = editingProfile
        ? ai.profiles.map((profile) => (profile.id === saved.id ? saved : profile))
        : [...ai.profiles, saved];
      if (onProfilesPersisted) onProfilesPersisted(fallback);
      else setProfiles(fallback);
      setError(err instanceof Error ? err.message : "Profile saved, but refresh failed.");
    }
  };

  const removeProfile = async (profileId: string) => {
    setBusy(profileId);
    setError(null);
    try {
      await deleteLlmProfile(profileId);
      const next = ai.profiles.filter((profile) => profile.id !== profileId);
      setProfiles(next);
      if (ai.default_profile_id === profileId) setDefaultProfile(next[0]?.id ?? "");
      onAiFieldChange(
        "task_overrides",
        Object.fromEntries(
          Object.entries(ai.task_overrides).filter(([, routedId]) => routedId !== profileId),
        ),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete LLM profile.");
    } finally {
      setBusy(null);
    }
  };

  const testProfile = async (profileId: string) => {
    setBusy(profileId);
    try {
      const result = await testLlmProfile(profileId);
      setStatusById((prev) => ({
        ...prev,
        [profileId]: result.ok ? "Connected" : result.status,
      }));
    } catch (err) {
      setStatusById((prev) => ({
        ...prev,
        [profileId]: err instanceof Error ? err.message : "Unavailable",
      }));
    } finally {
      setBusy(null);
    }
  };

  return (
    <Stack spacing={3}>
      {error && (
        <Alert severity="warning" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {success && (
        <Alert severity="success" onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      )}
      <Box>
        <Typography variant="h6" gutterBottom>
          Default AI Model
        </Typography>
        <Grid container spacing={2} alignItems="center">
          <Grid size={{ xs: 12, md: 5 }}>
            <TextField
              select
              fullWidth
              size="small"
              label="Default LLM profile"
              value={ai.default_profile_id}
              onChange={(event) => setDefaultProfile(event.target.value)}
            >
              {ai.profiles.map((profile) => (
                <MenuItem key={profile.id} value={profile.id}>
                  {profile.name}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid size={{ xs: 12, md: 5 }}>
            <Typography variant="body2">
              {defaultProfile
                ? `${defaultProfile.provider} / ${defaultProfile.model || "No model selected"}`
                : "No default profile"}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Privacy: {defaultProfile?.privacy_mode ?? "unknown"} · Status:{" "}
              {defaultProfile ? statusById[defaultProfile.id] ?? "Not tested" : "Unavailable"}
            </Typography>
          </Grid>
          <Grid size={{ xs: 12, md: 2 }}>
            <Tooltip title="Test default LLM">
              <span>
                <IconButton
                  disabled={!defaultProfile || Boolean(busy)}
                  onClick={() => defaultProfile && testProfile(defaultProfile.id)}
                >
                  <NetworkCheckIcon />
                </IconButton>
              </span>
            </Tooltip>
          </Grid>
        </Grid>
      </Box>

      <Box>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          alignItems={{ xs: "stretch", sm: "center" }}
          justifyContent="space-between"
          spacing={1}
          sx={{ mb: 1 }}
        >
          <Typography variant="h6">LLM Profiles</Typography>
          <Button
            startIcon={<AddIcon />}
            onClick={openAdd}
            sx={{ alignSelf: { xs: "stretch", sm: "auto" }, flexShrink: 0 }}
          >
            Add profile
          </Button>
        </Stack>
        <Stack spacing={1.5}>
          {ai.profiles.map((profile) => (
            <Box key={profile.id} sx={{ border: 1, borderColor: "divider", borderRadius: 1, p: 1.5 }}>
              <Grid container spacing={1.5} alignItems="center">
                <Grid size={{ xs: 12, md: 3 }}>
                  <Typography fontWeight={700}>{profile.name}</Typography>
                </Grid>
                <Grid size={{ xs: 6, md: 2 }}>{profile.provider}</Grid>
                <Grid size={{ xs: 6, md: 2 }}>{profile.model || "No model"}</Grid>
                <Grid size={{ xs: 12, md: 3 }}>
                  <Typography variant="caption" sx={{ wordBreak: "break-all" }}>
                    {profile.api_base}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 12, md: 1 }}>
                  <Typography variant="caption">{statusById[profile.id] ?? "Not tested"}</Typography>
                </Grid>
                <Grid size={{ xs: 12, md: 1 }}>
                  <Stack
                    direction="row"
                    spacing={0.25}
                    flexWrap="wrap"
                    useFlexGap
                    justifyContent={{ xs: "flex-start", md: "flex-end" }}
                  >
                    <Tooltip title="Test">
                      <IconButton
                        size="small"
                        disabled={Boolean(busy)}
                        onClick={() => testProfile(profile.id)}
                      >
                        <NetworkCheckIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Edit">
                      <IconButton size="small" disabled={Boolean(busy)} onClick={() => openEdit(profile)}>
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete">
                      <span>
                        <IconButton
                          size="small"
                          disabled={Boolean(busy) || ai.profiles.length <= 1}
                          onClick={() => removeProfile(profile.id)}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </Stack>
                </Grid>
              </Grid>
            </Box>
          ))}
        </Stack>
      </Box>

      <Accordion>
        <AccordionSummary>Tutor system prompt</AccordionSummary>
        <AccordionDetails>
          <TextField
            fullWidth
            multiline
            minRows={3}
            label="System prompt"
            value={ai.system_prompt}
            onChange={(event) => onAiFieldChange("system_prompt", event.target.value)}
          />
        </AccordionDetails>
      </Accordion>

      <AdvancedTaskRouting
        profiles={ai.profiles}
        taskOverrides={ai.task_overrides}
        onChange={(overrides) => onAiFieldChange("task_overrides", overrides)}
      />

      <LlmProfileDialog
        open={dialogOpen}
        profile={editingProfile}
        busy={busy === "dialog"}
        onClose={() => setDialogOpen(false)}
        onSaved={handleSavedProfile}
        onBusyChange={(value) => setBusy(value ? "dialog" : null)}
      />
    </Stack>
  );
}
