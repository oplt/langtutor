from __future__ import annotations

from backend.app.modules.rag.domain.models import Citation, RetrievedChunk


def _snippet_at_boundary(text: str, max_len: int = 240) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_len:
        return cleaned
    cut = cleaned[: max_len - 3]
    last_space = cut.rfind(" ")
    if last_space > max_len // 2:
        cut = cut[:last_space]
    return cut.rstrip() + "..."


class CitationService:
    def build_citations(self, chunks: list[RetrievedChunk]) -> list[Citation]:
        citations: list[Citation] = []
        for chunk in chunks:
            snippet = _snippet_at_boundary(chunk.content)
            citations.append(
                Citation(
                    document_id=chunk.document_id,
                    chunk_id=chunk.chunk_id,
                    filename=chunk.filename,
                    page_number=chunk.page_number,
                    score=chunk.score,
                    snippet=snippet,
                    chunk_index=chunk.chunk_index,
                )
            )
        return citations
