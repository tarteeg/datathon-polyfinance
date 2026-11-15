"""Bridges the deterministic finance math in this package to the app's existing live
Yahoo Finance integration (app.integrations.yahoo.service), so portfolio weights and
volatility are computed from real market data, not fixture snapshots.
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.integrations.yahoo import service as yahoo_service
from app.riskripple.finance import portfolio as P
from app.riskripple.finance import returns as R
from app.riskripple.finance import risk as K


@dataclass
class HoldingPriceInfo:
    symbol: str
    price: float | None
    currency: str | None
    error: str | None = None


def fetch_current_prices(symbols: list[str]) -> dict[str, HoldingPriceInfo]:
    """Real, live current price per symbol via Yahoo Finance. A failure for one
    symbol doesn't fail the others -- reported individually via `error`."""
    out: dict[str, HoldingPriceInfo] = {}
    for symbol in symbols:
        try:
            history = yahoo_service.fetch_history(symbol, "1d")
            price = history["ticker"]["regularMarketPrice"]
            currency = history["ticker"]["currency"]
            out[symbol] = HoldingPriceInfo(symbol=symbol, price=float(price) if price is not None else None, currency=currency)
        except Exception as exc:  # noqa: BLE001 -- a single bad ticker must not fail the batch
            out[symbol] = HoldingPriceInfo(symbol=symbol, price=None, currency=None, error=f"{type(exc).__name__}: {exc}")
    return out


def compute_real_weights(quantities: dict[str, float]) -> tuple[dict[str, float], dict[str, str], float]:
    """Given real share quantities, fetch real live prices and compute real dollar
    position weights. Returns (weights, per-symbol errors for symbols that couldn't
    be priced, total portfolio value in whatever currency each quote came back in --
    NOTE: this does not do FX conversion; mixed-currency portfolios will have an
    approximate total, flagged via per-symbol currency info the caller should surface).
    """
    prices = fetch_current_prices(list(quantities))
    values: dict[str, float] = {}
    errors: dict[str, str] = {}
    for symbol, qty in quantities.items():
        info = prices[symbol]
        if info.price is None:
            errors[symbol] = info.error or "no price available"
            continue
        values[symbol] = qty * info.price
    total = sum(values.values())
    if total <= 0:
        return {}, errors, 0.0
    weights = {symbol: value / total for symbol, value in values.items()}
    return weights, errors, total


def fetch_daily_price_history(symbol: str, period: str = "3y") -> pd.Series | None:
    """Real daily closing prices over `period` (default 3 years -> ~750 trading days,
    plenty for an annualized-volatility estimate) via the app's existing Yahoo
    integration. Returns None (not an exception) on failure, since volatility is
    supporting context, not something that should fail the whole investigation."""
    try:
        history = yahoo_service.fetch_history(symbol, period)
    except Exception:  # noqa: BLE001
        return None
    candles = history.get("candles") or []
    if not candles:
        return None
    index = pd.to_datetime([c["time"] for c in candles], unit="s")
    closes = pd.Series([c["Close"] for c in candles], index=index).sort_index()
    return closes.dropna()


def compute_annualized_volatility(symbol: str) -> float | None:
    prices = fetch_daily_price_history(symbol)
    if prices is None or len(prices) < 20:
        return None
    try:
        return K.annualized_volatility(R.daily_returns(prices))
    except Exception:  # noqa: BLE001
        return None
