"""Startup validation for layered configuration (env vs runtime JSON)."""

from __future__ import annotations

import logging

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

_KNOWN_EMBEDDING_DIMENSIONS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
}

# Env (`Settings`): infrastructure, feature flags, LLM bootstrap fallback.
# Runtime JSON (`SettingsRepository`): operator-tunable AI profiles, routing, privacy.
# `ai/service.py`: schema normalization + short-lived read caches only.


def _validate_rag_embedding_dimension() -> None:
    dimension = settings.RAG_EMBEDDING_DIMENSION
    if dimension <= 0:
        raise ValueError(f"RAG_EMBEDDING_DIMENSION must be positive; got {dimension}")

    model_key = settings.RAG_EMBEDDING_MODEL.strip().lower()
    expected = _KNOWN_EMBEDDING_DIMENSIONS.get(model_key)
    if expected is not None and expected != dimension:
        logger.warning(
            "runtime_config_embedding_dimension_mismatch model=%s configured=%s expected=%s",
            settings.RAG_EMBEDDING_MODEL,
            dimension,
            expected,
        )


async def validate_runtime_config() -> None:
    if settings.RAG_ENABLED and settings.RAG_VECTOR_BACKEND.lower() != "pgvector":
        raise ValueError(
            f"Unsupported RAG_VECTOR_BACKEND={settings.RAG_VECTOR_BACKEND!r}; "
            "only 'pgvector' is supported."
        )

    if settings.RAG_ENABLED:
        _validate_rag_embedding_dimension()

    from backend.app.core.health import check_redis

    redis_ok = await check_redis()
    if not redis_ok:
        if settings.REQUIRE_REDIS or settings.APP_ENV.lower() == "production":
            raise ValueError(
                "Redis is required (REQUIRE_REDIS or APP_ENV=production) but is unavailable."
            )
        logger.warning(
            "runtime_config_redis_unavailable features=rate_limit,oauth_state,tutor_turns,caches,job_locks"
        )

    from backend.app.modules.ai.service import AISettingsService

    try:
        llm = await AISettingsService().get_settings(effective=True)
    except Exception:
        logger.warning("runtime_config_llm_settings_unavailable", exc_info=True)
        return

    if llm.profiles:
        logger.info(
            "runtime_config_llm_profiles_loaded count=%s default=%s",
            len(llm.profiles),
            llm.default_profile_id,
        )
    else:
        logger.warning(
            "runtime_config_no_llm_profiles env_fallback provider=%s model=%s",
            settings.LLM_PROVIDER,
            settings.LLM_MODEL,
        )
