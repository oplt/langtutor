import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import CloudUploadRoundedIcon from "@mui/icons-material/CloudUploadRounded";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import QuizRoundedIcon from "@mui/icons-material/QuizRounded";
import SyncRoundedIcon from "@mui/icons-material/SyncRounded";

import { FeaturePanel } from "../../../shared/components/FeaturePanel";
import { useAsyncPanel } from "../../../shared/hooks/useAsyncPanel";
import {
  useDeleteRagDocumentMutation,
  useIndexRagDocumentMutation,
  useRagDocumentsQuery,
  useRagStatusQuery,
  useUploadRagDocumentMutation,
} from "../hooks/useDocumentsQueries";
import type { RagDocument } from "../api/ragApi";
import {
  buildDocumentQuizPrompt,
  documentStatusColor,
  documentStatusLabel,
} from "../utils/documentStatus";

function formatTimestamp(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString();
}

export function DocumentsPanel() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const statusQuery = useRagStatusQuery();
  const ragEnabled = statusQuery.data?.enabled ?? false;
  const documentsQuery = useRagDocumentsQuery(ragEnabled);
  const panel = useAsyncPanel(documentsQuery);
  const uploadMutation = useUploadRagDocumentMutation();
  const indexMutation = useIndexRagDocumentMutation();
  const deleteMutation = useDeleteRagDocumentMutation();

  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [indexingId, setIndexingId] = useState<string | null>(null);

  const documents = documentsQuery.data ?? [];
  const initialLoading = statusQuery.isLoading || (ragEnabled && panel.loading);
  const loadError =
    statusQuery.error instanceof Error
      ? statusQuery.error.message
      : ragEnabled && panel.error
        ? panel.error
        : null;

  const refresh = () => {
    void statusQuery.refetch();
    if (ragEnabled) {
      void documentsQuery.refetch();
    }
  };

  const handleUpload = async (files: FileList | null) => {
    const file = files?.[0];
    if (!file) return;
    setMessage(null);
    setActionError(null);
    try {
      const doc = await uploadMutation.mutateAsync(file);
      setMessage(`Uploaded "${doc.original_filename}". Index it to make it searchable.`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleIndex = async (documentId: string) => {
    setMessage(null);
    setActionError(null);
    setIndexingId(documentId);
    try {
      await indexMutation.mutateAsync(documentId);
      setMessage("Indexing started. Status updates automatically.");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Indexing failed.");
    } finally {
      setIndexingId(null);
    }
  };

  const handleDelete = async (document: RagDocument) => {
    setMessage(null);
    setActionError(null);
    try {
      await deleteMutation.mutateAsync(document.id);
      setMessage(`Removed "${document.original_filename}".`);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Could not delete document.");
    }
  };

  const handleQuiz = (document: RagDocument) => {
    const prompt = buildDocumentQuizPrompt(document.original_filename);
    navigate(`/dashboard/coach?prompt=${encodeURIComponent(prompt)}`);
  };

  const busy =
    uploadMutation.isPending ||
    indexMutation.isPending ||
    deleteMutation.isPending ||
    panel.isFetching ||
    statusQuery.isFetching;

  if (initialLoading) {
    return (
      <FeaturePanel
        title="Study documents"
        description="Upload lesson notes and PDFs for the AI tutor to search and quiz you on."
        loading
      >
        {null}
      </FeaturePanel>
    );
  }

  if (!ragEnabled) {
    return (
      <FeaturePanel
        title="Study documents"
        description="Upload lesson notes and PDFs for the AI tutor to search and quiz you on."
      >
        <Alert severity="info">
          Document uploads are disabled on the server. Ask your administrator to set{" "}
          <Typography component="span" variant="body2" sx={{ fontFamily: "monospace" }}>
            RAG_ENABLED=true
          </Typography>{" "}
          and run database migrations. See{" "}
          <Typography component="span" variant="body2">
            backend/app/modules/rag/README.md
          </Typography>
          .
        </Alert>
      </FeaturePanel>
    );
  }

  return (
    <FeaturePanel
      title="Study documents"
      description="Upload PDF, Markdown, text, Word, or CSV files. Index them so the tutor can search your materials and quiz you."
      error={loadError}
      actionError={actionError}
      onRetry={refresh}
    >
      <Stack spacing={2}>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <Chip size="small" label={`${documents.length} document${documents.length === 1 ? "" : "s"}`} />
          <Button
            size="small"
            variant="contained"
            startIcon={<CloudUploadRoundedIcon />}
            disabled={uploadMutation.isPending}
            onClick={() => fileInputRef.current?.click()}
          >
            Upload
          </Button>
          <Button size="small" onClick={refresh} disabled={busy} startIcon={<SyncRoundedIcon />}>
            Refresh
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            hidden
            accept=".pdf,.txt,.md,.docx,.csv,text/plain,text/markdown,application/pdf"
            onChange={(event) => void handleUpload(event.target.files)}
          />
        </Stack>

        {message && <Alert severity="success">{message}</Alert>}

        {!panel.loading && documents.length === 0 && (
          <Alert severity="info">
            No documents yet. Upload study notes or a lesson PDF, then index it before asking the tutor
            to quiz you.
          </Alert>
        )}

        <Stack spacing={1.5}>
          {documents.map((document) => (
            <DocumentRow
              key={document.id}
              document={document}
              indexing={indexingId === document.id}
              deleting={deleteMutation.isPending && deleteMutation.variables === document.id}
              onIndex={() => void handleIndex(document.id)}
              onDelete={() => void handleDelete(document)}
              onQuiz={() => handleQuiz(document)}
            />
          ))}
        </Stack>
      </Stack>
    </FeaturePanel>
  );
}

type DocumentRowProps = {
  document: RagDocument;
  indexing: boolean;
  deleting: boolean;
  onIndex: () => void;
  onDelete: () => void;
  onQuiz: () => void;
};

function DocumentRow({
  document,
  indexing,
  deleting,
  onIndex,
  onDelete,
  onQuiz,
}: DocumentRowProps) {
  const status = document.status;
  const isIndexed = status === "indexed";
  const isFailed = status === "failed";
  const needsIndex = status === "uploaded";
  const isProcessing = status === "parsing" || status === "chunking" || status === "embedding";

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1.5}
        alignItems={{ xs: "stretch", sm: "center" }}
        justifyContent="space-between"
      >
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography variant="subtitle2" noWrap title={document.original_filename}>
            {document.original_filename}
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
            <Chip
              size="small"
              color={documentStatusColor(status)}
              label={documentStatusLabel(status)}
              icon={isProcessing ? <CircularProgress size={12} color="inherit" /> : undefined}
            />
            <Typography variant="caption" color="text.secondary">
              {document.content_type}
            </Typography>
            {document.updated_at && (
              <Typography variant="caption" color="text.secondary">
                Updated {formatTimestamp(document.updated_at)}
              </Typography>
            )}
          </Stack>
        </Box>

        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap justifyContent={{ xs: "flex-start", sm: "flex-end" }}>
          {needsIndex && (
            <Button
              size="small"
              variant="outlined"
              disabled={indexing || deleting}
              onClick={onIndex}
            >
              Index
            </Button>
          )}
          {(isFailed || isIndexed) && (
            <Button
              size="small"
              variant="outlined"
              disabled={indexing || deleting}
              onClick={onIndex}
            >
              Re-index
            </Button>
          )}
          {isIndexed && (
            <Button
              size="small"
              variant="contained"
              startIcon={<QuizRoundedIcon />}
              disabled={deleting}
              onClick={onQuiz}
            >
              Quiz me on this
            </Button>
          )}
          <IconButton
            size="small"
            aria-label={`Delete ${document.original_filename}`}
            disabled={indexing || deleting}
            onClick={onDelete}
          >
            <DeleteOutlineIcon fontSize="small" />
          </IconButton>
        </Stack>
      </Stack>
    </Paper>
  );
}
