import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import FormControlLabel from "@mui/material/FormControlLabel";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import type { PrivacyPrefs } from "../api/privacyApi";

type SettingsPrivacyCardProps = {
  prefs: PrivacyPrefs;
  prefsLoading: boolean;
  busyAction: "export" | "deleteHistory" | "deleteAccount" | "retentionCleanup" | null;
  onPrefsChange: (next: PrivacyPrefs) => void;
  onSavePrefs: (next: PrivacyPrefs) => void | Promise<void>;
  onRetentionCleanup: () => void | Promise<void>;
  onExport: () => void | Promise<void>;
  onDeleteHistory: () => void | Promise<void>;
  onDeleteAccount: () => void | Promise<void>;
};

export function SettingsPrivacyCard({
  prefs,
  prefsLoading,
  busyAction,
  onPrefsChange,
  onSavePrefs,
  onRetentionCleanup,
  onExport,
  onDeleteHistory,
  onDeleteAccount,
}: SettingsPrivacyCardProps) {
  return (
    <>
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
                onPrefsChange(nextPrefs);
                void onSavePrefs(nextPrefs);
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
                onPrefsChange(nextPrefs);
                void onSavePrefs(nextPrefs);
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
                onPrefsChange(nextPrefs);
                void onSavePrefs(nextPrefs);
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
            onPrefsChange(nextPrefs);
            void onSavePrefs(nextPrefs);
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
            onPrefsChange(nextPrefs);
            void onSavePrefs(nextPrefs);
          }}
          onChange={(e) => onPrefsChange({ ...prefs, retentionDays: Number(e.target.value || 180) })}
        />
      </Stack>
      <Divider sx={{ my: 2 }} />
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Button
          variant="outlined"
          disabled={prefsLoading || busyAction !== null}
          onClick={() => {
            const defaultPrefs: PrivacyPrefs = {
              allowAnalytics: true,
              retainHistory: true,
              coachPersonalization: true,
              retentionDays: 180,
              goalPreset: "balanced",
            };
            onPrefsChange(defaultPrefs);
            void onSavePrefs(defaultPrefs);
          }}
        >
          Reset preferences
        </Button>
        <Button
          color="info"
          variant="outlined"
          disabled={busyAction !== null}
          onClick={() => void onRetentionCleanup()}
        >
          {busyAction === "retentionCleanup" ? <CircularProgress size={16} /> : "Run retention cleanup"}
        </Button>
        <Button variant="outlined" disabled={busyAction !== null} onClick={() => void onExport()}>
          {busyAction === "export" ? <CircularProgress size={16} /> : "Export account data"}
        </Button>
        <Button
          color="warning"
          variant="outlined"
          disabled={busyAction !== null}
          onClick={() => void onDeleteHistory()}
        >
          {busyAction === "deleteHistory" ? <CircularProgress size={16} /> : "Delete learning history"}
        </Button>
        <Button
          color="error"
          variant="contained"
          disabled={busyAction !== null}
          onClick={() => void onDeleteAccount()}
        >
          {busyAction === "deleteAccount" ? <CircularProgress size={16} /> : "Delete account"}
        </Button>
      </Stack>
      <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
        Export and deletion actions apply to your authenticated server-side data.
      </Typography>
    </>
  );
}
