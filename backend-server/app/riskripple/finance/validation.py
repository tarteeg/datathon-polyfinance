"""Data integrity checks for price series, per docs/FINANCIAL_MODELS.md section on data integrity.

These checks reject or qualify invalid analyses rather than silently calculating on bad data.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .errors import FinanceDataError

MIN_OBSERVATIONS_FOR_ANNUALIZATION = 20


@dataclass
class ValidationReport:
    series_name: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def validate_price_series(prices: pd.Series, *, name: str = "series", min_observations: int = MIN_OBSERVATIONS_FOR_ANNUALIZATION) -> ValidationReport:
    """Validate a single adjusted-close price series indexed by date.

    Checks: missing values, duplicate timestamps, nonpositive prices, date ordering,
    insufficient history. Does not mutate the input.
    """
    report = ValidationReport(series_name=name)

    if prices.empty:
        report.errors.append("series is empty")
        return report

    if not isinstance(prices.index, pd.DatetimeIndex):
        report.errors.append("index is not a DatetimeIndex")
        return report

    if prices.index.has_duplicates:
        dupes = prices.index[prices.index.duplicated()].unique()
        report.errors.append(f"duplicate timestamps: {list(dupes)[:5]}")

    if not prices.index.is_monotonic_increasing:
        report.errors.append("index is not sorted in ascending date order")

    if prices.isna().any():
        n_missing = int(prices.isna().sum())
        report.warnings.append(f"{n_missing} missing price observation(s)")

    non_na = prices.dropna()
    if (non_na <= 0).any():
        n_bad = int((non_na <= 0).sum())
        report.errors.append(f"{n_bad} nonpositive price observation(s)")

    if len(non_na) < min_observations:
        report.errors.append(
            f"insufficient history: {len(non_na)} observations, need at least {min_observations}"
        )

    return report


def validate_currency_consistency(currencies: dict[str, str]) -> ValidationReport:
    """Check that all assets in a basket report the same currency.

    Mixed-currency baskets are not an error per se, but portfolio-level return and
    volatility calculations assume a single base currency, so this must be surfaced
    explicitly rather than silently summed.
    """
    report = ValidationReport(series_name="currency_consistency")
    unique = set(currencies.values())
    if len(unique) > 1:
        report.warnings.append(
            f"mixed currencies across assets: {currencies}. "
            "Portfolio-level metrics assume a single base currency; convert before aggregating."
        )
    return report


def require_valid(report: ValidationReport) -> None:
    """Raise if a validation report contains errors. Call before any downstream calculation."""
    if not report.is_valid:
        raise FinanceDataError(
            f"validation failed for '{report.series_name}': {'; '.join(report.errors)}"
        )
