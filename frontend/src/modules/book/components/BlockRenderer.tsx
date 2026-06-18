import { useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Divider from "@mui/material/Divider";
import MenuItem from "@mui/material/MenuItem";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import type { LessonBlock } from "../types";

type BlockRendererProps = {
  block: LessonBlock;
  onQuizScore?: (score: number) => void;
};

export function BlockRenderer({ block, onQuizScore }: BlockRendererProps) {
  switch (block.type) {
    case "text":
      return <TextBlock block={block} />;
    case "vocabulary":
      return <VocabularyBlock block={block} />;
    case "dialogue":
      return <DialogueBlock block={block} />;
    case "pronunciation":
      return <PronunciationBlock block={block} />;
    case "listening":
      return <ListeningBlock block={block} />;
    case "quiz":
      return <QuizBlock block={block} onQuizScore={onQuizScore} />;
    default:
      return <Alert severity="warning">Unsupported block type: {block.type}</Alert>;
  }
}

function TextBlock({ block }: BlockRendererProps) {
  const markdown = String(block.payload.markdown ?? "");
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" gutterBottom>
          {block.title}
        </Typography>
        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
          {markdown.replace(/\*\*(.*?)\*\*/g, "$1")}
        </Typography>
      </CardContent>
    </Card>
  );
}

function VocabularyBlock({ block }: BlockRendererProps) {
  const cards =
    (block.payload.cards as Array<{ front: string; back: string; hint?: string }>) ?? [];
  const [index, setIndex] = useState(0);
  const card = cards[index];
  if (!card) return null;

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={2}>
          <Typography variant="subtitle1">{block.title}</Typography>
          <Box sx={{ p: 2, bgcolor: "action.hover", borderRadius: 1, textAlign: "center" }}>
            <Typography variant="h5">{card.front}</Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {card.back}
            </Typography>
            {card.hint && <Chip size="small" label={card.hint} sx={{ mt: 1 }} />}
          </Box>
          <Stack direction="row" spacing={1}>
            <Button
              variant="outlined"
              disabled={index === 0}
              onClick={() => setIndex((value) => Math.max(0, value - 1))}
            >
              Previous
            </Button>
            <Button
              variant="contained"
              disabled={index >= cards.length - 1}
              onClick={() => setIndex((value) => Math.min(cards.length - 1, value + 1))}
            >
              Next card
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}

function DialogueBlock({ block }: BlockRendererProps) {
  const lines = (block.payload.lines as Array<{ speaker: string; text: string }>) ?? [];
  const practicePrompt = block.payload.practice_prompt
    ? String(block.payload.practice_prompt)
    : "";

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" gutterBottom>
          {block.title}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {String(block.payload.scenario ?? "")}
        </Typography>
        <Stack spacing={1}>
          {lines.map((line, idx) => (
            <Box key={idx} sx={{ display: "flex", gap: 1 }}>
              <Chip size="small" label={line.speaker} />
              <Typography variant="body2">{line.text}</Typography>
            </Box>
          ))}
        </Stack>
        {practicePrompt && (
          <Alert severity="info" sx={{ mt: 2 }}>
            {practicePrompt}
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

function PronunciationBlock({ block }: BlockRendererProps) {
  const items = (block.payload.items as Array<{ word: string; note?: string }>) ?? [];
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" gutterBottom>
          {block.title}
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {String(block.payload.instruction ?? "")}
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {items.map((item) => (
            <Chip key={item.word} label={item.word} variant="outlined" />
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
}

function ListeningBlock({ block }: BlockRendererProps) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" gutterBottom>
          {block.title}
        </Typography>
        <Typography variant="body2" gutterBottom>
          Transcript: {String(block.payload.transcript ?? "")}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {String(block.payload.comprehension_question ?? "")}
        </Typography>
      </CardContent>
    </Card>
  );
}

function QuizBlock({ block, onQuizScore }: BlockRendererProps) {
  const questions =
    (block.payload.questions as Array<{
      id: string;
      prompt: string;
      question_type: string;
      options: string[];
      correct_answer: string;
      explanation: string;
    }>) ?? [];

  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);

  const score = useMemo(() => {
    if (!submitted || questions.length === 0) return null;
    const correct = questions.filter(
      (question) =>
        (answers[question.id] ?? "").trim().toLowerCase() ===
        question.correct_answer.trim().toLowerCase(),
    ).length;
    return correct / questions.length;
  }, [answers, questions, submitted]);

  const submit = () => {
    setSubmitted(true);
    if (questions.length > 0) {
      const correct = questions.filter(
        (question) =>
          (answers[question.id] ?? "").trim().toLowerCase() ===
          question.correct_answer.trim().toLowerCase(),
      ).length;
      onQuizScore?.(correct / questions.length);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Typography variant="subtitle1" gutterBottom>
          {block.title}
        </Typography>
        <Stack spacing={2} divider={<Divider flexItem />}>
          {questions.map((question) => (
            <Stack key={question.id} spacing={1}>
              <Typography variant="body2">{question.prompt}</Typography>
              {question.question_type === "choice" ? (
                <TextField
                  select
                  size="small"
                  label="Answer"
                  value={answers[question.id] ?? ""}
                  onChange={(event) =>
                    setAnswers((prev) => ({ ...prev, [question.id]: event.target.value }))
                  }
                  disabled={submitted}
                >
                  {question.options.map((option) => (
                    <MenuItem key={option} value={option}>
                      {option}
                    </MenuItem>
                  ))}
                </TextField>
              ) : (
                <TextField
                  size="small"
                  label="Your answer"
                  value={answers[question.id] ?? ""}
                  onChange={(event) =>
                    setAnswers((prev) => ({ ...prev, [question.id]: event.target.value }))
                  }
                  disabled={submitted}
                />
              )}
              {submitted && (
                <Typography
                  variant="caption"
                  color={
                    (answers[question.id] ?? "").trim().toLowerCase() ===
                    question.correct_answer.trim().toLowerCase()
                      ? "success.main"
                      : "error.main"
                  }
                >
                  {question.explanation}
                </Typography>
              )}
            </Stack>
          ))}
        </Stack>
        {!submitted ? (
          <Button sx={{ mt: 2 }} variant="contained" onClick={submit}>
            Check answers
          </Button>
        ) : (
          score !== null && (
            <Alert severity={score >= 0.7 ? "success" : "info"} sx={{ mt: 2 }}>
              Quiz score: {Math.round(score * 100)}%
            </Alert>
          )
        )}
      </CardContent>
    </Card>
  );
}
