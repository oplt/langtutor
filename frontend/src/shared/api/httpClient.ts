import { API_BASE } from "../../config";
import { getAuthHeader } from "../../auth";

export class ApiError extends Error {
  detail?: string;
  status: number;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

export async function httpRequest<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (options.auth !== false) {
    Object.assign(headers, getAuthHeader());
  }
  let body: string | undefined;
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers,
    body,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message =
      (data as { error?: { message?: string }; detail?: string | { message?: string } })?.error
        ?.message ??
      (typeof data?.detail === "string" ? data.detail : data?.detail?.message) ??
      `Request failed (${response.status})`;
    throw new ApiError(message, response.status);
  }
  return data as T;
}
