import { API_BASE } from "../../../config";
import { getAuthHeader } from "../../../auth";
import { ApiError } from "../../../shared/api/httpClient";
import { httpRequest } from "../../../shared/api/httpClient";

export type RagDocument = {
  id: string;
  user_id: string;
  organization_id: string | null;
  project_id: string | null;
  filename: string;
  original_filename: string;
  content_type: string;
  status: string;
  source_type: string;
  metadata: Record<string, unknown>;
  created_at: string | null;
  updated_at: string | null;
};

export type RagJob = {
  id: string;
  document_id: string;
  status: string;
  progress_stage: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
};

export type RagStatus = {
  enabled: boolean;
  vector_backend: string;
};

export async function fetchRagStatus(): Promise<RagStatus> {
  return httpRequest<RagStatus>("/api/rag/status");
}

export async function fetchRagDocuments(): Promise<RagDocument[]> {
  return httpRequest<RagDocument[]>("/api/rag/documents");
}

export async function uploadRagDocument(file: File): Promise<RagDocument> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/api/rag/documents/upload`, {
    method: "POST",
    headers: getAuthHeader(),
    body: formData,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message =
      (data as { error?: { message?: string }; detail?: string })?.error?.message ??
      (typeof data?.detail === "string" ? data.detail : undefined) ??
      `Upload failed (${response.status})`;
    throw new ApiError(message, response.status);
  }
  return data as RagDocument;
}

export async function indexRagDocument(documentId: string): Promise<RagJob> {
  return httpRequest<RagJob>(`/api/rag/documents/${encodeURIComponent(documentId)}/index`, {
    method: "POST",
  });
}

export async function deleteRagDocument(documentId: string): Promise<void> {
  await httpRequest(`/api/rag/documents/${encodeURIComponent(documentId)}`, {
    method: "DELETE",
  });
}

export async function fetchRagJob(jobId: string): Promise<RagJob> {
  return httpRequest<RagJob>(`/api/rag/jobs/${encodeURIComponent(jobId)}`);
}
