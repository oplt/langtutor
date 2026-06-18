import { httpRequest } from "../../../shared/api/httpClient";

export type NotebookEntry = {
  id: string;
  lemma: string;
  note: string;
  context: string;
  source: string;
  word_id: string | null;
  rank: number | null;
  level: string | null;
  translation: string | null;
  recognition_strength: number | null;
  recall_strength: number | null;
  next_review_at: string | null;
  created_at: string;
  updated_at: string;
};

export type NotebookEntriesResponse = {
  entries: NotebookEntry[];
  due_count: number;
};

export async function fetchNotebookEntries(): Promise<NotebookEntriesResponse> {
  return httpRequest<NotebookEntriesResponse>("/api/notebook/entries");
}

export async function saveNotebookEntry(payload: {
  lemma: string;
  note?: string;
  context?: string;
  source?: string;
}): Promise<NotebookEntry> {
  return httpRequest<NotebookEntry>("/api/notebook/entries", {
    method: "POST",
    body: payload,
  });
}

export async function deleteNotebookEntry(entryId: string): Promise<void> {
  await httpRequest(`/api/notebook/entries/${encodeURIComponent(entryId)}`, {
    method: "DELETE",
  });
}
