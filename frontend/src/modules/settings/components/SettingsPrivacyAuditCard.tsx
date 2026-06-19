import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import type { PrivacyAuditItem } from "../api/privacyApi";

type SettingsPrivacyAuditCardProps = {
  items: PrivacyAuditItem[];
  loading: boolean;
  error: Error | null;
  onRefresh: () => void;
};

export function SettingsPrivacyAuditCard({
  items,
  loading,
  error,
  onRefresh,
}: SettingsPrivacyAuditCardProps) {
  return (
    <>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="subtitle2">Privacy Activity</Typography>
        <Button size="small" variant="text" onClick={onRefresh}>
          Refresh
        </Button>
      </Stack>
      {error && (
        <Alert severity="error" sx={{ mb: 1 }}>
          Could not load privacy activity. Try Refresh.
        </Alert>
      )}
      {loading ? (
        <Stack direction="row" alignItems="center" spacing={1}>
          <CircularProgress size={14} />
          <Typography variant="caption" color="text.secondary">
            Loading privacy activity...
          </Typography>
        </Stack>
      ) : items.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No privacy activity recorded yet.
        </Typography>
      ) : (
        <List dense sx={{ p: 0 }}>
          {items.map((item) => (
            <ListItem key={item.id} disableGutters sx={{ py: 0.5 }}>
              <ListItemText
                primary={item.action.replaceAll("_", " ")}
                secondary={item.createdAt ? new Date(item.createdAt).toLocaleString() : "Unknown time"}
              />
            </ListItem>
          ))}
        </List>
      )}
    </>
  );
}
