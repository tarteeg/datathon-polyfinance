from datetime import datetime
from math import isnan

import yfinance as yf
from yfinance.exceptions import YFRateLimitError, YFTickerMissingError

from app.modules.stocks.schemas import Period
yf.config.debug.hide_exceptions = False

INTERVALS = {
    "1d": "1m", "5d": "1m",
    "1mo": "1h", "3mo": "1h", "6mo": "1h", "ytd": "1h", "1y": "1h",
    "3y": "1d", "5y": "1d",
}


class MarketDataUnavailable(Exception):
    pass


def fetch_history(symbol: str, period: Period):
    try:
        stock = yf.Ticker(symbol)
        frame = stock.history(
            period=period, interval=INTERVALS[period], prepost=False,
            auto_adjust=False, actions=False, timeout=10,
        )
        metadata = stock.history_metadata
    except (YFTickerMissingError, YFRateLimitError):
        raise
    except Exception as exc:
        raise MarketDataUnavailable("Could not fetch Yahoo Finance data") from exc

    price = metadata.get("regularMarketPrice")
    if price is None:
        raise MarketDataUnavailable("Yahoo Finance returned no regular-market price")

    candles = []
    for row in frame.dropna(subset=["Open", "High", "Low", "Close"]).itertuples():
        candles.append({
            "time": int(row.Index.timestamp()),
            "Open": row.Open,
            "High": row.High,
            "Low": row.Low,
            "Close": row.Close,
            "Volume": int(row.Volume) if not isnan(row.Volume) else None,
        })

    quote_time = metadata.get("regularMarketTime")
    if isinstance(quote_time, datetime):
        quote_time = int(quote_time.timestamp())

    return {
        "ticker": {
            "symbol": symbol,
            "name": metadata.get("shortName") or metadata.get("longName") or symbol,
            "currency": metadata.get("currency"),
            "exchange": metadata.get("fullExchangeName"),
            "regularMarketPrice": price,
            "previousClose": metadata.get("previousClose"),
            "regularMarketTime": quote_time,
        },
        "candles": candles,
    }
