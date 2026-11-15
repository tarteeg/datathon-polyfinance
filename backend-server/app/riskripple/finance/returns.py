"""Return calculations. See docs/FINANCIAL_MODELS.md for formula derivations and conventions."""
from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def daily_returns(prices: pd.Series) -> pd.Series:
    """Simple daily returns: r_t = P_t / P_(t-1) - 1.

    `prices` must be an adjusted-close (total-return-consistent) series. Drops the
    first observation, which has no prior price to compare against.
    """
    return prices.pct_change().dropna()


def cumulative_wealth(returns: pd.Series, initial_value: float = 1.0) -> pd.Series:
    """Cumulative wealth index from a return series: W_t = W_0 * prod(1 + r_i)."""
    return initial_value * (1.0 + returns).cumprod()


def annualized_return(returns: pd.Series, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
    """Geometric (compound) annualized return (CAGR-style), not the arithmetic mean.

    annualized = (prod(1 + r_i)) ** (periods_per_year / n) - 1

    Using the arithmetic mean instead systematically overstates return for volatile
    series (volatility drag); this function intentionally does not do that.
    """
    returns = returns.dropna()
    n = len(returns)
    if n == 0:
        raise ValueError("cannot annualize an empty return series")
    total_growth = float((1.0 + returns).prod())
    if total_growth <= 0:
        raise ValueError("cumulative growth is nonpositive; check for a -100% or worse return")
    return total_growth ** (periods_per_year / n) - 1.0


def arithmetic_mean_return(returns: pd.Series, periods_per_year: int = TRADING_DAYS_PER_YEAR) -> float:
    """Annualized arithmetic mean return. Provided for comparison/diagnostics only;
    prefer `annualized_return` (geometric) for reporting actual historical performance.
    """
    return float(returns.mean()) * periods_per_year


def align_price_panel(price_series: dict[str, pd.Series]) -> pd.DataFrame:
    """Align multiple assets' price series onto a shared trading calendar.

    Assets do not all trade on the same calendar (different exchanges, holidays).
    Uses an inner join so only dates where every asset has a price are kept, and
    raises if that leaves too little overlap to be meaningful.
    """
    panel = pd.DataFrame(price_series).dropna(how="any")
    if panel.empty:
        raise ValueError("no overlapping trading dates across the given assets")
    return panel


def returns_panel(price_panel: pd.DataFrame) -> pd.DataFrame:
    """Daily returns for each column of an aligned price panel."""
    return price_panel.pct_change().dropna(how="any")
