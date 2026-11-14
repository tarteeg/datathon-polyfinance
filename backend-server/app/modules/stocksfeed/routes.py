from fastapi import APIRouter, HTTPException, Query

from app.integrations.stocksfeed import service

router = APIRouter(tags=["stocksfeed"])


@router.get("/articles")
def get_articles(
    search: str | None = None,
    tickers: str | None = None,
    sectors: str | None = None,
    sentiment: str | None = None,
    hours: int | None = Query(None, ge=1, le=720),
    only_with_tickers: bool = True,
    limit: int = Query(20, ge=1, le=500),
):
    try:
        return service.fetch_articles({
            "search": search, "tickers": tickers, "sectors": sectors,
            "sentiment": sentiment, "hours": hours,
            "only_with_tickers": only_with_tickers, "limit": limit,
        })
    except service.StocksFeedError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/article/{article_slug}")
def get_article(article_slug: str):
    try:
        return service.fetch_article(article_slug)
    except service.StocksFeedError as exc:
        raise HTTPException(502, str(exc)) from exc


@router.get("/stocks/most-mentioned")
def most_mentioned(sector: str | None = None, hours: int = Query(24, ge=1, le=168),
                   limit: int = Query(10, ge=1, le=100)):
    try:
        return service.fetch_most_mentioned(sector, hours, limit)
    except service.StocksFeedError as exc:
        raise HTTPException(502, str(exc)) from exc
