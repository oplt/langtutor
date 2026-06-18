import { useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";

import {
  useDeleteNotebookEntryMutation,
  useNotebookEntriesQuery,
  useSaveNotebookEntryMutation,
} from "../hooks/useNotebookQueries";
import { FeaturePanel } from "../../../shared/components/FeaturePanel";
import { useAsyncPanel } from "../../../shared/hooks/useAsyncPanel";

export function WordBankPanel() {
  const entriesQuery = useNotebookEntriesQuery();
  const panel = useAsyncPanel(entriesQuery);
  const saveMutation = useSaveNotebookEntryMutation();
  const deleteMutation = useDeleteNotebookEntryMutation();
  const [lemma, setLemma] = useState("");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  const entries = entriesQuery.data?.entries ?? [];
  const dueCount = entriesQuery.data?.due_count ?? 0;

  const save = async () => {
    if (!lemma.trim()) return;
    setMessage(null);
    try {
      await saveMutation.mutateAsync({
        lemma: lemma.trim(),
        note: note.trim(),
        source: "manual",
      });
      setLemma("");
      setNote("");
      setMessage("Word saved to your bank and queued for review.");
    } catch {
      setMessage(null);
    }
  };

  const remove = async (entryId: string) => {
    try {
      await deleteMutation.mutateAsync(entryId);
    } catch {
      // mutation error surfaced via deleteMutation.error if needed
    }
  };

  const actionError =
    saveMutation.error instanceof Error
      ? saveMutation.error.message
      : deleteMutation.error instanceof Error
        ? deleteMutation.error.message
        : null;

  return (
    <FeaturePanel
      title="Word bank"
      description="Save unknown words from tutor chat or add them manually. Corpus-linked words join your spaced-repetition queue."
      loading={panel.loading}
      error={panel.error}
      onRetry={panel.refresh}
    >
      <Stack spacing={2}>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <Chip size="small" label={`${entries.length} saved`} />
          {dueCount > 0 && <Chip size="small" color="warning" label={`${dueCount} due for review`} />}
          <Button size="small" onClick={panel.refresh} disabled={panel.isFetching}>
            Refresh
          </Button>
        </Stack>

        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <TextField
            size="small"
            label="Dutch word"
            value={lemma}
            onChange={(e) => setLemma(e.target.value)}
            sx={{ flex: 1 }}
          />
          <TextField
            size="small"
            label="Note (optional)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            sx={{ flex: 2 }}
          />
          <Button
            variant="contained"
            onClick={() => void save()}
            disabled={saveMutation.isPending || !lemma.trim()}
          >
            Save
          </Button>
        </Stack>

        {actionError && <Alert severity="error">{actionError}</Alert>}
        {message && <Alert severity="success">{message}</Alert>}

        {!panel.loading && entries.length === 0 && (
          <Alert severity="info">No words saved yet. Ask your tutor to save a word, or add one above.</Alert>
        )}

        <Stack spacing={1}>
          {entries.map((entry) => (
            <Box
              key={entry.id}
              sx={{
                p: 1.5,
                border: 1,
                borderColor: "divider",
                borderRadius: 1,
                display: "flex",
                gap: 1,
                alignItems: "flex-start",
              }}
            >
              <Box sx={{ flex: 1 }}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                  <Typography variant="subtitle2">{entry.lemma}</Typography>
                  {entry.translation && <Chip size="small" label={entry.translation} variant="outlined" />}
                  {entry.level && <Chip size="small" label={entry.level} />}
                  <Chip size="small" label={entry.source} variant="outlined" />
                </Stack>
                {entry.note && (
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    {entry.note}
                  </Typography>
                )}
                {entry.context && (
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                    {entry.context}
                  </Typography>
                )}
                {entry.next_review_at && (
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
                    Next review: {new Date(entry.next_review_at).toLocaleString()}
                  </Typography>
                )}
              </Box>
              <IconButton size="small" aria-label="Delete word" onClick={() => void remove(entry.id)}>
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            </Box>
          ))}
        </Stack>
      </Stack>
    </FeaturePanel>
  );
}
