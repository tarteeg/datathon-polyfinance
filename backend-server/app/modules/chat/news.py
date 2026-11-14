import re
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit

from pydantic import BaseModel, Field

from app.integrations.stocksfeed.service import fetch_articles


class NewsQuery(BaseModel):
    tickers: list[str] = Field(default_factory=list, max_length=8)
    topic: str = Field(default="", max_length=150)
    hours: int = Field(default=168, ge=1, le=720)


NEWS_TOOL = {"tools": [{"toolSpec": {
    "name": "search_news",
    "description": (
        "Find current StocksFeed news. Use stock symbols for companies, topic for a subject, "
        "or neither for a market briefing. Use 24 hours for today, 168 for a week. "
        "Use the chart ticker for related news. Coverage is limited to the last 720 hours."
    ),
    "inputSchema": {"json": NewsQuery.model_json_schema()},
}}]}


def search_news(query: NewsQuery, *, portfolio_symbols: list[str] | None = None) -> dict:
    params = {"hours": query.hours, "limit": 15}
    tickers = portfolio_symbols if portfolio_symbols is not None else query.tickers
    if tickers:
        symbols = set()
        for raw in tickers:
            ticker = raw.upper().strip()
            if not re.fullmatch(r"[A-Z0-9^.-]{1,15}", ticker):
                raise ValueError("Invalid ticker")
            symbols.update((ticker, ticker.replace(".", "-"), ticker.replace("-", ".")))
        params["tickers"] = ",".join(sorted(symbols))
    if query.topic.strip():
        params["search"] = query.topic.strip()

    stories = {}
    for article in fetch_articles(params)["articles"]:
        url = article.get("url") or ""
        parsed = urlsplit(url)
        title = article.get("title")
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or not title or url in stories:
            continue
        summary = article.get("summary") or article.get("summary_short") or ""
        stories[url] = {
            "title": title, "url": url, "publisher": article.get("source") or parsed.hostname,
            "published": article.get("publish_date"), "summary": summary[:1800],
        }
        if len(stories) == 3:
            break
    return {"query": {**query.model_dump(), "tickers": tickers}, "retrieved": datetime.now(timezone.utc).isoformat(), "stories": list(stories.values())}


def source_list(news: dict) -> str:
    def escape(text):
        return re.sub(r"([\\\[\]*_`<>])", r"\\\1", " ".join(text.split()))

    entries = []
    for index, story in enumerate(news["stories"], 1):
        title = escape(story["title"])
        url = quote(story["url"], safe=":/?#[]@!$&'()*+,;=%")
        publisher = escape(story["publisher"])
        date = story["published"][:10] if story["published"] else "Date unavailable"
        entries.append(f"{index}. [{title}](<{url}>) — {publisher}, {date}")
    return "\n\nStocksFeed · " + news["retrieved"][:10] + " UTC\n\n" + "\n".join(entries)
