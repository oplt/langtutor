import { describe, expect, it } from "vitest";

import {
  WS_RECONNECT_BASE_MS,
  WS_RECONNECT_MAX_ATTEMPTS,
  WS_RECONNECT_MAX_MS,
  computeReconnectDelayMs,
  shouldAttemptReconnect,
} from "./wsReconnect";

describe("wsReconnect", () => {
  it("uses exponential backoff capped at the max delay", () => {
    expect(computeReconnectDelayMs(1)).toBe(WS_RECONNECT_BASE_MS);
    expect(computeReconnectDelayMs(2)).toBe(WS_RECONNECT_BASE_MS * 2);
    expect(computeReconnectDelayMs(3)).toBe(WS_RECONNECT_BASE_MS * 4);
    expect(computeReconnectDelayMs(20)).toBe(WS_RECONNECT_MAX_MS);
  });

  it("stops reconnecting after max attempts", () => {
    expect(shouldAttemptReconnect(0)).toBe(true);
    expect(shouldAttemptReconnect(WS_RECONNECT_MAX_ATTEMPTS - 1)).toBe(true);
    expect(shouldAttemptReconnect(WS_RECONNECT_MAX_ATTEMPTS)).toBe(false);
  });
});
