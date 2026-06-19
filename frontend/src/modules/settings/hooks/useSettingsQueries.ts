import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { heavyQueryOptions, queryStaleTimes } from "../../../shared/api/queryClient";
import { queryKeys } from "../../../shared/api/queryKeys";
import {
  fetchAppSettings,
  updateAppSettings,
  updateLlmRouting,
  type LlmTaskName,
  type SettingsDoc,
} from "../api/settingsApi";

export function useAppSettingsQuery() {
  return useQuery<SettingsDoc>({
    queryKey: queryKeys.settings.app,
    queryFn: fetchAppSettings,
    staleTime: queryStaleTimes.settings,
    ...heavyQueryOptions,
  });
}

export type SaveAiSettingsInput = {
  doc: SettingsDoc;
  routing: {
    default_profile_id: string;
    task_overrides: Partial<Record<LlmTaskName, string>>;
  };
};

export function useSaveAiSettingsMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ doc, routing }: SaveAiSettingsInput) => {
      const saved = await updateAppSettings(doc);
      await updateLlmRouting(routing);
      return saved;
    },
    onSuccess: (saved) => {
      queryClient.setQueryData(queryKeys.settings.app, saved);
    },
  });
}

export function useUpdateAppSettingsMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateAppSettings,
    onSuccess: (saved) => {
      queryClient.setQueryData(queryKeys.settings.app, saved);
    },
  });
}

export function useUpdateLlmRoutingMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateLlmRouting,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.settings.app });
    },
  });
}

export { updateLlmRouting };
