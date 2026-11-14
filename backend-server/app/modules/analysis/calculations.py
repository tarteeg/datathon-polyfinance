"""Deterministic portfolio calculations used by the finance chat tools.

Every function here is pure: no network, no clock, no model. Weights are
fractions that sum to 1. Sector profiles map a normalized sector name to its
share of a holding, also as a fraction.
"""

from math import sqrt

TRADING_DAYS = 252
# A weight this close to zero is treated as an empty position (rounding noise).
EPSILON = 1e-9


def weights_from_values(values: dict[str, float]) -> dict[str, float]:
    """Convert position values in a single currency into weights."""
    total = sum(values.values())
    if total <= 0:
        raise ValueError("The portfolio has no positive value to weight.")
    return {symbol: value / total for symbol, value in values.items()}


def apply_transfer(weights: dict[str, float], from_symbol: str, to_symbol: str, fraction: float) -> dict[str, float]:
    """Move `fraction` of the whole portfolio's value from one line to another.

    The destination may be a new line. Weights still sum to 1 afterwards.
    """
    if from_symbol not in weights:
        raise ValueError(f"{from_symbol} is not in the portfolio.")
    if from_symbol == to_symbol:
        raise ValueError("The reduced and added symbols must differ.")
    if not 0 < fraction <= 1:
        raise ValueError("The transfer must be between 0 and 100 percent of the portfolio.")
    if fraction > weights[from_symbol] + EPSILON:
        raise ValueError(
            f"The transfer ({fraction:.2%}) exceeds the weight of {from_symbol} ({weights[from_symbol]:.2%})."
        )
    after = dict(weights)
    after[from_symbol] = max(after[from_symbol] - fraction, 0.0)
    after[to_symbol] = after.get(to_symbol, 0.0) + fraction
    return {symbol: weight for symbol, weight in after.items() if weight > EPSILON}


def sector_exposure(weights: dict[str, float], profiles: dict[str, dict[str, float] | None]) -> dict:
    """Weight of each sector across the portfolio.

    A holding without a known profile contributes to `unknown` instead of
    being guessed. A profile that sums to less than 1 (cash, unclassified
    assets) also leaves the remainder as unknown.
    """
    sectors: dict[str, float] = {}
    unknown = 0.0
    missing = []
    for symbol, weight in weights.items():
        profile = profiles.get(symbol)
        if not profile:
            unknown += weight
            missing.append(symbol)
            continue
        covered = 0.0
        for sector, share in profile.items():
            sectors[sector] = sectors.get(sector, 0.0) + weight * share
            covered += share
        unknown += weight * max(1.0 - covered, 0.0)
    ordered = dict(sorted(sectors.items(), key=lambda item: item[1], reverse=True))
    return {"sectors": ordered, "unknown": unknown, "missingProfiles": missing}


def concentration(weights: dict[str, float]) -> dict:
    """Largest line, top-3 weight, Herfindahl index and effective number of lines."""
    if not weights:
        raise ValueError("The portfolio is empty.")
    ordered = sorted(weights.items(), key=lambda item: item[1], reverse=True)
    herfindahl = sum(weight * weight for weight in weights.values())
    return {
        "lines": len(weights),
        "largest": {"symbol": ordered[0][0], "weight": ordered[0][1]},
        "top3Weight": sum(weight for _, weight in ordered[:3]),
        "herfindahl": herfindahl,
        "effectiveLines": 1 / herfindahl,
    }


def daily_returns(prices: list[float]) -> list[float]:
    return [current / previous - 1 for previous, current in zip(prices, prices[1:])]


def series_statistics(dates: list[str], prices: list[float]) -> dict:
    """Total return, annualized return and volatility, and maximum drawdown of one price series."""
    if len(prices) < 2 or len(prices) != len(dates):
        raise ValueError("At least two dated prices are required.")
    if any(price <= 0 for price in prices):
        raise ValueError("Prices must be positive.")
    returns = daily_returns(prices)
    years = len(returns) / TRADING_DAYS
    total = prices[-1] / prices[0] - 1
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1) if len(returns) > 1 else 0.0

    peak_index = 0
    worst = 0.0
    worst_peak = worst_trough = 0
    for index, price in enumerate(prices):
        if price > prices[peak_index]:
            peak_index = index
        drawdown = price / prices[peak_index] - 1
        if drawdown < worst:
            worst, worst_peak, worst_trough = drawdown, peak_index, index
    recovery = None
    if worst < 0:
        recovery = next((dates[i] for i in range(worst_trough + 1, len(prices)) if prices[i] >= prices[worst_peak]), None)

    return {
        "start": dates[0],
        "end": dates[-1],
        "observations": len(prices),
        "totalReturn": total,
        "annualizedReturn": (1 + total) ** (1 / years) - 1 if years > 0 else None,
        "annualizedVolatility": sqrt(variance) * sqrt(TRADING_DAYS),
        "maxDrawdown": {
            "value": worst,
            "peak": dates[worst_peak],
            "trough": dates[worst_trough],
            "recovered": recovery,
        },
    }


def constant_weight_prices(series: dict[str, list[float]], weights: dict[str, float]) -> list[float]:
    """Index (start = 100) of a portfolio rebalanced to constant weights every day.

    All series must be aligned on the same dates.
    """
    symbols = list(weights)
    length = len(series[symbols[0]])
    if any(len(series[symbol]) != length for symbol in symbols):
        raise ValueError("Series must be aligned on the same dates.")
    total = sum(weights.values())
    level = [100.0]
    for day in range(1, length):
        change = sum(weights[s] / total * (series[s][day] / series[s][day - 1] - 1) for s in symbols)
        level.append(level[-1] * (1 + change))
    return level


def coverage_issues(metadata: dict[str, dict]) -> list[str]:
    """Problems that make a comparison between series unreliable.

    `metadata` maps a symbol to {"start", "end", "observations", "currency"};
    a symbol with no data maps to {"observations": 0}.
    """
    issues = []
    available = {symbol: meta for symbol, meta in metadata.items() if meta.get("observations", 0) >= 2}
    for symbol in metadata:
        if symbol not in available:
            issues.append(f"No usable price history for {symbol}.")
    if len(available) >= 2:
        starts = {meta["start"] for meta in available.values()}
        ends = {meta["end"] for meta in available.values()}
        if len(starts) > 1:
            latest = max(available.items(), key=lambda item: item[1]["start"])
            issues.append(f"Histories start on different dates; the shortest starts on {latest[1]['start']} ({latest[0]}).")
        if len(ends) > 1:
            issues.append("Histories end on different dates.")
        currencies = {meta.get("currency") for meta in available.values()}
        if len(currencies) > 1:
            issues.append(
                "Series are quoted in different currencies (" + ", ".join(sorted(str(c) for c in currencies)) + "); "
                "returns are in each asset's own currency and exclude exchange-rate effects."
            )
    return issues
