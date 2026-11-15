"""Converts real StocksFeed news articles into the same document shape the alert
pipeline already consumes for Federal Register documents, so `alerts.pipeline.
run_alert_scan` can scan news without any new matching/recommendation logic.

Reuses the existing `app.integrations.stocksfeed.service.fetch_articles` call --
the same live external API the rest of the app already uses for its news feed --
rather than re-implementing the HTTP call.

Used to hard-filter every article through a trade/export/sanctions keyword regex
before it ever reached relevance-checking, on the theory that most real news about a
held ticker isn't a trickle-down risk event. Confirmed live and removed: that filter
silently dropped a real NVIDIA-ticker article about a CEO succession story (and would
have dropped a lawsuit, a recall, an earnings surprise -- anything with no trade
vocabulary), even though a CEO/legal/operational story about a company you DIRECTLY
hold doesn't need a trade angle to be worth flagging. The news is already scoped to
tickers actually held (via StocksFeed's own `tickers` param), so that's the real
narrowing that matters -- an extra topic filter on top of already-scoped data was
hiding real signal, not reducing noise. The noise problem this used to guard against
(ordinary earnings/analyst coverage, not a real event) is now handled downstream, per
document, by `alerts.verification`'s direct-news materiality check -- an LLM judgment
call on THIS specific article, not a keyword pre-filter applied before anything reads
the article at all.
"""
from __future__ import annotations

import hashlib

from app.integrations.stocksfeed import service as stocksfeed_service


def _article_document_number(article: dict) -> str:
    key = article.get("url") or article.get("title") or ""
    return "news:" + hashlib.sha256(key.encode()).hexdigest()[:16]


def _article_to_document(article: dict, *, source_ticker: str) -> dict:
    body = "\n\n".join(
        part for part in (
            article.get("content"),
            article.get("summary_extended"),
            article.get("summary_short"),
        ) if part
    )
    return {
        "document_number": _article_document_number(article),
        "title": article.get("title") or "",
        "abstract": body,
        "publication_date": article.get("publish_date"),
        "document_url": article.get("url"),
        # Lets the alert pipeline route a "direct" match through the news-specific
        # materiality check (alerts.verification) instead of the regulatory path's
        # "directly named = automatically material" shortcut, which is correct for a
        # government filing but would make every routine news mention an alert.
        "source": "news",
        "source_ticker": source_ticker,
    }


def fetch_news_documents_for_tickers(tickers: list[str], *, limit_per_ticker: int = 5) -> list[dict]:
    """Fetches each ticker's recent real news (de-duplicated across callers that pass
    overlapping ticker lists) and returns it as alert-pipeline documents, unfiltered
    by topic -- see the module docstring for why the old trade-signal filter was
    removed. Articles are deduplicated by document_number (the same article can come
    back for more than one ticker query, e.g. a multi-company roundup); the first
    ticker it's seen for is recorded as `source_ticker`.
    """
    documents: dict[str, dict] = {}
    for ticker in dict.fromkeys(tickers):  # de-dupe while preserving order
        try:
            payload = stocksfeed_service.fetch_articles(
                {"tickers": ticker, "limit": limit_per_ticker, "only_with_tickers": True}
            )
        except stocksfeed_service.StocksFeedError:
            continue  # a single ticker's news being unavailable shouldn't fail the whole scan
        for article in payload.get("articles", []):
            doc = _article_to_document(article, source_ticker=ticker)
            documents.setdefault(doc["document_number"], doc)
    return list(documents.values())
