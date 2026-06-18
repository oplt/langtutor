import { httpRequest } from "../../../shared/api/httpClient";

export type AuthUser = {
  id: string;
  email: string;
  full_name?: string | null;
};

type TokenResponse = {
  access_token: string;
};

export async function fetchCurrentUser(): Promise<AuthUser> {
  return httpRequest<AuthUser>("/auth/me");
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  return httpRequest<TokenResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
    auth: false,
  });
}

export async function signup(
  email: string,
  password: string,
  fullName?: string,
): Promise<TokenResponse> {
  return httpRequest<TokenResponse>("/auth/signup", {
    method: "POST",
    body: { email, password, full_name: fullName ?? null },
    auth: false,
  });
}

export async function updateProfile(fullName: string): Promise<AuthUser> {
  return httpRequest<AuthUser>("/auth/me", {
    method: "PATCH",
    body: { full_name: fullName },
  });
}
