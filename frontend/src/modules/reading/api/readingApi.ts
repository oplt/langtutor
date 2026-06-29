export type InterestArea =
  | "news"
  | "sports"
  | "technology"
  | "science"
  | "business"
  | "arts"
  | "culture"
  | "travel"
  | "health"
  | "environment"
  | "history"
  | "daily_life";

export type SourceMode = "online" | "generated";
export type Strictness = "strict" | "balanced" | "natural";
export type AdaptationMode = "llm" | "rules" | "raw";

export type TranslationMode = "none" | "full" | "sentence_by_sentence";

export type ReadingGenerateRequest = {
  language: string;
  level: number;
  maxFrequencyRank: number;
  interestArea: InterestArea;
  wordCount: number;
  sourceMode: SourceMode;
  strictness: Strictness;
  translationMode?: TranslationMode;
};

export type ReadingCoverage = {
  totalWords: number;
  allowedWords: number;
  unknownWords: number;
  coveragePercent: number;
  unknownWordList: string[];
};

export type ReadingReplacement = {
  original: string;
  replacement: string;
  reason: string;
};

export type ReadingGlossaryEntry = {
  word: string;
  meaning: string;
  definition: string;
  exampleSentence: string;
  reasonKept: string;
};

export type ReadingQuizQuestion = {
  type: string;
  question: string;
  options: string[];
  answer: string;
};

export type ReadingSource = {
  title: string;
  url: string;
  publisher: string;
  publishedAt: string;
};

export type TranslationStatus = "ok" | "disabled" | "unavailable";

export type ReadingTranslation = {
  provider: string;
  language: string;
  status: TranslationStatus;
  text: string | null;
  detectedSourceLanguage?: string | null;
  modelTypeUsed?: string | null;
};

export type ReadingGenerateResponse = {
  adaptedText: string;
  translatedText?: string | null;
  translation?: ReadingTranslation | null;
  summary: string;
  source: ReadingSource;
  level: number;
  maxFrequencyRank: number;
  wordCountRequested: number;
  wordCountActual: number;
  coverage: ReadingCoverage;
  preCoverage?: ReadingCoverage | null;
  replacements: ReadingReplacement[];
  glossary: ReadingGlossaryEntry[];
  quiz: ReadingQuizQuestion[];
  sourceMode: SourceMode;
  strictness: Strictness;
  interestArea: InterestArea;
  adaptationMode: AdaptationMode;
  warnings: string[];
};

export type ReadingSaveResponse = {
  id: string;
  savedAt: string;
};

export async function generateReading(
  payload: ReadingGenerateRequest,
): Promise<ReadingGenerateResponse> {
  const { httpRequest } = await import("../../../shared/api/httpClient");
  return httpRequest<ReadingGenerateResponse>("/api/reading/generate", {
    method: "POST",
    body: payload,
    timeoutMs: 120_000,
  });
}

export async function saveReading(
  reading: ReadingGenerateResponse,
): Promise<ReadingSaveResponse> {
  const { httpRequest } = await import("../../../shared/api/httpClient");
  return httpRequest<ReadingSaveResponse>("/api/reading/save", {
    method: "POST",
    body: { reading },
  });
}
