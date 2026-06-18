import { useEffect, useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import {
  useBookQuery,
  useCompleteLessonPageMutation,
  useLessonPageQuery,
  useLessonProgressQuery,
} from "../hooks/useBookQueries";
import { BlockRenderer } from "./BlockRenderer";
import { CefrLevelSelect } from "../../../shared/components/CefrLevelSelect";
import type { CefrLevel } from "../types";

export function BookLessonPanel() {
  const [level, setLevel] = useState<CefrLevel>("A1");
  const [pageId, setPageId] = useState<string>("");
  const [quizScore, setQuizScore] = useState<number | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const bookQuery = useBookQuery(level);
  const progressQuery = useLessonProgressQuery(level);
  const pageQuery = useLessonPageQuery(level, pageId);
  const completeMutation = useCompleteLessonPageMutation(level);

  const book = bookQuery.data ?? null;
  const page = pageQuery.data ?? null;
  const completedIds = useMemo(
    () => new Set((progressQuery.data ?? []).map((row) => row.page_id)),
    [progressQuery.data],
  );

  const pageOptions = useMemo(() => {
    if (!book) return [];
    return book.chapters.flatMap((chapter) =>
      chapter.pages.map((outline) => ({
        id: outline.id,
        label: `${chapter.title} — ${outline.title}`,
      })),
    );
  }, [book]);

  useEffect(() => {
    if (!book || pageId) return;
    const firstPage = book.chapters[0]?.pages[0]?.id ?? "";
    if (firstPage) setPageId(firstPage);
  }, [book, pageId]);

  useEffect(() => {
    setQuizScore(null);
    setMessage(null);
  }, [level, pageId]);

  const loading =
    bookQuery.isLoading ||
    progressQuery.isLoading ||
    pageQuery.isLoading ||
    completeMutation.isPending;
  const loadError =
    bookQuery.error instanceof Error
      ? bookQuery.error.message
      : pageQuery.error instanceof Error
        ? pageQuery.error.message
        : null;

  const markComplete = async () => {
    if (!pageId) return;
    setActionError(null);
    try {
      await completeMutation.mutateAsync({ pageId, quizScore: quizScore ?? undefined });
      setMessage("Lesson marked complete.");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to save progress.");
    }
  };

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
        <Typography variant="h6">Structured lessons</Typography>
        <Chip size="small" label="Book blocks" color="primary" />
      </Stack>

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <CefrLevelSelect
          value={level}
          onChange={(nextLevel) => {
            setLevel(nextLevel);
            setPageId("");
          }}
          sx={{ minWidth: 100 }}
        />
        <TextField
          select
          size="small"
          label="Lesson page"
          value={pageId}
          onChange={(event) => setPageId(event.target.value)}
          sx={{ flex: 1, minWidth: 220 }}
          disabled={pageOptions.length === 0}
        >
          {pageOptions.map((option) => (
            <MenuItem key={option.id} value={option.id}>
              {option.label}
              {completedIds.has(option.id) ? " ✓" : ""}
            </MenuItem>
          ))}
        </TextField>
        <Button
          variant="outlined"
          onClick={() => void pageQuery.refetch()}
          disabled={!pageId || pageQuery.isFetching}
        >
          Reload
        </Button>
      </Stack>

      {loading && !page && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 2 }}>
          <CircularProgress size={28} />
        </Box>
      )}
      {(loadError || actionError) && <Alert severity="error">{loadError ?? actionError}</Alert>}
      {message && <Alert severity="success">{message}</Alert>}

      {page && !pageQuery.isLoading && (
        <Stack spacing={2}>
          <Box>
            <Typography variant="h6">{page.title}</Typography>
            <Typography variant="body2" color="text.secondary">
              {page.grammar_topic}
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap" useFlexGap>
              {page.learning_objectives.map((objective) => (
                <Chip key={objective} size="small" label={objective} variant="outlined" />
              ))}
            </Stack>
          </Box>

          {page.blocks.map((block) => (
            <BlockRenderer
              key={block.id}
              block={block}
              onQuizScore={(score) => setQuizScore(score)}
            />
          ))}

          <Button
            variant="contained"
            onClick={() => void markComplete()}
            disabled={completedIds.has(page.id) || completeMutation.isPending}
          >
            {completedIds.has(page.id) ? "Completed" : "Mark lesson complete"}
          </Button>
        </Stack>
      )}
    </Stack>
  );
}
