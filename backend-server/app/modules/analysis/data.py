"""Market data for the calculation tools: adjusted prices, sector profiles and exchange rates.

Separate from `app.integrations.yahoo.service.fetch_history`, which serves the
charts and the chat with unadjusted prices and must not change.
"""

import threading
import time
from datetime import date, datetime, timedelta, timezone

import requests
import yfinance as yf
from yfinance.exceptions import YFRateLimitError, YFTickerMissingError

CACHE_SECONDS = 15 * 60
VALET_URL = "https://www.bankofcanada.ca/valet/observations/{series}/json"
SECTOR_SOURCE = "Yahoo Finance sector classification"

_cache: dict[tuple, tuple[float, object]] = {}
_lock = threading.Lock()


class AnalysisDataError(Exception):
    pass


def _cached(key: tuple, load):
    now = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_SECONDS:
            return hit[1]
    value = load()
    with _lock:
        _cache[key] = (now, value)
    return value


def yahoo_symbol(symbol: str) -> str:
    """Yahoo uses a hyphen for share classes (BRK-B), the dashboard uses a dot (BRK.B)."""
    symbol = symbol.upper().strip()
    if "." in symbol and not symbol.endswith((".TO", ".V", ".NE", ".CN", ".L", ".PA", ".DE", ".AS")):
        return symbol.replace(".", "-")
    return symbol


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def adjusted_closes(symbol: str, years: int) -> dict:
    return _adjusted_history(symbol, {"period": f"{years}y"})


def adjusted_closes_between(symbol: str, start: str, end_exclusive: str) -> dict:
    return _adjusted_history(symbol, {"start": start, "end": end_exclusive})


def _adjusted_history(symbol: str, window: dict) -> dict:
    """Daily closes adjusted for splits and dividends, oldest first."""

    def load():
        try:
            ticker = yf.Ticker(yahoo_symbol(symbol))
            frame = ticker.history(**window, interval="1d", auto_adjust=True, actions=False, timeout=10)
            currency = (ticker.history_metadata or {}).get("currency")
        except (YFTickerMissingError, YFRateLimitError) as exc:
            raise AnalysisDataError(f"Yahoo Finance returned no history for {symbol}.") from exc
        except Exception as exc:
            raise AnalysisDataError(f"Could not fetch Yahoo Finance history for {symbol}.") from exc
        closes = frame["Close"].dropna() if "Close" in frame else []
        return {
            "symbol": symbol.upper(),
            "currency": currency,
            "dates": [index.date().isoformat() for index in closes.index] if len(closes) else [],
            "prices": [float(value) for value in closes] if len(closes) else [],
            "source": "Yahoo Finance daily closes, adjusted for splits and dividends",
            "retrieved": utc_now(),
        }

    return _cached(("closes", symbol.upper(), tuple(window.items())), load)


def _normalize_sector(name: str) -> str:
    key = name.strip().lower().replace(" ", "_").replace("-", "_")
    return {"realestate": "real_estate"}.get(key, key)


def sector_profile(symbol: str) -> dict:
    """Sector shares of a fund, or the single sector of a company.

    Returns {"symbol", "kind", "sectors" (fractions) or None, "source", "retrieved", "note"}.
    """

    def load():
        result = {"symbol": symbol.upper(), "kind": None, "sectors": None, "source": SECTOR_SOURCE,
                  "retrieved": utc_now(), "note": None}
        try:
            ticker = yf.Ticker(yahoo_symbol(symbol))
            info = ticker.info or {}
        except Exception:
            result["note"] = "Yahoo Finance did not return a profile."
            return result
        kind = info.get("quoteType")
        result["kind"] = kind
        if kind in {"ETF", "MUTUALFUND"}:
            try:
                weights = ticker.funds_data.sector_weightings or {}
            except Exception:
                weights = {}
            shares = {_normalize_sector(name): float(share) for name, share in weights.items() if share}
            if shares:
                result["sectors"] = shares
                result["note"] = "Fund sector weights as published by Yahoo Finance; the composition date is not provided."
            else:
                result["note"] = "Yahoo Finance did not return sector weights for this fund."
        elif info.get("sector"):
            result["sectors"] = {_normalize_sector(info["sector"]): 1.0}
        else:
            result["note"] = "No sector is available for this security."
        return result

    return _cached(("sector", symbol.upper()), load)


def cad_rates(currencies: set[str]) -> dict[str, dict]:
    """Latest Bank of Canada rate for converting each currency into CAD.

    Returns {currency: {"rate", "date", "series"}}. CAD maps to 1.
    """
    rates = {"CAD": {"rate": 1.0, "date": None, "series": None}}
    wanted = sorted(c.upper() for c in currencies if c and c.upper() != "CAD")
    if not wanted:
        return rates

    def load(series: str):
        start = (date.today() - timedelta(days=14)).isoformat()
        try:
            response = requests.get(VALET_URL.format(series=series), params={"start_date": start}, timeout=(5, 15))
            response.raise_for_status()
            observations = response.json().get("observations", [])
        except (requests.RequestException, ValueError) as exc:
            raise AnalysisDataError("The Bank of Canada exchange-rate service is unavailable.") from exc
        dated = [(row["d"], row[series]["v"]) for row in observations if row.get(series, {}).get("v")]
        if not dated:
            raise AnalysisDataError(f"The Bank of Canada returned no recent {series} rate.")
        day, value = max(dated)
        return {"rate": float(value), "date": day, "series": series}

    for currency in wanted:
        series = f"FX{currency}CAD"
        rates[currency] = _cached(("fx", series), lambda series=series: load(series))
    return rates
