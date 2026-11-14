"""Converts real StocksFeed news articles into the same document shape the alert
pipeline already consumes for Federal Register documents, so `alerts.pipeline.
run_alert_scan` can scan news without any new matching/recommendation logic.

Reuses the existing `app.integrations.stocksfeed.service.fetch_articles` call --
the same live external API the rest of the app already uses for its news feed --
rather than re-implementing the HTTP call.
"""
from __future__ import annotations

import hashlib
import re

from app.integrations.stocksfeed import service as stocksfeed_service

# Most real news about a held ticker is not a trickle-down risk event (earnings
# beats, analyst notes, executive gossip, a product review). Confirmed live: a real
# article about an NVIDIA executive's alleged ties to "a Chinese spy" contains the
# word "Chinese" -- which is in `research_tools._SINGLE_WORD_ALLOWLIST` as a
# sanctions-relevant geography term, and would coincidentally match NVDA's own 10-K
# (which genuinely, substantively discusses China/Chinese market exposure) even
# though this specific article has nothing to do with trade, export controls, or
# supply chains -- it's a personal/espionage story that happens to use a
# nationality adjective. Unlike a Federal Register document (which is near-certain
# to be substantively about trade/regulation if it mentions a country), ordinary
# news can mention a country/material incidentally. Cheap, honest fix: only pass an
# article into the exposure-matching pipeline at all if its own text contains some
# independent signal that it's actually about trade/regulatory/supply-chain
# mechanics -- not just because a country or material name happens to appear in it.
_TRADE_SIGNAL_RE = re.compile(
    r"\b(export|import|sanction|tariff|trade war|trade dispute|supply chain|"
    r"embargo|duty|duties|customs|antidumping|anti-dumping|quota|entity list|"
    r"forced labor|forced labour|geopolit|export control|ban on|restrict)",
    re.IGNORECASE,
)


def _has_trade_signal(text: str) -> bool:
    return bool(_TRADE_SIGNAL_RE.search(text))


def _article_document_number(article: dict) -> str:
    key = article.get("url") or article.get("title") or ""
    return "news:" + hashlib.sha256(key.encode()).hexdigest()[:16]


def _article_to_document(article: dict) -> dict:
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
    }


def fetch_news_documents_for_tickers(tickers: list[str], *, limit_per_ticker: int = 5) -> list[dict]:
    """Fetches each ticker's recent real news once (de-duplicated across callers that
    pass overlapping ticker lists) and returns only the articles that contain an
    independent trade/regulatory/supply-chain signal -- see `_has_trade_signal`.
    Articles are deduplicated by document_number (same article can come back for
    more than one ticker query, e.g. a multi-company roundup).
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
            text = f"{article.get('title', '')} {article.get('content', '')} {article.get('summary_extended', '')}"
            if not _has_trade_signal(text):
                continue
            doc = _article_to_document(article)
            documents.setdefault(doc["document_number"], doc)
    return list(documents.values())
