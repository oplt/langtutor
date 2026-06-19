import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { heavyQueryOptions, queryStaleTimes } from "../../../shared/api/queryClient";
import { queryKeys } from "../../../shared/api/queryKeys";
import {
  appendPreference,
  fetchMemoryL3,
  fetchMemoryOverview,
  synthesizeMemory,
  type MemoryOverview,
} from "../api/memoryApi";

export function useMemoryOverviewQuery() {
  return useQuery<MemoryOverview>({
    queryKey: queryKeys.memory.overview,
    queryFn: fetchMemoryOverview,
    staleTime: queryStaleTimes.memoryHeavy,
    ...heavyQueryOptions,
  });
}

export function useMemoryL3Query() {
  return useQuery<{ content: string }>({
    queryKey: queryKeys.memory.l3,
    queryFn: fetchMemoryL3,
    staleTime: queryStaleTimes.memoryHeavy,
    ...heavyQueryOptions,
  });
}

export function useAppendPreferenceMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => appendPreference(text),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.memory.overview });
      void queryClient.invalidateQueries({ queryKey: queryKeys.memory.l3 });
    },
  });
}

export function useSynthesizeMemoryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: synthesizeMemory,
    onSuccess: () => {
      window.setTimeout(() => {
        void queryClient.invalidateQueries({ queryKey: queryKeys.memory.overview });
        void queryClient.invalidateQueries({ queryKey: queryKeys.memory.l3 });
      }, 1500);
    },
  });
}
