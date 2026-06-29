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

### DeepL translation (reading)

Add to `.env` when you want English translations for generated Dutch reading texts:

```env
DEEPL_ENABLED=true
DEEPL_AUTH_KEY=your_deepl_api_key_here
DEEPL_API_BASE_URL=https://api-free.deepl.com
DEEPL_SOURCE_LANG=NL
DEEPL_TARGET_LANG=EN-US
DEEPL_TIMEOUT_SECONDS=10
DEEPL_MODEL_TYPE=latency_optimized
```

Use `https://api.deepl.com` for Pro accounts. If DeepL is disabled or unavailable, reading generation still returns Dutch text with `translation.status` set to `disabled` or `unavailable`.

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
| `JWT_SECRET` | Auth signing (≥32 chars). **Production:** set a unique random value; never use the `docker-compose.yml` placeholder. |
| `REDIS_URL` | Rate limits, OAuth state, tutor turn state, caches |
| `RAG_ENABLED` | User document RAG (`false` by default) |
| `KNOWLEDGE_USE_FTS` | PostgreSQL FTS for Dutch corpus (`false` = BM25 cache) |
| `MEMORY_L3_LLM_PROFILE` | Optional LLM synthesis for L3 profile slot |
| `RAG_EMBEDDING_API_KEY` | Embeddings only (falls back to `LLM_API_KEY`) |
| `APP_ENV` | `development` — set `production` to require Redis at startup |
| `REQUIRE_REDIS` | `false` — fail startup when Redis unavailable if `true` |
| `LOG_LEVEL` | Root log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `LOG_TO_FILE` | Write logs to disk (`true` by default) |
| `LOG_TO_CONSOLE` | Mirror logs to stdout (`true` by default) |
| `LOG_FILE_PATH` | Active log file (`logs/logs.txt`) |
| `LOG_FORMAT` | `json` (default) or `text` |
| `LOG_RETENTION_DAYS` | Days of rotated log files to keep (default `1`) |
| `SLOW_REQUEST_MS` | Warn when HTTP requests exceed this latency |
| `SLOW_JOB_MS` | Warn when background jobs exceed this latency |
| `SLOW_EXTERNAL_CALL_MS` | Warn when LLM/external HTTP calls exceed this latency |

### Production hardening

- Set `JWT_SECRET` to a cryptographically random string of at least 32 characters (for example `openssl rand -hex 32`). The value in `docker-compose.yml` is for local development only.
- Set `APP_ENV=production` and `REQUIRE_REDIS=true` when running multiple backend workers so shared caches (memory defaults, L3, RAG, tutor state) stay consistent.

## Health

- `GET /health` — liveness
- `GET /ready` — database, Redis, LLM profile checks

## Tests

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 backend/.venv/bin/python -m pytest backend/tests -q
cd frontend && npm run test
cd frontend && npm run test:e2e   # Playwright smoke tests
```

## Logging

Centralized logging lives in `backend/app/core/logging.py`.

- **Console + file**: enabled by default via `LOG_TO_CONSOLE` and `LOG_TO_FILE`.
- **Active file**: `backend/logs/logs.txt` (override with `LOG_FILE_PATH`).
- **Rotation**: daily at midnight; rotated files are named `logs.txt.YYYY-MM-DD`.
- **Retention**: `LOG_RETENTION_DAYS` controls how long rotated files are kept (default `1`). Only files matching the active log filename prefix are deleted.
- **Format**: JSON by default (`LOG_FORMAT=json`). Set `LOG_FORMAT=text` for key=value lines.
- **Request IDs**: middleware reads `X-Request-ID` or generates one, attaches it to logs, and returns `X-Request-ID` / `X-Trace-ID` response headers.
- **Sensitive data**: passwords, tokens, API keys, and URL credentials are redacted automatically. Never log raw prompts, authorization headers, or uploaded file contents.

```env
LOG_LEVEL=INFO
LOG_TO_CONSOLE=true
LOG_TO_FILE=true
LOG_FILE_PATH=logs/logs.txt
LOG_FORMAT=json
LOG_RETENTION_DAYS=1
SLOW_REQUEST_MS=1000
SLOW_JOB_MS=5000
SLOW_EXTERNAL_CALL_MS=3000
```

## Module docs

- User document RAG: `backend/app/modules/rag/README.md`
- Visual design tokens: `DESIGN.md`


