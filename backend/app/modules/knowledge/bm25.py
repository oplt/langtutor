from __future__ import annotations

import math
import re
from collections import Counter

_WORD_RE = re.compile(r"[\w']+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in _WORD_RE.findall(text)]


def term_frequencies(text: str) -> tuple[dict[str, int], int]:
    tokens = tokenize(text)
    return dict(Counter(tokens)), len(tokens)


def bm25_score(
    *,
    query_terms: list[str],
    term_freqs: dict[str, int],
    doc_len: int,
    avg_doc_len: float,
    doc_count: int,
    doc_freq: dict[str, int],
    k1: float = 1.2,
    b: float = 0.75,
) -> float:
    if doc_len <= 0 or doc_count <= 0:
        return 0.0

    score = 0.0
    for term in query_terms:
        tf = term_freqs.get(term, 0)
        if tf <= 0:
            continue
        df = doc_freq.get(term, 0)
        # BM25+ish idf with 0.5 smoothing.
        idf = math.log(1.0 + (doc_count - df + 0.5) / (df + 0.5))
        denom = tf + k1 * (1.0 - b + b * (doc_len / max(avg_doc_len, 1e-6)))
        score += idf * (tf * (k1 + 1.0) / denom)
    return float(score)
