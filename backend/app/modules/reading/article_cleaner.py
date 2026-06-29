from __future__ import annotations

import html
import re
from html.parser import HTMLParser

_SCRIPT_STYLE_RE = re.compile(r"<(script|style|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_WHITESPACE_RE = re.compile(r"\s+")
_SENTENCE_END_RE = re.compile(r"([.!?])\s+")


class _TextExtractor(HTMLParser):
    """Small dependency-free HTML text extractor for RSS summaries.

    Use trafilatura/readability for full article pages. This extractor is safe
    enough for RSS description/content snippets and preserves paragraph breaks.
    """

    _BLOCK_TAGS = {"p", "div", "br", "li", "section", "article", "h1", "h2", "h3"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):  # type: ignore[no-untyped-def]
        if tag.lower() in self._BLOCK_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self._BLOCK_TAGS:
            self.parts.append(" ")

    def handle_data(self, data: str) -> None:
        if data and data.strip():
            self.parts.append(data.strip())

    def get_text(self) -> str:
        return " ".join(self.parts)


def _truncate_cleanly(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].strip()
    sentence_matches = list(_SENTENCE_END_RE.finditer(cut))
    if sentence_matches and sentence_matches[-1].end() > max_chars * 0.55:
        return cut[: sentence_matches[-1].end()].strip()
    last_space = cut.rfind(" ")
    if last_space > max_chars * 0.55:
        cut = cut[:last_space]
    return cut.strip() + "…"


def clean_article_html(raw: str, *, max_chars: int = 4000) -> str:
    if not raw:
        return ""

    text = html.unescape(str(raw))
    text = _COMMENT_RE.sub(" ", text)
    text = _SCRIPT_STYLE_RE.sub(" ", text)

    if "<" in text and ">" in text:
        parser = _TextExtractor()
        try:
            parser.feed(text)
            text = parser.get_text()
        except Exception:
            # Last-resort fallback for malformed RSS HTML fragments.
            text = re.sub(r"<[^>]+>", " ", text)

    text = html.unescape(text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return _truncate_cleanly(text, max_chars=max_chars)
