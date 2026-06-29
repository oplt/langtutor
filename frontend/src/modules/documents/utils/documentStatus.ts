export const DOCUMENT_STATUS_LABELS: Record<string, string> = {
  uploaded: "Ready to index",
  parsing: "Parsing",
  chunking: "Chunking",
  embedding: "Embedding",
  indexed: "Indexed",
  failed: "Failed",
  deleted: "Deleted",
};

export const INDEXING_STATUSES = new Set(["parsing", "chunking", "embedding"]);

export function documentStatusLabel(status: string): string {
  return DOCUMENT_STATUS_LABELS[status] ?? status;
}

export function documentStatusColor(
  status: string,
): "default" | "info" | "success" | "warning" | "error" {
  switch (status) {
    case "indexed":
      return "success";
    case "failed":
      return "error";
    case "uploaded":
      return "warning";
    case "parsing":
    case "chunking":
    case "embedding":
      return "info";
    default:
      return "default";
  }
}

export function buildDocumentQuizPrompt(documentName: string): string {
  return (
    `Quiz me on my uploaded study document "${documentName}". ` +
    "Search it with rag_search, then ask me 3 comprehension questions using ask_user. " +
    "Focus on the most important concepts from the document."
  );
}
