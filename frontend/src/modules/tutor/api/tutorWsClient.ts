import { API_BASE } from "../../../config";
import type { TutorWsInbound, TutorWsOutbound } from "../types";
import {
  computeReconnectDelayMs,
  shouldAttemptReconnect,
} from "./wsReconnect";

/** Must match backend `auth/ws_tokens.WS_AUTH_SUBPROTOCOL`. */
export const WS_AUTH_SUBPROTOCOL = "languageapp.jwt";

export function buildTutorWsUrl(): string {
  const base = API_BASE.replace(/^http/i, (match: string) =>
    match.toLowerCase() === "https" ? "wss" : "ws",
  );
  return `${base}/api/tutor/ws`;
}

type Listener = (message: TutorWsInbound) => void;
type StateListener = (state: "connecting" | "open" | "closed" | "error") => void;

export class TutorWsClient {
  private socket: WebSocket | null = null;
  private listeners = new Set<Listener>();
  private stateListeners = new Set<StateListener>();
  private reconnectTimer: number | null = null;
  private reconnectAttempts = 0;
  private shouldReconnect = false;
  private token = "";

  connect(token: string) {
    this.token = token;
    this.shouldReconnect = true;
    this.reconnectAttempts = 0;
    this.openSocket();
  }

  disconnect() {
    this.shouldReconnect = false;
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.socket?.close();
    this.socket = null;
    this.emitState("closed");
  }

  send(message: TutorWsOutbound) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      throw new Error("Tutor socket is not connected.");
    }
    this.socket.send(JSON.stringify(message));
  }

  onMessage(listener: Listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  onState(listener: StateListener) {
    this.stateListeners.add(listener);
    return () => this.stateListeners.delete(listener);
  }

  private openSocket() {
    if (!this.token) return;
    this.emitState("connecting");
    const socket = new WebSocket(buildTutorWsUrl(), [WS_AUTH_SUBPROTOCOL, this.token]);
    this.socket = socket;

    socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.emitState("open");
    };
    socket.onclose = () => {
      this.emitState("closed");
      if (!this.shouldReconnect) return;

      this.reconnectAttempts += 1;
      if (!shouldAttemptReconnect(this.reconnectAttempts)) {
        this.shouldReconnect = false;
        this.emitState("error");
        this.listeners.forEach((listener) =>
          listener({
            type: "error",
            code: "WS_RECONNECT_EXHAUSTED",
            message: "Tutor connection failed after multiple retries. Refresh the page to try again.",
          }),
        );
        return;
      }

      const delayMs = computeReconnectDelayMs(this.reconnectAttempts);
      this.reconnectTimer = window.setTimeout(() => this.openSocket(), delayMs);
    };
    socket.onerror = () => this.emitState("error");
    socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(String(event.data)) as TutorWsInbound;
        this.listeners.forEach((listener) => listener(parsed));
      } catch {
        this.listeners.forEach((listener) =>
          listener({ type: "error", message: "Malformed tutor stream payload." }),
        );
      }
    };
  }

  private emitState(state: "connecting" | "open" | "closed" | "error") {
    this.stateListeners.forEach((listener) => listener(state));
  }
}
