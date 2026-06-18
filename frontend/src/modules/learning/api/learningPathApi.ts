import { httpRequest } from "../../../shared/api/httpClient";

export type CefrLevel = "A1" | "A2" | "B1" | "B2" | "C1" | "C2";

export const CEFR_LEVELS: CefrLevel[] = ["A1", "A2", "B1", "B2", "C1", "C2"];

export type PathNext = {
  action: string;
  module_name?: string;
  knowledge_point_name?: string;
  knowledge_point_type?: string;
  stage?: string;
  reason?: string;
  pending_prompt?: string;
};

export type PathMap = {
  level: CefrLevel;
  next: PathNext;
  map: {
    counts: { mastered: number; learning: number; new: number; total: number };
    complete: boolean;
    modules: Array<{
      id: string;
      name: string;
      stage: string;
      mastered: number;
      total: number;
    }>;
  };
};

export type PathDrill = {
  step: PathNext;
  drill: {
    question_id: string;
    knowledge_point_id: string;
    prompt: string;
    question_type: string;
    options: string[];
  } | null;
};

export async function fetchPathMap(level: CefrLevel): Promise<PathMap> {
  return httpRequest<PathMap>(`/api/learning/path/${level}/map`);
}

export async function fetchPathDrill(level: CefrLevel): Promise<PathDrill> {
  return httpRequest<PathDrill>(`/api/learning/path/${level}/drill`);
}

export type PathGradeResult = {
  correct: boolean;
  map: PathMap;
  drill: PathDrill;
};

export async function gradePathAnswer(level: CefrLevel, answer: string): Promise<PathGradeResult> {
  return httpRequest<PathGradeResult>(
    `/api/learning/path/${level}/grade`,
    { method: "POST", body: { answer } },
  );
}
