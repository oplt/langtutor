import type { UseQueryResult } from "@tanstack/react-query";

export function useAsyncPanel<T>(query: UseQueryResult<T, Error>) {
  return {
    data: query.data,
    loading: query.isLoading && query.data === undefined,
    error: query.error?.message ?? null,
    isFetching: query.isFetching,
    refresh: () => {
      void query.refetch();
    },
  };
}
