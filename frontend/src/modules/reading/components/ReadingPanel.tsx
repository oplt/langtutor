import { useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Divider from "@mui/material/Divider";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormLabel from "@mui/material/FormLabel";
import Link from "@mui/material/Link";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Typography from "@mui/material/Typography";
import AutoStoriesRoundedIcon from "@mui/icons-material/AutoStoriesRounded";
import DownloadRoundedIcon from "@mui/icons-material/DownloadRounded";
import RefreshRoundedIcon from "@mui/icons-material/RefreshRounded";
import SaveRoundedIcon from "@mui/icons-material/SaveRounded";
import TrendingDownRoundedIcon from "@mui/icons-material/TrendingDownRounded";
import TrendingUpRoundedIcon from "@mui/icons-material/TrendingUpRounded";

import { FeaturePanel } from "../../../shared/components/FeaturePanel";
import { ApiError } from "../../../shared/api/httpClient";
import type {
  InterestArea,
  ReadingGenerateRequest,
  ReadingGenerateResponse,
  SourceMode,
  Strictness,
} from "../api/readingApi";
import { useGenerateReadingMutation, useSaveReadingMutation } from "../hooks/useReadingQueries";
import {
  FREQUENCY_LEVELS,
  INTEREST_AREAS,
  SOURCE_MODE_OPTIONS,
  STRICTNESS_OPTIONS,
  WORD_COUNT_OPTIONS,
  difficultyBadge,
  levelForFrequency,
} from "../utils/readingConstants";

function highlightUnknownWords(text: string, unknownWords: string[]): string {
  if (!unknownWords.length) return text;
  let result = text;
  for (const word of unknownWords) {
    const pattern = new RegExp(`\\b(${word})\\b`, "gi");
    result = result.replace(pattern, "⟦$1⟧");
  }
  return result;
}

const compactToggleGroupSx = {
  display: "flex",
  width: "100%",
  "& .MuiToggleButton-root": {
    flex: 1,
    minWidth: 0,
    px: { xs: 0.5, sm: 1 },
    py: 0.75,
    textTransform: "none",
  },
} as const;

export function ReadingPanel() {
  const [level, setLevel] = useState(3);
  const [interestArea, setInterestArea] = useState<InterestArea>("news");
  const [wordCount, setWordCount] = useState(500);
  const [sourceMode, setSourceMode] = useState<SourceMode>("online");
  const [strictness, setStrictness] = useState<Strictness>("balanced");
  const [result, setResult] = useState<ReadingGenerateResponse | null>(null);
  const [showReplacements, setShowReplacements] = useState(true);
  const [highlightUnknown, setHighlightUnknown] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const generateMutation = useGenerateReadingMutation();
  const saveMutation = useSaveReadingMutation();

  const levelMeta = levelForFrequency(level);
  const badge = result ? difficultyBadge(result.coverage.coveragePercent) : null;

  const displayText = useMemo(() => {
    if (!result) return "";
    const text = result.adaptedText;
    if (!highlightUnknown) return text;
    return highlightUnknownWords(text, result.coverage.unknownWordList);
  }, [result, highlightUnknown]);

  const englishTranslation = useMemo(() => {
    if (!result) return null;
    if (result.translation?.status === "ok" && result.translation.text) {
      return result.translation.text;
    }
    return result.translatedText ?? null;
  }, [result]);

  const buildPayload = (overrides?: Partial<ReadingGenerateRequest>): ReadingGenerateRequest => ({
    language: "nl",
    level,
    maxFrequencyRank: levelMeta.maxWords,
    interestArea,
    wordCount,
    sourceMode,
    strictness,
    translationMode: "full",
    ...overrides,
  });

  const handleLevelChange = (nextLevel: number) => {
    setLevel(nextLevel);
    const meta = levelForFrequency(nextLevel);
    setWordCount(meta.defaultWordCount);
  };

  const handleGenerate = async (overrides?: Partial<ReadingGenerateRequest>) => {
    setMessage(null);
    const payload = buildPayload(overrides);
    if (overrides?.level) {
      payload.maxFrequencyRank = levelForFrequency(overrides.level).maxWords;
    }
    try {
      const response = await generateMutation.mutateAsync(payload);
      setResult(response);
      if (overrides?.level) setLevel(overrides.level);
      if (overrides?.wordCount) setWordCount(overrides.wordCount);
      if (overrides?.strictness) setStrictness(overrides.strictness);
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setMessage(
          err.detail ??
            "Generated text did not meet the vocabulary coverage target. Try a higher level or looser strictness.",
        );
      } else if (err instanceof ApiError && err.status === 504) {
        setMessage(err.detail ?? "Reading generation timed out. Try a shorter text.");
      } else {
        setMessage(err instanceof Error ? err.message : "Failed to generate reading text.");
      }
    }
  };

  const handleSave = async () => {
    if (!result) return;
    setMessage(null);
    try {
      const saved = await saveMutation.mutateAsync(result);
      setMessage(`Reading saved (${saved.id.slice(0, 8)}…).`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Failed to save reading.");
    }
  };

  const handleExportVocabulary = () => {
    if (!result) return;
    const lines = [
      ...result.replacements.map((r) => `${r.original} → ${r.replacement}`),
      ...result.glossary.map((g) => `${g.word}: ${g.meaning || g.definition}`),
      ...result.coverage.unknownWordList.map((w) => `${w} (outside level)`),
    ];
    const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `reading-vocabulary-level-${result.level}.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const generating = generateMutation.isPending;

  return (
    <FeaturePanel
      title="Reading trainer"
      description="Generate adapted Dutch reading texts matched to your vocabulary level and interests."
      actionError={message}
    >
      <Stack spacing={3}>
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Frequency level
          </Typography>
          <ToggleButtonGroup
            exclusive
            value={level}
            onChange={(_, value) => value && handleLevelChange(value)}
            sx={{
              display: "flex",
              width: "100%",
              "& .MuiToggleButton-root": {
                flex: 1,
                minWidth: 0,
                px: { xs: 0.5, sm: 1 },
                py: 1,
                textTransform: "none",
              },
            }}
          >
            {FREQUENCY_LEVELS.map((item) => (
              <ToggleButton key={item.level} value={item.level}>
                <Stack spacing={0.25} alignItems="center" sx={{ width: "100%" }}>
                  <Typography variant="caption" color="text.secondary" lineHeight={1}>
                    Level {item.level}
                  </Typography>
                  <Typography variant="body2" fontWeight={600} noWrap sx={{ maxWidth: "100%" }}>
                    {item.label}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{
                      lineHeight: 1.2,
                      textAlign: "center",
                      fontSize: { xs: "0.65rem", sm: "0.75rem" },
                      px: 0.25,
                    }}
                  >
                    {item.wordCoverage}
                  </Typography>
                </Stack>
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Box>

        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Interest area
          </Typography>
          <ToggleButtonGroup
            exclusive
            value={interestArea}
            onChange={(_, value) => value && setInterestArea(value as InterestArea)}
            sx={{
              display: "flex",
              width: "100%",
              "& .MuiToggleButton-root": {
                flex: 1,
                minWidth: 0,
                px: { xs: 0.25, sm: 0.5 },
                py: 1,
                textTransform: "none",
              },
            }}
          >
            {INTEREST_AREAS.map((item) => (
              <ToggleButton key={item.id} value={item.id}>
                <Typography
                  variant="caption"
                  fontWeight={600}
                  sx={{
                    lineHeight: 1.2,
                    textAlign: "center",
                    fontSize: { xs: "0.65rem", sm: "0.75rem" },
                    px: 0.25,
                  }}
                >
                  {item.label}
                </Typography>
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Box>

        <Stack direction="row" spacing={2} sx={{ width: "100%" }}>
          <FormControl sx={{ flex: 1, minWidth: 0 }}>
            <FormLabel sx={{ mb: 1 }}>Text length</FormLabel>
            <ToggleButtonGroup
              exclusive
              size="small"
              value={wordCount}
              onChange={(_, value) => value && setWordCount(value)}
              sx={compactToggleGroupSx}
            >
              {WORD_COUNT_OPTIONS.map((count) => (
                <ToggleButton key={count} value={count}>
                  {count} words
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </FormControl>

          <FormControl sx={{ flex: 1, minWidth: 0 }}>
            <FormLabel sx={{ mb: 1 }}>Source mode</FormLabel>
            <ToggleButtonGroup
              exclusive
              size="small"
              value={sourceMode}
              onChange={(_, value) => value && setSourceMode(value as SourceMode)}
              sx={compactToggleGroupSx}
            >
              {SOURCE_MODE_OPTIONS.map((option) => (
                <ToggleButton key={option.id} value={option.id}>
                  {option.label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </FormControl>

          <FormControl sx={{ flex: 1, minWidth: 0 }}>
            <FormLabel sx={{ mb: 1 }}>Rewrite strictness</FormLabel>
            <ToggleButtonGroup
              exclusive
              size="small"
              value={strictness}
              onChange={(_, value) => value && setStrictness(value as Strictness)}
              sx={compactToggleGroupSx}
            >
              {STRICTNESS_OPTIONS.map((option) => (
                <ToggleButton key={option.id} value={option.id}>
                  {option.label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </FormControl>
        </Stack>

        <Button
          variant="contained"
          startIcon={generating ? <CircularProgress size={18} color="inherit" /> : <AutoStoriesRoundedIcon />}
          disabled={generating}
          onClick={() => void handleGenerate()}
          sx={{ alignSelf: "flex-start" }}
        >
          {generating ? "Generating…" : "Generate reading"}
        </Button>

        {generating ? (
          <Alert severity="info" icon={<CircularProgress size={18} />}>
            Fetching source material and adapting text to your vocabulary level. This may take a moment.
          </Alert>
        ) : null}

        {result ? (
          <Stack spacing={2}>
            <Divider />
            {result.warnings.length > 0 ? (
              <Alert severity="warning">
                {result.warnings.join(" ")}
              </Alert>
            ) : null}
            {result.adaptationMode === "llm" ? (
              <Chip label="LLM-adapted" color="success" size="small" sx={{ alignSelf: "flex-start" }} />
            ) : result.adaptationMode === "rules" ? (
              <Chip label="Rule-based adaptation" color="warning" size="small" sx={{ alignSelf: "flex-start" }} />
            ) : null}
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Chip label={`Level ${result.level} · ${levelForFrequency(result.level).cefrLabel}`} />
              {badge ? <Chip label={badge.label} color={badge.color} size="small" /> : null}
              <Chip label={`${result.coverage.coveragePercent}% coverage`} size="small" />
              <Chip label={`${result.wordCountActual} words`} size="small" variant="outlined" />
              <Chip label={`${result.coverage.unknownWords} unknown`} size="small" variant="outlined" />
            </Stack>

            <Box>
              <Typography variant="h6" gutterBottom>
                {result.source.title}
              </Typography>
              {result.source.url ? (
                <Typography variant="body2" color="text.secondary">
                  Source:{" "}
                  <Link href={result.source.url} target="_blank" rel="noopener noreferrer">
                    {result.source.publisher || result.source.url}
                  </Link>
                </Typography>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Source: {result.source.publisher || "Generated topic text"}
                </Typography>
              )}
            </Box>

            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography
                variant="body1"
                sx={{ whiteSpace: "pre-wrap", lineHeight: 1.7 }}
                component="div"
              >
                {displayText.split("⟦").map((part, index) => {
                  if (index === 0) return part;
                  const end = part.indexOf("⟧");
                  if (end === -1) return part;
                  const word = part.slice(0, end);
                  const rest = part.slice(end + 1);
                  return (
                    <span key={`${word}-${index}`}>
                      <Box component="mark" sx={{ bgcolor: "warning.light", px: 0.25, borderRadius: 0.5 }}>
                        {word}
                      </Box>
                      {rest}
                    </span>
                  );
                })}
              </Typography>
            </Paper>

            {englishTranslation ? (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  English translation
                </Typography>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 2,
                    bgcolor: "action.hover",
                    borderColor: "divider",
                  }}
                >
                  <Typography
                    variant="body1"
                    sx={{ whiteSpace: "pre-wrap", lineHeight: 1.7, color: "text.secondary" }}
                    component="div"
                  >
                    {englishTranslation}
                  </Typography>
                </Paper>
              </Box>
            ) : result.translation?.status === "unavailable" ? (
              <Typography variant="body2" color="text.secondary">
                English translation is temporarily unavailable.
              </Typography>
            ) : null}

            <Stack direction="row" spacing={2} flexWrap="wrap">
              <FormControlLabel
                control={
                  <Switch checked={showReplacements} onChange={(e) => setShowReplacements(e.target.checked)} />
                }
                label="Show replaced difficult words"
              />
              <FormControlLabel
                control={
                  <Switch checked={highlightUnknown} onChange={(e) => setHighlightUnknown(e.target.checked)} />
                }
                label="Highlight words outside my level"
              />
            </Stack>

            {showReplacements && result.replacements.length > 0 ? (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Replaced words
                </Typography>
                <Stack spacing={0.5}>
                  {result.replacements.map((item) => (
                    <Typography key={`${item.original}-${item.replacement}`} variant="body2">
                      <strong>{item.original}</strong> → {item.replacement}
                      {item.reason ? ` — ${item.reason}` : ""}
                    </Typography>
                  ))}
                </Stack>
              </Box>
            ) : null}

            {result.quiz.length > 0 ? (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Comprehension quiz
                </Typography>
                <Stack spacing={1.5}>
                  {result.quiz.map((question, index) => (
                    <Paper key={`${question.question}-${index}`} variant="outlined" sx={{ p: 1.5 }}>
                      <Typography variant="body2" fontWeight={600}>
                        {index + 1}. {question.question}
                      </Typography>
                      <Stack spacing={0.25} sx={{ mt: 1 }}>
                        {question.options.map((option) => (
                          <Typography key={option} variant="body2" color="text.secondary">
                            • {option}
                          </Typography>
                        ))}
                      </Stack>
                      <Typography variant="caption" color="success.main" sx={{ mt: 1, display: "block" }}>
                        Answer: {question.answer}
                      </Typography>
                    </Paper>
                  ))}
                </Stack>
              </Box>
            ) : null}

            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Button
                size="small"
                startIcon={<RefreshRoundedIcon />}
                disabled={generating}
                onClick={() => void handleGenerate()}
              >
                Regenerate
              </Button>
              <Button
                size="small"
                startIcon={<TrendingDownRoundedIcon />}
                disabled={generating || level <= 1}
                onClick={() => void handleGenerate({ level: Math.max(1, level - 1) })}
              >
                Make easier
              </Button>
              <Button
                size="small"
                startIcon={<TrendingUpRoundedIcon />}
                disabled={generating || level >= 6}
                onClick={() => void handleGenerate({ level: Math.min(6, level + 1) })}
              >
                Make harder
              </Button>
              <Button
                size="small"
                startIcon={<SaveRoundedIcon />}
                disabled={saveMutation.isPending}
                onClick={() => void handleSave()}
              >
                Save text
              </Button>
              <Button
                size="small"
                startIcon={<DownloadRoundedIcon />}
                onClick={handleExportVocabulary}
              >
                Export vocabulary
              </Button>
            </Stack>
          </Stack>
        ) : null}
      </Stack>
    </FeaturePanel>
  );
}
