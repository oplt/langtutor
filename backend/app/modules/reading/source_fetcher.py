from __future__ import annotations

import asyncio
import logging
import random
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import httpx

from backend.app.modules.reading.article_cleaner import clean_article_html
from backend.app.modules.reading.source_registry import SourceDefinition, get_direct_rss_sources_for_interest

logger = logging.getLogger(__name__)

_FETCH_TIMEOUT = httpx.Timeout(connect=4.0, read=8.0, write=4.0, pool=4.0)
_TOTAL_FETCH_BUDGET_SECONDS = 8.0
_USER_AGENT = "LanguageApp-ReadingBot/1.0 (+educational; rss-summary; contact=admin@example.com)"
_RSS_CACHE_TTL_SECONDS = 300
_RSS_CACHE: dict[str, tuple[float, list[dict[str, str]]]] = {}


@dataclass(frozen=True)
class FetchedArticle:
    title: str
    summary: str
    url: str
    publisher: str
    published_at: str
    content: str


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _find_text(parent: ET.Element, names: tuple[str, ...]) -> str:
    for child in parent:
        local = _local_name(child.tag)
        if local in names:
            text = "".join(child.itertext()).strip()
            if text:
                return text
    return ""


def _find_link(parent: ET.Element) -> str:
    # RSS: <link>https://...</link>; Atom: <link href="https://..." rel="alternate" />
    for child in parent:
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href", "").strip()
        rel = child.attrib.get("rel", "alternate")
        if href and rel in {"alternate", ""}:
            return href
        text = "".join(child.itertext()).strip()
        if text:
            return text
    return ""


def _parse_feed_items(xml_text: str) -> list[dict[str, str]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []

    items: list[dict[str, str]] = []
    for element in root.iter():
        local = _local_name(element.tag)
        if local not in {"item", "entry"}:
            continue

        title = _find_text(element, ("title",))
        link = _find_link(element)
        description = _find_text(element, ("description", "summary", "content", "encoded"))
        pub_date = _find_text(element, ("pubDate", "published", "updated", "date"))

        if title or description:
            items.append(
                {
                    "title": title,
                    "link": link,
                    "description": description,
                    "published_at": pub_date,
                }
            )
    return items


async def _get_feed_items(client: httpx.AsyncClient, source: SourceDefinition) -> list[dict[str, str]]:
    now = time.time()
    cached = _RSS_CACHE.get(source.url)
    if cached and now - cached[0] < _RSS_CACHE_TTL_SECONDS:
        return cached[1]

    headers = {
        "User-Agent": _USER_AGENT,
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.1",
    }
    response = await client.get(source.url, headers=headers)
    response.raise_for_status()
    items = _parse_feed_items(response.text)
    _RSS_CACHE[source.url] = (now, items)
    return items


async def _fetch_rss(
    client: httpx.AsyncClient,
    source: SourceDefinition,
    *,
    desired_word_count: int,
) -> FetchedArticle | None:
    if source.type != "rss":
        return None
    if source.use_mode not in {"rss_summary", "source_facts", "facts_and_link_only"}:
        return None

    try:
        items = await _get_feed_items(client, source)
    except Exception as exc:
        logger.warning(
            "reading_source_fetch_failed source=%s url=%s error=%s",
            source.name,
            source.url,
            exc,
        )
        return None

    valid_items = [item for item in items if item.get("title") or item.get("description")]
    if not valid_items:
        return None

    # RSS feeds often mix one-line notices with useful summaries. A random
    # short notice cannot support a requested 300+ word learner text without
    # hallucination, so choose the richest recent candidate from each source.
    recent_items = valid_items[:12]
    item = max(
        recent_items,
        key=lambda candidate: len(
            clean_article_html(candidate.get("description", ""), max_chars=1800).split()
        ),
    )
    summary = clean_article_html(item.get("description", ""), max_chars=1800)
    title = clean_article_html(item.get("title", ""), max_chars=220)
    if not summary and not title:
        return None

    # RSS summaries are intentionally used as source facts/snippets only. Do not
    # fetch full copyrighted pages unless that source is approved elsewhere.
    content = summary or title
    return FetchedArticle(
        title=title or "Artikel",
        summary=summary,
        url=item.get("link", source.website_url or source.url),
        publisher=source.publisher or source.name,
        published_at=item.get("published_at", ""),
        content=content,
    )


def build_topic_fallback(interest_area: str, word_count: int) -> FetchedArticle:
    topics = {
        "news": "actueel nieuws in Nederland en België",
        "sports": "sport, beweging en teams",
        "technology": "technologie en digitale hulpmiddelen",
        "science": "wetenschap en onderzoek",
        "business": "werk, geld en economie",
        "arts": "kunst en creativiteit",
        "culture": "cultuur en samenleving",
        "travel": "reizen en nieuwe plaatsen ontdekken",
        "health": "gezondheid en welzijn",
        "environment": "natuur, klimaat en milieu",
        "history": "geschiedenis en het verleden",
        "daily_life": "het dagelijks leven",
    }
    topic = topics.get(interest_area, "het dagelijks leven")
    paragraphs = [
        f"Deze oefentekst gaat over {topic}.",
        "De tekst is bedoeld voor mensen die Nederlands leren.",
        "Hij gebruikt korte zinnen en duidelijke voorbeelden.",
        "De informatie is algemeen en moet niet worden gelezen als actueel nieuws of persoonlijk advies.",
        "De app kan deze tekst later eenvoudiger of moeilijker maken met de gekozen woordenlijst.",
    ]
    text = " ".join(paragraphs)
    return FetchedArticle(
        title=f"Oefentekst: {topic}",
        summary=text,
        url="generated://fallback",
        publisher="LanguageApp",
        published_at="",
        content=text,
    )


async def fetch_source_material(
    *,
    interest_area: str,
    source_mode: str,
    word_count: int = 500,
) -> FetchedArticle:
    if source_mode == "generated":
        logger.info("reading_source_mode_generated interest=%s", interest_area)
        return build_topic_fallback(interest_area, word_count)

    sources = list(get_direct_rss_sources_for_interest(interest_area))
    if not sources:
        logger.warning("reading_source_no_direct_rss interest=%s", interest_area)
        return build_topic_fallback(interest_area, word_count)

    # Check all approved feeds concurrently, then choose among successful
    # results. Sequential first-success fetching biased output toward NOS.
    async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT, follow_redirects=True) as client:
        async def fetch(source: SourceDefinition) -> FetchedArticle | None:
            logger.info("reading_source_fetch_started source=%s interest=%s", source.name, interest_area)
            article = await _fetch_rss(client, source, desired_word_count=word_count)
            if article:
                logger.info(
                    "reading_source_fetch_completed source=%s title=%s source_words=%s requested_words=%s",
                    source.name,
                    article.title,
                    len(article.content.split()),
                    word_count,
                )
            return article

        tasks = [asyncio.create_task(fetch(source)) for source in sources]
        done, pending = await asyncio.wait(tasks, timeout=_TOTAL_FETCH_BUDGET_SECONDS)
        if pending:
            logger.warning("reading_source_fetch_budget_exhausted interest=%s", interest_area)
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        results = [task.result() for task in done if not task.cancelled() and task.exception() is None]

    available = [article for article in results if article is not None]
    if available:
        minimum_source_words = min(120, max(30, round(word_count * 0.4)))
        sufficiently_detailed = [
            article for article in available
            if len(article.content.split()) >= minimum_source_words
        ]
        if sufficiently_detailed:
            return random.choice(sufficiently_detailed)
        richest = max(available, key=lambda article: len(article.content.split()))
        logger.warning(
            "reading_source_short_fallback source=%s source_words=%s requested_words=%s",
            richest.publisher,
            len(richest.content.split()),
            word_count,
        )
        return richest

    logger.warning("reading_source_fetch_all_failed interest=%s; using topic fallback", interest_area)
    return build_topic_fallback(interest_area, word_count)
