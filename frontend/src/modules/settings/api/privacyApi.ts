import { httpRequest } from "../../../shared/api/httpClient";

export type PrivacyPrefs = {
  allowAnalytics: boolean;
  retainHistory: boolean;
  coachPersonalization: boolean;
  retentionDays: number;
  goalPreset: "balanced" | "vocabulary" | "grammar" | "conversation";
};

export type PrivacyAuditItem = {
  id: string;
  action: string;
  createdAt: string | null;
  details: Record<string, unknown>;
};

export async function fetchPrivacyPreferences(): Promise<PrivacyPrefs> {
  return httpRequest<PrivacyPrefs>("/api/privacy/preferences");
}

export async function updatePrivacyPreferences(prefs: PrivacyPrefs): Promise<PrivacyPrefs> {
  return httpRequest<PrivacyPrefs>("/api/privacy/preferences", {
    method: "PUT",
    body: prefs,
  });
}

export async function fetchPrivacyAuditLog(limit = 25): Promise<PrivacyAuditItem[]> {
  const data = await httpRequest<{ items: PrivacyAuditItem[] }>(
    `/api/privacy/audit-log?limit=${limit}`,
  );
  return Array.isArray(data.items) ? data.items : [];
}

export async function runPrivacyRetentionCleanup(): Promise<{ ok: boolean; removed: number }> {
  return httpRequest("/api/privacy/run-retention", { method: "POST" });
}

export async function exportPrivacyAccountData(): Promise<unknown> {
  return httpRequest("/api/privacy/export");
}

export async function deletePrivacyHistory(): Promise<{ ok: boolean; removed: number }> {
  return httpRequest("/api/privacy/delete-history", { method: "POST" });
}

export async function deletePrivacyAccount(): Promise<{ ok: boolean }> {
  return httpRequest("/api/privacy/account", { method: "DELETE" });
}
