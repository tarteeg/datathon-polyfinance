from datetime import datetime
from math import isnan

from dateutil.relativedelta import relativedelta
import yfinance as yf
from yfinance.exceptions import YFRateLimitError, YFTickerMissingError

from app.modules.stocks.schemas import Period
yf.config.debug.hide_exceptions = False

INTERVALS = {
    "1d": "1m", "5d": "1m",
    "mtd": "1h", "1mo": "1h", "2mo": "1d", "3mo": "1h", "6mo": "1h", "ytd": "1h", "1y": "1h",
    "3y": "1d", "5y": "1d",
}


class MarketDataUnavailable(Exception):
    pass


def fetch_history(symbol: str, period: Period):
    try:
        stock = yf.Ticker(symbol)
        frame = stock.history(
            period="3mo" if period in {"2mo", "mtd"} else period, interval=INTERVALS[period], prepost=False,
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

    prior_month_close = None
    if period == "mtd" and not frame.empty:
        # Yahoo returns an exchange-local index. Include the prior session close in the return only.
        start = datetime.now(frame.index.tz).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        previous = frame.loc[frame.index < start, "Close"].dropna()
        prior_month_close = float(previous.iloc[-1]) if not previous.empty else None
        frame = frame.loc[frame.index >= start]

    if period == "2mo" and not frame.empty:
        start = datetime.now(frame.index.tz).date() - relativedelta(months=2)
        frame = frame.loc[frame.index.date >= start]

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
            "priorMonthClose": prior_month_close,
            "previousClose": metadata.get("previousClose"),
            "regularMarketTime": quote_time,
        },
        "candles": candles,
    }
