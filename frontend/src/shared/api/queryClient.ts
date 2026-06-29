import { QueryClient } from "@tanstack/react-query";

export const queryStaleTimes = {
  default: 60_000,
  auth: 60_000,
  settings: 5 * 60_000,
  memoryHeavy: 5 * 60_000,
  learning: 60_000,
} as const;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: queryStaleTimes.default,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const heavyQueryOptions = {
  refetchOnWindowFocus: false,
} as const;
