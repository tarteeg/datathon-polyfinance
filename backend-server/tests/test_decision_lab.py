from math import sqrt

import pandas as pd
import pytest
from pydantic import ValidationError

from app.modules.analysis import data
from app.modules.decision_lab import service
from app.modules.decision_lab.schemas import LabRequest

DATES = ["2021-12-31", "2022-01-03", "2022-01-04"]


def request(**changes):
    return LabRequest.model_validate({
        "weights": {"SPY": 60, "TLT": 40}, "asset": "TLT", "shock_pct": -13,
        "loss_limit_pct": 5, "end": DATES[-1], **changes,
    })


def history(prices):
    return {"dates": DATES, "prices": prices, "currency": "USD", "retrieved": "test"}


def test_rebalanced_path_attribution_drawdown_and_sample_volatility():
    # Day 1: .6 * 10% + .4 * 0% = 6%. Day 2: .6 * -10% + .4 * 5% = -4%.
    histories = {"SPY": history([100, 110, 99]), "TLT": history([100, 100, 105])}
    result = service.replay(request(), DATES, histories)
    assert [p.usd for p in result.series] == pytest.approx([10000, 10600, 10176])
    assert result.total_return_pct == pytest.approx(1.76)
    assert result.contributions_pp == pytest.approx({"SPY": -0.36, "TLT": 2.12})
    assert result.volatility_pct == pytest.approx(10 / sqrt(2) * sqrt(252))
    assert result.max_drawdown_pct == pytest.approx(-4)
    assert (result.peak, result.trough) == tuple(DATES[1:])
    assert result.correlation == pytest.approx(-1)


@pytest.mark.parametrize("shock,status,usd", [(-10, "within", -400), (-12.5, "at", -500), (-13, "beyond", -520)])
def test_reverse_stress(shock, status, usd):
    result = service.stress(request(shock_pct=shock))
    assert result.threshold_shock_pct == -12.5
    assert result.impact_usd == usd
    assert result.status == status


@pytest.mark.parametrize("weight,threshold", [(0, None), (4, None), (5, -100)])
def test_impossible_breach(weight, threshold):
    result = service.stress(request(weights={"SPY": 100-weight, "TLT": weight}, shock_pct=-100))
    assert result.threshold_shock_pct == threshold
    assert not result.can_exceed


@pytest.mark.parametrize("change", [
    {"weights": {"SPY": 60, "TLT": 35}}, {"weights": {"SPY": 101, "TLT": -1}},
    {"currency": "CAD"}, {"shock_pct": -101}, {"loss_limit_pct": 0}, {"start": "2023-01-01"},
])
def test_invalid_inputs(change):
    with pytest.raises(ValidationError):
        request(**change)


@pytest.mark.parametrize("bad", [
    {"dates": DATES[1:], "prices": [100, 101]}, {"dates": DATES[::2], "prices": [100, 101]},
    {"currency": "CAD"}, {"prices": [100, float("nan"), 101]},
])
def test_missing_baseline_session_currency_or_price(monkeypatch, bad):
    monkeypatch.setattr(service, "adjusted_closes_between", lambda s, *_:
                        history([100, 100, 105]) | (bad if s == "TLT" else {}))
    result = service.analyze(request())
    assert result.replay is None and result.replay_error
    assert result.scenario.impact_usd == -520


def test_no_trading_sessions():
    result = service.analyze(request(start="2022-01-01", end="2022-01-02"))
    assert result.replay is None and "two trading days" in result.replay_error


def test_personas_receive_identical_calculations(monkeypatch):
    monkeypatch.setattr(service, "adjusted_closes_between", lambda *_: history([100, 100, 100]))
    results = [service.analyze(request(persona=p)) for p in ["Robert", "Amira", "Mateo"]]
    assert results[0].replay.correlation is None
    assert results[0] == results[1] == results[2]


def test_adjusted_adapter_avoids_false_distribution_loss(monkeypatch):
    class Ticker:
        history_metadata = {"currency": "USD"}

        def history(self, *, auto_adjust, **kwargs):
            # A $5 distribution reduces the raw close; reinvested wealth is flat.
            closes = [95, 95, 95] if auto_adjust else [100, 95, 95]
            return pd.DataFrame({"Close": closes}, index=pd.to_datetime(DATES))

    monkeypatch.setattr(data.yf, "Ticker", lambda _: Ticker())
    monkeypatch.setattr(data, "_cache", {})
    prices = data.adjusted_closes_between("TLT", DATES[0], "2022-01-05")
    result = service.replay(request(), DATES, {"SPY": history([100]*3), "TLT": prices})
    assert result.total_return_pct == result.max_drawdown_pct == 0


def test_bedrock_stream_accepts_a_tool_call_without_arguments(monkeypatch):
    from app.modules.chat import routes

    class Stream(list):
        def close(self):
            pass

    class Client:
        def converse_stream(self, **kwargs):
            return {"stream": Stream([
                {"contentBlockStart": {"contentBlockIndex": 0, "start": {
                    "toolUse": {"toolUseId": "call1", "name": "analyze_breakpoint"}}}},
                {"messageStop": {"stopReason": "tool_use"}},
            ])}

    monkeypatch.setattr(routes, "bedrock", Client)
    with pytest.raises(StopIteration) as stop:
        next(routes.model_events({}, {}, True))
    assert stop.value.value[1] == [{"toolUseId": "call1", "name": "analyze_breakpoint", "input": {}}]
