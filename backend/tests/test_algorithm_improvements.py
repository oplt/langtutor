from backend.app.modules.knowledge.cefr_filters import chunk_matches_cefr
from backend.app.modules.rag.application.rerank_service import rerank_chunks
from backend.app.modules.rag.domain.models import RetrievedChunk


def test_rerank_prefers_lexical_overlap() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="1",
            document_id="d1",
            content="De fiets staat in de garage.",
            score=0.55,
            metadata={},
            filename="notes.txt",
            chunk_index=0,
        ),
        RetrievedChunk(
            chunk_id="2",
            document_id="d1",
            content="Amsterdam weather forecast for next week.",
            score=0.60,
            metadata={},
            filename="notes.txt",
            chunk_index=1,
        ),
    ]
    ranked = rerank_chunks("fiets garage", chunks, top_k=1)
    assert ranked[0].chunk_id == "1"


def test_cefr_filter_rejects_out_of_level_words() -> None:
    assert chunk_matches_cefr({"rank": 150}, cefr_level="A1") is True
    assert chunk_matches_cefr({"rank": 1500}, cefr_level="A1") is False
