"""Volatility, correlation, drawdown, and risk-adjusted return calculations."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .returns import TRADING_DAYS_PER_YEAR, cumulative_wealth


def annualized_volatility(returns: pd.Series, periods_per_year: int = TRADING_DAYS_PER_YEAR, ddof: int = 1) -> float:
    """sigma_annual = std(daily_returns, ddof=1) * sqrt(periods_per_year).

    Uses the sample standard deviation (ddof=1), consistent with estimating volatility
    from a finite historical sample rather than treating it as a known population parameter.
    """
    returns = returns.dropna()
    if len(returns) < 2:
        raise ValueError("need at least 2 return observations to estimate volatility")
    return float(returns.std(ddof=ddof)) * np.sqrt(periods_per_year)


def covariance_matrix(returns_panel: pd.DataFrame, periods_per_year: int = TRADING_DAYS_PER_YEAR, ddof: int = 1) -> pd.DataFrame:
    """Annualized sample covariance matrix of asset returns."""
    return returns_panel.cov(ddof=ddof) * periods_per_year


def correlation_matrix(returns_panel: pd.DataFrame) -> pd.DataFrame:
    """Pairwise Pearson correlation of asset returns. Correlation is scale-free, so
    it is not annualized."""
    return returns_panel.corr()


@dataclass
class DrawdownResult:
    max_drawdown: float
    peak_date: pd.Timestamp
    trough_date: pd.Timestamp
    recovery_date: pd.Timestamp | None  # None if not yet recovered within the series


def max_drawdown(returns: pd.Series) -> DrawdownResult:
    """Largest peak-to-trough decline in cumulative wealth.

    wealth_t = prod(1 + r_i) for i <= t
    drawdown_t = wealth_t / running_max(wealth) - 1
    max_drawdown = min(drawdown_t)
    """
    wealth = cumulative_wealth(returns.dropna())
    running_peak = wealth.cummax()
    drawdown = wealth / running_peak - 1.0

    trough_date = drawdown.idxmin()
    mdd = float(drawdown.loc[trough_date])
    peak_date = wealth.loc[:trough_date].idxmax()

    post_trough = wealth.loc[trough_date:]
    peak_value = wealth.loc[peak_date]
    recovered = post_trough[post_trough >= peak_value]
    recovery_date = recovered.index[0] if len(recovered) > 0 else None

    return DrawdownResult(
        max_drawdown=mdd,
        peak_date=peak_date,
        trough_date=trough_date,
        recovery_date=recovery_date,
    )


def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> float:
    """Sharpe = (annualized_return - risk_free_rate) / annualized_volatility.

    `risk_free_rate` must already be an annualized rate in the same currency as
    `returns`. Caller is responsible for currency/annualization consistency
    (see validation.validate_currency_consistency).
    """
    from .returns import annualized_return  # local import to avoid a cycle at module load

    ann_return = annualized_return(returns, periods_per_year)
    ann_vol = annualized_volatility(returns, periods_per_year)
    if ann_vol == 0:
        raise ValueError("annualized volatility is zero; Sharpe ratio is undefined")
    return (ann_return - risk_free_rate) / ann_vol
