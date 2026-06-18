import { useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import type { AskUserAnswer, AskUserPayload, AskUserQuestion } from "../types";

type Props = {
  payload: AskUserPayload;
  disabled?: boolean;
  onSubmit: (answers: AskUserAnswer[], summary: string) => void;
};

type QuestionState = {
  selected: string[];
  freeText: string;
};

function initState(questions: AskUserQuestion[]): Record<string, QuestionState> {
  const state: Record<string, QuestionState> = {};
  for (const question of questions) {
    state[question.id] = { selected: [], freeText: "" };
  }
  return state;
}

function buildAnswers(
  questions: AskUserQuestion[],
  state: Record<string, QuestionState>,
): AskUserAnswer[] {
  const answers: AskUserAnswer[] = [];
  for (const question of questions) {
    const entry = state[question.id];
    if (!entry) continue;
    const parts = [...entry.selected];
    const trimmed = entry.freeText.trim();
    if (trimmed) parts.push(trimmed);
    if (!parts.length) continue;
    answers.push({ questionId: question.id, text: parts.join("; ") });
  }
  return answers;
}

function QuestionPanel({
  question,
  value,
  onChange,
  disabled,
}: {
  question: AskUserQuestion;
  value: QuestionState;
  onChange: (next: QuestionState) => void;
  disabled?: boolean;
}) {
  const options = question.options ?? [];
  const multi = Boolean(question.multi_select);
  const allowFreeText = question.allow_free_text !== false;

  const toggleOption = (label: string) => {
    if (multi) {
      const selected = value.selected.includes(label)
        ? value.selected.filter((item) => item !== label)
        : [...value.selected, label];
      onChange({ ...value, selected });
      return;
    }
    onChange({ ...value, selected: [label] });
  };

  return (
    <Stack spacing={1.5}>
      <Typography variant="body2">{question.prompt}</Typography>
      {options.length > 0 && (
        <Stack direction="row" flexWrap="wrap" gap={1} useFlexGap>
          {options.map((option) => {
            const active = value.selected.includes(option.label);
            return (
              <Chip
                key={option.label}
                label={option.label}
                title={option.description ?? undefined}
                color={active ? "primary" : "default"}
                variant={active ? "filled" : "outlined"}
                onClick={() => !disabled && toggleOption(option.label)}
                disabled={disabled}
              />
            );
          })}
        </Stack>
      )}
      {allowFreeText && (
        <TextField
          size="small"
          fullWidth
          multiline
          minRows={2}
          placeholder={question.placeholder ?? "Type your answer..."}
          value={value.freeText}
          onChange={(e) => onChange({ ...value, freeText: e.target.value })}
          disabled={disabled}
        />
      )}
    </Stack>
  );
}

export function AskUserCard({ payload, disabled, onSubmit }: Props) {
  const questions = payload.questions;
  const [tab, setTab] = useState(0);
  const [state, setState] = useState(() => initState(questions));

  const answers = useMemo(() => buildAnswers(questions, state), [questions, state]);
  const canSubmit = answers.length > 0;

  const submit = () => {
    if (!canSubmit) return;
    const summary = answers.map((answer) => answer.text).join(" · ");
    onSubmit(answers, summary);
  };

  if (!questions.length) return null;

  const showTabs = questions.length > 1;

  return (
    <Alert severity="info" sx={{ alignItems: "flex-start" }}>
      <Stack spacing={1.5} sx={{ width: "100%" }}>
        {payload.intro && (
          <Typography variant="body2" color="text.secondary">
            {payload.intro}
          </Typography>
        )}
        {showTabs && (
          <Tabs
            value={tab}
            onChange={(_, value: number) => setTab(value)}
            variant="scrollable"
            allowScrollButtonsMobile
          >
            {questions.map((question, index) => (
              <Tab
                key={question.id}
                value={index}
                label={question.header || `Q${index + 1}`}
              />
            ))}
          </Tabs>
        )}
        <QuestionPanel
          question={questions[showTabs ? tab : 0]}
          value={state[questions[showTabs ? tab : 0].id]}
          onChange={(next) =>
            setState((prev) => ({ ...prev, [questions[showTabs ? tab : 0].id]: next }))
          }
          disabled={disabled}
        />
        <Box>
          <Button variant="contained" size="small" disabled={disabled || !canSubmit} onClick={submit}>
            Submit answer
          </Button>
        </Box>
      </Stack>
    </Alert>
  );
}
