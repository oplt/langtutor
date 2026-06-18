import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "../../../shared/api/queryKeys";
import {
  deleteNotebookEntry,
  fetchNotebookEntries,
  saveNotebookEntry,
  type NotebookEntriesResponse,
} from "../api/notebookApi";

export function useNotebookEntriesQuery() {
  return useQuery<NotebookEntriesResponse>({
    queryKey: queryKeys.notebook.entries,
    queryFn: fetchNotebookEntries,
  });
}

export function useSaveNotebookEntryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: saveNotebookEntry,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.notebook.entries });
      void queryClient.invalidateQueries({ queryKey: queryKeys.learning.progressSummary });
    },
  });
}

export function useDeleteNotebookEntryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteNotebookEntry,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.notebook.entries });
    },
  });
}
