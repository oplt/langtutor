import { describe, expect, it } from "vitest";

import { METRICS_POLL_INTERVAL_MS } from "./config";

describe("metrics polling config", () => {
  it("uses at least 15000ms when dev metrics polling is configured", () => {
    expect(METRICS_POLL_INTERVAL_MS).toBeGreaterThanOrEqual(15_000);
  });
});
