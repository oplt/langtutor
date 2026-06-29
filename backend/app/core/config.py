from pathlib import Path
import json
from typing import Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

# Configuration layers:
# - Settings (this file): infrastructure, feature flags, LLM env bootstrap fallback.
# - settings/repository.py JSON: operator-tunable AI profiles, routing, privacy prefs.
# - ai/service.py: normalization + short-lived read caches (not source of truth).


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        extra="ignore",
    )

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = 60
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    CORS_ALLOW_ORIGINS: str = ""
    RATE_LIMIT_LOGIN_PER_MIN: int = 5
    RATE_LIMIT_SIGNUP_PER_MIN: int = 5
    RATE_LIMIT_ANALYZE_PER_MIN: int = 10
    AI_AGENT_ENABLED: bool = True
    # Low-priority optional: allow the model to evaluate small arithmetic expressions
    # in a restricted sandbox.
    SANDBOX_ENABLED: bool = False
    LLM_PROVIDER: str = "ollama"
    LLM_BASE_URL: str = "http://127.0.0.1:11434"
    LLM_MODEL: str = "llama3.1:8b"
    LLM_API_KEY: str = ""
    RAG_EMBEDDING_API_KEY: str = ""
    LLM_TIMEOUT_SECONDS: int = 30
    LLM_TUTOR_TIMEOUT_SECONDS: int = 90
    FRONTEND_BASE_URL: str = "http://localhost:5173"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    TUTOR_TURN_RUNNING_TTL_SECONDS: int = 1800
    TUTOR_TURN_PAUSED_TTL_SECONDS: int = 86400
    LOG_LEVEL: str = "INFO"
    LOG_FILE_PATH: str = "logs/logs.txt"
    LOG_TO_FILE: bool = True
    LOG_TO_CONSOLE: bool = True
    LOG_TO_STDOUT: bool = True
    LOG_FORMAT: str = "json"
    LOG_JSON: bool = True
    LOG_RETENTION_DAYS: int = 1
    APP_ENV: str = "development"
    REQUIRE_REDIS: bool = False
    SLOW_REQUEST_MS: int = 1000
    SLOW_JOB_MS: int = 5000
    SLOW_EXTERNAL_CALL_MS: int = 3000
    READING_GENERATE_TIMEOUT_SECONDS: int = 120
    READING_COVERAGE_RELAXED_PERCENT: float = 80.0
    READING_COVERAGE_BALANCED_PERCENT: float = 85.0
    READING_COVERAGE_STRICT_PERCENT: float = 92.0
    READING_COVERAGE_MAX_ATTEMPTS: int = 3
    READING_GENERATE_CACHE_TTL_SECONDS: int = 600
    READING_GENERATE_FALLBACK_CACHE_TTL_SECONDS: int = 120
    LLM_SETTINGS_CACHE_TTL_SECONDS: int = 60
    LLM_TASK_CLIENT_CACHE_TTL_SECONDS: int = 120
    LEARNING_LEVELS_CACHE_TTL_SECONDS: int = 3600
    LEARNING_PROGRESS_CACHE_TTL_SECONDS: int = 45
    RAG_EMBEDDING_CACHE_TTL_SECONDS: int = 3600

    DEEPL_ENABLED: bool = True
    DEEPL_AUTH_KEY: str = ""
    DEEPL_API_BASE_URL: str = "https://api-free.deepl.com"
    DEEPL_SOURCE_LANG: str = "NL"
    DEEPL_TARGET_LANG: str = "EN-US"
    DEEPL_TIMEOUT_SECONDS: int = 10
    DEEPL_MODEL_TYPE: str = ""

    # User document RAG (LangChain-backed, separate from global knowledge BM25).
    # Disabled by default — set RAG_ENABLED=true when pgvector + embeddings are configured.
    RAG_ENABLED: bool = False
    RAG_VECTOR_BACKEND: str = "pgvector"
    RAG_EMBEDDING_PROVIDER: str = "openai"
    RAG_EMBEDDING_MODEL: str = "text-embedding-3-small"
    RAG_EMBEDDING_DIMENSION: int = 1536
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 150
    RAG_TOP_K: int = 5
    RAG_SCORE_THRESHOLD: float = 0.3
    RAG_MAX_CONTEXT_TOKENS: int = 6000
    RAG_ALLOWED_FILE_TYPES: str = "pdf,txt,md,docx,csv"
    RAG_MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    RAG_EMBEDDING_BATCH_SIZE: int = 32
    RAG_EMBEDDING_BATCH_CONCURRENCY: int = 4
    RAG_STORAGE_ROOT: str = "data/rag/uploads"

    # Comma-separated emails allowed to create/ingest knowledge bases (empty = deny all).
    KNOWLEDGE_ADMIN_EMAILS: str = ""
    KNOWLEDGE_USE_FTS: bool = False
    KNOWLEDGE_BM25_MIN_SCORE: float = 0.35
    KNOWLEDGE_FTS_MIN_SCORE: float = 0.05
    AUTO_ROUTE_MIN_CONFIDENCE: float = 0.75

    MEMORY_L3_LLM_PROFILE: bool = False
    MEMORY_L3_PROFILE_MAX_TOKENS: int = 200

    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_SERVICE_NAME: str = "languageapp"

    @property
    def rag_allowed_file_types_list(self) -> list[str]:
        return [ext.strip().lower() for ext in self.RAG_ALLOWED_FILE_TYPES.split(",") if ext.strip()]

    @property
    def embedding_api_key(self) -> str:
        return self.RAG_EMBEDDING_API_KEY.strip() or self.LLM_API_KEY

    @property
    def knowledge_admin_emails_list(self) -> set[str]:
        return {
            email.strip().lower()
            for email in self.KNOWLEDGE_ADMIN_EMAILS.split(",")
            if email.strip()
        }


    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return value

    @field_validator("LOG_RETENTION_DAYS", mode="before")
    @classmethod
    def validate_log_retention_days(cls, value: Any) -> int:
        try:
            days = int(value)
        except (TypeError, ValueError):
            return 1
        return max(1, min(days, 365))

    @field_validator("LOG_FORMAT", mode="before")
    @classmethod
    def normalize_log_format(cls, value: Any) -> str:
        fmt = str(value or "json").strip().lower()
        if fmt not in {"json", "text"}:
            return "json"
        return fmt

    @property
    def cors_origins_list(self) -> list[str]:
        raw = self.CORS_ORIGINS.strip() or self.CORS_ALLOW_ORIGINS.strip()
        if not raw:
            return ["http://localhost:5173", "http://127.0.0.1:5173"]

        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            except json.JSONDecodeError:
                pass

        return [origin.strip() for origin in raw.split(",") if origin.strip()]


settings = Settings()
