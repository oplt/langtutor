import { httpRequest } from "../../../shared/api/httpClient";
import type { CefrLevel } from "./learningPathApi";

export type ExerciseType =
  | "recognition"
  | "recall"
  | "production"
  | "fill_blank"
  | "translation";

export type QuizQuestion = {
  id: string;
  word_id?: string | null;
  lemma: string;
  exercise_type: ExerciseType;
  question_type: string;
  prompt: string;
  options: string[];
  correct_answer: string;
  explanation: string;
  use_ai_judge: boolean;
};

export type QuizSession = {
  session_id: string;
  level: string;
  source: string;
  questions: QuizQuestion[];
};

export type QuizSubmitResult = {
  correct: boolean;
  verdict: "correct" | "partial" | "incorrect";
  feedback: string;
  word_progress_updated: boolean;
};

export async function generateQuiz(
  level: CefrLevel,
  count = 5,
  useLlm = true,
): Promise<QuizSession> {
  return httpRequest<QuizSession>("/api/learning/quiz/generate", {
    method: "POST",
    body: {
      level,
      count,
      use_llm: useLlm,
      exercise_types: ["recognition", "recall", "fill_blank", "production"],
    },
  });
}

export async function submitQuizAnswer(
  question: QuizQuestion,
  userAnswer: string,
): Promise<QuizSubmitResult> {
  return httpRequest<QuizSubmitResult>("/api/learning/quiz/submit", {
    method: "POST",
    body: { question, user_answer: userAnswer },
  });
}

export async function judgeQuizAnswer(payload: {
  prompt: string;
  question_type: string;
  correct_answer: string;
  explanation?: string;
  user_answer: string;
  options?: string[];
}): Promise<QuizSubmitResult> {
  return httpRequest<QuizSubmitResult>("/api/learning/quiz/judge", {
    method: "POST",
    body: payload,
  });
}
