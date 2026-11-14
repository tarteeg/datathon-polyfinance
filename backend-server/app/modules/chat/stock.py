from datetime import datetime, timezone
from urllib.parse import quote

from pydantic import BaseModel, Field

from app.integrations.yahoo import service as yahoo
from app.modules.stocks.schemas import Period


class StockQuery(BaseModel):
    ticker: str = Field(pattern=r"^[A-Za-z0-9^][A-Za-z0-9.^=-]{0,19}$")
    period: Period = "1d"


STOCK_TOOL = {"toolSpec": {
    "name": "get_stock",
    "description": (
        "Look up one stock by its Yahoo Finance symbol. Returns the company name, exchange, "
        "latest regular-session price, currency, timestamp, and observed price history statistics. "
        "Use 1d for a quote, 1mo for a month, ytd for year to date. Use the requested share class."
    ),
    "inputSchema": {"json": StockQuery.model_json_schema()},
}}


def utc(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat() if timestamp is not None else None


def lookup_stock(query: StockQuery) -> dict:
    symbol = query.ticker.upper()
    if symbol in {"BRK.B", "BRK.A", "BF.B", "BF.A"}:
        symbol = symbol.replace(".", "-")
    history = yahoo.fetch_history(symbol, query.period)
    ticker, candles = history["ticker"], history["candles"]
    price = ticker["regularMarketPrice"]
    first = candles[0] if candles else None
    baseline = ticker.get("previousClose") if query.period == "1d" else first["Close"] if first else None
    result = {
        "symbol": symbol, "name": ticker["name"], "exchange": ticker.get("exchange"),
        "currency": ticker.get("currency"), "price": price, "asOf": utc(ticker.get("regularMarketTime")),
        "period": query.period, "previousClose": ticker.get("previousClose"),
        "baselineDescription": "previous close" if query.period == "1d" else "first candle close",
        "baseline": baseline, "priceChange": price - baseline if baseline is not None else None,
        "percentChange": (price / baseline - 1) * 100 if baseline else None,
        "history": None,
    }
    if candles:
        high = max(candles, key=lambda c: c["High"])
        low = min(candles, key=lambda c: c["Low"])
        result["history"] = {
            "start": utc(first["time"]), "firstClose": first["Close"],
            "end": utc(candles[-1]["time"]), "lastClose": candles[-1]["Close"],
            "high": high["High"], "highCandle": utc(high["time"]),
            "low": low["Low"], "lowCandle": utc(low["time"]),
            "interval": yahoo.INTERVALS[query.period],
        }
    return result


def stock_source(stock: dict) -> str:
    symbol = stock["symbol"]
    url = "https://finance.yahoo.com/quote/" + quote(symbol, safe="") + "/"
    stamp = stock["asOf"] or "timestamp unavailable"
    return f"\n\n[Yahoo Finance · {symbol}]({url}) · {stock['currency'] or 'currency unavailable'} · Quote: {stamp}"
