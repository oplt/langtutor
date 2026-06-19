import { useMemo, useState } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import TextField from "@mui/material/TextField";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
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

  const handleSingleSelect = (_event: React.MouseEvent<HTMLElement>, next: string | null) => {
    if (!next || disabled) return;
    onChange({ ...value, selected: [next] });
  };

  const handleMultiSelect = (_event: React.MouseEvent<HTMLElement>, next: string[]) => {
    if (disabled) return;
    onChange({ ...value, selected: next });
  };

  return (
    <Stack spacing={1.5}>
      <Typography variant="body2">{question.prompt}</Typography>
      {options.length > 0 && multi && (
        <ToggleButtonGroup
          value={value.selected}
          onChange={handleMultiSelect}
          aria-label={question.header || "Answer options"}
          size="small"
          sx={{ flexWrap: "wrap", gap: 0.5 }}
        >
          {options.map((option) => (
            <ToggleButton
              key={option.label}
              value={option.label}
              disabled={disabled}
              aria-label={option.description ?? option.label}
            >
              {option.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      )}
      {options.length > 0 && !multi && (
        <ToggleButtonGroup
          exclusive
          value={value.selected[0] ?? null}
          onChange={handleSingleSelect}
          aria-label={question.header || "Answer options"}
          size="small"
          sx={{ flexWrap: "wrap", gap: 0.5 }}
        >
          {options.map((option) => (
            <ToggleButton
              key={option.label}
              value={option.label}
              disabled={disabled}
              aria-label={option.description ?? option.label}
            >
              {option.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
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
  const activeQuestion = questions[showTabs ? tab : 0];

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
                id={`ask-user-tab-${question.id}`}
                aria-controls={`ask-user-panel-${question.id}`}
                label={question.header || `Q${index + 1}`}
              />
            ))}
          </Tabs>
        )}
        <Box
          id={`ask-user-panel-${activeQuestion.id}`}
          role="tabpanel"
          aria-labelledby={`ask-user-tab-${activeQuestion.id}`}
        >
          <QuestionPanel
            question={activeQuestion}
            value={state[activeQuestion.id]}
            onChange={(next) =>
              setState((prev) => ({ ...prev, [activeQuestion.id]: next }))
            }
            disabled={disabled}
          />
        </Box>
        <Box>
          <Button variant="contained" size="small" disabled={disabled || !canSubmit} onClick={submit}>
            Submit answer
          </Button>
        </Box>
      </Stack>
    </Alert>
  );
}
