// auth.tsx
const KEY = "access_token";
const PERSIST_KEY = "access_token_persist";

export function setToken(token: string, remember = true) {
  if (remember) {
    localStorage.setItem(KEY, token);
    localStorage.setItem(PERSIST_KEY, "1");
    sessionStorage.removeItem(KEY);
  } else {
    sessionStorage.setItem(KEY, token);
    localStorage.removeItem(KEY);
    localStorage.setItem(PERSIST_KEY, "0");
  }
}

export function getToken(): string | null {
  const localToken = localStorage.getItem(KEY);
  if (localToken) return localToken;
  return sessionStorage.getItem(KEY);
}

export function clearToken() {
  localStorage.removeItem(KEY);
  localStorage.removeItem(PERSIST_KEY);
  sessionStorage.removeItem(KEY);
}

export function shouldRememberSession(): boolean {
  return localStorage.getItem(PERSIST_KEY) !== "0";
}

// Add this function to get auth header
export function getAuthHeader(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}