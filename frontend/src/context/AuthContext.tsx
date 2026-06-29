import React, { createContext, useCallback, useContext, useMemo, useState } from "react";
import { clearToken, getToken, setToken as persistToken } from "../auth";
import { clearStorySession } from "../modules/learning/storySessionCache";
import {
  currentUserQueryOptions,
  useCurrentUserQuery,
  useInvalidateCurrentUser,
} from "../modules/auth/hooks/useCurrentUserQuery";
import { clearTutorChatSession } from "../modules/tutor/tutorChatSessionCache";
import { queryClient } from "../shared/api/queryClient";
import { ApiError } from "../shared/api/httpClient";

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
  const [sessionDegraded, setSessionDegraded] = useState(false);
  const invalidateCurrentUser = useInvalidateCurrentUser();
  const currentUserQuery = useCurrentUserQuery(Boolean(token));

  const logout = useCallback(() => {
    clearToken();
    queryClient.removeQueries({ queryKey: currentUserQueryOptions.queryKey });
    queryClient.clear();
    clearStorySession();
    clearTutorChatSession();
    setTokenState(null);
    setSessionDegraded(false);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!token) return;
    const result = await queryClient.fetchQuery(currentUserQueryOptions);
    if (!result) return;
    setSessionDegraded(false);
  }, [token]);

  const retrySession = useCallback(async () => {
    if (!token) return;
    setSessionDegraded(false);
    try {
      await refreshUser();
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 401) {
        logout();
        return;
      }
      setSessionDegraded(true);
    }
  }, [token, refreshUser, logout]);

  const loginWithToken = useCallback((nextToken: string, remember = true) => {
    persistToken(nextToken, remember);
    setTokenState(nextToken);
    setSessionDegraded(false);
  }, []);

  const status: AuthStatus = useMemo(() => {
    if (!token) return "unauthenticated";
    if (currentUserQuery.isPending) return "loading";
    if (currentUserQuery.isError) {
      if (
        currentUserQuery.error instanceof ApiError &&
        currentUserQuery.error.status === 401
      ) {
        return "unauthenticated";
      }
      return sessionDegraded ? "authenticated" : "loading";
    }
    return currentUserQuery.data ? "authenticated" : "loading";
  }, [token, currentUserQuery.isPending, currentUserQuery.isError, currentUserQuery.error, currentUserQuery.data, sessionDegraded]);

  React.useEffect(() => {
    if (!token) return;
    if (
      currentUserQuery.isError &&
      currentUserQuery.error instanceof ApiError &&
      currentUserQuery.error.status === 401
    ) {
      logout();
    } else if (currentUserQuery.isError) {
      setSessionDegraded(true);
    }
  }, [token, currentUserQuery.isError, currentUserQuery.error, logout]);

  const user = currentUserQuery.data ?? null;

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      status,
      sessionDegraded,
      loginWithToken,
      logout,
      refreshUser: async () => {
        await invalidateCurrentUser();
        await refreshUser();
      },
      retrySession,
    }),
    [token, user, status, sessionDegraded, loginWithToken, logout, refreshUser, retrySession, invalidateCurrentUser],
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
