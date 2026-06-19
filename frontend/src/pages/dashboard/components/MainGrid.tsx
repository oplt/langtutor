import { useEffect, useMemo, useState } from "react";
import Grid from "@mui/material/Grid2";
import Box from "@mui/material/Box";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import LinearProgress from "@mui/material/LinearProgress";
import Skeleton from "@mui/material/Skeleton";
import Alert from "@mui/material/Alert";
import Chip from "@mui/material/Chip";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Button from "@mui/material/Button";
import Divider from "@mui/material/Divider";
import { Link as RouterLink } from "react-router-dom";

import type { LevelInfo, StoryOut } from "../../../modules/learning/api/learningApi";
import type { CefrLevel } from "../../../modules/learning/api/learningPathApi";
import { CEFR_LEVELS } from "../../../modules/learning/api/learningPathApi";
import {
  useGenerateStoryMutation,
  useLearningLevelsQuery,
  useProgressSummaryQuery,
} from "../../../modules/learning/hooks/useLearningQueries";
import {
  loadStoryFromSession,
  saveStoryToSession,
} from "../../../modules/learning/storySessionCache";

type Focus = "overview" | "progress";

export default function MainGrid({ focus = "overview" }: { focus?: Focus }) {
  const levelsQuery = useLearningLevelsQuery();
  const progressQuery = useProgressSummaryQuery();
  const storyMutation = useGenerateStoryMutation();

  const [level, setLevel] = useState<CefrLevel>("A1");
  const [story, setStory] = useState<StoryOut | null>(null);
  const [targetWords, setTargetWords] = useState<8 | 10 | 12>(10);

  useEffect(() => {
    setStory(loadStoryFromSession(level));
  }, [level]);

  const levels = levelsQuery.data ?? [];
  const progress = progressQuery.data ?? null;
  const loadError =
    levelsQuery.isError || progressQuery.isError
      ? "Learning data is temporarily unavailable."
      : null;

  const retryLearningData = () => {
    void levelsQuery.refetch();
    void progressQuery.refetch();
  };

  const currentLevelMeta = useMemo(
    () => levels.find((item: LevelInfo) => item.level === level),
    [levels, level],
  );
  const coveragePct = useMemo(() => {
    if (!progress || !progress.total_words) return 0;
    return Math.min(100, Math.round((progress.mastered_words / progress.total_words) * 100));
  }, [progress]);

  const generateStory = async (levelValue: CefrLevel, wordCount = targetWords) => {
    try {
      const payload = await storyMutation.mutateAsync({
        level: levelValue,
        targetWordCount: wordCount,
      });
      setStory(payload);
      saveStoryToSession(levelValue, payload);
    } catch {
      // storyMutation.error handled below
    }
  };

  const storyError = storyMutation.error
    ? "Story generation failed. Please try again."
    : null;

  if (focus === "progress") {
    const levelRows = progress?.levels ?? [];
    return (
      <Box sx={{ width: "100%", maxWidth: { sm: "100%", md: 1200 } }}>
        {(loadError || storyError) && (
          <Alert
            severity="warning"
            sx={{ mb: 2 }}
            action={
              loadError ? (
                <Button color="inherit" size="small" onClick={retryLearningData}>
                  Retry
                </Button>
              ) : undefined
            }
          >
            {loadError ?? storyError}
          </Alert>
        )}
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h5" sx={{ mb: 1 }}>
              Progress by level
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Mastery is based on recognition + recall strength above 60.
            </Typography>
            {levelsQuery.isLoading ? (
              <Stack spacing={2} sx={{ mt: 2 }}>
                {CEFR_LEVELS.map((item) => (
                  <Skeleton key={item} variant="rounded" height={36} />
                ))}
              </Stack>
            ) : levelRows.length === 0 ? (
              <Stack spacing={2} sx={{ mt: 2, alignItems: "flex-start" }}>
                <Typography variant="body2" color="text.secondary">
                  No progress recorded yet. Generate a story or take a quiz to start building mastery.
                </Typography>
                <Button variant="contained" component={RouterLink} to="/dashboard/tasks">
                  Start learning
                </Button>
              </Stack>
            ) : (
              <Stack spacing={2} sx={{ mt: 2 }}>
                {levelRows.map((item) => {
                const pct = item.total ? Math.round((item.mastered / item.total) * 100) : 0;
                return (
                  <Box key={item.level}>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Typography variant="subtitle1">{item.level}</Typography>
                      <Typography variant="body2">
                        {item.mastered}/{item.total} ({pct}%)
                      </Typography>
                    </Stack>
                    <LinearProgress variant="determinate" value={pct} sx={{ mt: 0.5 }} />
                  </Box>
                );
              })}
              </Stack>
            )}
            <Divider sx={{ my: 2 }} />
            <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
              <Chip label={`Total mastered: ${progress?.mastered_words ?? 0}`} color="success" />
              <Chip
                label={
                  progress?.next_review_at
                    ? `Next review: ${new Date(progress.next_review_at).toLocaleDateString()}`
                    : "Next review: not scheduled"
                }
                variant="outlined"
              />
            </Stack>
          </CardContent>
        </Card>
      </Box>
    );
  }

  return (
    <Box sx={{ width: "100%", maxWidth: { sm: "100%", md: 1200 } }}>
      {(loadError || storyError) && (
        <Alert
          severity="warning"
          sx={{ mb: 2 }}
          action={
            loadError ? (
              <Button color="inherit" size="small" onClick={retryLearningData}>
                Retry
              </Button>
            ) : undefined
          }
        >
          {loadError ?? storyError}
        </Alert>
      )}
      <Stack spacing={2}>
        <Grid container spacing={2} columns={12}>
          <Grid size={{ xs: 12, md: 4 }}>
            <Card variant="outlined" sx={{ height: "100%" }}>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">
                  Current level
                </Typography>
                <Typography variant="h4" sx={{ mt: 1 }}>
                  {level}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {currentLevelMeta?.word_coverage ?? "Loading words"}
                </Typography>
                <ToggleButtonGroup
                  size="small"
                  exclusive
                  value={level}
                  aria-label="CEFR level"
                  onChange={(_event, value) => {
                    if (value) setLevel(value);
                  }}
                  sx={{ mt: 2, flexWrap: "wrap" }}
                >
                  {(levels.length ? levels : CEFR_LEVELS.map((item) => ({ level: item, word_coverage: "", grammar_focus: "", input_type: "" }))).map((item: LevelInfo | { level: CefrLevel }) => (
                    <ToggleButton key={item.level} value={item.level}>
                      {item.level}
                    </ToggleButton>
                  ))}
                </ToggleButtonGroup>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <Card variant="outlined" sx={{ height: "100%" }}>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">
                  Coverage
                </Typography>
                <Typography variant="h4" sx={{ mt: 1 }}>
                  {coveragePct}%
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {progress?.mastered_words ?? 0}/{progress?.total_words ?? 0} words mastered
                </Typography>
                <LinearProgress variant="determinate" value={coveragePct} sx={{ mt: 2 }} />
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <Card variant="outlined" sx={{ height: "100%" }}>
              <CardContent>
                <Typography variant="subtitle2" color="text.secondary">
                  Focus today
                </Typography>
                <Typography variant="h6" sx={{ mt: 1 }}>
                  {currentLevelMeta?.grammar_focus ?? "Loading focus"}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {currentLevelMeta?.input_type ?? "Structured input"}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Grid container spacing={2} columns={12}>
          <Grid size={{ xs: 12, md: 8 }}>
            <Card variant="outlined" sx={{ height: "100%" }}>
              <CardContent>
                <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
                  <Box>
                    <Typography variant="h5">{story?.title ?? "Micro-story"}</Typography>
                    <Typography variant="body2" color="text.secondary">
                      {story?.word_count ?? 0} words · {story?.new_word_count ?? 0} new words
                    </Typography>
                  </Box>
                  <Button
                    variant="outlined"
                    onClick={() => void generateStory(level, targetWords)}
                    disabled={storyMutation.isPending}
                  >
                    {storyMutation.isPending ? "Generating..." : story ? "New story" : "Generate story"}
                  </Button>
                </Stack>
                <Typography variant="body1" sx={{ mt: 2, whiteSpace: "pre-line" }}>
                  {storyMutation.isPending ? (
                    <Stack spacing={1}>
                      <Skeleton variant="text" />
                      <Skeleton variant="text" />
                      <Skeleton variant="text" width="80%" />
                    </Stack>
                  ) : (
                    story?.body ??
                    "Choose a CEFR level and click Generate story to build a micro-story with target vocabulary."
                  )}
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 2 }} alignItems="center" flexWrap="wrap">
                  <Typography variant="subtitle2" color="text.secondary">
                    Target words
                  </Typography>
                  {(story?.target_words || []).slice(0, 12).map((word) => (
                    <Chip key={word} label={word} size="small" />
                  ))}
                </Stack>
              </CardContent>
            </Card>
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <Card variant="outlined" sx={{ height: "100%" }}>
              <CardContent>
                <Typography variant="subtitle1" sx={{ mb: 1 }}>
                  Practice plan
                </Typography>
                <Stack spacing={1}>
                  <Chip label="Recognition: choose the right word" variant="outlined" />
                  <Chip label="Recall: translate or explain" variant="outlined" />
                  <Chip label="Form: spell the word" variant="outlined" />
                  <Chip label="Sentence: use it in context" variant="outlined" />
                  <Chip label="Free production: write 2 lines" variant="outlined" />
                </Stack>
                <Divider sx={{ my: 2 }} />
                <Typography variant="subtitle2" color="text.secondary">
                  Target words per story
                </Typography>
                <ToggleButtonGroup
                  size="small"
                  exclusive
                  value={targetWords}
                  onChange={(_event, value) => {
                    if (value) {
                      setTargetWords(value);
                    }
                  }}
                  sx={{ mt: 1 }}
                >
                  <ToggleButton value={8}>8</ToggleButton>
                  <ToggleButton value={10}>10</ToggleButton>
                  <ToggleButton value={12}>12</ToggleButton>
                </ToggleButtonGroup>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Stack>
    </Box>
  );
}
