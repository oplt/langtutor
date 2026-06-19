import { httpRequest } from "../../../shared/api/httpClient";

export type AuthUser = {
  id: string;
  email: string;
  full_name?: string | null;
};

type TokenResponse = {
  access_token: string;
};

export type SignupPayload = {
  email: string;
  password: string;
  full_name?: string | null;
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

export async function signup(payload: SignupPayload): Promise<TokenResponse> {
  return httpRequest<TokenResponse>("/auth/signup", {
    method: "POST",
    body: {
      email: payload.email.trim(),
      password: payload.password,
      full_name: payload.full_name ?? null,
    },
    auth: false,
  });
}

export async function updateProfile(fullName: string): Promise<AuthUser> {
  return httpRequest<AuthUser>("/auth/me", {
    method: "PATCH",
    body: { full_name: fullName },
  });
}
