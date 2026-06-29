import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "../../../shared/api/queryKeys";
import {
  deleteRagDocument,
  fetchRagDocuments,
  fetchRagStatus,
  indexRagDocument,
  uploadRagDocument,
  type RagDocument,
  type RagStatus,
} from "../api/ragApi";
import { INDEXING_STATUSES } from "../utils/documentStatus";

export function useRagStatusQuery() {
  return useQuery<RagStatus>({
    queryKey: queryKeys.rag.status,
    queryFn: fetchRagStatus,
  });
}

export function useRagDocumentsQuery(enabled: boolean) {
  return useQuery<RagDocument[]>({
    queryKey: queryKeys.rag.documents,
    queryFn: fetchRagDocuments,
    enabled,
    refetchInterval: (query) => {
      const docs = query.state.data;
      if (!docs?.some((doc) => INDEXING_STATUSES.has(doc.status))) {
        return false;
      }
      return 3000;
    },
  });
}

export function useUploadRagDocumentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: uploadRagDocument,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.rag.documents });
    },
  });
}

export function useIndexRagDocumentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: indexRagDocument,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.rag.documents });
    },
  });
}

export function useDeleteRagDocumentMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteRagDocument,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.rag.documents });
    },
  });
}
