# User Document RAG Module

LangChain-backed retrieval over **user-uploaded documents**, separate from the global Dutch corpus in `backend/app/modules/knowledge/` (BM25 `rag` tool).

## Enable

```env
RAG_ENABLED=true
RAG_VECTOR_BACKEND=pgvector
RAG_EMBEDDING_PROVIDER=openai   # or ollama
RAG_EMBEDDING_MODEL=text-embedding-3-small
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=150
RAG_TOP_K=5
RAG_SCORE_THRESHOLD=0.3
RAG_ALLOWED_FILE_TYPES=pdf,txt,md,docx,csv
```

Install optional deps:

```bash
pip install -r backend/requirements-rag.txt
```

Run migration:

```bash
cd backend && .venv/bin/alembic upgrade head
```

## Upload & index

```bash
# Upload
curl -H "Authorization: Bearer $TOKEN" \
  -F "file=@notes.md" \
  http://localhost:8000/api/rag/documents/upload

# Index (parse → chunk → embed) — returns 202 immediately; poll job status
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/rag/documents/{document_id}/index

# Job status (includes document `progress_stage`: parsing, chunking, embedding, indexed, failed)
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/rag/jobs/{job_id}

# Live progress WebSocket (polls until job completes)
# wscat -c "ws://localhost:8000/api/rag/jobs/{job_id}/ws?token=$TOKEN"
```

## Query

```bash
# Retrieve chunks only
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"What grammar rule is explained?"}' \
  http://localhost:8000/api/rag/retrieve

# Full RAG answer with citations
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"Summarize my uploaded lesson notes"}' \
  http://localhost:8000/api/rag/ask
```

## AI agent integration

When `RAG_ENABLED=true`, the tutor agent exposes tool **`rag_search`** (uploaded documents). The existing **`rag`** tool still searches the global Dutch knowledge base.

Context order in RAG answers:

1. System/developer prompt  
2. Authenticated user permissions  
3. User memory (L3)  
4. Retrieved document chunks  
5. User question  

## Access control

- Documents are owned by `user_id`.
- Optional `project_id` scopes retrieval (e.g. `classroom:<grant_uuid>` for teacher-shared classroom docs).
- Users cannot retrieve another user's private documents.
- Project access requires classroom grant membership.

## Vector backend

Default: `pgvector` adapter storing embeddings in `rag_chunks.embedding` (`vector` column). Similarity search uses database-native cosine distance (`<=>`) with an HNSW index (`ix_rag_chunks_embedding_cosine_hnsw`). Run `alembic upgrade head` after deploy to apply the migration.

Only `pgvector` is supported; other backends are rejected at startup.

## Architecture

```
backend/app/modules/rag/
  domain/           # Pure models & enums
  application/      # Services (no LangChain imports)
  infrastructure/   # LangChain loaders/splitters/embeddings, DB, storage
  api/              # FastAPI routes
```

LangChain is confined to `infrastructure/langchain_*.py`.

## Tests

```bash
cd /path/to/LanguageApp
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 backend/.venv/bin/python -m pytest backend/tests/test_rag_module.py -q
```
