import { httpRequest } from "../../../shared/api/httpClient";
import type { CefrLevel } from "./learningPathApi";

export type LevelInfo = {
  level: CefrLevel;
  rank_min: number;
  rank_max: number;
  word_coverage: string;
  grammar_focus: string;
  input_type: string;
  word_count: number;
};

export type StoryOut = {
  id: string;
  level: CefrLevel;
  title: string;
  body: string;
  word_count: number;
  new_word_count: number;
  new_words: string[];
  review_words: string[];
  target_words: string[];
};

export type ProgressSummary = {
  total_words: number;
  mastered_words: number;
  next_review_at: string | null;
  levels: Array<{ level: CefrLevel; mastered: number; total: number }>;
};

export async function fetchLearningLevels(): Promise<LevelInfo[]> {
  const data = await httpRequest<{ levels: LevelInfo[] }>("/api/learning/levels");
  return data.levels ?? [];
}

export async function fetchProgressSummary(): Promise<ProgressSummary> {
  return httpRequest<ProgressSummary>("/api/learning/progress/summary");
}

export async function generateStory(
  level: CefrLevel,
  targetWordCount: number,
  maxWords = 180,
): Promise<StoryOut> {
  return httpRequest<StoryOut>("/api/learning/stories/generate", {
    method: "POST",
    body: {
      level,
      target_word_count: targetWordCount,
      max_words: maxWords,
    },
  });
}
