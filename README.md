# LanguageApp

Dutch language learning platform with an AI tutor, spaced-repetition practice, and a searchable knowledge base.

## Architecture

```
backend/app/
  modules/
    agent/      # Tutor capabilities, tools, LLM loop
    tutor/      # HTTP + WebSocket turn execution
    knowledge/  # Dutch corpus (BM25 + optional PostgreSQL FTS)
    rag/        # User-uploaded document RAG (pgvector)
    memory/     # L2/L3 learner memory + background synthesis
    learning/   # Quizzes, mastery path, progress
frontend/src/
  modules/      # Feature APIs + React Query hooks
  shared/       # httpClient, PageLoading, FeaturePanel
```

## Local development

```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn backend.app.main:app --reload

# Frontend
cd frontend && npm ci && npm run dev
```

Or from the repo root: `make start`

Docker (Postgres + Redis + backend):

```bash
docker compose up --build
```

See [`docs/observability/README.md`](docs/observability/README.md) for Grafana dashboard import.

## Quality checks

```bash
make check   # backend lint + tests + frontend build/lint/tests
```

## Key environment variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | PostgreSQL (asyncpg) |
| `JWT_SECRET` | Auth signing (≥32 chars) |
| `REDIS_URL` | Rate limits, OAuth state, tutor turn state, caches |
| `RAG_ENABLED` | User document RAG (`false` by default) |
| `KNOWLEDGE_USE_FTS` | PostgreSQL FTS for Dutch corpus (`false` = BM25 cache) |
| `MEMORY_L3_LLM_PROFILE` | Optional LLM synthesis for L3 profile slot |
| `RAG_EMBEDDING_API_KEY` | Embeddings only (falls back to `LLM_API_KEY`) |
| `APP_ENV` | `development` — set `production` to require Redis at startup |
| `REQUIRE_REDIS` | `false` — fail startup when Redis unavailable if `true` |

## Health

- `GET /health` — liveness
- `GET /ready` — database, Redis, LLM profile checks

## Tests

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 backend/.venv/bin/python -m pytest backend/tests -q
cd frontend && npm run test
cd frontend && npm run test:e2e   # Playwright smoke tests
```

## Module docs

- User document RAG: `backend/app/modules/rag/README.md`
- Visual design tokens: `DESIGN.md`

Interactive architecture graph (optional): run `npx gitnexus analyze` in the repo root.
