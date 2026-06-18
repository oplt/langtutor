import { httpRequest } from "../../../shared/api/httpClient";

export type MemoryOverview = {
  trace_count: number;
  l2: Array<{ surface: string; entry_count: number; updated_at: string | null }>;
  l3: Array<{ slot: string; entry_count: number; preview: string; updated_at: string | null }>;
};

export async function fetchMemoryOverview(): Promise<MemoryOverview> {
  return httpRequest<MemoryOverview>("/api/memory/overview");
}

export async function fetchMemoryL3(): Promise<{ content: string }> {
  return httpRequest<{ content: string }>("/api/memory/l3");
}

export async function appendPreference(text: string) {
  return httpRequest("/api/memory/preferences", {
    method: "POST",
    body: { text, op: "add" },
  });
}

export async function synthesizeMemory() {
  return httpRequest("/api/memory/synthesize", { method: "POST" });
}
