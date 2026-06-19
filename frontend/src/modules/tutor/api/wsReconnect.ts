export const WS_RECONNECT_BASE_MS = 1_000;
export const WS_RECONNECT_MAX_MS = 30_000;
export const WS_RECONNECT_MAX_ATTEMPTS = 10;

export function computeReconnectDelayMs(attempt: number): number {
  if (attempt <= 0) return WS_RECONNECT_BASE_MS;
  const delay = WS_RECONNECT_BASE_MS * 2 ** (attempt - 1);
  return Math.min(delay, WS_RECONNECT_MAX_MS);
}

export function shouldAttemptReconnect(attempt: number): boolean {
  return attempt < WS_RECONNECT_MAX_ATTEMPTS;
}
