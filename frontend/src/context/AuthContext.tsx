import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { clearToken, getToken, setToken as persistToken } from "../auth";
import { fetchCurrentUser } from "../modules/auth/api/authApi";
import { clearStorySession } from "../modules/learning/storySessionCache";
import { clearTutorChatSession } from "../modules/tutor/tutorChatSessionCache";
import { queryClient } from "../shared/api/queryClient";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type User = {
  id: string;
  email: string;
  full_name?: string | null;
};

type AuthContextValue = {
  token: string | null;
  user: User | null;
  status: AuthStatus;
  sessionDegraded: boolean;
  loginWithToken: (token: string, remember?: boolean) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
  retrySession: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const [user, setUser] = useState<User | null>(null);
  const [sessionDegraded, setSessionDegraded] = useState(false);
  const [status, setStatus] = useState<AuthStatus>(() =>
    getToken() ? "loading" : "unauthenticated",
  );

  const logout = useCallback(() => {
    clearToken();
    queryClient.clear();
    clearStorySession();
    clearTutorChatSession();
    setTokenState(null);
    setUser(null);
    setSessionDegraded(false);
    setStatus("unauthenticated");
  }, []);

  const refreshUser = useCallback(async () => {
    if (!token) return;
    try {
      const data = await fetchCurrentUser();
      setUser(data);
      setSessionDegraded(false);
      setStatus("authenticated");
    } catch {
      throw new Error("unauthorized");
    }
  }, [token]);

  const retrySession = useCallback(async () => {
    if (!token) return;
    setStatus("loading");
    setSessionDegraded(false);
    try {
      await refreshUser();
    } catch (err: unknown) {
      if (err instanceof Error && err.message === "unauthorized") {
        logout();
        return;
      }
      setSessionDegraded(true);
      setStatus("authenticated");
    }
  }, [token, refreshUser, logout]);

  useEffect(() => {
    if (!token) return;

    let active = true;
    setStatus("loading");
    refreshUser().catch((err: unknown) => {
      if (!active) return;
      if (err instanceof Error && err.message === "unauthorized") {
        logout();
        return;
      }
      setSessionDegraded(true);
      setStatus("authenticated");
    });

    return () => {
      active = false;
    };
  }, [token, refreshUser, logout]);

  const loginWithToken = useCallback((nextToken: string, remember = true) => {
    persistToken(nextToken, remember);
    setTokenState(nextToken);
    setSessionDegraded(false);
    setStatus("loading");
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      status,
      sessionDegraded,
      loginWithToken,
      logout,
      refreshUser,
      retrySession,
    }),
    [token, user, status, sessionDegraded, loginWithToken, logout, refreshUser, retrySession],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
