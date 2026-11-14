"""Calculation tools for the finance chat.

`ANALYSIS_TOOLS` holds the Bedrock tool definitions and `run_analysis_tool`
executes one call. The finance chat loop registers both. All figures come from
`calculations.py`; this module only gathers data and formats results.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.modules.analysis import calculations as calc
from app.modules.analysis.data import AnalysisDataError, adjusted_closes, cad_rates, sector_profile, utc_now
from app.modules.chat.portfolio import Holding, portfolio_snapshot

SYMBOL = r"^[A-Za-z0-9^][A-Za-z0-9.^=-]{0,19}$"
BASE_CURRENCY = "CAD"


def pct(fraction: float | None, digits: int = 2) -> float | None:
    return None if fraction is None else round(fraction * 100, digits)


class PortfolioChoice(BaseModel):
    portfolio: Literal["mine", "hypothetical"] = Field(
        description="mine: the signed-in user's saved positions. hypothetical: weights stated in the question, "
        "used only when the user explicitly describes an example portfolio."
    )
    weights: dict[str, float] | None = Field(
        default=None, description="Percent weight per Yahoo Finance symbol. Required for a hypothetical portfolio."
    )

    @field_validator("weights")
    @classmethod
    def positive(cls, value):
        if value is not None and (not value or any(w <= 0 for w in value.values())):
            raise ValueError("Hypothetical weights must be positive.")
        return value


class TransferQuery(PortfolioChoice):
    from_ticker: str = Field(pattern=SYMBOL, description="Holding whose weight is reduced.")
    to_ticker: str = Field(pattern=SYMBOL, description="Holding or fund that receives the transfer; may be new.")
    percent: float = Field(gt=0, le=100, description="Share of the whole portfolio's value moved, in percent.")


class RiskQuery(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=10, description="Yahoo Finance symbols.")
    weights: dict[str, float] | None = Field(
        default=None, description="Optional percent weight per symbol to add a constant-weight portfolio line."
    )
    years: int = Field(default=5, ge=1, le=10, description="History length in years.")


class CoverageQuery(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=10)
    years: int = Field(default=5, ge=1, le=10)


class Amount(BaseModel):
    amount: float
    currency: str = Field(pattern=r"^[A-Za-z]{3}$")


class ConversionQuery(BaseModel):
    amounts: list[Amount] = Field(min_length=1, max_length=20)
    target: Literal["CAD", "USD"] = "CAD"


def _spec(name: str, description: str, model: type[BaseModel]) -> dict:
    return {"toolSpec": {"name": name, "description": description, "inputSchema": {"json": model.model_json_schema()}}}


ANALYSIS_TOOLS = [
    _spec("simulate_transfer", (
        "Simulate moving a percentage of the whole portfolio's value from one holding to another fund or stock. "
        "Returns weights, sector exposure and concentration before and after, in one call. "
        "Use for 'what changes if I move X% to Y' questions."
    ), TransferQuery),
    _spec("sector_exposure", "Sector weights of the current or a hypothetical portfolio, with the unclassified share.", PortfolioChoice),
    _spec("concentration", (
        "Concentration of the current or a hypothetical portfolio: largest line, top-3 weight, "
        "Herfindahl index and effective number of lines."
    ), PortfolioChoice),
    _spec("risk_history", (
        "Historical risk from daily prices adjusted for splits and dividends: total and annualized return, "
        "annualized volatility and maximum drawdown with dates, per symbol and optionally for a constant-weight "
        "portfolio. Always includes a data coverage check. Past figures do not predict future results."
    ), RiskQuery),
    _spec("check_data", (
        "Check that price histories cover the same dates and currency before comparing them. "
        "Reports gaps; never fills them."
    ), CoverageQuery),
    _spec("convert_currency", "Convert amounts with the latest Bank of Canada daily exchange rate.", ConversionQuery),
]

ANALYSIS_TOOL_NAMES = {tool["toolSpec"]["name"] for tool in ANALYSIS_TOOLS}

# Inputs worth showing in the chat's tool activity timeline.
ACTIVITY_INPUTS = {"portfolio", "from_ticker", "to_ticker", "percent", "tickers", "years", "target"}


def _portfolio_weights(choice: PortfolioChoice, holdings: list[Holding] | None) -> dict:
    """Weights of the requested portfolio, with values converted to CAD for the user's own portfolio."""
    if choice.portfolio == "hypothetical":
        if not choice.weights:
            raise ValueError("A hypothetical portfolio needs percent weights per symbol.")
        weights = calc.weights_from_values({s.upper(): w for s, w in choice.weights.items()})
        # `notes` lists data exclusions only; a hypothetical portfolio is complete by definition.
        return {"kind": "hypothetical", "weights": weights, "notes": []}

    if holdings is None:
        raise ValueError("The signed-in portfolio is not available in this conversation.")
    snapshot = portfolio_snapshot(holdings, "valuation")
    rows = [row for row in snapshot["positions"] if "value" in row]
    notes = []
    unpriced = [row["ticker"] for row in snapshot["positions"] if "value" not in row]
    if unpriced:
        notes.append("Excluded, no price or currency: " + ", ".join(unpriced) + ".")
    if snapshot["watchlist"]:
        notes.append("Excluded, tracked without a share count: " + ", ".join(snapshot["watchlist"]) + ".")
    if not rows:
        raise ValueError("No saved position has both a share count and a price.")
    rates = cad_rates({row["currency"] for row in rows})
    values = {}
    for row in rows:
        symbol = row["ticker"].upper()
        values[symbol] = values.get(symbol, 0.0) + row["value"] * rates[row["currency"].upper()]["rate"]
    fx = {c: r for c, r in rates.items() if c != BASE_CURRENCY}
    return {
        "kind": "mine",
        "weights": calc.weights_from_values(values),
        "valuesCAD": {s: round(v, 2) for s, v in values.items()},
        "totalCAD": round(sum(values.values()), 2),
        "pricesAsOf": sorted({row["asOf"] for row in rows if row.get("asOf")}),
        "exchangeRates": {c: {"cadPerUnit": r["rate"], "date": r["date"], "source": f"Bank of Canada Valet {r['series']}"}
                          for c, r in fx.items()},
        "notes": notes,
    }


def _profiles(symbols) -> tuple[dict, list[dict]]:
    profiles, sources = {}, []
    for symbol in sorted(set(symbols)):
        profile = sector_profile(symbol)
        profiles[symbol] = profile["sectors"]
        sources.append({k: profile[k] for k in ("symbol", "kind", "source", "retrieved", "note") if profile[k]})
    return profiles, sources


def _format_exposure(exposure: dict) -> dict:
    return {
        "sectorsPercent": {sector: pct(share) for sector, share in exposure["sectors"].items()},
        "unclassifiedPercent": pct(exposure["unknown"]),
        "missingProfiles": exposure["missingProfiles"],
    }


def _format_concentration(result: dict) -> dict:
    return {
        "lines": result["lines"],
        "largest": {"symbol": result["largest"]["symbol"], "weightPercent": pct(result["largest"]["weight"])},
        "top3WeightPercent": pct(result["top3Weight"]),
        "herfindahl": round(result["herfindahl"], 4),
        "effectiveLines": round(result["effectiveLines"], 2),
    }


def _weights_percent(weights: dict) -> dict:
    return {symbol: pct(weight) for symbol, weight in sorted(weights.items(), key=lambda item: item[1], reverse=True)}


def _simulate_transfer(query: TransferQuery, holdings) -> tuple[dict, str]:
    base = _portfolio_weights(query, holdings)
    source, target = query.from_ticker.upper(), query.to_ticker.upper()
    before = base["weights"]
    after = calc.apply_transfer(before, source, target, query.percent / 100)
    profiles, sources = _profiles([*before, *after])
    exposure_before = calc.sector_exposure(before, profiles)
    exposure_after = calc.sector_exposure(after, profiles)
    sectors = sorted(set(exposure_before["sectors"]) | set(exposure_after["sectors"]),
                     key=lambda s: exposure_after["sectors"].get(s, 0), reverse=True)
    change = {
        s: {"beforePercent": pct(exposure_before["sectors"].get(s, 0.0)),
            "afterPercent": pct(exposure_after["sectors"].get(s, 0.0)),
            "changePoints": pct(exposure_after["sectors"].get(s, 0.0) - exposure_before["sectors"].get(s, 0.0))}
        for s in sectors
    }
    result = {
        "scenario": {"portfolio": base["kind"], "fromTicker": source, "toTicker": target, "percentOfPortfolio": query.percent,
                     "assumptions": ["Simulation only, no trade.",
                                     *(["Hypothetical weights stated in the question, not the user's saved portfolio."]
                                       if base["kind"] == "hypothetical" else []),
                                     "The transfer is a share of the whole portfolio's value, taken from the reduced holding.",
                                     "Fund sector weights are current, not historical; holdings are assumed unchanged."]},
        "weightsPercent": {"before": _weights_percent(before), "after": _weights_percent(after)},
        "sectorExposure": {"before": _format_exposure(exposure_before), "after": _format_exposure(exposure_after),
                           "changeBySector": change},
        "concentration": {"before": _format_concentration(calc.concentration(before)),
                          "after": _format_concentration(calc.concentration(after))},
        "sectorSources": sources,
        "computed": utc_now(),
    }
    if base["kind"] == "mine":
        result["portfolioValue"] = {k: base[k] for k in ("totalCAD", "valuesCAD", "pricesAsOf", "exchangeRates")}
        result["portfolioValue"]["transferredCAD"] = round(base["totalCAD"] * query.percent / 100, 2)
    if base["notes"]:
        result["notes"] = base["notes"]
    partial = exposure_before["unknown"] > 0.005 or exposure_after["unknown"] > 0.005 or base["notes"]
    return result, "partial" if partial else "completed"


def _sector_exposure(query: PortfolioChoice, holdings) -> tuple[dict, str]:
    base = _portfolio_weights(query, holdings)
    profiles, sources = _profiles(base["weights"])
    exposure = calc.sector_exposure(base["weights"], profiles)
    result = {"portfolio": base["kind"], "weightsPercent": _weights_percent(base["weights"]),
              "sectorExposure": _format_exposure(exposure), "sectorSources": sources, "computed": utc_now()}
    if base["notes"]:
        result["notes"] = base["notes"]
    return result, "partial" if exposure["unknown"] > 0.005 or base["notes"] else "completed"


def _concentration(query: PortfolioChoice, holdings) -> tuple[dict, str]:
    base = _portfolio_weights(query, holdings)
    result = {"portfolio": base["kind"], "weightsPercent": _weights_percent(base["weights"]),
              "concentration": _format_concentration(calc.concentration(base["weights"])), "computed": utc_now()}
    if base["notes"]:
        result["notes"] = base["notes"]
    return result, "partial" if base["notes"] else "completed"


def _histories(tickers: list[str], years: int) -> dict[str, dict]:
    histories = {}
    for symbol in dict.fromkeys(t.upper().strip() for t in tickers):
        try:
            histories[symbol] = adjusted_closes(symbol, years)
        except AnalysisDataError:
            histories[symbol] = {"symbol": symbol, "dates": [], "prices": [], "currency": None}
    return histories


def _coverage(histories: dict[str, dict]) -> dict:
    metadata = {}
    for symbol, history in histories.items():
        dates = history["dates"]
        metadata[symbol] = ({"start": dates[0], "end": dates[-1], "observations": len(dates), "currency": history["currency"]}
                            if dates else {"observations": 0, "currency": history["currency"]})
    return {"series": metadata, "issues": calc.coverage_issues(metadata)}


def _check_data(query: CoverageQuery, _holdings) -> tuple[dict, str]:
    coverage = _coverage(_histories(query.tickers, query.years))
    coverage["checked"] = utc_now()
    return coverage, "partial" if coverage["issues"] else "completed"


def _risk_history(query: RiskQuery, _holdings) -> tuple[dict, str]:
    histories = _histories(query.tickers, query.years)
    coverage = _coverage(histories)
    usable = {s: h for s, h in histories.items() if len(h["dates"]) >= 2}
    if not usable:
        return {"dataCheck": coverage}, "failed"
    common = sorted(set.intersection(*(set(h["dates"]) for h in usable.values())))
    if len(common) < 2:
        return {"dataCheck": coverage, "error": "The histories have no common trading dates."}, "failed"
    aligned = {}
    for symbol, history in usable.items():
        by_date = dict(zip(history["dates"], history["prices"]))
        aligned[symbol] = [by_date[day] for day in common]

    def describe(stats: dict) -> dict:
        drawdown = stats["maxDrawdown"]
        return {
            "start": stats["start"], "end": stats["end"], "observations": stats["observations"],
            "totalReturnPercent": pct(stats["totalReturn"]),
            "annualizedReturnPercent": pct(stats["annualizedReturn"]),
            "annualizedVolatilityPercent": pct(stats["annualizedVolatility"]),
            "maxDrawdown": {"percent": pct(drawdown["value"]), "peak": drawdown["peak"], "trough": drawdown["trough"],
                            "recoveredOn": drawdown["recovered"]},
        }

    result = {
        "dataCheck": coverage,
        "commonPeriod": {"start": common[0], "end": common[-1], "tradingDays": len(common)},
        "bySymbol": {s: {"currency": usable[s]["currency"], **describe(calc.series_statistics(common, aligned[s]))}
                     for s in aligned},
        "method": ["Daily closes adjusted for splits and dividends (Yahoo Finance).",
                   "Statistics use only the trading dates common to all symbols.",
                   "Volatility is the standard deviation of daily returns times the square root of 252.",
                   "Returns are in each asset's own currency."],
        "sources": [{"symbol": h["symbol"], "source": h["source"], "retrieved": h["retrieved"]} for h in usable.values()],
    }
    if query.weights:
        weights = {s.upper(): w for s, w in query.weights.items() if s.upper() in aligned and w > 0}
        missing = sorted({s.upper() for s in query.weights} - set(weights))
        if weights:
            level = calc.constant_weight_prices(aligned, weights)
            result["portfolio"] = {"weightsPercent": _weights_percent(calc.weights_from_values(weights)),
                                   **describe(calc.series_statistics(common, level))}
            result["method"].append("The portfolio line is rebalanced to constant weights every trading day.")
        if missing:
            result["portfolioMissing"] = missing
    status = "partial" if coverage["issues"] or result.get("portfolioMissing") else "completed"
    return result, status


def _convert_currency(query: ConversionQuery, _holdings) -> tuple[dict, str]:
    currencies = {a.currency.upper() for a in query.amounts} | {query.target}
    rates = cad_rates(currencies)
    target = rates[query.target]["rate"]
    rows = []
    for item in query.amounts:
        rate = rates[item.currency.upper()]["rate"] / target
        rows.append({"amount": item.amount, "currency": item.currency.upper(), "converted": round(item.amount * rate, 2),
                     "target": query.target, "rate": round(rate, 6)})
    used = {c: {"cadPerUnit": r["rate"], "date": r["date"], "source": f"Bank of Canada Valet {r['series']}"}
            for c, r in rates.items() if c != "CAD"}
    return {"conversions": rows, "exchangeRates": used, "retrieved": utc_now()}, "completed"


_RUNNERS = {
    "simulate_transfer": (TransferQuery, _simulate_transfer),
    "sector_exposure": (PortfolioChoice, _sector_exposure),
    "concentration": (PortfolioChoice, _concentration),
    "risk_history": (RiskQuery, _risk_history),
    "check_data": (CoverageQuery, _check_data),
    "convert_currency": (ConversionQuery, _convert_currency),
}


def run_analysis_tool(name: str, arguments: dict, holdings: list[Holding] | None) -> tuple[dict, str]:
    """Run one calculation tool. Returns (evidence for the model, activity status)."""
    model, runner = _RUNNERS[name]
    try:
        return runner(model.model_validate(arguments), holdings)
    except (ValueError, AnalysisDataError) as error:
        return {"error": str(error).splitlines()[0][:300], "input": arguments}, "failed"
