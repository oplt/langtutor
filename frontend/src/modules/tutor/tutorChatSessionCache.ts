import type { TutorChatMessage } from "./types";

const STORAGE_KEY = "language-app:tutor-chat";

type TutorChatSession = {
  sessionId: string;
  cefrLevel: string;
  persona: string;
  messages: TutorChatMessage[];
};

export function loadTutorChatSession(): TutorChatSession | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as TutorChatSession;
    if (!Array.isArray(parsed.messages)) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveTutorChatSession(session: TutorChatSession): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    // ignore quota errors
  }
}

export function clearTutorChatSession(): void {
  sessionStorage.removeItem(STORAGE_KEY);
}
