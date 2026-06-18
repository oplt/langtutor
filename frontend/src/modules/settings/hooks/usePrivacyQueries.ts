import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "../../../shared/api/queryKeys";
import {
  deletePrivacyAccount,
  deletePrivacyHistory,
  exportPrivacyAccountData,
  fetchPrivacyAuditLog,
  fetchPrivacyPreferences,
  runPrivacyRetentionCleanup,
  updatePrivacyPreferences,
  type PrivacyPrefs,
} from "../api/privacyApi";

const AUDIT_LOG_LIMIT = 25;

export function usePrivacyPreferencesQuery() {
  return useQuery<PrivacyPrefs>({
    queryKey: queryKeys.privacy.preferences,
    queryFn: fetchPrivacyPreferences,
  });
}

export function usePrivacyAuditLogQuery() {
  return useQuery({
    queryKey: queryKeys.privacy.auditLog(AUDIT_LOG_LIMIT),
    queryFn: () => fetchPrivacyAuditLog(AUDIT_LOG_LIMIT),
  });
}

export function useUpdatePrivacyPreferencesMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updatePrivacyPreferences,
    onSuccess: (saved) => {
      queryClient.setQueryData(queryKeys.privacy.preferences, saved);
      void queryClient.invalidateQueries({
        queryKey: queryKeys.privacy.auditLog(AUDIT_LOG_LIMIT),
      });
    },
  });
}

export function usePrivacyActionMutations() {
  const queryClient = useQueryClient();
  const invalidateAudit = () => {
    void queryClient.invalidateQueries({
      queryKey: queryKeys.privacy.auditLog(AUDIT_LOG_LIMIT),
    });
  };

  const retentionCleanup = useMutation({
    mutationFn: runPrivacyRetentionCleanup,
    onSuccess: invalidateAudit,
  });

  const exportAccount = useMutation({
    mutationFn: () => exportPrivacyAccountData(),
    onSuccess: invalidateAudit,
  });

  const deleteHistory = useMutation({
    mutationFn: deletePrivacyHistory,
    onSuccess: invalidateAudit,
  });

  const deleteAccount = useMutation({
    mutationFn: deletePrivacyAccount,
    onSuccess: invalidateAudit,
  });

  return { retentionCleanup, exportAccount, deleteHistory, deleteAccount };
}

export { AUDIT_LOG_LIMIT };
export type { PrivacyPrefs };
