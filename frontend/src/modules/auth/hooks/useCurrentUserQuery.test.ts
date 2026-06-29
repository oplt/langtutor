import { describe, expect, it } from "vitest";

import { currentUserQueryOptions } from "./useCurrentUserQuery";
import { queryKeys } from "../../../shared/api/queryKeys";

describe("useCurrentUserQuery", () => {
  it("deduplicates /auth/me through one shared query key", () => {
    expect(currentUserQueryOptions.queryKey).toEqual(queryKeys.auth.me);
  });

  it("keeps current-user data fresh for at least 60 seconds", () => {
    expect(currentUserQueryOptions.staleTime).toBeGreaterThanOrEqual(60_000);
  });

  it("does not refetch on window focus", () => {
    expect(currentUserQueryOptions.refetchOnWindowFocus).toBe(false);
  });
});
