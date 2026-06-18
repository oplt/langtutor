import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import App from "./App.tsx";
import "./output.css";
import { AuthProvider } from "./context/AuthContext";
import { queryClient } from "./shared/api/queryClient";

const container = document.getElementById("root");
if (!container) throw new Error('Root element "#root" not found');

// StrictMode intentionally doubles effects in development to surface unsafe lifecycles.
createRoot(container).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>
);
