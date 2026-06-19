import { beforeEach, describe, expect, it, vi } from "vitest";
import { signup } from "./authApi";
import { httpRequest } from "../../../shared/api/httpClient";

vi.mock("../../../shared/api/httpClient", () => ({
  httpRequest: vi.fn(),
}));

describe("signup", () => {
  beforeEach(() => {
    vi.mocked(httpRequest).mockResolvedValue({ access_token: "test-token" });
  });

  it("maps full name, email, and password to the correct request body", async () => {
    await signup({
      full_name: "ali",
      email: "admin@admin.com",
      password: "12345678",
    });

    expect(httpRequest).toHaveBeenCalledWith("/auth/signup", {
      method: "POST",
      body: {
        email: "admin@admin.com",
        password: "12345678",
        full_name: "ali",
      },
      auth: false,
    });
  });

  it("trims email whitespace before sending", async () => {
    await signup({
      full_name: "ali",
      email: "  admin@admin.com  ",
      password: "12345678",
    });

    expect(httpRequest).toHaveBeenCalledWith("/auth/signup", {
      method: "POST",
      body: {
        email: "admin@admin.com",
        password: "12345678",
        full_name: "ali",
      },
      auth: false,
    });
  });
});
