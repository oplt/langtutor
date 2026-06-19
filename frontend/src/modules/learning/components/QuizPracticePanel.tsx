import { useCallback, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useQueryClient } from "@tanstack/react-query";

import { CefrLevelSelect } from "../../../shared/components/CefrLevelSelect";
import { FeaturePanel } from "../../../shared/components/FeaturePanel";
import { queryKeys } from "../../../shared/api/queryKeys";
import { generateQuiz, submitQuizAnswer } from "../api/quizApi";
import type { CefrLevel } from "../api/learningPathApi";
import type { QuizQuestion, QuizSession } from "../api/quizApi";

const TYPE_LABELS: Record<string, string> = {
  recognition: "Recognition",
  recall: "Recall",
  production: "Production",
  fill_blank: "Fill blank",
  translation: "Translation",
};

export function QuizPracticePanel() {
  const queryClient = useQueryClient();
  const [level, setLevel] = useState<CefrLevel>("A1");
  const [session, setSession] = useState<QuizSession | null>(null);
  const [index, setIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [score, setScore] = useState({ correct: 0, total: 0 });

  const current: QuizQuestion | null = session?.questions[index] ?? null;

  const start = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    setActionError(null);
    setFeedback(null);
    setScore({ correct: 0, total: 0 });
    setIndex(0);
    setAnswer("");
    try {
      const data = await generateQuiz(level, 5, true);
      setSession(data);
      if (!data.questions.length) {
        setLoadError("No questions generated. Try again or check AI settings.");
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to generate quiz.");
      setSession(null);
    } finally {
      setLoading(false);
    }
  }, [level]);

  const submit = async () => {
    if (!current || !answer.trim()) return;
    setLoading(true);
    setLoadError(null);
    setActionError(null);
    try {
      const result = await submitQuizAnswer(current, answer.trim());
      setFeedback(result.feedback);
      setScore((prev) => ({
        correct: prev.correct + (result.correct ? 1 : 0),
        total: prev.total + 1,
      }));
      void queryClient.invalidateQueries({ queryKey: queryKeys.learning.progressSummary });
      const nextIndex = index + 1;
      if (session && nextIndex < session.questions.length) {
        setIndex(nextIndex);
        setAnswer("");
        setFeedback(null);
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not submit answer.");
    } finally {
      setLoading(false);
    }
  };

  const finished =
    session && session.questions.length > 0 && index >= session.questions.length;

  return (
    <FeaturePanel
      title="Word quiz"
      description="Recognition, recall, and production drills from your Dutch word list."
      loading={loading && !session}
      error={loadError}
      actionError={actionError}
      onRetry={() => void start()}
    >
      <Stack spacing={2}>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <CefrLevelSelect value={level} onChange={setLevel} label="Level" />
          <Button variant="contained" size="small" onClick={() => void start()} disabled={loading}>
            {session ? "New quiz" : "Generate quiz"}
          </Button>
          {session && (
            <Chip size="small" label={`Source: ${session.source}`} variant="outlined" />
          )}
        </Stack>

        {feedback && !finished && <Alert severity="info">{feedback}</Alert>}

        {finished && (
          <Alert severity="success">
            Session complete: {score.correct}/{score.total} correct.
          </Alert>
        )}

        {current && !finished && (
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Stack spacing={1.5}>
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                <Chip
                  size="small"
                  label={TYPE_LABELS[current.exercise_type] ?? current.exercise_type}
                />
                <Typography variant="caption" color="text.secondary">
                  {index + 1} / {session?.questions.length}
                </Typography>
                {current.lemma && (
                  <Chip size="small" variant="outlined" label={current.lemma} />
                )}
              </Stack>
              <Typography variant="body1">{current.prompt}</Typography>
              {current.options.length > 0 && (
                <Stack direction="row" flexWrap="wrap" gap={0.5} useFlexGap>
                  {current.options.map((option) => (
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
                  fullWidth
                  size="small"
                  multiline={current.use_ai_judge}
                  minRows={current.use_ai_judge ? 2 : 1}
                  placeholder="Your answer"
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey && !current.use_ai_judge) {
                      e.preventDefault();
                      void submit();
                    }
                  }}
                />
                <Button
                  variant="contained"
                  onClick={() => void submit()}
                  disabled={loading || !answer.trim()}
                >
                  Check
                </Button>
              </Stack>
              {current.use_ai_judge && (
                <Typography variant="caption" color="text.secondary">
                  Open-ended — AI judge provides feedback.
                </Typography>
              )}
            </Stack>
          </Paper>
        )}

        {!session && !loading && (
          <Paper variant="outlined" sx={{ p: 2.5, textAlign: "center" }}>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Ready to practice?
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Generate recognition, recall, fill-blank, and production drills from your Dutch word
              list. Answers update word progress automatically.
            </Typography>
            <Button variant="contained" onClick={() => void start()}>
              Generate quiz
            </Button>
          </Paper>
        )}
      </Stack>
    </FeaturePanel>
  );
}
