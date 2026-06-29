import { useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchCurrentUser } from "../api/authApi";
import { queryKeys } from "../../../shared/api/queryKeys";
import { queryStaleTimes } from "../../../shared/api/queryClient";
import { ApiError } from "../../../shared/api/httpClient";

export const currentUserQueryOptions = {
  queryKey: queryKeys.auth.me,
  queryFn: fetchCurrentUser,
  staleTime: queryStaleTimes.auth,
  gcTime: 5 * 60_000,
  refetchOnWindowFocus: false,
  retry: (failureCount: number, error: unknown) => {
    if (error instanceof ApiError && error.status === 401) return false;
    return failureCount < 1;
  },
} as const;

export function useCurrentUserQuery(enabled: boolean) {
  return useQuery({
    ...currentUserQueryOptions,
    enabled,
  });
}

export function useInvalidateCurrentUser() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: queryKeys.auth.me });
}
