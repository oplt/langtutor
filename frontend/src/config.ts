export const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** Minimum interval for optional dev metrics polling (ms). */
export const METRICS_POLL_INTERVAL_MS = Number(
  import.meta.env.VITE_METRICS_POLL_INTERVAL_MS ?? 15_000,
);

/** Enable optional dev metrics polling only when explicitly requested. */
export const DEV_METRICS_POLL_ENABLED =
  import.meta.env.VITE_DEV_METRICS_POLL === "true";
