import os
from urllib.parse import quote

import requests


class StocksFeedError(Exception):
    pass


def _fetch(path, params=None):
    base_url = os.getenv("STOCKSFEED_BASE_URL", "").rstrip("/")
    if not base_url:
        raise StocksFeedError("STOCKSFEED_BASE_URL is not configured")
    try:
        response = requests.get(f"{base_url}/{path}", params=params, timeout=(5, 20))
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise StocksFeedError("StocksFeedAI could not return articles") from exc
    if not isinstance(payload, dict):
        raise StocksFeedError("Invalid StocksFeedAI response")
    return payload


def fetch_articles(params: dict) -> dict:
    payload = _fetch("articles", params)
    if not isinstance(payload.get("articles"), list):
        raise StocksFeedError("Invalid StocksFeedAI article list")
    return payload


def fetch_article(slug: str) -> dict:
    payload = _fetch(f"article/{quote(slug, safe='')}")
    if "article" not in payload or not isinstance(payload["article"], (dict, type(None))):
        raise StocksFeedError("Invalid StocksFeedAI article response")
    return payload


def fetch_most_mentioned(sector, hours, limit):
    payload = _fetch("stocks/most-mentioned", {"sector": sector, "hours": hours, "limit": limit})
    if not isinstance(payload.get("stocks"), list) or not isinstance(payload.get("sectors"), list):
        raise StocksFeedError("Invalid StocksFeedAI ranking response")
    return payload
