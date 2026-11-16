"""Portfolio-level aggregation: weighted returns, volatility, and concentration."""
from __future__ import annotations

import numpy as np
import pandas as pd


def normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("portfolio weights must sum to a positive number")
    return {k: v / total for k, v in weights.items()}


def portfolio_returns(returns_panel: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    """R_p,t = sum_i(w_i * R_i,t). `weights` keys must be a subset of returns_panel columns."""
    missing = set(weights) - set(returns_panel.columns)
    if missing:
        raise ValueError(f"weights reference assets not in returns panel: {missing}")
    w = pd.Series(weights).reindex(returns_panel.columns).fillna(0.0)
    return returns_panel.mul(w, axis=1).sum(axis=1)


def portfolio_volatility(weights: dict[str, float], covariance: pd.DataFrame) -> float:
    """sigma_p = sqrt(w^T * Covariance * w), using the annualized covariance matrix."""
    assets = list(covariance.columns)
    w = np.array([weights.get(a, 0.0) for a in assets])
    cov = covariance.loc[assets, assets].to_numpy()
    variance = float(w @ cov @ w)
    if variance < 0:
        # Can only happen from numerical noise on a near-singular covariance matrix.
        variance = 0.0
    return float(np.sqrt(variance))


def herfindahl_index(weights: dict[str, float]) -> float:
    """Herfindahl-Hirschman concentration index: sum(w_i^2). 1/n for an equal-weight
    portfolio of n assets, 1.0 for a single-asset portfolio."""
    return float(sum(w ** 2 for w in weights.values()))


def max_single_asset_weight(weights: dict[str, float]) -> tuple[str, float]:
    asset = max(weights, key=lambda k: weights[k])
    return asset, weights[asset]


def sector_concentration(weights: dict[str, float], asset_sectors: dict[str, str]) -> dict[str, float]:
    """Aggregate weights by sector. Assets missing from `asset_sectors` are bucketed as 'unknown'."""
    sector_weights: dict[str, float] = {}
    for asset, w in weights.items():
        sector = asset_sectors.get(asset, "unknown")
        sector_weights[sector] = sector_weights.get(sector, 0.0) + w
    return sector_weights
