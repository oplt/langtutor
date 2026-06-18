import { httpRequest } from "../../../shared/api/httpClient";
import type { CefrLevel, LessonBook, LessonPage, LessonProgress } from "../types";

export async function fetchBooks(): Promise<LessonBook[]> {
  const data = await httpRequest<{ books: LessonBook[] }>("/api/book/levels");
  return data.books;
}

export async function fetchBook(level: CefrLevel): Promise<LessonBook> {
  return httpRequest<LessonBook>(`/api/book/${level}`);
}

export async function fetchLessonPage(level: CefrLevel, pageId: string): Promise<LessonPage> {
  return httpRequest<LessonPage>(`/api/book/${level}/pages/${encodeURIComponent(pageId)}`);
}

export async function fetchLessonProgress(level?: CefrLevel): Promise<LessonProgress[]> {
  const query = level ? `?level=${level}` : "";
  const data = await httpRequest<{ completed_pages: LessonProgress[] }>(
    `/api/book/progress${query}`,
  );
  return data.completed_pages;
}

export async function completeLessonPage(
  level: CefrLevel,
  pageId: string,
  quizScore?: number,
): Promise<LessonProgress> {
  return httpRequest<LessonProgress>(
    `/api/book/${level}/pages/${encodeURIComponent(pageId)}/complete`,
    { method: "POST", body: { quiz_score: quizScore ?? null } },
  );
}
