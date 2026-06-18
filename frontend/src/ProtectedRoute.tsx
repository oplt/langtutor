import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./context/AuthContext";
import { PageLoading } from "./shared/components/PageLoading";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { token, status } = useAuth();

  if (status === "loading") {
    return <PageLoading label="Checking your session…" />;
  }

  if (!token || status !== "authenticated") {
    return <Navigate to="/#auth" replace />;
  }

  return <>{children}</>;
}
