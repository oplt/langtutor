import { describe, expect, it } from "vitest";
import { ApiError } from "./httpClient";

describe("ApiError", () => {
  it("stores status and detail", () => {
    const error = new ApiError("Request failed", 401, "unauthorized");
    expect(error.message).toBe("Request failed");
    expect(error.status).toBe(401);
    expect(error.detail).toBe("unauthorized");
    expect(error).toBeInstanceOf(Error);
  });
});
