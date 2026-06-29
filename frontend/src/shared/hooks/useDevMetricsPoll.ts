import { useEffect } from "react";

import { API_BASE, DEV_METRICS_POLL_ENABLED, METRICS_POLL_INTERVAL_MS } from "../../config";

function isDocumentVisible(): boolean {
  return typeof document === "undefined" || document.visibilityState === "visible";
}

/**
 * Optional dev-only metrics poller. Disabled by default.
 * Uses METRICS_POLL_INTERVAL_MS (default 15s) and pauses in background tabs.
 */
export function useDevMetricsPoll(enabled: boolean = DEV_METRICS_POLL_ENABLED) {
  useEffect(() => {
    if (!enabled || METRICS_POLL_INTERVAL_MS < 15_000) return;

    let active = true;

    const poll = () => {
      if (!active || !isDocumentVisible()) return;
      void fetch(`${API_BASE}/metrics`, { method: "GET" }).catch(() => undefined);
    };

    const onVisibility = () => {
      if (isDocumentVisible()) poll();
    };

    document.addEventListener("visibilitychange", onVisibility);
    const timer = window.setInterval(poll, METRICS_POLL_INTERVAL_MS);
    poll();

    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [enabled]);
}
