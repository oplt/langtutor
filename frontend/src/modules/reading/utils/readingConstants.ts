import type { InterestArea, SourceMode, Strictness } from "../api/readingApi";

export type FrequencyLevel = {
  level: number;
  label: string;
  cefrLabel: string;
  maxWords: number;
  wordCoverage: string;
  defaultWordCount: number;
};

export const FREQUENCY_LEVELS: FrequencyLevel[] = [
  { level: 1, label: "Beginner", cefrLabel: "Beginner", maxWords: 500, wordCoverage: "the most common 500 words", defaultWordCount: 300 },
  { level: 2, label: "Elementary", cefrLabel: "Elementary", maxWords: 1000, wordCoverage: "the most common 1000 words", defaultWordCount: 300 },
  { level: 3, label: "Pre-intermediate", cefrLabel: "Pre-intermediate", maxWords: 2000, wordCoverage: "the most common 2000 words", defaultWordCount: 500 },
  { level: 4, label: "Intermediate", cefrLabel: "Intermediate", maxWords: 3000, wordCoverage: "the most common 3000 words", defaultWordCount: 500 },
  { level: 5, label: "Upper-intermediate", cefrLabel: "Upper-intermediate", maxWords: 4000, wordCoverage: "the most common 4000 words", defaultWordCount: 1000 },
  { level: 6, label: "Advanced", cefrLabel: "Advanced", maxWords: 5000, wordCoverage: "the most common 5000 words", defaultWordCount: 1000 },
];

export const INTEREST_AREAS: { id: InterestArea; label: string }[] = [
  { id: "news", label: "News" },
  { id: "sports", label: "Sports" },
  { id: "technology", label: "Technology" },
  { id: "science", label: "Science" },
  { id: "business", label: "Business" },
  { id: "arts", label: "Arts" },
  { id: "culture", label: "Culture" },
  { id: "travel", label: "Travel" },
  { id: "health", label: "Health" },
  { id: "environment", label: "Environment" },
  { id: "history", label: "History" },
  { id: "daily_life", label: "Daily life" },
];

export const WORD_COUNT_OPTIONS = [300, 500, 1000] as const;

export const STRICTNESS_OPTIONS: {
  id: Strictness;
  label: string;
  description: string;
}[] = [
  {
    id: "strict",
    label: "Strict",
    description: "Strict mode makes the text easier but sometimes less natural.",
  },
  {
    id: "balanced",
    label: "Balanced",
    description: "Balanced mode keeps important topic words and explains them.",
  },
  {
    id: "natural",
    label: "Natural",
    description: "Natural mode keeps more authentic phrasing but explains difficult words.",
  },
];

export const SOURCE_MODE_OPTIONS: { id: SourceMode; label: string; description: string }[] = [
  {
    id: "online",
    label: "Online sources",
    description: "Use RSS summaries and short excerpts from public sources.",
  },
  {
    id: "generated",
    label: "Topic-based",
    description: "Generate an educational text from the selected topic without fetching news.",
  },
];

export function levelForFrequency(level: number): FrequencyLevel {
  return FREQUENCY_LEVELS.find((item) => item.level === level) ?? FREQUENCY_LEVELS[2];
}

export function difficultyBadge(coveragePercent: number): { label: string; color: "success" | "warning" | "error" } {
  if (coveragePercent >= 90) return { label: "Comfortable", color: "success" };
  if (coveragePercent >= 75) return { label: "Challenging", color: "warning" };
  return { label: "Stretch", color: "error" };
}
