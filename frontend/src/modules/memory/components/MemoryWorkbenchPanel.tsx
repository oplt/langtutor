import { useState } from "react";
import Skeleton from "@mui/material/Skeleton";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  useAppendPreferenceMutation,
  useMemoryL3Query,
  useMemoryOverviewQuery,
  useSynthesizeMemoryMutation,
} from "../hooks/useMemoryQueries";

export function MemoryWorkbenchPanel() {
  const overviewQuery = useMemoryOverviewQuery();
  const l3Query = useMemoryL3Query();
  const appendMutation = useAppendPreferenceMutation();
  const synthesizeMutation = useSynthesizeMemoryMutation();
  const [preference, setPreference] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const overview = overviewQuery.data ?? null;
  const l3Preview = l3Query.data?.content ?? "";
  const initialLoading = overviewQuery.isLoading || l3Query.isLoading;
  const loading =
    overviewQuery.isFetching ||
    l3Query.isFetching ||
    appendMutation.isPending ||
    synthesizeMutation.isPending;
  const error =
    overviewQuery.error instanceof Error
      ? overviewQuery.error.message
      : l3Query.error instanceof Error
        ? l3Query.error.message
        : appendMutation.error instanceof Error
          ? appendMutation.error.message
          : synthesizeMutation.error instanceof Error
            ? synthesizeMutation.error.message
            : null;

  const refresh = () => {
    void overviewQuery.refetch();
    void l3Query.refetch();
  };

  const savePreference = async () => {
    if (!preference.trim()) return;
    setMessage(null);
    try {
      await appendMutation.mutateAsync(preference.trim());
      setPreference("");
      setMessage("Preference saved.");
    } catch {
      // error via mutation state
    }
  };

  const synthesize = async () => {
    setMessage(null);
    try {
      await synthesizeMutation.mutateAsync();
      setMessage(
        "Memory synthesis scheduled. Updates may take a moment — use Refresh to check.",
      );
    } catch {
      // error via mutation state
    }
  };

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
        <Typography variant="h6">Learner memory</Typography>
        <Chip size="small" label={`${overview?.trace_count ?? 0} traces`} />
        <Button size="small" onClick={refresh} disabled={loading}>
          Refresh
        </Button>
        <Button size="small" variant="outlined" onClick={() => void synthesize()} disabled={loading}>
          Synthesize profile
        </Button>
      </Stack>

      {error && <Alert severity="error">{error}</Alert>}
      {message && <Alert severity="success" onClose={() => setMessage(null)}>{message}</Alert>}

      {initialLoading ? (
        <Stack spacing={1.5}>
          <Skeleton variant="rounded" height={120} />
          <Stack direction="row" spacing={1}>
            <Skeleton variant="rounded" width={90} height={28} />
            <Skeleton variant="rounded" width={90} height={28} />
            <Skeleton variant="rounded" width={90} height={28} />
          </Stack>
        </Stack>
      ) : (
        <>
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          L3 profile (injected into tutor)
        </Typography>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ whiteSpace: "pre-wrap", fontFamily: "monospace", fontSize: 12 }}
        >
          {l3Preview || "No synthesized memory yet. Chat or practice to build traces."}
        </Typography>
      </Paper>

      {overview && (
        <Stack direction="row" flexWrap="wrap" gap={0.5} useFlexGap>
          {overview.l2.map((doc) => (
            <Chip
              key={doc.surface}
              size="small"
              variant="outlined"
              label={`L2 ${doc.surface}: ${doc.entry_count}`}
            />
          ))}
          {overview.l3.map((doc) => (
            <Chip
              key={doc.slot}
              size="small"
              variant="outlined"
              label={`L3 ${doc.slot}: ${doc.entry_count}`}
            />
          ))}
        </Stack>
      )}

      <Stack direction="row" spacing={1}>
        <TextField
          fullWidth
          size="small"
          label="Add preference"
          placeholder='e.g. "Explain grammar in English" or "Prefer formal Dutch"'
          value={preference}
          onChange={(e) => setPreference(e.target.value)}
        />
        <Button variant="contained" onClick={() => void savePreference()} disabled={loading}>
          Save
        </Button>
      </Stack>
        </>
      )}
    </Stack>
  );
}
