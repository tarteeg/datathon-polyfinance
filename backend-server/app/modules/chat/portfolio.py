from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, PositiveFloat

from app.integrations.yahoo import service as yahoo
from app.modules.chat.stock import utc


class Holding(BaseModel):
    ticker: str
    quantity: PositiveFloat | None


class PortfolioQuery(BaseModel):
    view: Literal["holdings", "valuation", "news"]
    hours: int = Field(default=168, ge=1, le=720, description="News lookback in hours; 24 for today.")


PORTFOLIO_TOOL = {"toolSpec": {
    "name": "get_my_portfolio",
    "description": (
        "Read the signed-in user's portfolio. Use holdings for symbols, quantities and watchlist; "
        "valuation for market values, daily performance, contributors and concentration; news for "
        "recent coverage of their saved symbols. The account and tickers are supplied by the server."
    ),
    "inputSchema": {"json": PortfolioQuery.model_json_schema()},
}}


def position_value(holding):
    row = holding.model_dump()
    try:
        quote = yahoo.fetch_history(holding.ticker.replace(".", "-"), "1d")["ticker"]
    except (yahoo.YFTickerMissingError, yahoo.YFRateLimitError, yahoo.MarketDataUnavailable):
        return row
    row.update(price=quote["regularMarketPrice"], currency=quote["currency"], asOf=utc(quote["regularMarketTime"]))
    if not row["currency"]:
        return row
    shares, price = Decimal(str(holding.quantity)), Decimal(str(row["price"]))
    row["value"] = float(shares * price)
    previous = quote.get("previousClose")
    if previous is not None:
        row["dailyChange"] = float(shares * (price - Decimal(str(previous))))
    return row


def portfolio_snapshot(holdings, view):
    positions = [h for h in holdings if h.quantity is not None]
    watchlist = [h.ticker for h in holdings if h.quantity is None]
    result = {"view": view, "watchlist": watchlist, "positions": [h.model_dump() for h in positions],
              "totals": {}, "retrieved": datetime.now(timezone.utc).isoformat()}
    if view != "valuation" or not positions:
        return result
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(position_value, positions))
    result["positions"] = rows
    totals = result["totals"]
    for row in rows:
        if "value" not in row:
            continue
        group = totals.setdefault(row["currency"], {"value": 0, "dailyChange": 0, "missingPreviousClose": 0})
        group["value"] += row["value"]
        if "dailyChange" in row:
            group["dailyChange"] += row["dailyChange"]
        else:
            group["missingPreviousClose"] += 1
    for group in totals.values():
        if group["missingPreviousClose"]:
            group["dailyChange"] = None
        else:
            baseline = group["value"] - group["dailyChange"]
            group["dailyPercent"] = 100 * group["dailyChange"] / baseline if baseline else None
    for row in rows:
        if "value" in row and totals[row["currency"]]["value"]:
            row["weightPercent"] = 100 * row["value"] / totals[row["currency"]]["value"]
    return result
