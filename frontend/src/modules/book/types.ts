export type CefrLevel = "A1" | "A2" | "B1" | "B2" | "C1" | "C2";

export type BlockType =
  | "text"
  | "vocabulary"
  | "quiz"
  | "dialogue"
  | "pronunciation"
  | "listening";

export type LessonBlock = {
  id: string;
  type: BlockType;
  status: string;
  title: string;
  params: Record<string, unknown>;
  payload: Record<string, unknown>;
};

export type LessonPageOutline = {
  id: string;
  title: string;
  order: number;
  grammar_topic: string;
};

export type LessonChapter = {
  id: string;
  title: string;
  order: number;
  pages: LessonPageOutline[];
};

export type LessonBook = {
  id: string;
  level: CefrLevel;
  title: string;
  description: string;
  chapters: LessonChapter[];
};

export type LessonPage = {
  id: string;
  book_id: string;
  level: CefrLevel;
  chapter_id: string;
  title: string;
  grammar_topic: string;
  learning_objectives: string[];
  blocks: LessonBlock[];
};

export type LessonProgress = {
  page_id: string;
  level: CefrLevel;
  quiz_score: number | null;
  completed_at: string;
};
