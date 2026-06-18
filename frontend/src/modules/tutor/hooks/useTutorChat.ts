import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getToken } from "../../../auth";
import {
  loadTutorChatSession,
  saveTutorChatSession,
} from "../tutorChatSessionCache";
import { TutorWsClient } from "../api/tutorWsClient";
import type {
  AskUserAnswer,
  AskUserPayload,
  TutorChatMessage,
  TutorConnectionState,
  TutorWsInbound,
} from "../types";

function newId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function useTutorChat(initialCefrLevel = "A1") {
  const restored = loadTutorChatSession();
  const clientRef = useRef<TutorWsClient | null>(null);
  const [connection, setConnection] = useState<TutorConnectionState>("idle");
  const [sessionId, setSessionId] = useState<string>(restored?.sessionId ?? "");
  const [cefrLevel, setCefrLevel] = useState(restored?.cefrLevel ?? initialCefrLevel);
  const [persona, setPersona] = useState<string>(restored?.persona ?? "conversation-partner");
  const [messages, setMessages] = useState<TutorChatMessage[]>(restored?.messages ?? []);
  const [activeTurnId, setActiveTurnId] = useState<string | null>(null);
  const [pausedQuestion, setPausedQuestion] = useState<string | null>(null);
  const [pausedAskUser, setPausedAskUser] = useState<AskUserPayload | null>(null);
  const [isBusy, setIsBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const streamingIdRef = useRef<string | null>(null);

  const conversationHistory = useMemo(
    () =>
      messages
        .filter((message) => message.role === "user" || message.role === "assistant")
        .map((message) => ({ role: message.role, content: message.content })),
    [messages],
  );

  const appendAssistantStreaming = useCallback((chunk: string) => {
    const streamId = streamingIdRef.current;
    if (!streamId) {
      const id = newId();
      streamingIdRef.current = id;
      setMessages((prev) => [...prev, { id, role: "assistant", content: chunk, streaming: true }]);
      return;
    }
    setMessages((prev) =>
      prev.map((message) =>
        message.id === streamId ? { ...message, content: message.content + chunk } : message,
      ),
    );
  }, []);

  const finalizeAssistant = useCallback(() => {
    const streamId = streamingIdRef.current;
    if (!streamId) return;
    setMessages((prev) =>
      prev.map((message) =>
        message.id === streamId ? { ...message, streaming: false } : message,
      ),
    );
    streamingIdRef.current = null;
  }, []);

  const handleInbound = useCallback(
    (payload: TutorWsInbound) => {
      if (payload.type === "turn_started") {
        setSessionId(payload.session_id);
        setActiveTurnId(payload.turn_id);
        setPausedQuestion(null);
        setPausedAskUser(null);
        setIsBusy(true);
        setError(null);
        return;
      }

      if (payload.type === "event") {
        setSessionId(payload.session_id);
        const event = payload.event;
        if (event.type === "content" && event.content) {
          appendAssistantStreaming(event.content);
        }
        if (event.type === "content_delta" && event.content) {
          appendAssistantStreaming(event.content);
        }
        if (event.type === "error" && event.content) {
          setError(event.content);
        }
        if (event.type === "ask_user" && event.content) {
          finalizeAssistant();
          setPausedQuestion(event.content);
          const askUser = event.metadata?.ask_user;
          if (askUser && typeof askUser === "object" && Array.isArray((askUser as AskUserPayload).questions)) {
            setPausedAskUser(askUser as AskUserPayload);
          }
        }
        if (event.type === "done") {
          finalizeAssistant();
        }
        return;
      }

      if (payload.type === "turn_paused") {
        finalizeAssistant();
        setPausedQuestion(payload.question);
        setPausedAskUser(payload.ask_user ?? null);
        setIsBusy(false);
        return;
      }

      if (payload.type === "turn_done" || payload.type === "turn_cancelled") {
        finalizeAssistant();
        setActiveTurnId(null);
        setPausedAskUser(null);
        setIsBusy(false);
        return;
      }

      if (payload.type === "error") {
        setError(payload.message);
        setIsBusy(false);
        finalizeAssistant();
      }
    },
    [appendAssistantStreaming, finalizeAssistant],
  );

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setConnection("error");
      setError("Sign in to use the AI tutor.");
      return;
    }

    const client = new TutorWsClient();
    clientRef.current = client;
    const offMessage = client.onMessage(handleInbound);
    const offState = client.onState((state) => {
      if (state === "open") setConnection("open");
      else if (state === "connecting") setConnection("connecting");
      else if (state === "error") setConnection("error");
      else setConnection("closed");
    });
    client.connect(token);

    const ping = window.setInterval(() => {
      try {
        client.send({ type: "ping" });
      } catch {
        // socket reconnect will handle it
      }
    }, 25000);

    return () => {
      window.clearInterval(ping);
      offMessage();
      offState();
      client.disconnect();
      clientRef.current = null;
    };
  }, [handleInbound]);

  useEffect(() => {
    saveTutorChatSession({
      sessionId,
      cefrLevel,
      persona,
      messages: messages.map((message) => ({ ...message, streaming: false })),
    });
  }, [sessionId, cefrLevel, persona, messages]);

  const clearError = useCallback(() => setError(null), []);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isBusy) return;
      const client = clientRef.current;
      if (!client) throw new Error("Tutor socket unavailable.");

      setMessages((prev) => [...prev, { id: newId(), role: "user", content: trimmed }]);
      streamingIdRef.current = null;
      setError(null);
      setPausedQuestion(null);
      setPausedAskUser(null);

      client.send({
        type: "message",
        payload: {
          message: trimmed,
          session_id: sessionId || undefined,
          capability: "auto",
          cefr_level: cefrLevel,
          persona,
          language: "en",
          conversation_history: conversationHistory,
        },
      });
    },
    [cefrLevel, conversationHistory, isBusy, persona, sessionId],
  );

  const sendPausedReply = useCallback(
    async (reply: string, answers?: AskUserAnswer[]) => {
      const trimmed = reply.trim();
      if (!activeTurnId || (!trimmed && !answers?.length)) return;
      const client = clientRef.current;
      if (!client) throw new Error("Tutor socket unavailable.");

      const display = trimmed || (answers ?? []).map((answer) => answer.text).join(" · ");
      setMessages((prev) => [...prev, { id: newId(), role: "user", content: display }]);
      setPausedQuestion(null);
      setPausedAskUser(null);
      setIsBusy(true);
      setError(null);
      streamingIdRef.current = null;

      client.send({
        type: "submit_user_reply",
        turn_id: activeTurnId,
        reply: trimmed,
        answers,
      });
    },
    [activeTurnId],
  );

  const cancelTurn = useCallback(() => {
    if (!activeTurnId) return;
    clientRef.current?.send({ type: "cancel_turn", turn_id: activeTurnId });
    setIsBusy(false);
    setActiveTurnId(null);
    setPausedAskUser(null);
    finalizeAssistant();
  }, [activeTurnId, finalizeAssistant]);

  return {
    connection,
    sessionId,
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
  };
}
