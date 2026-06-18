export type AskUserOption = {
  label: string;
  description?: string | null;
};

export type AskUserQuestion = {
  id: string;
  prompt: string;
  header?: string | null;
  multi_select?: boolean;
  options?: AskUserOption[];
  allow_free_text?: boolean;
  placeholder?: string | null;
};

export type AskUserPayload = {
  intro?: string | null;
  questions: AskUserQuestion[];
};

export type AskUserAnswer = {
  questionId: string;
  text: string;
};

export type TutorWsOutbound =
  | { type: "ping" }
  | {
      type: "message";
      payload: {
        message: string;
        session_id?: string;
        capability?: string;
        cefr_level?: string;
        persona?: string;
        language?: string;
        conversation_history?: Array<{ role: string; content: string }>;
      };
    }
  | {
      type: "submit_user_reply";
      turn_id: string;
      reply?: string;
      answers?: AskUserAnswer[];
    }
  | { type: "cancel_turn"; turn_id: string };

export type TutorStreamEvent = {
  type: string;
  source?: string;
  content?: string;
  metadata?: Record<string, unknown>;
};

export type TutorWsInbound =
  | { type: "pong" }
  | { type: "turn_started"; turn_id: string; session_id: string }
  | {
      type: "event";
      turn_id: string;
      session_id: string;
      seq: number;
      event: TutorStreamEvent;
    }
  | {
      type: "turn_paused";
      turn_id: string;
      session_id: string;
      question: string;
      ask_user?: AskUserPayload;
    }
  | { type: "turn_done"; turn_id: string; session_id: string }
  | { type: "turn_cancelled"; turn_id: string; session_id?: string }
  | { type: "error"; message: string; code?: string; turn_id?: string };

export type TutorChatMessage = {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  streaming?: boolean;
  error?: boolean;
};

export type TutorConnectionState = "idle" | "connecting" | "open" | "closed" | "error";
