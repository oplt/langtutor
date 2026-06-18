import { useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import LinearProgress from "@mui/material/LinearProgress";

import { CefrLevelSelect } from "../../../shared/components/CefrLevelSelect";
import { FeaturePanel } from "../../../shared/components/FeaturePanel";
import type { CefrLevel } from "../api/learningPathApi";
import {
  useGradePathAnswerMutation,
  usePathDrillQuery,
  usePathMapQuery,
} from "../hooks/useLearningQueries";

export function MasteryPathPanel() {
  const [level, setLevel] = useState<CefrLevel>("A1");
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const mapQuery = usePathMapQuery(level);
  const drillQuery = usePathDrillQuery(level);
  const gradeMutation = useGradePathAnswerMutation(level);

  const map = mapQuery.data ?? null;
  const drill = drillQuery.data ?? null;
  const loading = mapQuery.isLoading || drillQuery.isLoading || gradeMutation.isPending;
  const loadError =
    mapQuery.error instanceof Error
      ? mapQuery.error.message
      : drillQuery.error instanceof Error
        ? drillQuery.error.message
        : null;

  const refresh = () => {
    setError(null);
    void mapQuery.refetch();
    void drillQuery.refetch();
  };

  const submit = async () => {
    if (!answer.trim()) return;
    setError(null);
    try {
      const result = await gradeMutation.mutateAsync(answer.trim());
      setFeedback(result.correct ? "Correct — nice work." : "Not quite — try the next drill.");
      setAnswer("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not grade answer.");
    }
  };

  const progressPct =
    map && map.map.counts.total
      ? Math.round((map.map.counts.mastered / map.map.counts.total) * 100)
      : 0;

  return (
    <FeaturePanel
      title="Mastery path"
      description="Structured drills aligned to your CEFR level."
      loading={mapQuery.isLoading && !map}
      error={loadError}
      onRetry={refresh}
    >
      <Stack spacing={2}>
      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
        <CefrLevelSelect
          value={level}
          label="Level"
          onChange={(nextLevel) => {
            setLevel(nextLevel);
            setFeedback(null);
            setAnswer("");
          }}
        />
        <Button size="small" onClick={refresh} disabled={mapQuery.isFetching || drillQuery.isFetching}>
          Refresh
        </Button>
      </Stack>

      {error && <Alert severity="error">{error}</Alert>}
      {feedback && <Alert severity="info">{feedback}</Alert>}

      {map && (
        <Box>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="subtitle2">Path progress</Typography>
            <Chip
              size="small"
              label={`${map.map.counts.mastered}/${map.map.counts.total} objectives`}
            />
            {map.map.complete && <Chip size="small" color="success" label="Level complete" />}
          </Stack>
          <LinearProgress variant="determinate" value={progressPct} sx={{ mb: 1 }} />
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Next: {map.next.action}
            {map.next.knowledge_point_name ? ` — ${map.next.knowledge_point_name}` : ""}
            {map.next.stage ? ` (${map.next.stage})` : ""}
          </Typography>
          <Stack direction="row" flexWrap="wrap" gap={0.5} useFlexGap>
            {map.map.modules.map((module) => (
              <Chip
                key={module.id}
                size="small"
                variant="outlined"
                label={`${module.name}: ${module.mastered}/${module.total}`}
              />
            ))}
          </Stack>
        </Box>
      )}

      {drill?.drill && (
        <Alert severity="warning">
          <Typography variant="subtitle2" gutterBottom>
            {drill.step.knowledge_point_name || "Practice"}
          </Typography>
          <Typography variant="body2" sx={{ mb: 1 }}>
            {drill.drill.prompt}
          </Typography>
          {drill.drill.options.length > 0 && (
            <Stack direction="row" flexWrap="wrap" gap={0.5} useFlexGap sx={{ mb: 1 }}>
              {drill.drill.options.map((option) => (
                <Chip
                  key={option}
                  size="small"
                  label={option}
                  onClick={() => setAnswer(option)}
                />
              ))}
            </Stack>
          )}
          <Stack direction="row" spacing={1} alignItems="center">
            <TextField
              size="small"
              fullWidth
              placeholder="Your answer"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void submit();
              }}
            />
            <Button variant="contained" onClick={() => void submit()} disabled={loading}>
              Check
            </Button>
          </Stack>
        </Alert>
      )}

      {drill && !drill.drill && map && !map.map.complete && (
        <Typography variant="body2" color="text.secondary">
          {drill.step.reason || "No drill available for the current step."}
        </Typography>
      )}
      </Stack>
    </FeaturePanel>
  );
}
