import { memo, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import StopRoundedIcon from "@mui/icons-material/StopRounded";
import SendRoundedIcon from "@mui/icons-material/SendRounded";

import type { CefrLevel } from "../../learning/api/learningPathApi";
import { CefrLevelSelect } from "../../../shared/components/CefrLevelSelect";
import { FeaturePanel } from "../../../shared/components/FeaturePanel";
import { AskUserCard } from "./AskUserCard";
import { useTutorChat } from "../hooks/useTutorChat";
import type { TutorChatMessage, TutorConnectionState } from "../types";

const PERSONAS = [
  { value: "conversation-partner", label: "Conversation partner" },
  { value: "grammar-coach", label: "Grammar coach" },
  { value: "nl-dutch", label: "Netherlands Dutch" },
  { value: "be-dutch", label: "Belgium Dutch" },
] as const;

function connectionLabel(state: TutorConnectionState) {
  switch (state) {
    case "open":
      return { label: "Connected", color: "success" as const };
    case "connecting":
      return { label: "Connecting", color: "default" as const };
    case "error":
      return { label: "Offline", color: "error" as const };
    case "closed":
      return { label: "Reconnecting", color: "warning" as const };
    default:
      return { label: "Idle", color: "default" as const };
  }
}

function messageBubblePropsEqual(
  prev: { message: TutorChatMessage },
  next: { message: TutorChatMessage },
) {
  const left = prev.message;
  const right = next.message;
  return (
    left.id === right.id &&
    left.role === right.role &&
    left.content === right.content &&
    left.streaming === right.streaming &&
    left.error === right.error
  );
}

const MessageBubble = memo(function MessageBubble({ message }: { message: TutorChatMessage }) {
  const isUser = message.role === "user";
  return (
    <Box sx={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start" }}>
      <Paper
        variant="outlined"
        sx={{
          px: 1.5,
          py: 1,
          maxWidth: "85%",
          bgcolor: isUser ? "primary.main" : "background.paper",
          color: isUser ? "primary.contrastText" : "text.primary",
          borderColor: message.error ? "error.main" : "divider",
        }}
      >
        <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
          {message.content}
          {message.streaming ? "▍" : ""}
        </Typography>
      </Paper>
    </Box>
  );
}, messageBubblePropsEqual);

export function TutorChatPanel() {
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    connection,
    cefrLevel,
    setCefrLevel,
    persona,
    setPersona,
    messages,
    pausedQuestion,
    pausedAskUser,
    isBusy,
    error,
    clearError,
    sendMessage,
    sendPausedReply,
    cancelTurn,
  } = useTutorChat();

  const [draft, setDraft] = useState("");
  const [connectionAnnouncement, setConnectionAnnouncement] = useState("");
  const sentPromptRef = useRef<string | null>(null);
  const conn = useMemo(() => connectionLabel(connection), [connection]);
  const awaitingReply = Boolean(pausedQuestion || pausedAskUser);
  const structuredPause = Boolean(pausedAskUser?.questions?.length);
  const promptParam = searchParams.get("prompt");

  useEffect(() => {
    setConnectionAnnouncement(`Tutor connection ${conn.label.toLowerCase()}.`);
  }, [conn.label]);

  useEffect(() => {
    if (!promptParam) {
      sentPromptRef.current = null;
    }
  }, [promptParam]);

  useEffect(() => {
    if (!promptParam || sentPromptRef.current === promptParam) return;
    if (connection !== "open" || isBusy || awaitingReply) return;

    sentPromptRef.current = promptParam;
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.delete("prompt");
        return next;
      },
      { replace: true },
    );
    void sendMessage(promptParam);
  }, [
    awaitingReply,
    connection,
    isBusy,
    promptParam,
    sendMessage,
    setSearchParams,
  ]);

  const submit = async () => {
    if (!draft.trim() || structuredPause) return;
    const text = draft;
    setDraft("");
    if (awaitingReply) await sendPausedReply(text);
    else await sendMessage(text);
  };

  return (
    <FeaturePanel
      title="Dutch AI Tutor"
      description="Practice grammar, conversation, and drills. The tutor streams replies and can pause to ask follow-up questions."
      loading={connection === "connecting" || connection === "idle"}
      error={connection === "error" ? error || "Sign in to use the AI tutor." : null}
    >
      <Stack spacing={2} sx={{ height: "100%" }}>
      <Box
        component="span"
        aria-live="polite"
        sx={{
          position: "absolute",
          width: 1,
          height: 1,
          padding: 0,
          margin: -1,
          overflow: "hidden",
          clip: "rect(0, 0, 0, 0)",
          whiteSpace: "nowrap",
          border: 0,
        }}
      >
        {connectionAnnouncement}
      </Box>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1}
        alignItems={{ xs: "stretch", sm: "center" }}
        flexWrap="wrap"
        useFlexGap
      >
        <Chip size="small" color={conn.color} label={conn.label} />
        <CefrLevelSelect
          value={cefrLevel as CefrLevel}
          onChange={setCefrLevel}
          sx={{ minWidth: 110 }}
        />
        <TextField
          select
          size="small"
          label="Persona"
          value={persona}
          onChange={(e) => setPersona(e.target.value)}
          sx={{ minWidth: { xs: "100%", sm: 190 } }}
        >
          {PERSONAS.map((entry) => (
            <MenuItem key={entry.value} value={entry.value}>
              {entry.label}
            </MenuItem>
          ))}
        </TextField>
        {isBusy && (
          <Button size="small" color="warning" startIcon={<StopRoundedIcon />} onClick={cancelTurn}>
            Stop
          </Button>
        )}
      </Stack>

      {connection === "open" && error && (
        <Alert severity="error" onClose={clearError}>
          {error}
        </Alert>
      )}

      {structuredPause && pausedAskUser && (
        <AskUserCard
          payload={pausedAskUser}
          disabled={connection !== "open" || isBusy}
          onSubmit={(answers, summary) => void sendPausedReply(summary, answers)}
        />
      )}

      {awaitingReply && !structuredPause && pausedQuestion && (
        <Alert severity="info">
          <Typography variant="subtitle2" gutterBottom>
            Tutor question
          </Typography>
          <Typography variant="body2">{pausedQuestion}</Typography>
        </Alert>
      )}

      <Paper
        variant="outlined"
        aria-live="polite"
        aria-relevant="additions text"
        sx={{
          flex: 1,
          minHeight: 360,
          p: 2,
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: 1.5,
        }}
      >
        {messages.length === 0 ? (
          <Stack spacing={1} sx={{ m: "auto", textAlign: "center", maxWidth: 420 }}>
            <Typography variant="subtitle1">Practice with your tutor</Typography>
            <Typography variant="body2" color="text.secondary">
              Ask for grammar help, a simpler sentence, or a short drill. The tutor can pause and
              ask you to answer before continuing.
            </Typography>
          </Stack>
        ) : (
          messages.map((message) => <MessageBubble key={message.id} message={message} />)
        )}
        {isBusy && !streamingVisible(messages) && (
          <Stack direction="row" spacing={1} alignItems="center">
            <CircularProgress size={16} />
            <Typography variant="caption" color="text.secondary">
              Tutor is thinking...
            </Typography>
          </Stack>
        )}
      </Paper>

      {!structuredPause && (
        <Stack direction="row" spacing={1} alignItems="flex-end">
          <TextField
            fullWidth
            multiline
            minRows={2}
            maxRows={6}
            placeholder={
              awaitingReply
                ? "Type your answer to the tutor question..."
                : "Ask for a simpler version, grammar hint, or practice prompt."
            }
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void submit();
              }
            }}
            disabled={connection !== "open"}
          />
          <IconButton
            color="primary"
            aria-label="Send message"
            disabled={
              connection !== "open" || (!awaitingReply && isBusy) || !draft.trim()
            }
            onClick={() => void submit()}
          >
            <SendRoundedIcon />
          </IconButton>
        </Stack>
      )}
      </Stack>
    </FeaturePanel>
  );
}

function streamingVisible(messages: TutorChatMessage[]) {
  return messages.some((message) => message.streaming);
}
