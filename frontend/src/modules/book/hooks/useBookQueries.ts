import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "../../../shared/api/queryKeys";
import {
  completeLessonPage,
  fetchBook,
  fetchLessonPage,
  fetchLessonProgress,
} from "../api/bookApi";
import type { CefrLevel, LessonBook, LessonPage, LessonProgress } from "../types";

export function useBookQuery(level: CefrLevel) {
  return useQuery<LessonBook>({
    queryKey: queryKeys.book.detail(level),
    queryFn: () => fetchBook(level),
  });
}

export function useLessonProgressQuery(level: CefrLevel) {
  return useQuery<LessonProgress[]>({
    queryKey: queryKeys.book.progress(level),
    queryFn: () => fetchLessonProgress(level),
  });
}

export function useLessonPageQuery(level: CefrLevel, pageId: string, enabled = true) {
  return useQuery<LessonPage>({
    queryKey: queryKeys.book.page(level, pageId),
    queryFn: () => fetchLessonPage(level, pageId),
    enabled: enabled && Boolean(pageId),
  });
}

export function useCompleteLessonPageMutation(level: CefrLevel) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ pageId, quizScore }: { pageId: string; quizScore?: number }) =>
      completeLessonPage(level, pageId, quizScore),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.book.progress(level) });
    },
  });
}
