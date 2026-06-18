"""Redis key namespaces and feature inventory for operators and health checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RedisFeature:
    name: str
    key_pattern: str
    purpose: str


REDIS_FEATURES: tuple[RedisFeature, ...] = (
    RedisFeature("rate_limit", "rl:*", "Per-route HTTP rate limiting"),
    RedisFeature("oauth_state", "oauth:google:state:*", "Google OAuth CSRF state (one-time)"),
    RedisFeature("tutor_turn", "tutor:turn:*", "Tutor turn pause/resume state"),
    RedisFeature("tutor_session", "tutor:session:*", "Active tutor session → turn mapping"),
    RedisFeature("rag_embedding", "rag:embed:v1:*", "RAG query embedding cache"),
    RedisFeature("learning_levels", "learning:levels:v1", "CEFR levels list cache"),
    RedisFeature("learning_progress", "learning:progress:*", "Per-user progress summary cache"),
    RedisFeature("kb_search", "kb:search:*", "BM25 search result cache (shared across workers)"),
    RedisFeature("job_lock", "lock:jobs:*", "Background job deduplication locks"),
)


def redis_feature_inventory() -> list[dict[str, str]]:
    return [
        {"name": feature.name, "keys": feature.key_pattern, "purpose": feature.purpose}
        for feature in REDIS_FEATURES
    ]
