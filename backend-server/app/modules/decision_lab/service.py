from datetime import date, timedelta
from math import isclose, isfinite
from statistics import StatisticsError, correlation

import exchange_calendars as calendars

from app.modules.analysis import calculations as calc
from app.modules.analysis.data import AnalysisDataError, adjusted_closes_between
from .schemas import LabRequest, LabResult, Replay, Scenario, Status


def limit_status(loss_pct: float, limit_pct: float) -> Status:
    if isclose(loss_pct, limit_pct, rel_tol=1e-12):
        return "at"
    return "beyond" if loss_pct > limit_pct else "within"


def stress(q: LabRequest) -> Scenario:
    weight = q.weights[q.asset] / 100
    impact = weight * q.shock_pct
    maximum = limit_status(q.weights[q.asset], q.loss_limit_pct)
    return Scenario(
        impact_pct=impact, impact_usd=q.principal * impact / 100,
        limit_usd=q.principal * q.loss_limit_pct / 100,
        threshold_shock_pct=-min(100, q.loss_limit_pct / weight) if maximum != "within" and weight else None,
        can_exceed=maximum == "beyond", status=limit_status(-impact, q.loss_limit_pct),
    )


def replay(q: LabRequest, dates: list[str], histories: dict) -> Replay:
    if len(dates) < 3:
        raise AnalysisDataError("At least two trading days and their preceding close are required.")
    prices = {}
    for symbol, history in histories.items():
        if history["currency"] != q.currency:
            raise AnalysisDataError(f"{symbol} has missing or incompatible currency. USD prices are required.")
        observed = dict(zip(history["dates"], history["prices"], strict=True))
        for day in dates:
            price = observed.get(day)
            if price is None or not isfinite(price) or price <= 0:
                raise AnalysisDataError(f"{symbol} is missing a usable adjusted close on {day}.")
        prices[symbol] = [observed[day] for day in dates]

    weights = {s: w / 100 for s, w in q.weights.items()}
    levels = calc.constant_weight_prices(prices, weights)
    metrics = calc.series_statistics(dates, levels)
    returns = {s: calc.daily_returns(p) for s, p in prices.items()}
    # Prior day's portfolio index starts at 100, so these amounts are percentage points.
    contributions = {s: sum(level * weights[s] * r for level, r in zip(levels[:-1], daily))
                     for s, daily in returns.items()}
    try:
        corr = correlation(returns["SPY"], returns["TLT"])
    except StatisticsError:
        corr = None
    drawdown = metrics["maxDrawdown"]
    return Replay(
        total_return_pct=100 * metrics["totalReturn"], volatility_pct=100 * metrics["annualizedVolatility"],
        max_drawdown_pct=100 * drawdown["value"], peak=drawdown["peak"], trough=drawdown["trough"],
        drawdown_status=limit_status(-100 * drawdown["value"], q.loss_limit_pct),
        contributions_pp=contributions, correlation=corr,
        series=[{"date": d, "usd": q.principal * level / 100} for d, level in zip(dates, levels)],
        retrieved={s: h["retrieved"] for s, h in histories.items()},
        sources={s: f"https://finance.yahoo.com/quote/{s}/history/" for s in prices},
        trading_days=len(dates)-1, baseline=dates[0], last_close=dates[-1],
    )


def analyze(q: LabRequest) -> LabResult:
    calendar = calendars.get_calendar("XNYS", start="2002-01-01", end=f"{date.today().year + 1}-01-01")
    sessions = calendar.sessions_in_range(q.start.isoformat(), q.end.isoformat())
    scenario = stress(q)
    try:
        if len(sessions) < 2:
            raise AnalysisDataError("Select a period containing at least two trading days.")
        dates = [calendar.previous_session(sessions[0]).date().isoformat(), *sessions.strftime("%Y-%m-%d")]
        end_exclusive = (q.end + timedelta(days=1)).isoformat()
        histories = {s: adjusted_closes_between(s, dates[0], end_exclusive) for s in q.weights}
        return LabResult(scenario=scenario, replay=replay(q, dates, histories), replay_error=None)
    except AnalysisDataError as error:
        return LabResult(scenario=scenario, replay=None, replay_error=str(error))
