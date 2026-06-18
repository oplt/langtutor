import { describe, expect, it } from "vitest";

import { WS_AUTH_SUBPROTOCOL, buildTutorWsUrl } from "./tutorWsClient";

describe("buildTutorWsUrl", () => {
  it("does not put the JWT in the query string", () => {
    const url = buildTutorWsUrl();
    expect(url).not.toContain("token=");
    expect(url.endsWith("/api/tutor/ws")).toBe(true);
  });

  it("exports the backend auth subprotocol constant", () => {
    expect(WS_AUTH_SUBPROTOCOL).toBe("languageapp.jwt");
  });
});
