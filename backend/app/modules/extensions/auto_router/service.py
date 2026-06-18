from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# (pattern, capability, reason)
_INTENT_RULES: list[tuple[re.Pattern[str], str, str]] = [
    (
        re.compile(
            r"\b(quiz|test me|drill|mastery|practice words|vocab test)\b",
            re.I,
        ),
        "mastery_path",
        "Learner asked for a quiz or mastery drill.",
    ),
    (
        re.compile(
            r"\b(research|history|culture|cultural|essay|netherlands|dutch history|"
            r"golden age|immigration|tradition)\b",
            re.I,
        ),
        "deep_research",
        "Learner asked for cultural or historical context.",
    ),
    (
        re.compile(
            r"\b(step[- ]by[- ]step|derive|derivation|parse|why is|grammatical proof|"
            r"break down|analyze (this|the) sentence)\b",
            re.I,
        ),
        "deep_solve",
        "Learner asked for step-by-step grammar analysis.",
    ),
    (
        re.compile(
            r"\b(chart|graph|visuali[sz]e|progress (chart|graph)|show my progress|"
            r"how am i doing)\b",
            re.I,
        ),
        "visualize",
        "Learner asked for a progress visualization.",
    ),
    (
        re.compile(
            r"\b(converse|conversation|let'?s (talk|chat|speak)|practice speaking|"
            r"role[- ]?play|dialogue)\b",
            re.I,
        ),
        "chat",
        "Learner asked for free conversation practice.",
    ),
    (
        re.compile(r"\b(explain|what does|meaning of|define|translate)\b", re.I),
        "chat",
        "Learner asked for an explanation or translation.",
    ),
]


@dataclass(frozen=True)
class RouteDecision:
    capability: str
    reason: str
    confidence: float
    suggested_persona: str | None = None


def classify_intent(message: str) -> RouteDecision:
    text = (message or "").strip()
    if not text:
        return RouteDecision(
            capability="chat",
            reason="Empty message; defaulting to general tutor chat.",
            confidence=0.5,
        )

    for pattern, capability, reason in _INTENT_RULES:
        if pattern.search(text):
            persona = None
            if capability == "chat" and "conversation" in reason.lower():
                persona = "conversation-partner"
            decision = RouteDecision(
                capability=capability,
                reason=reason,
                confidence=0.85,
                suggested_persona=persona,
            )
            logger.info(
                "auto_route capability=%s confidence=%s reason=%s",
                decision.capability,
                decision.confidence,
                decision.reason,
            )
            return decision

    decision = RouteDecision(
        capability="chat",
        reason="No strong intent signal; defaulting to general tutor chat.",
        confidence=0.6,
    )
    logger.info(
        "auto_route capability=%s confidence=%s reason=%s",
        decision.capability,
        decision.confidence,
        decision.reason,
    )
    return decision


def resolve_capability(
    requested: str | None,
    message: str,
) -> tuple[str, dict[str, object]]:
    """Resolve `auto` (or missing) to a concrete capability name."""
    if requested and requested not in {"", "auto"}:
        return requested, {}

    decision = classify_intent(message)
    metadata: dict[str, object] = {
        "route_reason": decision.reason,
        "route_confidence": decision.confidence,
        "routed_from": "auto",
    }
    if decision.suggested_persona:
        metadata["suggested_persona"] = decision.suggested_persona
    return decision.capability, metadata
