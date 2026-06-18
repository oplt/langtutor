import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "../../../shared/api/queryKeys";
import {
  fetchLearningLevels,
  fetchProgressSummary,
  generateStory,
  type LevelInfo,
  type ProgressSummary,
  type StoryOut,
} from "../api/learningApi";
import {
  fetchPathDrill,
  fetchPathMap,
  gradePathAnswer,
  type CefrLevel,
  type PathDrill,
  type PathGradeResult,
  type PathMap,
} from "../api/learningPathApi";

export function useLearningLevelsQuery() {
  return useQuery<LevelInfo[]>({
    queryKey: queryKeys.learning.levels,
    queryFn: fetchLearningLevels,
  });
}

export function useProgressSummaryQuery() {
  return useQuery<ProgressSummary>({
    queryKey: queryKeys.learning.progressSummary,
    queryFn: fetchProgressSummary,
  });
}

export function usePathMapQuery(level: CefrLevel) {
  return useQuery<PathMap>({
    queryKey: queryKeys.learning.pathMap(level),
    queryFn: () => fetchPathMap(level),
  });
}

export function usePathDrillQuery(level: CefrLevel) {
  return useQuery<PathDrill>({
    queryKey: queryKeys.learning.pathDrill(level),
    queryFn: () => fetchPathDrill(level),
  });
}

export function useGradePathAnswerMutation(level: CefrLevel) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (answer: string) => gradePathAnswer(level, answer),
    onSuccess: (result: PathGradeResult) => {
      queryClient.setQueryData(queryKeys.learning.pathMap(level), result.map);
      queryClient.setQueryData(queryKeys.learning.pathDrill(level), result.drill);
      void queryClient.invalidateQueries({ queryKey: queryKeys.learning.progressSummary });
    },
  });
}

export function useGenerateStoryMutation() {
  return useMutation({
    mutationFn: ({
      level,
      targetWordCount,
    }: {
      level: CefrLevel;
      targetWordCount: number;
    }) => generateStory(level, targetWordCount),
  });
}

export type { StoryOut };
