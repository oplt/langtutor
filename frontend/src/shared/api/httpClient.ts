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

const DEFAULT_TIMEOUT_MS = 30_000;

export async function httpRequest<T>(
  path: string,
  options: {
    method?: string;
    body?: unknown;
    auth?: boolean;
    timeoutMs?: number;
  } = {},
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

  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      method: options.method ?? "GET",
      headers,
      body,
      signal: controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(`Request timed out after ${timeoutMs}ms`, 408);
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }

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
